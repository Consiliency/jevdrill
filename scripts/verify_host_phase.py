"""Collect one native HOST receipt with the pinned companion, or reduce one run's receipts.

A receipt is collected on a hosted runner of one `host.yml` run. It holds the inherited ROUTE
regressions (with the HOST controls added to their test command), the companion's own tests
at the handoff's commit, and the witness the conformance fixture writes. The reduction accepts
exactly three receipts of the workflow run it is part of. A local collection is a diagnostic:
it is never uploaded and no reduction accepts it.
"""

import argparse
import contextlib
import hashlib
import importlib.util
import json
import math
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "evidence/HOST"
_route_spec = importlib.util.spec_from_file_location(
    "host_route_regressions", ROOT / "scripts/verify_route_phase.py"
)
route = importlib.util.module_from_spec(_route_spec)
_route_spec.loader.exec_module(route)

SCHEMA_VERSION = 3
MATRIX = route.MATRIX
PLATFORMS = ("Linux", "Darwin", "Windows")
COLLECTION_BOUND_SECONDS = 600
PROOF_COST_TARGET_SECONDS = 300
# The Python the companion's own CI tests (HOST plan, R6 and J7). The workflow syncs the
# companion on it, and the receipt records it.
COMPANION_PYTHON = "3.12"
# The one marker deselected from the companion's tests (HOST plan, R4 and J6). It is bound
# in the command, and so in the command digest.
DESELECTION = ("-m", "not dotfiles_integration")
COMPANION_FILES = (
    "test_jevdrill_adapter.py",
    "test_jevdrill_queue.py",
    "test_phase_loop_launcher.py",
    "test_phase_loop_work_unit_observability.py",
    "test_jevdrill_input.py",
    "test_jevdrill_usage.py",
    "test_jevdrill_diagnostics.py",
)
# Left out of the companion command off Linux, as at the tag: usage capture is Linux-only.
LINUX_ONLY_COMPANION_FILES = (
    "test_jevdrill_input.py",
    "test_jevdrill_usage.py",
    "test_jevdrill_diagnostics.py",
)
# The conformance fixture's discovery child (tests/conformance/conftest.py), normalized.
DISCOVERY_COMMAND = (
    "<python>",
    "-m",
    "pytest",
    "-v",
    "--override-ini=addopts=",
    *DESELECTION,
    "tests/test_jevdrill_discovery.py",
    "--junitxml=<temporary>/discovery.xml",
    "--basetemp=<temporary>/discovery-child",
)
HOST_STATIC_COMMAND = (
    "<python>",
    "-m",
    "ruff",
    "check",
    "tests/conformance",
    "research/evaluation/host",
)
# The companion's contract copies (HOST plan, R2 and J5). Each schema copy equals its
# namesake in schemas/; each fixture copy equals its namesake in tests/contracts/fixtures/
# once the placeholder is replaced, in the companion's copy only.
CONTRACT_DIRECTORY = "tests/fixtures/jevdrill"
CONTRACT_SCHEMAS = (
    "DeleteRequest.json",
    "DiscoveryDeleteRequest.json",
    "DiscoveryInputs.json",
    "DiscoveryInspectRequest.json",
    "DiscoveryRef.json",
    "DiscoveryResult.json",
    "DiscoveryRouteInputs.json",
    "ExecutionRun.json",
    "NoticeInbox.json",
    "NoticeRequest.json",
    "ReportAcknowledgment.json",
    "ReportRequest.json",
    "RouteInputs.json",
    "RoutingDecision.json",
)
CONTRACT_FIXTURES = ("discovery.json", "host.json", "route-inputs.json")
TOKEN_COUNTER_PLACEHOLDER = b"<jev-token-counter-revision>"
TOKEN_COUNTER_REVISION = b"utf8-bytes-upper-bound-v1"

# The only parent variables a child sees, as in tests/conformance/conftest.py: what an
# interpreter needs to start on Linux, macOS and Windows. Everything else is set by name.
INHERITED_VARIABLES = (
    "PATH",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TMPDIR",
    "TEMP",
    "TMP",
    "SYSTEMROOT",
    "SystemRoot",
    "WINDIR",
    "COMSPEC",
    "PATHEXT",
)
# The ROUTE regression checks also build the package, run npm's consumer and name the run,
# as route.yml's do: they keep the runner's home and caches, the run id and the compiler.
ROUTE_INHERITED_VARIABLES = (
    *INHERITED_VARIABLES,
    "HOME",
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
    "XDG_CACHE_HOME",
    "UV_CACHE_DIR",
    "RUNNER_TEMP",
    "GITHUB_RUN_ID",
    "BAML_CLI",
)
# The one behaviour switch the collector sets: it activates the two JD-084 launcher tests,
# which skip without it (HOST plan, "Readings and points settled").
SCHEDULER_SWITCH = {"PHASE_LOOP_TDD_EXPECT_SCHED": "1"}

REQUIREMENTS = {f"EC-HOST-{number}" for number in range(1, 5)} | {"IF-0-HOST-1", "IF-0-VC-2"}

# Every JEV Drill control the clause tables name, with its exact case count. Each runs in the
# inherited ROUTE test command on all three platforms. A changed count is a declared change.
CONTROL_COUNTS = {
    "tests/analysis/test_observations.py::test_missing_failed_canceled_corrected_and_unknown_observations": 1,
    "tests/analysis/test_observations.py::test_substitution_preference_and_evaluation_are_distinct": 1,
    "tests/application/test_application.py::test_report_is_a_versioned_durable_acknowledgment": 1,
    "tests/application/test_discovery_application.py::test_bad_links_never_enter_prepare": 8,
    "tests/application/test_discovery_application.py::test_public_discovery_two_independent_tasks_and_replay": 1,
    "tests/application/test_host_notices.py::test_notice_snapshots_do_not_mutate_retry_or_replay": 1,
    "tests/application/test_host_routing.py::test_capability_mismatch_carries_supported_refresh_advice": 2,
    "tests/application/test_host_routing.py::test_dry_run_is_never_ordered_by_learned_policy": 2,
    "tests/application/test_host_routing.py::test_recursion_bypass_makes_no_judgment_call": 2,
    "tests/application/test_route_integration.py::test_builtin_task_judgment_keeps_verified_spending_bounds": 2,
    "tests/application/test_route_integration.py::test_retry_requires_recorded_run_and_remaining_attempt_authority": 1,
    "tests/conformance/test_discovery_handoff.py::test_entered_reference_deletion_revision_and_policy_controls": 1,
    "tests/conformance/test_discovery_handoff.py::test_installed_discovery_harness_planning_two_independent_tasks": 1,
    "tests/conformance/test_discovery_handoff.py::test_installed_flow_carries_a_judged_task": 1,
    "tests/conformance/test_launch_paths.py::test_entered_permission_expansion_denials": 1,
    "tests/conformance/test_launch_paths.py::test_independent_checks_reject_entered_routed_artifacts": 1,
    "tests/conformance/test_launch_paths.py::test_real_main_delegated_lane_constructors": 1,
    "tests/conformance/test_notices.py::test_every_report_connection_queries_notices": 1,
    "tests/conformance/test_notices.py::test_pending_notice_reaches_the_notice_sink": 1,
    "tests/conformance/test_transport_queue.py::test_entered_ack_loss_and_cross_producer_deletion": 1,
    "tests/conformance/test_usage_reporting.py::test_installed_usage_persistence": 11,
    "tests/contracts/test_host_contracts.py::test_host_shared_contract": 28,
    "tests/evaluation/test_host_acceptance.py::test_frozen_groups_are_disjoint_and_holdouts_unopened": 1,
    "tests/evaluation/test_host_acceptance.py::test_independent_controlled_artifact_checks": 6,
    "tests/privacy/test_round41_learning.py::test_report_sensitive_map_key_rejects_before_persistence": 1,
    "tests/privacy/test_sink_proof.py::test_a_report_with_a_refused_identifier_is_refused_before_it_is_stored": 2,
    "tests/storage/test_dry_run_evidence.py::test_cached_decision_is_reused_only_when_its_mode_matches": 4,
    "tests/storage/test_dry_run_evidence.py::test_no_dry_run_becomes_an_observation": 22,
    "tests/storage/test_dry_run_evidence.py::test_routing_and_storage_share_the_dry_run_code": 1,
    "tests/storage/test_host_notices.py::test_notice_scope_reads_and_cross_producer_deletion": 1,
    "tests/verification/test_host_phase.py::test_missing_companion_configuration_is_failure": 1,
    "tests/verification/test_host_phase.py::test_reducer_accepts_valid_receipts": 1,
    "tests/verification/test_host_phase.py::test_reducer_rejects_invalid_receipts": 41,
}
_ALL = {name: None for name in PLATFORMS}
_LINUX = {"Linux": None}
# Every host-integration control the clause tables name, with its exact count on each platform
# whose companion command selects its file (ids relative to phase-loop-runtime/).
_COMPANION = {
    "tests/test_jevdrill_adapter.py::test_dry_run_and_recursion_bypass_do_not_route": (1, _ALL),
    "tests/test_jevdrill_adapter.py::test_forged_capability_or_candidate_cannot_expand_authority": (
        1,
        _ALL,
    ),
    "tests/test_jevdrill_adapter.py::test_guidance_is_verified_injected_once_and_deactivated": (
        1,
        _ALL,
    ),
    "tests/test_jevdrill_adapter.py::test_no_requested_ceiling_does_not_require_token_enforcement": (
        1,
        _ALL,
    ),
    "tests/test_jevdrill_adapter.py::test_observed_substitution_is_not_attributed_to_selected_plan": (
        1,
        _ALL,
    ),
    "tests/test_jevdrill_adapter.py::test_override_staleness_and_final_token_enforcement": (
        1,
        _ALL,
    ),
    "tests/test_jevdrill_adapter.py::test_production_sanitizer_rejects_raw_fields_and_erases_free_text": (
        1,
        _ALL,
    ),
    "tests/test_jevdrill_adapter.py::test_real_runner_construction_sites_reach_bridge": (3, _ALL),
    "tests/test_jevdrill_adapter.py::test_requested_ceiling_rejects_unproven_executor_limits": (
        3,
        _ALL,
    ),
    "tests/test_jevdrill_queue.py::test_acknowledgment_loss_replays_exact_report": (1, _ALL),
    "tests/test_jevdrill_queue.py::test_only_matching_durable_acknowledgment_removes_report": (
        2,
        _ALL,
    ),
    "tests/test_jevdrill_queue.py::test_overflow_and_expiry_have_persistent_loss_counters": (
        1,
        _ALL,
    ),
    "tests/test_jevdrill_queue.py::test_process_crash_windows_recover_durable_reports": (3, _ALL),
    "tests/test_jevdrill_usage.py::test_incomplete_drain_is_unknown_and_bounded": (1, _LINUX),
    "tests/test_phase_loop_launcher.py::test_launcher_accepts_explicit_nonserialized_lease_authority": (
        1,
        _ALL,
    ),
    "tests/test_phase_loop_launcher.py::test_supervised_launch_drains_retained_stdout_before_returning": (
        1,
        _ALL,
    ),
}
COMPANION_CONTROL_COUNTS = {
    node: {name: count for name in platforms} for node, (count, platforms) in _COMPANION.items()
}
# Every case the companion command selects, by platform: the whole selection is exact.
COMPANION_TOTALS = {"Linux": 215, "Darwin": 79, "Windows": 79}
# Host-integration controls in the conformance fixture's discovery child, on every platform.
DISCOVERY_CONTROL_COUNTS = {
    "tests/test_jevdrill_discovery.py::test_entered_discovery_requires_harness_decomposition": 1,
    "tests/test_jevdrill_discovery.py::test_entered_linked_launch_rejections": 5,
    "tests/test_jevdrill_discovery.py::test_entered_linked_launch_rejections[decline]": 1,
    "tests/test_jevdrill_discovery.py::test_installed_discovery_decomposition_two_task_launch": 2,
    "tests/test_jevdrill_discovery.py::test_installed_discovery_status_gates_planning[no_optional_guidance]": 1,
    "tests/test_jevdrill_discovery.py::test_native_unsupported_observer_records_unknown_capture": 1,
}
DISCOVERY_TOTAL = 14
# The probe child's cases (Consiliency/jevdrill#114), as the witness names them.
PROBE_COUNTS = {
    "research/evaluation/host/test_baseline_probe.py::test_paired_baseline": 18,
    "research/evaluation/host/test_baseline_probe.py::test_routed_negative_control": 2,
    "research/evaluation/host/test_bridge_probe.py::test_installed_flow_carries_a_judged_task": 1,
    "research/evaluation/host/test_bridge_probe.py::test_real_bridge": 14,
}
PROBE_TOTAL = 35

_C = "tests/conformance/"
_A = "tests/test_jevdrill_adapter.py::"
_Q = "tests/test_jevdrill_queue.py::"
_D = "tests/test_jevdrill_discovery.py::"
_L = "tests/test_phase_loop_launcher.py::"
_TWO_TASKS = (
    _C
    + "test_discovery_handoff.py::test_installed_discovery_harness_planning_two_independent_tasks"
)
_LINKS = (
    _C + "test_discovery_handoff.py::test_entered_reference_deletion_revision_and_policy_controls"
)
_ROUTED = _C + "test_launch_paths.py::test_independent_checks_reject_entered_routed_artifacts"
_FROZEN = "tests/evaluation/test_host_acceptance.py::test_frozen_groups_are_disjoint_and_holdouts_unopened"
_SUBSTITUTION = (
    "tests/analysis/test_observations.py::test_substitution_preference_and_evaluation_are_distinct"
)
_USAGE = _C + "test_usage_reporting.py::test_installed_usage_persistence"
_ROUTING = "tests/application/test_host_routing.py::"
# Each clause of the plan's tables: its criterion, whether it is covered, and its controls.
# A partly covered clause is split, so that its uncovered half stands as its own clause.
CLAUSES = {
    "EC-HOST-1/validated-plans": (
        "EC-HOST-1",
        "covered",
        (
            _C + "test_launch_paths.py::test_real_main_delegated_lane_constructors",
            _A + "test_real_runner_construction_sites_reach_bridge",
        ),
    ),
    "EC-HOST-1/substitutions": (
        "EC-HOST-1",
        "covered",
        (_SUBSTITUTION, _A + "test_observed_substitution_is_not_attributed_to_selected_plan"),
    ),
    "EC-HOST-1/permissions": (
        "EC-HOST-1",
        "covered",
        (
            _C + "test_launch_paths.py::test_entered_permission_expansion_denials",
            _A + "test_forged_capability_or_candidate_cannot_expand_authority",
        ),
    ),
    "EC-HOST-1/recursion": (
        "EC-HOST-1",
        "covered",
        (
            _ROUTING + "test_recursion_bypass_makes_no_judgment_call",
            _A + "test_dry_run_and_recursion_bypass_do_not_route",
        ),
    ),
    "EC-HOST-1/rerouting-context-bound": (
        "EC-HOST-1",
        "covered",
        (
            "tests/application/test_route_integration.py::test_retry_requires_recorded_run_and_remaining_attempt_authority",
        ),
    ),
    "EC-HOST-1/rerouting-context-host": ("EC-HOST-1", "not_covered", ()),
    "EC-HOST-1/guidance-once": (
        "EC-HOST-1",
        "covered",
        (_A + "test_guidance_is_verified_injected_once_and_deactivated",),
    ),
    "EC-HOST-1/deactivation": (
        "EC-HOST-1",
        "covered",
        (_A + "test_guidance_is_verified_injected_once_and_deactivated",),
    ),
    "EC-HOST-1/host-limitations": ("EC-HOST-1", "not_covered", ()),
    "EC-HOST-1/dry-run-ordering": (
        "EC-HOST-1",
        "covered",
        (
            _ROUTING + "test_dry_run_is_never_ordered_by_learned_policy",
            _A + "test_dry_run_and_recursion_bypass_do_not_route",
        ),
    ),
    "EC-HOST-1/dry-run-counting": (
        "EC-HOST-1",
        "covered",
        (
            "tests/storage/test_dry_run_evidence.py::test_cached_decision_is_reused_only_when_its_mode_matches",
            "tests/storage/test_dry_run_evidence.py::test_no_dry_run_becomes_an_observation",
            "tests/storage/test_dry_run_evidence.py::test_routing_and_storage_share_the_dry_run_code",
        ),
    ),
    "EC-HOST-2/one-queue": (
        "EC-HOST-2",
        "covered",
        (
            _Q + "test_overflow_and_expiry_have_persistent_loss_counters",
            _C + "test_transport_queue.py::test_entered_ack_loss_and_cross_producer_deletion",
        ),
    ),
    "EC-HOST-2/explicit-reports-same-queue": ("EC-HOST-2", "not_covered", ()),
    "EC-HOST-2/redaction": (
        "EC-HOST-2",
        "covered",
        (
            "tests/privacy/test_round41_learning.py::test_report_sensitive_map_key_rejects_before_persistence",
            "tests/privacy/test_sink_proof.py::test_a_report_with_a_refused_identifier_is_refused_before_it_is_stored",
            _A + "test_production_sanitizer_rejects_raw_fields_and_erases_free_text",
            _USAGE,
        ),
    ),
    "EC-HOST-2/acknowledgments": (
        "EC-HOST-2",
        "covered",
        (
            "tests/application/test_application.py::test_report_is_a_versioned_durable_acknowledgment",
            _Q + "test_acknowledgment_loss_replays_exact_report",
            _Q + "test_process_crash_windows_recover_durable_reports",
            _Q + "test_only_matching_durable_acknowledgment_removes_report",
        ),
    ),
    "EC-HOST-2/mismatch-advice": (
        "EC-HOST-2",
        "covered",
        (_ROUTING + "test_capability_mismatch_carries_supported_refresh_advice",),
    ),
    "EC-HOST-2/disconnect-advice": ("EC-HOST-2", "not_covered", ()),
    "EC-HOST-2/host-choices": ("EC-HOST-2", "covered", (_SUBSTITUTION,)),
    "EC-HOST-2/unknown-telemetry": (
        "EC-HOST-2",
        "covered",
        (
            "tests/analysis/test_observations.py::test_missing_failed_canceled_corrected_and_unknown_observations",
            "tests/test_jevdrill_usage.py::test_incomplete_drain_is_unknown_and_bounded",
            _D + "test_native_unsupported_observer_records_unknown_capture",
            _USAGE,
        ),
    ),
    "EC-HOST-2/pending-notices": (
        "EC-HOST-2",
        "covered",
        (
            "tests/storage/test_host_notices.py::test_notice_scope_reads_and_cross_producer_deletion",
            "tests/application/test_host_notices.py::test_notice_snapshots_do_not_mutate_retry_or_replay",
            _C + "test_notices.py::test_every_report_connection_queries_notices",
            _C + "test_notices.py::test_pending_notice_reaches_the_notice_sink",
        ),
    ),
    "EC-HOST-3/contract-suites": (
        "EC-HOST-3",
        "covered",
        ("tests/contracts/test_host_contracts.py::test_host_shared_contract",),
    ),
    "EC-HOST-3/independent-evaluations": (
        "EC-HOST-3",
        "covered",
        (
            "tests/evaluation/test_host_acceptance.py::test_independent_controlled_artifact_checks",
            _ROUTED,
        ),
    ),
    "EC-HOST-3/holdout-reserved": ("EC-HOST-3", "covered", (_FROZEN,)),
    "EC-HOST-3/baselines-and-overhead": ("EC-HOST-3", "covered", (_ROUTED,)),
    "EC-HOST-3/insufficient-evidence": ("EC-HOST-3", "covered", (_FROZEN,)),
    "EC-HOST-3/live-evaluation": ("EC-HOST-3", "outside_reading", ()),
    "EC-HOST-4/installed-flow": (
        "EC-HOST-4",
        "covered",
        (
            _D + "test_installed_discovery_decomposition_two_task_launch",
            _D + "test_installed_discovery_status_gates_planning[no_optional_guidance]",
            _TWO_TASKS,
            _C + "test_discovery_handoff.py::test_installed_flow_carries_a_judged_task",
        ),
    ),
    "EC-HOST-4/harness-decomposes": (
        "EC-HOST-4",
        "covered",
        (_D + "test_entered_discovery_requires_harness_decomposition", _TWO_TASKS),
    ),
    "EC-HOST-4/two-tasks": (
        "EC-HOST-4",
        "covered",
        (
            "tests/application/test_discovery_application.py::test_public_discovery_two_independent_tasks_and_replay",
            _D + "test_installed_discovery_decomposition_two_task_launch",
            _TWO_TASKS,
        ),
    ),
    "EC-HOST-4/links": (
        "EC-HOST-4",
        "covered",
        (
            "tests/application/test_discovery_application.py::test_bad_links_never_enter_prepare",
            _LINKS,
            _D + "test_entered_linked_launch_rejections",
        ),
    ),
    "EC-HOST-4/guidance-lifetime": (
        "EC-HOST-4",
        "covered",
        (
            _A + "test_guidance_is_verified_injected_once_and_deactivated",
            _D + "test_installed_discovery_decomposition_two_task_launch",
        ),
    ),
    "EC-HOST-4/retain-model-refusal": (
        "EC-HOST-4",
        "covered",
        (_A + "test_override_staleness_and_final_token_enforcement",),
    ),
    "EC-HOST-4/retain-model-launch": ("EC-HOST-4", "not_covered", ()),
    "EC-HOST-4/decline": (
        "EC-HOST-4",
        "covered",
        (_D + "test_entered_linked_launch_rejections[decline]", _LINKS),
    ),
    "EC-HOST-4/production-paths": (
        "EC-HOST-4",
        "covered",
        (_TWO_TASKS, _D + "test_installed_discovery_decomposition_two_task_launch"),
    ),
    "EC-HOST-4/no-recursion-no-single-model": (
        "EC-HOST-4",
        "covered",
        (
            _ROUTING + "test_recursion_bypass_makes_no_judgment_call",
            _A + "test_dry_run_and_recursion_bypass_do_not_route",
            _TWO_TASKS,
        ),
    ),
    "JD-084/leased-launch": (
        "JD-084",
        "covered",
        (
            _L + "test_launcher_accepts_explicit_nonserialized_lease_authority",
            _L + "test_supervised_launch_drains_retained_stdout_before_returning",
        ),
    ),
    "JD-083/ceilings": (
        "JD-083",
        "covered",
        (
            "tests/application/test_route_integration.py::test_builtin_task_judgment_keeps_verified_spending_bounds",
            _A + "test_requested_ceiling_rejects_unproven_executor_limits",
            _A + "test_override_staleness_and_final_token_enforcement",
            _A + "test_no_requested_ceiling_does_not_require_token_enforcement",
        ),
    ),
    "IF-0-HOST-1/installed-flow": ("IF-0-HOST-1", "covered", (_TWO_TASKS,)),
    "IF-0-VC-2/reducer": (
        "IF-0-VC-2",
        "covered",
        (
            "tests/verification/test_host_phase.py::test_reducer_rejects_invalid_receipts",
            "tests/verification/test_host_phase.py::test_missing_companion_configuration_is_failure",
            "tests/verification/test_host_phase.py::test_reducer_accepts_valid_receipts",
        ),
    ),
    "scope/readiness-recheck-before-launch": ("scope", "not_covered", ()),
    "scope/budget-after-host-spawn": ("scope", "not_covered", ()),
    "scope/ordinary-macos-execution-local": ("scope", "not_covered", ()),
    "scope/no-silent-forwarding": ("scope", "not_covered", ()),
}
# The JEV Drill controls of each criterion; their files join the inherited test command.
CONTROLS = {
    criterion: sorted(
        {
            node
            for owner, _status, nodes in CLAUSES.values()
            if owner == criterion
            for node in nodes
            if node in CONTROL_COUNTS
        }
    )
    for criterion in sorted({owner for owner, _status, _nodes in CLAUSES.values()})
}
TEST_PATHS = tuple(sorted({node.split("::")[0] for node in CONTROL_COUNTS}))
# J6: each launch-path claim of EC-HOST-1 and EC-HOST-4 rests on a selected test, none of
# them in the deselected launcher class.
LAUNCH_PATHS = {
    "main": (
        _C + "test_launch_paths.py::test_real_main_delegated_lane_constructors",
        _A + "test_real_runner_construction_sites_reach_bridge[main]",
    ),
    "delegated": (
        _C + "test_launch_paths.py::test_real_main_delegated_lane_constructors",
        _A + "test_real_runner_construction_sites_reach_bridge[delegated]",
    ),
    "lane": (
        _C + "test_launch_paths.py::test_real_main_delegated_lane_constructors",
        _A + "test_real_runner_construction_sites_reach_bridge[lane]",
    ),
    "widened_launch_refused": (
        _C + "test_launch_paths.py::test_entered_permission_expansion_denials",
        _A + "test_forged_capability_or_candidate_cannot_expand_authority",
    ),
    "dry_run_and_recursion_bypass_not_routed": (
        _A + "test_dry_run_and_recursion_bypass_do_not_route",
    ),
    "installed_two_task_launch": (
        _TWO_TASKS,
        _D + "test_installed_discovery_decomposition_two_task_launch",
    ),
    "leased_launch": (
        _L + "test_launcher_accepts_explicit_nonserialized_lease_authority",
        _L + "test_supervised_launch_drains_retained_stdout_before_returning",
    ),
}
DESELECTED_LAUNCHER_CLASS = "tests/test_phase_loop_launcher.py::PhaseLoopLauncherTest"
DESELECTED_LAUNCHER_COUNT = 53
SPEC_DELTA = {
    "schema": "spec_delta_closeout.v1",
    "phase": "HOST",
    "decision": "roadmap_amendment",
    "roadmap_amendment_items": ["JD-083", "JD-084"],
    "roadmap_text_amended": False,
    "target_surfaces": ["shared event/adapter contracts", "platform execution boundaries"],
    "evidence_paths": ["evidence/HOST/spec-delta.json", "evidence/HOST/verification.json"],
    "redaction_posture": "metadata_only",
    "missing_or_malformed_evidence": {"blocker_class": "contract_bug", "repair": "non_human"},
    "downstream_handling": "replan_LEARN",
    "canonical_adoption": False,
    "publication_performed": False,
}
CLOSEOUT_STATUSES = {"verification_pending", "blocked", "complete"}
_SHA = re.compile(r"[0-9a-f]{40}")
_DIGEST = re.compile(r"[0-9a-f]{64}")


class CollectionError(Exception):
    """A precondition of a collection failed; nothing that depends on it ran."""


def digest_value(value):
    """The SHA-256 hex of `value` as canonical JSON (sorted keys, compact separators)."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _text_bytes(path):
    """A file's bytes with CRLF line endings read as LF, so line endings change no digest."""
    return path.read_bytes().replace(b"\r\n", b"\n")


def source_digest(root):
    """A digest over the companion's sources, tests, contract copies and lock."""
    paths = {
        p
        for pattern in (
            "src/**/*.py",
            "src/**/*.json",
            "tests/**/*.py",
            "tests/fixtures/jevdrill/*.json",
            "pyproject.toml",
            "uv.lock",
        )
        for p in root.glob(pattern)
        if p.is_file() and "__pycache__" not in p.parts
    }
    return digest_value(
        {
            p.relative_to(root).as_posix(): hashlib.sha256(_text_bytes(p)).hexdigest()
            for p in sorted(paths, key=lambda p: p.relative_to(root).as_posix())
        }
    )


def input_digest(root):
    """The ROUTE inputs plus every HOST input, this verifier's source among them."""
    extra = {}
    for pattern in (
        "research/evaluation/host/*.py",
        "research/evaluation/host/protocol.json",
        "tests/conformance/fixtures/*.json",
        "evidence/HOST/adapter-handoff.json",
        "evidence/HOST/coverage.json",
        "evidence/HOST/spec-delta.json",
        "plans/phase-plan-v1-HOST.md",
        ".github/workflows/host.yml",
    ):
        extra.update(
            {
                p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in root.glob(pattern)
                if p.is_file()
            }
        )
    return digest_value({"route_source": route.input_digest(root), "host_sources": extra})


def assertions_from(path, root):
    """One {"node_id", "outcome"} per JUnit case; a test class keeps its name in the id."""
    rows = []
    for case in ET.parse(path).getroot().iter("testcase"):
        parts = case.get("classname", "").split(".")
        classes = []
        while parts and not (root / ("/".join(parts) + ".py")).is_file():
            classes.insert(0, parts.pop())
        rows.append(
            {
                # As pytest's own id: a method keeps its class, so it can never stand for a
                # module-level control of the same name.
                "node_id": "::".join(["/".join(parts) + ".py", *classes, case.get("name", "")]),
                "outcome": "skipped"
                if case.find("skipped") is not None
                else "failed"
                if case.find("failure") is not None or case.find("error") is not None
                else "passed",
            }
        )
    return sorted(rows, key=lambda row: row["node_id"])


def companion_command(python, temporary, os_name):
    files = [
        name
        for name in COMPANION_FILES
        if os_name == "Linux" or name not in LINUX_ONLY_COMPANION_FILES
    ]
    return [
        str(python),
        "-m",
        "pytest",
        "-q",
        *DESELECTION,
        *["phase-loop-runtime/tests/" + name for name in files],
        f"--junitxml={Path(temporary) / 'companion.xml'}",
        f"--basetemp={Path(temporary) / 'companion-tests'}",
    ]


def normalized_command(command, report):
    """The command with its interpreter and temporary paths replaced; no flag is touched."""
    return [
        "<python>"
        if index == 0
        else f"--junitxml=<temporary>/{report}.xml"
        if part.startswith("--junitxml=")
        else f"--basetemp=<temporary>/{report}-{'tests' if report == 'companion' else 'child'}"
        if part.startswith("--basetemp=")
        else part
        for index, part in enumerate(command)
    ]


def expected_companion_command(os_name):
    return normalized_command(companion_command("<python>", "<temporary>", os_name), "companion")


def contract_copies(root, runtime):
    """Compare the companion's contract copies with jevdrill's files (J5).

    Each copy is read with LF line endings; a fixture copy has the placeholder replaced first.
    The digests are of what was compared, so they equal jevdrill's own when the copies match.
    """
    directory = runtime / CONTRACT_DIRECTORY
    expected = {*CONTRACT_SCHEMAS, *CONTRACT_FIXTURES, "digests.json"}
    present = {path.name for path in directory.glob("*") if path.is_file()}
    mismatches = [] if present == expected else ["unexpected or missing contract copies"]
    files = {}
    raw = {}
    for name, own in [(name, root / "schemas" / name) for name in CONTRACT_SCHEMAS] + [
        (name, root / "tests/contracts/fixtures" / name) for name in CONTRACT_FIXTURES
    ]:
        copy = directory / name
        if not copy.is_file() or not own.is_file():
            files[name] = None
            mismatches.append(name)
            continue
        raw[name] = _text_bytes(copy)
        compared = raw[name]
        if name in CONTRACT_FIXTURES:
            compared = compared.replace(TOKEN_COUNTER_PLACEHOLDER, TOKEN_COUNTER_REVISION)
        files[name] = hashlib.sha256(compared).hexdigest()
        if compared != _text_bytes(own):
            mismatches.append(name)
    try:
        recorded = json.loads(_text_bytes(directory / "digests.json"))
    except OSError, ValueError:
        recorded = None
    if recorded != {
        name: hashlib.sha256(raw[name]).hexdigest() if name in raw else None
        for name in CONTRACT_SCHEMAS
    }:
        mismatches.append("digests.json")
    return {"files": files, "mismatches": sorted(set(mismatches))}


def child_environment(home, **values):
    """A child's whole environment: the allowlist, an empty home, and the named values."""
    env = {name: os.environ[name] for name in INHERITED_VARIABLES if name in os.environ}
    env.update(HOME=str(home), USERPROFILE=str(home), NO_PROXY="127.0.0.1,localhost")
    env["no_proxy"] = env["NO_PROXY"]
    env.update(values)
    return env


def route_environment(**values):
    """The ROUTE regression checks' whole environment: their allowlist and the named values."""
    env = {name: os.environ[name] for name in ROUTE_INHERITED_VARIABLES if name in os.environ}
    env.update(values)
    return env


@contextlib.contextmanager
def process_environment(env):
    """Run the in-process ROUTE collection with exactly `env`, so its children inherit only it."""
    saved = dict(os.environ)
    os.environ.clear()
    os.environ.update(env)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(saved)


def _repository(url):
    match = re.search(r"github\.com[:/]([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$", url or "")
    return match.group(1) if match else None


def checkout_state(root, env):
    """The repository, commit and cleanness of a git checkout; never a path."""

    def git(*args):
        try:
            result = subprocess.run(
                ["git", "-C", str(root), *args],
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
                check=False,
            )
        except OSError, subprocess.SubprocessError:
            return None
        return result.stdout.strip() if result.returncode == 0 else None

    commit = git("rev-parse", "HEAD")
    return {
        "repository": _repository(git("remote", "get-url", "origin")),
        "commit": commit if commit and _SHA.fullmatch(commit) else None,
        "clean": git("status", "--porcelain", "--untracked-files=all") == "",
    }


def _redacted(value, prefixes):
    if isinstance(value, dict):
        return {key: _redacted(item, prefixes) for key, item in value.items()}
    if isinstance(value, list):
        return [_redacted(item, prefixes) for item in value]
    if isinstance(value, str):
        for prefix, name in prefixes:
            value = value.replace(prefix, name)
    return value


def _handoff(root):
    handoff = json.loads((root / "evidence/HOST/adapter-handoff.json").read_text(encoding="utf-8"))
    if (
        not isinstance(handoff, dict)
        or handoff.get("schema_version") != 2
        or not isinstance(handoff.get("repository"), str)
        or not _SHA.fullmatch(str(handoff.get("commit")))
        or not isinstance(handoff.get("package_version"), str)
        or not isinstance(handoff.get("modules"), dict)
        or not handoff["modules"]
    ):
        raise ValueError("malformed handoff record")
    return handoff


# Run by the companion interpreter: where its modules load from, their digests (LF), the
# package version, the platform and its own Python.
PROVENANCE_PROBE = r"""
import hashlib, importlib, importlib.metadata, json, platform, sys
from pathlib import Path
root = Path(sys.argv[1]).resolve()
names = json.loads(sys.argv[2])
paths = {n: Path(importlib.import_module("phase_loop_runtime." + n).__file__).resolve() for n in names}
print(json.dumps({
    "modules": {n: hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest() for n, p in paths.items()},
    "version": importlib.metadata.version("phase-loop-runtime"),
    "os": platform.system(),
    "python_version": platform.python_version(),
    "source_root_matches": all(p.is_relative_to(root / "src") for p in paths.values()),
}))
"""


def _run(command, *, cwd, env, timeout):
    """Run one child once: (exit code, output, whether its deadline expired). No retry."""
    try:
        result = subprocess.run(
            command, cwd=cwd, env=env, capture_output=True, timeout=timeout, check=False
        )
        return result.returncode, result.stdout + result.stderr, False
    except subprocess.TimeoutExpired as error:
        return 125, b"TimeoutExpired\n" + (error.stdout or b"") + (error.stderr or b""), True
    except OSError as error:
        return 125, type(error).__name__.encode(), False


def collect(root, companion_root):
    started = time.monotonic()
    run = {
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "repository": os.environ.get("GITHUB_REPOSITORY"),
    }
    configured = os.environ.get("JEVDRILL_AGENT_HARNESS_PYTHON")
    if not configured or not Path(configured).is_file():
        raise CollectionError("JEVDRILL_AGENT_HARNESS_PYTHON must name the companion interpreter")
    python = Path(configured)
    runtime = companion_root / "phase-loop-runtime"
    if not runtime.is_dir():
        raise CollectionError("the companion checkout is missing")
    cli = Path(sys.executable).parent / ("jevdrill.exe" if os.name == "nt" else "jevdrill")
    if not cli.is_file():
        raise CollectionError("the installed jevdrill CLI is missing")
    try:
        handoff = _handoff(root)
    except (OSError, ValueError) as error:
        raise CollectionError("the handoff record is missing or malformed") from error
    before = input_digest(root)
    companion_before = source_digest(runtime)
    with tempfile.TemporaryDirectory(
        prefix="jevdrill-host-", dir=os.environ.get("RUNNER_TEMP")
    ) as temporary:
        tmp = Path(temporary)
        home = tmp / "home"
        home.mkdir()
        jevdrill = checkout_state(root, child_environment(home))
        companion = checkout_state(companion_root, child_environment(home))
        code, output, expired = _run(
            [
                str(python),
                "-c",
                PROVENANCE_PROBE,
                str(runtime),
                json.dumps(sorted(handoff["modules"])),
            ],
            cwd=companion_root,
            env=child_environment(home),
            timeout=30,
        )
        if code != 0:
            print(output.decode(errors="replace")[-20000:], file=sys.stderr, flush=True)
            raise CollectionError(
                "the companion did not import" + (" within 30 seconds" if expired else "")
            )
        try:
            provenance = json.loads(output)
        except ValueError:
            provenance = None
        if not isinstance(provenance, dict):
            raise CollectionError("the companion's provenance could not be read")
        witness_path = tmp / "witness.json"
        with process_environment(
            route_environment(
                JEVDRILL_AGENT_HARNESS_ROOT=str(companion_root),
                JEVDRILL_AGENT_HARNESS_PYTHON=str(python),
                JEVDRILL_TEST_CLI=str(cli),
                JEVDRILL_EVALUATION_OUTPUT=str(witness_path),
            )
        ):
            inherited = route.collect(root, extra_test_paths=TEST_PATHS)
        if not run["run_id"]:
            # route.collect names the machine outside CI; a HOST receipt never does.
            inherited["runner_identity"] = "local"
        command = companion_command(python, tmp, platform.system())
        code, output, expired = _run(
            command,
            cwd=companion_root,
            env=child_environment(
                home,
                PYTHONPATH=os.pathsep.join([str(runtime / "src"), str(runtime / "tests")]),
                JEVDRILL_TEST_CLI=str(cli),
                JEVDRILL_TEST_PYTHON=sys.executable,
                **SCHEDULER_SWITCH,
            ),
            timeout=max(0.001, COLLECTION_BOUND_SECONDS - (time.monotonic() - started)),
        )
        print(f"companion: {'passed' if code == 0 else 'FAILED'}", flush=True)
        if code:
            print(output.decode(errors="replace")[-20000:], flush=True)
        try:
            assertions = assertions_from(tmp / "companion.xml", runtime)
        except OSError, ET.ParseError:
            assertions = []
        static_code, static_output, _ = _run(
            [sys.executable, *HOST_STATIC_COMMAND[1:]],
            cwd=root,
            env=child_environment(home),
            timeout=max(0.001, COLLECTION_BOUND_SECONDS - (time.monotonic() - started)),
        )
        try:
            witness = json.loads(witness_path.read_text(encoding="utf-8"))
        except OSError, ValueError:
            witness = None
        prefixes = sorted(
            {
                (str(path), name)
                for location, name in (
                    (tmp, "<temporary>"),
                    (os.environ.get("RUNNER_TEMP"), "<runner-temp>"),
                    (tempfile.gettempdir(), "<system-temp>"),
                    (companion_root, "<companion>"),
                    (root, "<jevdrill>"),
                    (Path.home(), "<home>"),
                )
                if location
                for path in (Path(location), Path(location).as_posix())
            },
            key=lambda item: -len(item[0]),
        )
        witness = _redacted(witness, prefixes)
        discovery = (witness or {}).get("companion_discovery")
        if isinstance(discovery, dict) and isinstance(discovery.get("command"), list):
            discovery["command"] = normalized_command(discovery["command"], "discovery")
            discovery["command_sha256"] = digest_value(discovery["command"])
    normalized = normalized_command(command, "companion")
    failed = sorted(
        row["node_id"]
        for rows in (inherited.get("assertions", []), assertions)
        for row in rows
        if row.get("outcome") != "passed"
    )
    duration = round(time.monotonic() - started, 3)
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": "HOST",
        "execution_kind": "native",
        "os": platform.system(),
        "architecture": platform.machine(),
        "python_minor": f"{sys.version_info.major}.{sys.version_info.minor}",
        "python_version": platform.python_version(),
        "runner_identity": run["run_id"] or "local",
        "workflow_run": run,
        "jevdrill": jevdrill,
        "input_digest": before,
        "source_stable": input_digest(root) == before,
        "route_regressions": inherited,
        "companion": {
            **companion,
            "python": {
                "version": provenance.get("python_version"),
                "minor": ".".join(str(provenance.get("python_version", "")).split(".")[:2]),
            },
            "installed_provenance": provenance,
            "contract_copies": contract_copies(root, runtime),
            "environment": sorted(
                child_environment(
                    Path(),
                    PYTHONPATH="",
                    JEVDRILL_TEST_CLI="",
                    JEVDRILL_TEST_PYTHON="",
                    **SCHEDULER_SWITCH,
                )
            ),
            "command": normalized,
            "command_sha256": digest_value(normalized),
            "input_digest": companion_before,
            "source_stable": source_digest(runtime) == companion_before,
            "exit_code": code,
            "deadline_expired": expired,
            "output_sha256": hashlib.sha256(output).hexdigest(),
            "assertions": assertions,
            "assertions_sha256": digest_value(assertions),
        },
        "witnesses": witness,
        "witness_sha256": digest_value(witness),
        "host_static": {
            "command": list(HOST_STATIC_COMMAND),
            "exit_code": static_code,
            "output_sha256": hashlib.sha256(static_output).hexdigest(),
        },
        "failed_ids": failed,
        "failed_checks": sorted(
            check.get("name")
            for check in inherited.get("checks", [])
            if isinstance(check, dict) and check.get("exit_code") != 0
        ),
        "duration_seconds": duration,
        "proof_cost_target_exceeded": duration > PROOF_COST_TARGET_SECONDS,
    }


def _dict(value):
    return value if isinstance(value, dict) else {}


def _rows(value, key):
    """The well-formed rows of an assertion list, and whether every row was well formed."""
    if not isinstance(value, list):
        return [], False
    rows = [
        row
        for row in value
        if isinstance(row, dict)
        and isinstance(row.get(key), str)
        and isinstance(row.get("outcome"), str)
    ]
    return rows, len(rows) == len(value)


def _count(rows, key, node):
    return sum(
        1
        for row in rows
        if row.get("outcome") == "passed" and (row[key] == node or row[key].startswith(node + "["))
    )


def _is_digest(value):
    return isinstance(value, str) and _DIGEST.fullmatch(value) is not None


def _dotted(node):
    """A path id as the conformance fixture writes it: the JUnit class name, then the name."""
    path, _, name = node.partition("::")
    return path.removesuffix(".py").replace("/", ".") + "::" + name


def witness_errors(witness):
    errors = []
    if not isinstance(witness, dict) or not isinstance(witness.get("records"), list):
        return ["missing production witnesses"]
    records = [row for row in witness["records"] if isinstance(row, dict)]
    if len(records) != len(witness["records"]):
        errors.append("malformed witness record")
    assertions, well_formed = _rows(witness.get("assertions"), "id")
    discovery = [
        row for row in assertions if row["id"].startswith("tests.test_jevdrill_discovery::")
    ]
    if (
        not well_formed
        or len(assertions) != PROBE_TOTAL + DISCOVERY_TOTAL
        or len(discovery) != DISCOVERY_TOTAL
        or len({row["id"] for row in assertions}) != len(assertions)
        or any(row["outcome"] != "passed" for row in assertions)
    ):
        errors.append("failed, skipped or inexact entered assertions")
    for node, count in PROBE_COUNTS.items():
        if _count(assertions, "id", _dotted(node)) != count:
            errors.append("probe count not exact: " + node)
    if (
        witness.get("holdouts_opened") is not False
        or witness.get("promotion_eligible") is not False
    ):
        errors.append("holdout or promotion authority violation")
    if witness.get("performance_claims") != "insufficient_evidence":
        errors.append("ineligible performance claim")
    if witness.get("claim_scope") != "synthetic_conformance_only":
        errors.append("witness claims more than synthetic conformance")
    flows = [row for row in records if row.get("flow") == "discovery"]
    if sorted(str(row.get("objective")) for row in flows) != ["alpha", "beta"]:
        errors.append("missing objective-dependent discovery")
    decisions = []
    for flow in flows:
        entered = flow.get("entered")
        if not isinstance(entered, list) or not {
            "main",
            "open_application",
            "discover",
            "next_question",
            "route",
        } <= {item for item in entered if isinstance(item, str)}:
            errors.append("missing installed entry")
        events = flow.get("construction_events")
        events = (
            [item for item in events if isinstance(item, str)] if isinstance(events, list) else []
        )
        routed = [index for index, event in enumerate(events) if event.endswith("route-v2")]
        if (
            "planning.executor" not in events
            or not routed
            or events.index("planning.executor") >= min(routed)
        ):
            errors.append("missing entered harness decomposition")
        runs = flow.get("runs")
        runs = [run for run in runs if isinstance(run, dict)] if isinstance(runs, list) else []
        if (
            len(runs) < 2
            or len({str(run.get("task_id")) for run in runs}) != len(runs)
            or len({str(run.get("model")) for run in runs}) < 2
            or len({str(run.get("effort")) for run in runs}) < 2
        ):
            errors.append("missing independent two-task configuration")
        if len({str(_dict(run.get("discovery_ref")).get("discovery_id")) for run in runs}) != 1:
            errors.append("tasks from more than one discovery")
        for run in runs:
            ref, execution = _dict(run.get("discovery_ref")), _dict(run.get("execution_run"))
            decisions.append(run.get("decision_id"))
            if (
                not ref.get("trace_digest")
                or not ref.get("discovery_id")
                or not run.get("task_id")
                or execution.get("task_id") != run.get("task_id")
                or not execution.get("applied_plan_id")
                or execution.get("selected_plan_id") != execution.get("applied_plan_id")
                or not execution.get("execution_run_id")
            ):
                errors.append("missing task decision run discovery linkage")
    # Declared change 15: each task has its own decision.
    if (
        not decisions
        or not all(isinstance(item, str) and item for item in decisions)
        or len(set(decisions)) != len(decisions)
    ):
        errors.append("missing or reused routing decision")
    # Declared change 14: one task of the installed flow was judged at JudgeCandidate-v2.
    judged = [row for row in records if row.get("flow") == "judged"]
    if (
        len(judged) != 1
        or judged[0].get("stored_function_revision") != "JudgeCandidate-v2"
        or judged[0].get("stored_judgments") != 1
        or judged[0].get("loopback_judgment_requests") != 1
        or judged[0].get("decision_status") != "ready"
        or not judged[0].get("routing_decision_id")
    ):
        errors.append("missing v2 judged task")
    controls = [row for row in records if row.get("flow") == "discovery-control"]
    if sorted(str(row.get("fault")) for row in controls) != sorted(
        ["forged", "deleted", "stale_catalog", "relaxed", "decline"]
    ):
        errors.append("missing entered linked controls")
    if any(
        not row.get("discovery_id")
        or not row.get("task_id")
        or row.get("rejected_before_execution") is not True
        for row in controls
    ):
        errors.append("missing linked control rejection evidence")
    for family in ("implementation", "review", "documentation"):
        rows = [row for row in records if row.get("task_family") == family]
        damaged = [row for row in rows if row.get("damaged")]
        positive = [row for row in rows if not row.get("damaged") and not row.get("control")]
        if not damaged or any(
            not isinstance(row.get("objective_checks"), dict)
            or all(row["objective_checks"].values())
            for row in damaged
        ):
            errors.append("missing independent artifact rejection")
        if not positive or any(
            not isinstance(row.get("objective_checks"), dict)
            or not row["objective_checks"]
            or not all(row["objective_checks"].values())
            for row in positive
        ):
            errors.append("missing independent positive artifact checks")
    return errors


def _discovery_errors(receipt, companion_digest):
    if not isinstance(receipt, dict):
        return ["missing integrated companion discovery"]
    errors = []
    assertions, well_formed = _rows(receipt.get("assertions"), "node_id")
    if (
        receipt.get("origin") != "installed_companion_conformance_subprocess"
        or receipt.get("command") != list(DISCOVERY_COMMAND)
        or receipt.get("command_sha256") != digest_value(list(DISCOVERY_COMMAND))
        or receipt.get("input_digest") != companion_digest
        or receipt.get("source_stable") is not True
        or receipt.get("exit_code") != 0
        or not _is_digest(receipt.get("output_sha256"))
    ):
        errors.append("missing or mismatched integrated companion discovery")
    if (
        not well_formed
        or any(row["outcome"] != "passed" for row in assertions)
        or len(assertions) != DISCOVERY_TOTAL
        or len({row["node_id"] for row in assertions}) != len(assertions)
        or receipt.get("assertions_sha256") != digest_value(receipt.get("assertions"))
    ):
        errors.append("failed, skipped or inexact companion discovery tests")
    for node, count in DISCOVERY_CONTROL_COUNTS.items():
        if _count(assertions, "node_id", node) != count:
            errors.append("companion discovery count not exact: " + node)
    return errors


def _companion_errors(companion, os_name, handoff, reference):
    errors = []
    if companion.get("repository") != handoff.get("repository") or companion.get(
        "commit"
    ) != handoff.get("commit"):
        errors.append("companion receipt is not for the handoff's commit")
    if companion.get("clean") is not True:
        errors.append("companion checkout was not clean")
    python = _dict(companion.get("python"))
    if python.get("minor") != COMPANION_PYTHON or not isinstance(python.get("version"), str):
        errors.append("companion Python is not the pinned version")
    provenance = _dict(companion.get("installed_provenance"))
    if (
        provenance.get("modules") != handoff.get("modules")
        or provenance.get("version") != handoff.get("package_version")
        or provenance.get("os") != os_name
        or provenance.get("python_version") != python.get("version")
        or provenance.get("source_root_matches") is not True
    ):
        errors.append("mismatched installed companion provenance")
    copies = companion.get("contract_copies")
    if (
        not isinstance(copies, dict)
        or copies.get("mismatches") != []
        or copies != _dict(reference.get("contract_copies"))
    ):
        errors.append("companion contract copies differ from jevdrill's")
    expected = expected_companion_command(os_name)
    if companion.get("command") != expected:
        errors.append("companion command is not the expected command")
    if companion.get("command_sha256") != digest_value(expected):
        errors.append("companion command digest mismatch")
    if (
        companion.get("input_digest") != reference.get("digest")
        or companion.get("source_stable") is not True
    ):
        errors.append("stale or changed companion sources")
    if companion.get("deadline_expired") is not False:
        errors.append("companion tests exceeded the collection deadline")
    if companion.get("exit_code") != 0 or not _is_digest(companion.get("output_sha256")):
        errors.append("companion tests failed")
    assertions, well_formed = _rows(companion.get("assertions"), "node_id")
    if not well_formed or companion.get("assertions_sha256") != digest_value(
        companion.get("assertions")
    ):
        errors.append("malformed companion assertions")
    errors.extend(
        "failed or skipped companion test: " + row["node_id"]
        for row in assertions
        if row["outcome"] != "passed"
    )
    if len(assertions) != COMPANION_TOTALS.get(os_name) or len(
        {row["node_id"] for row in assertions}
    ) != len(assertions):
        errors.append("companion test count not exact")
    for node, counts in COMPANION_CONTROL_COUNTS.items():
        if _count(assertions, "node_id", node) != counts.get(os_name, 0):
            errors.append("companion control count not exact: " + node)
    return errors


def _platform_errors(manifest, identity, root, reference, handoff, route_digest):
    errors = []
    run = _dict(reference.get("run"))
    if (
        manifest.get("phase") != "HOST"
        or manifest.get("schema_version") != SCHEMA_VERSION
        or manifest.get("execution_kind") != "native"
    ):
        errors.append("unsupported HOST receipt")
    if manifest.get("input_digest") != reference.get("input_digest"):
        errors.append("stale HOST input digest")
    if manifest.get("source_stable") is not True:
        errors.append("HOST inputs changed during collection")
    workflow = _dict(manifest.get("workflow_run"))
    if (
        not run.get("run_id")
        or workflow.get("run_id") != run.get("run_id")
        or workflow.get("run_attempt") != run.get("run_attempt")
        or workflow.get("repository") != run.get("repository")
        or manifest.get("runner_identity") != run.get("run_id")
    ):
        errors.append("receipt is not from this workflow run")
    if not manifest.get("architecture") or not isinstance(manifest.get("python_version"), str):
        errors.append("missing runner identity")
    jevdrill, expected = _dict(manifest.get("jevdrill")), _dict(reference.get("jevdrill"))
    if (
        not expected.get("commit")
        or jevdrill.get("commit") != expected.get("commit")
        or jevdrill.get("repository") != run.get("repository")
        or jevdrill.get("clean") is not True
    ):
        errors.append("jevdrill checkout is not the reduced commit, or was not clean")
    inherited = manifest.get("route_regressions")
    rows, _ = _rows(_dict(inherited).get("assertions"), "node_id")
    try:
        inherited_errors = route.reduce_manifests(
            [inherited],
            route_digest,
            root,
            required_platforms={identity},
            extra_test_paths=TEST_PATHS,
        )
    # A malformed inherited receipt is a verdict, never a traceback.
    except AttributeError, IndexError, KeyError, TypeError, ValueError:
        inherited_errors = ["malformed inherited regressions"]
    errors.extend("ROUTE regression: " + error for error in inherited_errors)
    for node, count in CONTROL_COUNTS.items():
        if _count(rows, "node_id", node) != count:
            errors.append("HOST control count not exact: " + node)
    companion = _dict(manifest.get("companion"))
    errors.extend(
        _companion_errors(companion, identity[0], handoff, _dict(reference.get("companion")))
    )
    witness = manifest.get("witnesses")
    if manifest.get("witness_sha256") != digest_value(witness):
        errors.append("witness digest mismatch")
    errors.extend(witness_errors(witness))
    errors.extend(
        _discovery_errors(
            _dict(witness).get("companion_discovery"),
            _dict(reference.get("companion")).get("digest"),
        )
    )
    static = _dict(manifest.get("host_static"))
    if static.get("exit_code") != 0 or static.get("command") != list(HOST_STATIC_COMMAND):
        errors.append("failed or wrong host static check")
    duration = manifest.get("duration_seconds")
    if (
        type(duration) not in (int, float)
        or not math.isfinite(duration)
        or not 0 < duration <= COLLECTION_BOUND_SECONDS
    ):
        errors.append("collection over 600 seconds, or no valid duration")
    elif manifest.get("proof_cost_target_exceeded") is not (duration > PROOF_COST_TARGET_SECONDS):
        errors.append("misreported five-minute proof-cost flag")
    return errors


def coverage_errors(root):
    """The coverage and spec-delta records, which must agree with this verifier's constants."""
    errors = []
    try:
        coverage = json.loads((root / "evidence/HOST/coverage.json").read_text(encoding="utf-8"))
        clauses = coverage["clauses"]
        if (
            coverage.get("schema_version") != 2
            or coverage.get("phase") != "HOST"
            or coverage.get("claim_scope") != "synthetic_conformance_only"
            or not isinstance(clauses, dict)
            or set(clauses) != set(CLAUSES)
            or any(
                [row.get("criterion"), row.get("status"), row.get("controls")]
                != [criterion, status, list(nodes)]
                for name, (criterion, status, nodes) in CLAUSES.items()
                for row in [clauses[name]]
            )
        ):
            errors.append("clause coverage disagrees with the verifier")
        if coverage.get("controls") != expected_control_table():
            errors.append("control counts in the coverage record disagree with the verifier")
        if coverage.get("launch_paths") != {
            name: list(nodes) for name, nodes in LAUNCH_PATHS.items()
        }:
            errors.append("launch-path mapping disagrees with the verifier")
        deselected = coverage.get("deselected_launcher_tests")
        if (
            not isinstance(deselected, dict)
            or deselected.get("class") != DESELECTED_LAUNCHER_CLASS
            or deselected.get("count") != DESELECTED_LAUNCHER_COUNT
            or deselected.get("marker") != DESELECTION[1].removeprefix("not ")
        ):
            errors.append("deselected launcher tests misstated")
    except OSError, ValueError, KeyError, TypeError, AttributeError:
        errors.append("missing or malformed HOST coverage record")
    try:
        delta = json.loads((root / "evidence/HOST/spec-delta.json").read_text(encoding="utf-8"))
        if (
            not isinstance(delta, dict)
            or {key: delta.get(key) for key in SPEC_DELTA} != SPEC_DELTA
            or delta.get("closeout_status") not in CLOSEOUT_STATUSES
        ):
            errors.append("malformed HOST spec-delta")
    except OSError, ValueError:
        errors.append("malformed HOST spec-delta")
    return errors


def expected_control_table():
    """Each control: where it runs, and its exact count on each platform it runs on."""
    table = {}
    for node, count in CONTROL_COUNTS.items():
        table[node] = {"suite": "jevdrill", "counts": {name: count for name in PLATFORMS}}
    for node, counts in COMPANION_CONTROL_COUNTS.items():
        table[node] = {"suite": "companion", "counts": dict(counts)}
    for node, count in DISCOVERY_CONTROL_COUNTS.items():
        table[node] = {
            "suite": "companion_discovery",
            "counts": {name: count for name in PLATFORMS},
        }
    return table


def receipt_errors(manifests, reference, root=ROOT, *, required_platforms=None):
    """Every reason the receipts, the checkouts or the records cannot be accepted."""
    errors = []
    try:
        handoff = _handoff(root)
    except OSError, ValueError:
        handoff = {}
        errors.append("missing or malformed handoff record")
    reference = _dict(reference)
    if not _dict(reference.get("run")).get("run_id"):
        errors.append("reduction outside a workflow run")
    companion = _dict(reference.get("companion"))
    if (
        companion.get("repository") != handoff.get("repository")
        or companion.get("commit") != handoff.get("commit")
        or companion.get("clean") is not True
    ):
        errors.append("reducer's companion checkout is not the handoff's clean commit")
    if _dict(companion.get("contract_copies")).get("mismatches") != []:
        errors.append("reducer's companion contract copies differ from jevdrill's")
    seen = set()
    route_digest = route.input_digest(root)
    for manifest in manifests:
        if not isinstance(manifest, dict):
            errors.append("malformed HOST receipt")
            continue
        identity = (manifest.get("os"), manifest.get("python_minor"))
        if not all(isinstance(part, str) for part in identity):
            errors.append("malformed platform identity")
            continue
        if identity not in MATRIX or identity in seen:
            errors.append("unexpected or duplicate platform")
        seen.add(identity)
        if "collection_error" in manifest:
            errors.append(f"{identity[0]}: collection failed: {manifest['collection_error']}")
            continue
        errors.extend(
            f"{identity[0]}: {error}"
            for error in _platform_errors(
                manifest, identity, root, reference, handoff, route_digest
            )
        )
    required = MATRIX if required_platforms is None else required_platforms
    errors.extend(f"missing {name}/Python {minor}" for name, minor in sorted(required - seen))
    errors.extend(coverage_errors(root))
    return sorted(set(errors))


def not_covered():
    return sorted(name for name, (_c, status, _n) in CLAUSES.items() if status == "not_covered")


def outside_reading():
    """Clauses the plan reads as outside their criterion; they do not block, and are shown."""
    return sorted(name for name, (_c, status, _n) in CLAUSES.items() if status == "outside_reading")


def reduce_manifests(manifests, reference, root=ROOT, *, required_platforms=None):
    """Receipt errors, then one entry per clause not covered: a gate needs an empty list."""
    return receipt_errors(manifests, reference, root, required_platforms=required_platforms) + [
        "not covered: " + name for name in not_covered()
    ]


def reference_state(root, companion_root):
    """What the reducer checks receipts against: its own checkouts and its own workflow run."""
    runtime = companion_root / "phase-loop-runtime"
    with tempfile.TemporaryDirectory(prefix="jevdrill-host-reduce-") as temporary:
        env = child_environment(Path(temporary))
        jevdrill = checkout_state(root, env)
        companion = checkout_state(companion_root, env)
    return {
        "input_digest": input_digest(root),
        "jevdrill": jevdrill,
        "companion": {
            **companion,
            "digest": source_digest(runtime) if runtime.is_dir() else None,
            "contract_copies": contract_copies(root, runtime),
        },
        "run": {
            "run_id": os.environ.get("GITHUB_RUN_ID"),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "repository": os.environ.get("GITHUB_REPOSITORY"),
        },
    }


def read_receipts(directory):
    """Every receipt in the directory; one that cannot be read is kept as None and reported."""
    receipts = []
    for path in sorted(directory.glob("*.json")):
        try:
            receipts.append(json.loads(path.read_text(encoding="utf-8")))
        except OSError, ValueError:
            receipts.append(None)
    return receipts


def verdict(manifests, reference, root=ROOT):
    errors = receipt_errors(manifests, reference, root)
    gaps = not_covered()
    blocked = bool(errors or gaps)
    return {
        "schema_version": 1,
        "phase": "HOST",
        "status": "blocked" if blocked else "passed",
        "controls_passed": not errors,
        "errors": errors,
        "not_covered": gaps,
        # A gate produced here still rests on the plan's reading of these clauses.
        "outside_reading": outside_reading(),
        "proof_cost_over_five_minutes": sorted(
            str(item.get("os"))
            for item in manifests
            if isinstance(item, dict) and item.get("proof_cost_target_exceeded") is True
        ),
        "input_digest": reference.get("input_digest"),
        "companion": {
            key: _dict(reference.get("companion")).get(key)
            for key in ("repository", "commit", "digest")
        },
        "run": reference.get("run"),
        "platforms": sorted(str(item.get("os")) for item in manifests if isinstance(item, dict)),
        "produced_if_gates": [] if blocked else ["IF-0-HOST-1"],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agent-harness", type=Path, default=os.environ.get("JEVDRILL_AGENT_HARNESS_ROOT")
    )
    parser.add_argument("--local-only", action="store_true")
    parser.add_argument("--reduce-only", action="store_true")
    args = parser.parse_args(argv)
    if args.agent_harness is None:
        parser.error("Explicit --agent-harness PATH or JEVDRILL_AGENT_HARNESS_ROOT is required")
    companion_root = Path(args.agent_harness).resolve()
    platforms = OUTPUT / "platforms"
    platforms.mkdir(parents=True, exist_ok=True)
    identity = (platform.system(), f"{sys.version_info.major}.{sys.version_info.minor}")
    current = None
    if not args.reduce_only:
        path = platforms / f"{identity[0]}-{identity[1]}.json"
        try:
            current = collect(ROOT, companion_root)
        except CollectionError as error:
            print(f"HOST collection failed: {error}", file=sys.stderr, flush=True)
            failed = {
                "schema_version": SCHEMA_VERSION,
                "phase": "HOST",
                "os": identity[0],
                "python_minor": identity[1],
                "collection_error": str(error),
            }
            path.write_text(json.dumps(failed, indent=2) + "\n", encoding="utf-8")
            return 1
        path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
        (OUTPUT / "evaluation.json").write_text(
            json.dumps(current["witnesses"], indent=2) + "\n", encoding="utf-8"
        )
    reference = reference_state(ROOT, companion_root)
    if args.local_only:
        errors = receipt_errors([current], reference, ROOT, required_platforms={identity})
        print(json.dumps({"local_errors": errors}, indent=2))
        return int(bool(errors))
    report = verdict(read_receipts(platforms), reference, ROOT)
    (OUTPUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return int(report["status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
