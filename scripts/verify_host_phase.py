"""Collect one native HOST receipt with the pinned companion, or reduce one run's receipts.

A receipt is collected on a hosted runner of one `host.yml` run. In a fixed order it holds the
inherited ROUTE regressions (one unmodified call of the ROUTE collector, its command the one
`route.yml` runs), HOST's own controls (one command of this collector's own), the companion's
own tests at the handoff's commit, and the witness the conformance fixture writes. The inherited
part keeps ROUTE's own 600 seconds; everything else is HOST's part, bounded at 900 seconds
(HOST plan, declared change 17). The reduction accepts exactly three receipts of the workflow
run it is part of. A local collection is a diagnostic: it is never uploaded and no reduction
accepts it.
"""

import argparse
import contextlib
import errno
import hashlib
import importlib.util
import json
import os
import platform
import re
import secrets
import select
import signal
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

# Schema 4 divides a collection in two parts (declared change 17); schema 5 adds each checkout's
# git configuration digest. A receipt of schema 4 or below is rejected as old.
SCHEMA_VERSION = 5
MATRIX = route.MATRIX
PLATFORMS = ("Linux", "Darwin", "Windows")
# The inherited part's bound: the ROUTE collector's own budget (scripts/verify_route_phase.py,
# `600 - elapsed` per child in `collect`; `<= 600` in `reduce_manifests`), not reopened here.
INHERITED_BOUND_SECONDS = 600
# A watchdog on the inherited call, not a bound and not a budget: the ROUTE collector keeps its
# own 600-second deadline, which is neither changed nor passed in. The collector stops the call
# only this long after that deadline, so that ROUTE's own timeout handling can run and its receipt
# keep its timeout output, as the collector before declared change 17 kept it. The reducer still
# rejects an inherited part over INHERITED_BOUND_SECONDS, however it ended.
INHERITED_WATCHDOG_GRACE_SECONDS = 30
# HOST's part: everything in a collection outside the ROUTE collector call (HOST plan, SL-6).
HOST_BOUND_SECONDS = 900
# The longest a collection's children can run, stated when it is run outside CI: the inherited
# call until its watchdog, then HOST's part. A receipt over either part's bound is still rejected.
TOTAL_LIMIT_SECONDS = (
    INHERITED_BOUND_SECONDS + INHERITED_WATCHDOG_GRACE_SECONDS + HOST_BOUND_SECONDS
)
# How long the collector waits for a child it has killed before it gives up waiting.
KILLED_CHILD_WAIT_SECONDS = 30
PROOF_COST_TARGET_SECONDS = 300
# The ROUTE receipt's own duration is rounded to the millisecond (verify_route_phase.py, the
# end of `collect`); the inherited part may be shorter than it by at most this rounding.
ROUTE_DURATION_ROUNDING = 0.0005
# The parts are recorded unrounded from one clock; their sum may differ from the total only by
# floating-point error, never by a time anyone could move.
PARTS_SUM_TOLERANCE = 1e-6
# Every recorded time is a number of seconds in this range; anything else is malformed.
MAX_RECORDED_SECONDS = 10**6
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
# The one substitution, as the receipt records it; bound with the companion command's digest.
CONTRACT_SUBSTITUTION = [TOKEN_COUNTER_PLACEHOLDER.decode(), TOKEN_COUNTER_REVISION.decode()]

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
# The four values the collector adds by name to the inherited call's and HOST's command's
# environment: the companion checkout and interpreter, the installed CLI, and the witness file
# the conformance fixture writes. Nothing else is added to either.
HOST_VARIABLES = (
    "JEVDRILL_AGENT_HARNESS_ROOT",
    "JEVDRILL_AGENT_HARNESS_PYTHON",
    "JEVDRILL_TEST_CLI",
    "JEVDRILL_EVALUATION_OUTPUT",
)
# The one behaviour switch the collector sets, for the companion's command only: it activates
# the two JD-084 launcher tests, which skip without it (HOST plan, "Readings and points settled").
SCHEDULER_SWITCH = {"PHASE_LOOP_TDD_EXPECT_SCHED": "1"}

REQUIREMENTS = {f"EC-HOST-{number}" for number in range(1, 5)} | {"IF-0-HOST-1", "IF-0-VC-2"}

# Every JEV Drill control the clause tables name, with its exact case count, on all three
# platforms. CONTROL_SOURCES says which command each is counted from. A changed count is a
# declared change.
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
    "tests/verification/test_host_phase.py::test_reducer_rejects_invalid_receipts": 64,
}
INHERITED = "inherited"
HOST = "host"
# The one source each JEV Drill control is counted from (declared change 17). "inherited": its
# file is a path the ROUTE collector's own test command already selects, so it is counted from
# the inherited results and its file is not in HOST's command. "host": counted from HOST's own
# command. A control found in both is rejected.
CONTROL_SOURCES = {
    "tests/analysis/test_observations.py::test_missing_failed_canceled_corrected_and_unknown_observations": HOST,
    "tests/analysis/test_observations.py::test_substitution_preference_and_evaluation_are_distinct": HOST,
    "tests/application/test_application.py::test_report_is_a_versioned_durable_acknowledgment": INHERITED,
    "tests/application/test_discovery_application.py::test_bad_links_never_enter_prepare": INHERITED,
    "tests/application/test_discovery_application.py::test_public_discovery_two_independent_tasks_and_replay": INHERITED,
    "tests/application/test_host_notices.py::test_notice_snapshots_do_not_mutate_retry_or_replay": HOST,
    "tests/application/test_host_routing.py::test_capability_mismatch_carries_supported_refresh_advice": HOST,
    "tests/application/test_host_routing.py::test_dry_run_is_never_ordered_by_learned_policy": HOST,
    "tests/application/test_host_routing.py::test_recursion_bypass_makes_no_judgment_call": HOST,
    "tests/application/test_route_integration.py::test_builtin_task_judgment_keeps_verified_spending_bounds": INHERITED,
    "tests/application/test_route_integration.py::test_retry_requires_recorded_run_and_remaining_attempt_authority": INHERITED,
    "tests/conformance/test_discovery_handoff.py::test_entered_reference_deletion_revision_and_policy_controls": HOST,
    "tests/conformance/test_discovery_handoff.py::test_installed_discovery_harness_planning_two_independent_tasks": HOST,
    "tests/conformance/test_discovery_handoff.py::test_installed_flow_carries_a_judged_task": HOST,
    "tests/conformance/test_launch_paths.py::test_entered_permission_expansion_denials": HOST,
    "tests/conformance/test_launch_paths.py::test_independent_checks_reject_entered_routed_artifacts": HOST,
    "tests/conformance/test_launch_paths.py::test_real_main_delegated_lane_constructors": HOST,
    "tests/conformance/test_notices.py::test_every_report_connection_queries_notices": HOST,
    "tests/conformance/test_notices.py::test_pending_notice_reaches_the_notice_sink": HOST,
    "tests/conformance/test_transport_queue.py::test_entered_ack_loss_and_cross_producer_deletion": HOST,
    "tests/conformance/test_usage_reporting.py::test_installed_usage_persistence": HOST,
    "tests/contracts/test_host_contracts.py::test_host_shared_contract": HOST,
    "tests/evaluation/test_host_acceptance.py::test_frozen_groups_are_disjoint_and_holdouts_unopened": INHERITED,
    "tests/evaluation/test_host_acceptance.py::test_independent_controlled_artifact_checks": INHERITED,
    "tests/privacy/test_round41_learning.py::test_report_sensitive_map_key_rejects_before_persistence": INHERITED,
    "tests/privacy/test_sink_proof.py::test_a_report_with_a_refused_identifier_is_refused_before_it_is_stored": INHERITED,
    "tests/storage/test_dry_run_evidence.py::test_cached_decision_is_reused_only_when_its_mode_matches": HOST,
    "tests/storage/test_dry_run_evidence.py::test_no_dry_run_becomes_an_observation": HOST,
    "tests/storage/test_dry_run_evidence.py::test_routing_and_storage_share_the_dry_run_code": HOST,
    "tests/storage/test_host_notices.py::test_notice_scope_reads_and_cross_producer_deletion": HOST,
    "tests/verification/test_host_phase.py::test_missing_companion_configuration_is_failure": HOST,
    "tests/verification/test_host_phase.py::test_reducer_accepts_valid_receipts": HOST,
    "tests/verification/test_host_phase.py::test_reducer_rejects_invalid_receipts": HOST,
}
# HOST's own command selects exactly the files of the controls counted from it, and nothing the
# ROUTE collector's command selects: no test runs in both.
HOST_TEST_PATHS = tuple(
    sorted({node.split("::")[0] for node, source in CONTROL_SOURCES.items() if source == HOST})
)
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
# The JEV Drill controls of each criterion; each is counted from its source in CONTROL_SOURCES.
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


def host_test_command(python, temporary):
    """HOST's own command: its controls' files, with the flags the ROUTE test command uses.

    The same on every platform: none of these files holds a test ROUTE leaves out on Windows.
    """
    return [
        str(python),
        "-m",
        "pytest",
        "-q",
        "-o",
        "faulthandler_timeout=30",
        *HOST_TEST_PATHS,
        f"--junitxml={Path(temporary) / 'host.xml'}",
        f"--basetemp={Path(temporary) / 'host-tests'}",
    ]


# The path separators of each platform a receipt can record. On Linux and macOS a backslash is an
# ordinary file-name character, so `<root>\\host-tests` names a sibling of the root, not a path
# under it.
PLATFORM_SEPARATORS = {"Linux": ("/",), "Darwin": ("/",), "Windows": ("\\", "/")}


def _under_temporary(value, temporary, separators):
    """`value` with the temporary root replaced by `<temporary>` and what follows it kept, with
    `/` separators. A path is under the root only through one of `separators`; a value outside
    the root is returned unchanged, so that it cannot match."""
    root = str(temporary)
    if value == root or value.startswith(tuple(root + separator for separator in separators)):
        rest = value[len(root) :]
        for separator in separators:
            rest = rest.replace(separator, "/")
        return "<temporary>" + rest
    return value


def normalized_command(command, report, temporary=None, os_name=None):
    """The command with its interpreter and temporary paths replaced; no flag is touched.

    With `temporary`, the root of the collection's temporary directory, only that root is replaced
    in a `--junitxml` or `--basetemp` value, and what follows it is kept, so the reducer sees the
    exact directory a command used. Without it (the conformance fixture's discovery child, whose
    root the collector does not know) the whole value is replaced. `os_name` is the platform whose
    separators count: the collector passes its own, which is the platform its receipt records;
    the reducer's expected commands, joined on the reducer's own platform, use the reducer's.
    """
    separators = PLATFORM_SEPARATORS[os_name or platform.system()]
    suffix = "tests" if report in ("companion", "host") else "child"
    normalized = []
    for index, part in enumerate(command):
        if index == 0:
            normalized.append("<python>")
        elif part.startswith(("--junitxml=", "--basetemp=")):
            flag, value = part.split("=", 1)
            if temporary is not None:
                normalized.append(f"{flag}={_under_temporary(value, temporary, separators)}")
            elif flag == "--junitxml":
                normalized.append(f"--junitxml=<temporary>/{report}.xml")
            else:
                normalized.append(f"--basetemp=<temporary>/{report}-{suffix}")
        else:
            normalized.append(part)
    return normalized


def expected_companion_command(os_name):
    command = companion_command("<python>", "<temporary>", os_name)
    return normalized_command(command, "companion", temporary="<temporary>")


def expected_host_command():
    """HOST's command as the reducer rebuilds it from this verifier's own constants."""
    return normalized_command(
        host_test_command("<python>", "<temporary>"), "host", temporary="<temporary>"
    )


def expected_inherited_command(os_name):
    """The ROUTE collector's own test command on `os_name`, with no added path, normalized."""
    command = route.commands_for("<python>", Path("<temporary>"), os_name)["tests"]
    return route.normalized_command(command, "tests")


def companion_command_digest(command):
    """The command digest: the normalized command and the contract substitution, together."""
    return digest_value({"command": command, "contract_substitution": CONTRACT_SUBSTITUTION})


def _version_minor(version):
    """The `major.minor` of a full version such as `3.14.0` or `3.12.9rc1`; else None."""
    match = (
        re.fullmatch(r"(\d+)\.(\d+)\.\d+[0-9A-Za-z.+-]*", version)
        if isinstance(version, str)
        else None
    )
    return f"{match.group(1)}.{match.group(2)}" if match else None


@contextlib.contextmanager
def workflow_commands_stopped():
    """Child output printed inside this block cannot issue workflow commands on a runner.

    The runner reads `::name::` lines in a job log as commands until it sees the token; the
    token is fresh, printed by this process only, and appears in no child's output.
    """
    token = secrets.token_hex(16)
    print(f"::stop-commands::{token}", flush=True)
    try:
        yield token
    finally:
        print(f"::{token}::", flush=True)


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
    """The whole environment of the inherited call and of HOST's command: the ROUTE allowlist
    and the named values (HOST_VARIABLES), nothing else."""
    env = {name: os.environ[name] for name in ROUTE_INHERITED_VARIABLES if name in os.environ}
    env.update(values)
    return env


def _repository(url):
    match = re.search(r"github\.com[:/]([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$", url or "")
    return match.group(1) if match else None


# A test id as pytest writes it: a file under tests/, one or more names, an optional parameter.
# No `.` or `..` segment, no empty segment, no absolute path.
_TEST_ID = re.compile(
    r"tests/(?:(?!\.{1,2}/)[\w.-]+/)*(?!\.{1,2}\.py)[\w.-]+\.py(?:::[A-Za-z_]\w*)+(?:\[.+\])?",
    re.DOTALL,
)
# Given to every git call of the cleanness check: no file-system monitor, which a checkout's own
# configuration could name as a command to run.
GIT_SAFE_OPTIONS = ("-c", "core.fsmonitor=false")


def git_config_digest(root):
    """A digest of a checkout's own git configuration and exclude files, read from disk.

    `config`, a worktree's `config.worktree`, and every file under `info/` (exclude, attributes,
    sparse-checkout). A missing file is recorded as missing; the result names no path.
    """
    dot = Path(root) / ".git"
    try:
        if dot.is_file():
            gitdir = Path(dot.read_text(encoding="utf-8").split("gitdir:", 1)[1].strip())
            gitdir = gitdir if gitdir.is_absolute() else (Path(root) / gitdir)
            common = gitdir
            if (gitdir / "commondir").is_file():
                common = gitdir / (gitdir / "commondir").read_text(encoding="utf-8").strip()
        else:
            gitdir = common = dot
        files = {"config": common / "config", "config.worktree": gitdir / "config.worktree"}
        for base, label in ((common, "info"), (gitdir, "worktree-info")):
            if (base / "info").is_dir():
                for path in sorted((base / "info").rglob("*")):
                    if path.is_file():
                        files[f"{label}/{path.relative_to(base / 'info').as_posix()}"] = path
        return digest_value(
            {
                name: hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
                for name, path in sorted(files.items())
            }
        )
    except OSError, IndexError, ValueError:
        return None


def git_environment(env, home):
    """The cleanness check's git environment: `env` without any HOME of a child's, with a home of
    its own that no child uses, an empty global configuration file in it, and no system
    configuration. So no user or system configuration (ignore files, attributes, filters,
    include targets) reaches these calls, on any platform."""
    config = Path(home) / "empty-gitconfig"
    config.write_bytes(b"")
    clean = {k: v for k, v in env.items() if k != "XDG_CONFIG_HOME"}
    clean.update(
        HOME=str(home),
        USERPROFILE=str(home),
        GIT_CONFIG_GLOBAL=str(config),
        GIT_CONFIG_NOSYSTEM="1",
    )
    return clean


def checkout_state(root, env, expected_config=None):
    """The repository, commit, cleanness and git configuration digest of a checkout; no path.

    The git calls run in `git_environment`. The configuration digest is taken first; when
    `expected_config` is given (the second reading) and the configuration has changed since,
    `git status` is not run at all, so that nothing a collection added to the configuration (a
    filter, say) can run, and the checkout is not reported clean.
    """
    with tempfile.TemporaryDirectory(prefix="jevdrill-git-home-") as home:
        git_env = git_environment(env, home)

        def git(*args):
            try:
                result = subprocess.run(
                    ["git", *GIT_SAFE_OPTIONS, "-C", str(root), *args],
                    capture_output=True,
                    text=True,
                    env=git_env,
                    timeout=30,
                    check=False,
                )
            except OSError, subprocess.SubprocessError:
                return None
            return result.stdout.strip() if result.returncode == 0 else None

        effective = git("config", "--list", "--show-origin", "--includes", "-z")
        files = git_config_digest(root)
        config = (
            digest_value({"files": files, "effective": effective})
            if files is not None and effective is not None
            else None
        )
        commit = git("rev-parse", "HEAD")
        repository = _repository(git("remote", "get-url", "origin"))
        changed = expected_config is not None and config != expected_config
        clean = False if changed else git("status", "--porcelain", "--untracked-files=all") == ""
    return {
        "repository": repository,
        "commit": commit if commit and _SHA.fullmatch(commit) else None,
        "clean": clean,
        "git_config_sha256": config,
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


# Run by this collector's own interpreter as the inherited part: one call of the unmodified ROUTE
# collector with no added path, whose receipt is written to the file named second.
INHERITED_CALL = r"""
import importlib.util, json, sys
from pathlib import Path
root = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("route_regressions", root / "scripts/verify_route_phase.py")
route = importlib.util.module_from_spec(spec)
spec.loader.exec_module(route)
Path(sys.argv[2]).write_text(json.dumps(route.collect(root)), encoding="utf-8")
"""


class ProcessTree:
    """Every process one child starts, so that all of them can be stopped together.

    On Linux and macOS the child leads a new session, so it and every descendant that stays in
    the session's process group are signalled together. While the child is still running (its
    bound was reached), the group is first frozen and every process still linked to the child
    by parentage is found, so that a descendant that started a session of its own is stopped
    too. A descendant that left the group and whose parent had already ended is not found. On
    Windows the child is assigned to a job object as soon as it exists; every process it starts
    afterwards is in the job, even once its parent has ended, and terminating the job ends them
    all. If the job cannot be made, `taskkill /T` stops the tree as linked at that moment.
    """

    POPEN_OPTIONS = {} if os.name == "nt" else {"start_new_session": True}

    def __init__(self, child):
        self.child = child
        self.job = _windows_job(child.pid) if os.name == "nt" else None

    def stop(self):
        """Stop every process of the tree; whether the stop was carried out.

        On Linux and macOS it is called before the child is reaped (`_await_exit` leaves it
        unreaped), so the child's process id still names its process group, and no other process
        can have taken it."""
        if os.name != "nt":
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(self.child.pid, signal.SIGSTOP)
            linked = _descendants(self.child.pid)
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(self.child.pid, signal.SIGKILL)
            for pid in sorted(linked):
                with contextlib.suppress(ProcessLookupError, PermissionError):
                    os.kill(pid, signal.SIGKILL)
            return True
        if self.job is not None:
            kernel32 = _kernel32()
            stopped = bool(kernel32.TerminateJobObject(self.job, 1))
            kernel32.CloseHandle(self.job)
            self.job = None
            return stopped
        try:
            result = subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(self.child.pid)],
                capture_output=True,
                env=_system_environment(),
                timeout=30,
                check=False,
            )
        except OSError, subprocess.SubprocessError:
            return False
        return result.returncode == 0


def _system_environment():
    """What a system tool (`ps`, `taskkill`) needs to start: the allowlist, nothing else."""
    return {name: os.environ[name] for name in INHERITED_VARIABLES if name in os.environ}


def _descendants(pid):
    """Every process linked to `pid` by parentage now, on Linux and macOS (`ps`)."""
    try:
        listing = subprocess.run(
            ["ps", "-A", "-o", "pid=", "-o", "ppid="],
            capture_output=True,
            text=True,
            env=_system_environment(),
            timeout=30,
            check=False,
        ).stdout
    except OSError, subprocess.SubprocessError:
        listing = None
    if listing is None or not listing.strip():
        # Without a listing no descendant outside the process group can be found.
        print("HOST collection: ps gave no process listing; only the group is stopped", flush=True)
        return set()
    children = {}
    for line in listing.splitlines():
        fields = line.split()
        if len(fields) == 2 and all(field.isdigit() for field in fields):
            children.setdefault(int(fields[1]), []).append(int(fields[0]))
    found, pending = set(), [pid]
    while pending:
        for child in children.get(pending.pop(), ()):
            if child not in found and child != pid:
                found.add(child)
                pending.append(child)
    return found


def _kernel32():
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    kernel32.TerminateJobObject.restype = wintypes.BOOL
    kernel32.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    return kernel32


def _windows_job(pid):
    """A job object holding the process `pid`, or None if one cannot be made."""
    kernel32 = _kernel32()
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        return None
    # PROCESS_SET_QUOTA | PROCESS_TERMINATE: what AssignProcessToJobObject needs.
    process = kernel32.OpenProcess(0x0100 | 0x0001, False, pid)
    assigned = bool(process) and bool(kernel32.AssignProcessToJobObject(job, process))
    if process:
        kernel32.CloseHandle(process)
    if not assigned:
        kernel32.CloseHandle(job)
        print("HOST collection: no job object; taskkill /T will stop this child", flush=True)
        return None
    return job


def _ended_unreaped(pid, timeout):
    """Whether process `pid` ended within `timeout` seconds, without reaping it; None if this
    platform offers no way (a process handle on Windows, a pidfd on Linux, kqueue on macOS)."""
    if os.name == "nt":
        # A handle of our own that can only wait: the child's `Popen` keeps its exit code unread
        # until the job is terminated, as on Linux and macOS the child stays unreaped.
        kernel32 = _kernel32()
        handle = kernel32.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
        if not handle:
            return None
        try:
            result = kernel32.WaitForSingleObject(handle, int(max(0, timeout) * 1000))
        finally:
            kernel32.CloseHandle(handle)
        return True if result == 0 else False if result == 0x102 else None  # WAIT_TIMEOUT
    if hasattr(os, "pidfd_open"):
        try:
            descriptor = os.pidfd_open(pid)
        except OSError:
            return None
        try:
            poller = select.poll()
            poller.register(descriptor, select.POLLIN)
            return bool(poller.poll(max(0, timeout) * 1000))
        finally:
            os.close(descriptor)
    if hasattr(select, "kqueue"):
        queue = select.kqueue()
        try:
            event = select.kevent(
                pid,
                filter=select.KQ_FILTER_PROC,
                flags=select.KQ_EV_ADD | select.KQ_EV_ENABLE | select.KQ_EV_ONESHOT,
                fflags=select.KQ_NOTE_EXIT,
            )
            try:
                events = queue.control([event], 1, max(0, timeout))
            except ProcessLookupError:
                return True  # it ended before it was registered: an unreaped zombie
            if any(e.flags & select.KQ_EV_ERROR and e.data == errno.ESRCH for e in events):
                return True
            return bool(events)
        finally:
            queue.close()
    return None


def _await_exit(child, timeout):
    """Return once the child has ended, or raise TimeoutExpired after `timeout` seconds.

    On every platform the child is left unreaped, so that the tree is stopped before the child is
    reaped (security finding N4a): on Linux and macOS its process id still names its group, and on
    Windows the job is terminated before `Popen` takes the child's exit code. Only where no way to
    wait without reaping is available is it waited for.
    """
    ended = _ended_unreaped(child.pid, timeout)
    if ended is False:
        raise subprocess.TimeoutExpired(child.args, timeout)
    if ended:
        return
    child.wait(timeout=timeout)


def _run(command, *, cwd, env, timeout, capture=True, launched=None):
    """Run one child once: (exit code, output, whether its deadline expired). No retry.

    When the child returns or its deadline expires, every process it started is stopped
    (ProcessTree). Output goes to a temporary file, not a pipe, so that a descendant still
    holding it cannot keep the collection waiting; with `capture=False` it goes to this
    process's own output instead. A child whose bound is already spent is not started.
    `launched`, when given, receives the argument list exactly as it was launched.
    """
    if timeout <= 0:
        return 125, b"TimeoutExpired\nthe bound was reached before this child started\n", True
    argv = list(command)
    with tempfile.TemporaryFile() as sink:
        try:
            child = subprocess.Popen(
                argv,
                cwd=cwd,
                env=env,
                stdout=sink if capture else None,
                stderr=subprocess.STDOUT if capture else None,
                **ProcessTree.POPEN_OPTIONS,
            )
        except OSError as error:
            return 125, type(error).__name__.encode(), False
        if launched is not None:
            launched.append(argv)
        tree = None
        expired = ended = False
        try:
            tree = ProcessTree(child)
            _await_exit(child, timeout)
            ended = True
        except subprocess.TimeoutExpired:
            expired = True
        finally:
            # On any way out, even an interruption, every process the child started is stopped,
            # before the child is reaped.
            if tree is None or not tree.stop():
                print("HOST collection: the process tree could not be stopped", flush=True)
            # Whatever the tree's stop did, a child that had not ended is killed before it is
            # waited for, and the wait is bounded: no failed stop can leave the collection waiting.
            if not ended:
                with contextlib.suppress(OSError):
                    child.kill()
            try:
                child.wait(timeout=KILLED_CHILD_WAIT_SECONDS)
            except subprocess.TimeoutExpired:
                print("HOST collection: a killed child did not end", flush=True)
        code = 125 if expired or child.returncode is None else child.returncode
        sink.seek(0)
        output = sink.read()
    return code, b"TimeoutExpired\n" + output if expired else output, expired


def collect(root, companion_root):
    """Collect one receipt, in a fixed order: the inherited call, HOST's command, the companion.

    One clock covers the collection. The inherited part is the time of the ROUTE collector call;
    HOST's part is the total less that. Each part's children are stopped at its bound.
    """
    started = time.monotonic()
    run = {
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "repository": os.environ.get("GITHUB_REPOSITORY"),
    }
    if not run["run_id"]:
        print(
            f"HOST collection outside CI: at most {TOTAL_LIMIT_SECONDS} seconds in total "
            f"({INHERITED_BOUND_SECONDS} for the inherited ROUTE regressions under ROUTE's own "
            f"deadline, a {INHERITED_WATCHDOG_GRACE_SECONDS}-second watchdog after it, and "
            f"{HOST_BOUND_SECONDS} for HOST's own part); every process a part started is stopped "
            "when it ends, and a receipt over either part's bound is rejected.",
            flush=True,
        )
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
    inherited_seconds = 0.0

    def host_remaining():
        # HOST's part is everything outside the ROUTE collector call, on the collection's clock.
        return HOST_BOUND_SECONDS - (time.monotonic() - started - inherited_seconds)

    with (
        tempfile.TemporaryDirectory(
            prefix="jevdrill-host-", dir=os.environ.get("RUNNER_TEMP"), ignore_cleanup_errors=True
        ) as temporary,
        workflow_commands_stopped(),
    ):
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
            timeout=min(30, host_remaining()),
        )
        if code != 0:
            print(output.decode(errors="replace")[-20000:], flush=True)
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
        host_values = dict(
            zip(
                HOST_VARIABLES,
                (str(companion_root), str(python), str(cli), str(witness_path)),
                strict=True,
            )
        )
        # 1. The inherited part: one call of the ROUTE collector, its command route.yml's own,
        # under its own 600-second budget. The collector's watchdog stops the call only after that
        # budget and its grace have passed. Its output goes straight to the log, as in route.yml.
        route_receipt = tmp / "route.json"
        call_started = time.monotonic()
        call_code, _, call_expired = _run(
            [sys.executable, "-c", INHERITED_CALL, str(root), str(route_receipt)],
            cwd=root,
            env=route_environment(**host_values),
            timeout=INHERITED_BOUND_SECONDS + INHERITED_WATCHDOG_GRACE_SECONDS,
            capture=False,
        )
        inherited_seconds = time.monotonic() - call_started
        print(
            f"inherited ROUTE regressions: {'returned' if call_code == 0 else 'FAILED'}"
            + (" (stopped by the collector's watchdog)" if call_expired else ""),
            flush=True,
        )
        try:
            inherited = json.loads(route_receipt.read_text(encoding="utf-8"))
        except OSError, ValueError:
            inherited = None
        if not isinstance(inherited, dict):
            inherited = {}
        if not run["run_id"] and "runner_identity" in inherited:
            # route.collect names the machine outside CI; a HOST receipt never does.
            inherited["runner_identity"] = "local"
        # 2. HOST's own controls, in a command of this collector's own.
        host_command = host_test_command(sys.executable, tmp)
        host_started = time.monotonic()
        host_launched = []
        host_code, host_output, host_expired = _run(
            host_command,
            cwd=root,
            env=route_environment(**host_values),
            timeout=host_remaining(),
            launched=host_launched,
        )
        host_command_seconds = time.monotonic() - host_started
        print(f"HOST controls: {'passed' if host_code == 0 else 'FAILED'}", flush=True)
        if host_code:
            print(host_output.decode(errors="replace")[-20000:], flush=True)
        try:
            host_assertions = assertions_from(tmp / "host.xml", root)
        except OSError, ET.ParseError:
            host_assertions = []
        # 3. The companion's own tests.
        command = companion_command(python, tmp, platform.system())
        companion_started = time.monotonic()
        companion_launched = []
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
            timeout=host_remaining(),
            launched=companion_launched,
        )
        companion_seconds = time.monotonic() - companion_started
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
            timeout=host_remaining(),
        )
        # After the last child: both checkouts again, so a collection that changed or dirtied
        # either is seen.
        jevdrill_after = checkout_state(
            root, child_environment(home), expected_config=jevdrill["git_config_sha256"]
        )
        companion_after = checkout_state(
            companion_root, child_environment(home), expected_config=companion["git_config_sha256"]
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
    # The receipt records each command as it was launched, not as it was built; a child that was
    # never started records an empty command.
    normalized = normalized_command(
        companion_launched[0] if companion_launched else [],
        "companion",
        temporary=tmp,
        os_name=platform.system(),
    )
    host_normalized = normalized_command(
        host_launched[0] if host_launched else [],
        "host",
        temporary=tmp,
        os_name=platform.system(),
    )
    copies = contract_copies(root, runtime)
    companion_stable = source_digest(runtime) == companion_before
    host_stable = input_digest(root) == before
    # Sampled after the last child, the checkouts' second reading, the final source digests and
    # the contract comparison; what follows hashes values in memory. Recorded unrounded.
    duration = time.monotonic() - started
    receipt = {
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
        "source_stable": host_stable,
        "inherited_call": {"exit_code": call_code, "deadline_expired": call_expired},
        "route_regressions": inherited,
        "host_controls": {
            "command": host_normalized,
            "command_sha256": digest_value(host_normalized),
            "exit_code": host_code,
            "deadline_expired": host_expired,
            "output_sha256": hashlib.sha256(host_output).hexdigest(),
            "assertions": host_assertions,
            "assertions_sha256": digest_value(host_assertions),
            "duration_seconds": host_command_seconds,
        },
        "companion": {
            **companion,
            "python": {
                "version": provenance.get("python_version"),
                "minor": _version_minor(provenance.get("python_version")),
            },
            "installed_provenance": provenance,
            "contract_copies": copies,
            "contract_substitution": CONTRACT_SUBSTITUTION,
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
            "command_sha256": companion_command_digest(normalized),
            "input_digest": companion_before,
            "source_stable": companion_stable,
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
        "checkouts_after": {"jevdrill": jevdrill_after, "companion": companion_after},
        # The two parts on the collection's one clock, and as information the time of the
        # companion's tests inside HOST's part (HOST's command's own is in `host_controls`).
        "parts": {
            "inherited_seconds": inherited_seconds,
            "host_seconds": duration - inherited_seconds,
            "companion_seconds": companion_seconds,
        },
        "duration_seconds": duration,
        "proof_cost_target_exceeded": duration > PROOF_COST_TARGET_SECONDS,
    }
    receipt["failed_ids"], receipt["failed_checks"] = failure_summary(receipt)
    return receipt


def failure_summary(manifest):
    """What failed, derived from the assertion lists and checks a receipt holds."""
    rows = [
        row
        for value in (
            _dict(manifest.get("route_regressions")).get("assertions"),
            _dict(manifest.get("host_controls")).get("assertions"),
            _dict(manifest.get("companion")).get("assertions"),
        )
        for row in _rows(value, "node_id")[0]
    ]
    checks = _dict(manifest.get("route_regressions")).get("checks")
    return (
        sorted(row["node_id"] for row in rows if row["outcome"] != "passed"),
        sorted(
            check["name"]
            for check in (checks if isinstance(checks, list) else [])
            if isinstance(check, dict)
            and isinstance(check.get("name"), str)
            and check.get("exit_code") != 0
        ),
    )


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


def _matching(rows, node):
    """The rows of `node`, a whole test or one of its parameters, whatever their outcome."""
    return [row for row in rows if row["node_id"] == node or row["node_id"].startswith(node + "[")]


def _seconds(value):
    """Whether `value` is a recorded time: a number of seconds, compared before any arithmetic."""
    return type(value) in (int, float) and 0 <= value <= MAX_RECORDED_SECONDS


def _is_digest(value):
    return isinstance(value, str) and _DIGEST.fullmatch(value) is not None


def _dotted(node):
    """A path id as the conformance fixture writes it: the JUnit class name, then the name."""
    path, _, name = node.partition("::")
    return path.removesuffix(".py").replace("/", ".") + "::" + name


def witness_errors(witness):
    errors = []
    if (
        not isinstance(witness, dict)
        or not isinstance(witness.get("records"), list)
        or not witness["records"]
    ):
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
        # The run list is validated as received: an entry that is not an object is an error,
        # never silently dropped.
        received = flow.get("runs")
        if not isinstance(received, list) or not all(isinstance(run, dict) for run in received):
            errors.append("malformed discovery run list")
        runs = (
            [run for run in received if isinstance(run, dict)] if isinstance(received, list) else []
        )
        # Each run names its task, model and effort as non-empty strings; a missing value is
        # never a second configuration.
        typed = True
        for key in ("task_id", "model", "effort"):
            if not all(isinstance(run.get(key), str) and run[key] for run in runs):
                errors.append(f"discovery run with no string {key}")
                typed = False
        if (
            len(runs) < 2
            or not typed
            or len({run.get("task_id") for run in runs}) != len(runs)
            or len({run.get("model") for run in runs}) < 2
            or len({run.get("effort") for run in runs}) < 2
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
    # The two counts are integers (a boolean is not one judgment), and the row names its task.
    judged = [row for row in records if row.get("flow") == "judged"]
    if (
        len(judged) != 1
        or judged[0].get("stored_function_revision") != "JudgeCandidate-v2"
        or type(judged[0].get("stored_judgments")) is not int
        or judged[0]["stored_judgments"] != 1
        or type(judged[0].get("loopback_judgment_requests")) is not int
        or judged[0]["loopback_judgment_requests"] != 1
        or judged[0].get("decision_status") != "ready"
        or not isinstance(judged[0].get("routing_decision_id"), str)
        or not judged[0]["routing_decision_id"]
        or not isinstance(judged[0].get("task_id"), str)
        or not judged[0]["task_id"]
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
        or type(receipt.get("exit_code")) is not int
        or receipt["exit_code"] != 0
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
    if python.get("minor") != COMPANION_PYTHON or _version_minor(python.get("version")) != (
        COMPANION_PYTHON
    ):
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
    if companion.get("contract_substitution") != CONTRACT_SUBSTITUTION:
        errors.append("companion receipt does not name the contract substitution")
    if companion.get("command_sha256") != companion_command_digest(expected):
        errors.append("companion command digest mismatch")
    if (
        companion.get("input_digest") != reference.get("digest")
        or companion.get("source_stable") is not True
    ):
        errors.append("stale or changed companion sources")
    if companion.get("deadline_expired") is not False:
        errors.append("companion tests exceeded the collection deadline")
    if (
        type(companion.get("exit_code")) is not int
        or companion["exit_code"] != 0
        or not _is_digest(companion.get("output_sha256"))
    ):
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


def _host_command_errors(host):
    """HOST's own command: rebuilt from this verifier's constants, run whole, every case passed."""
    errors = []
    expected = expected_host_command()
    if host.get("command") != expected:
        errors.append("HOST command is not the expected command")
    if host.get("command_sha256") != digest_value(expected):
        errors.append("HOST command digest mismatch")
    if host.get("deadline_expired") is not False:
        errors.append(f"HOST command stopped at HOST's {HOST_BOUND_SECONDS}-second bound")
    if (
        type(host.get("exit_code")) is not int
        or host["exit_code"] != 0
        or not _is_digest(host.get("output_sha256"))
    ):
        errors.append("HOST command failed")
    assertions, well_formed = _rows(host.get("assertions"), "node_id")
    if (
        not well_formed
        or not assertions
        or host.get("assertions_sha256") != digest_value(host.get("assertions"))
    ):
        errors.append("missing or malformed HOST command assertions")
    if len({row["node_id"] for row in assertions}) != len(assertions):
        errors.append("a test appears twice in HOST's command")
    errors.extend(
        f"malformed test id in HOST's command: {row['node_id'][:200]!r}"
        for row in assertions
        if not _TEST_ID.fullmatch(row["node_id"])
    )
    errors.extend(
        "failed or skipped test in HOST's command: " + row["node_id"]
        for row in assertions
        if row["outcome"] != "passed"
    )
    return errors


def _source_errors(inherited_rows, host_rows):
    """Each control counted exactly, from its one stated source; none found in both commands."""
    errors = []
    both = {row["node_id"] for row in inherited_rows} & {row["node_id"] for row in host_rows}
    errors.extend("a test ran in both commands: " + node for node in sorted(both))
    sources = {INHERITED: inherited_rows, HOST: host_rows}
    for node, count in CONTROL_COUNTS.items():
        source = CONTROL_SOURCES.get(node)
        if source not in sources:
            errors.append("control without a stated source: " + node)
            continue
        own = sources[source]
        other = sources[HOST if source == INHERITED else INHERITED]
        elsewhere = _matching(other, node)
        if elsewhere:
            errors.append("control counted from two sources: " + node)
        if _count(own, "node_id", node) != count or elsewhere:
            errors.append("HOST control count not exact: " + node)
        if any(row["outcome"] != "passed" for row in _matching(own, node) + elsewhere):
            errors.append("failed or skipped HOST control: " + node)
    return errors


def _time_errors(manifest, inner_duration):
    """The total, the two parts and their bounds, on the collection's one clock."""
    errors = []
    duration = manifest.get("duration_seconds")
    total_valid = _seconds(duration) and duration > 0
    if not total_valid:
        errors.append("no valid collection duration")
    else:
        if manifest.get("proof_cost_target_exceeded") is not (duration > PROOF_COST_TARGET_SECONDS):
            errors.append("misreported five-minute proof-cost flag")
        if type(inner_duration) not in (int, float) or not inner_duration <= duration:
            errors.append("inherited collection longer than its receipt's")
    parts = manifest.get("parts")
    host_command = _dict(manifest.get("host_controls")).get("duration_seconds")
    if (
        not isinstance(parts, dict)
        or set(parts) != {"inherited_seconds", "host_seconds", "companion_seconds"}
        or not all(_seconds(value) for value in parts.values())
        or not _seconds(host_command)
    ):
        errors.append("missing or malformed part time")
        return errors
    inherited_part, host_part = parts["inherited_seconds"], parts["host_seconds"]
    if inherited_part > INHERITED_BOUND_SECONDS:
        errors.append(f"inherited part over {INHERITED_BOUND_SECONDS} seconds")
    if host_part > HOST_BOUND_SECONDS:
        errors.append(f"HOST part over {HOST_BOUND_SECONDS} seconds")
    if total_valid and abs(inherited_part + host_part - duration) > PARTS_SUM_TOLERANCE:
        errors.append("parts do not sum to the total")
    if _seconds(inner_duration) and inherited_part + ROUTE_DURATION_ROUNDING < inner_duration:
        errors.append("inherited part shorter than the ROUTE receipt's own duration")
    if host_command + parts["companion_seconds"] > host_part + PARTS_SUM_TOLERANCE:
        errors.append("HOST command and companion times exceed HOST's part")
    return errors


def _platform_errors(manifest, identity, root, reference, handoff, route_digest):
    errors = []
    run = _dict(reference.get("run"))
    schema = manifest.get("schema_version")
    if (
        manifest.get("phase") != "HOST"
        or schema != SCHEMA_VERSION
        or manifest.get("execution_kind") != "native"
    ):
        errors.append("unsupported HOST receipt")
    if type(schema) is int and 0 < schema < SCHEMA_VERSION:
        # Its HOST controls ran inside the inherited command under one bound: nothing in it can
        # be read as the two parts this verifier requires.
        return [*errors, f"HOST receipt of an old shape (schema {schema})"]
    if manifest.get("input_digest") != reference.get("input_digest"):
        errors.append("stale HOST input digest")
    if manifest.get("source_stable") is not True:
        errors.append("HOST inputs changed during collection")
    workflow = _dict(manifest.get("workflow_run"))
    if (
        not run.get("run_id")
        or workflow.get("run_id") != run.get("run_id")
        or not isinstance(workflow.get("run_attempt"), str)
        or not workflow["run_attempt"]
        or workflow.get("run_attempt") != run.get("run_attempt")
        or workflow.get("repository") != run.get("repository")
        or manifest.get("runner_identity") != run.get("run_id")
    ):
        errors.append("receipt is not from this workflow run")
    if not isinstance(manifest.get("architecture"), str) or not manifest["architecture"]:
        errors.append("missing or malformed architecture")
    if _version_minor(manifest.get("python_version")) != identity[1]:
        errors.append("Python version disagrees with the receipt's minor")
    jevdrill, expected = _dict(manifest.get("jevdrill")), _dict(reference.get("jevdrill"))
    if (
        not expected.get("commit")
        or jevdrill.get("commit") != expected.get("commit")
        or jevdrill.get("repository") != run.get("repository")
        or jevdrill.get("clean") is not True
    ):
        errors.append("jevdrill checkout is not the reduced commit, or was not clean")
    jevdrill_after = _dict(_dict(manifest.get("checkouts_after")).get("jevdrill"))
    companion_after = _dict(_dict(manifest.get("checkouts_after")).get("companion"))
    companion_state = _dict(manifest.get("companion"))
    for before, after in ((jevdrill, jevdrill_after), (companion_state, companion_after)):
        if (
            any(after.get(key) != before.get(key) for key in ("repository", "commit", "clean"))
            or after.get("clean") is not True
        ):
            errors.append("a checkout changed or was left unclean by the collection")
        if not _is_digest(before.get("git_config_sha256")) or after.get(
            "git_config_sha256"
        ) != before.get("git_config_sha256"):
            errors.append("a checkout's git configuration changed during the collection")
    inherited = manifest.get("route_regressions")
    rows, _ = _rows(_dict(inherited).get("assertions"), "node_id")
    try:
        # The inherited command is ROUTE's own: no path is added (declared change 17).
        inherited_errors = route.reduce_manifests(
            [inherited], route_digest, root, required_platforms={identity}
        )
    # A malformed inherited receipt is a verdict, never a traceback.
    except AttributeError, IndexError, KeyError, TypeError, ValueError:
        inherited_errors = ["malformed inherited regressions"]
    errors.extend("ROUTE regression: " + error for error in inherited_errors)
    inner = _dict(inherited)
    checks = inner.get("checks")
    tests = (
        [check for check in checks if isinstance(check, dict) and check.get("name") == "tests"]
        if isinstance(checks, list)
        else []
    )
    if (
        len(tests) != 1
        or not isinstance(tests[0].get("command"), list)
        or not all(isinstance(part, str) for part in tests[0]["command"])
        or route.normalized_command(tests[0]["command"], "tests")
        != expected_inherited_command(identity[0])
    ):
        errors.append("inherited command differs from ROUTE's own")
    call = _dict(manifest.get("inherited_call"))
    if (
        type(call.get("exit_code")) is not int
        or call["exit_code"] != 0
        or call.get("deadline_expired") is not False
    ):
        errors.append("inherited ROUTE call failed or was stopped by the collector's watchdog")
    if inner.get("runner_identity") != manifest.get("runner_identity"):
        errors.append("inherited ROUTE receipt is from another run")
    if inner.get("python_minor") != identity[1] or inner.get("python_version") != manifest.get(
        "python_version"
    ):
        errors.append("inherited ROUTE receipt's Python disagrees with the receipt's")
    host = _dict(manifest.get("host_controls"))
    if not host:
        errors.append("missing HOST command receipt")
    errors.extend(_host_command_errors(host))
    host_rows, _ = _rows(host.get("assertions"), "node_id")
    errors.extend(_source_errors(rows, host_rows))
    if manifest.get("failed_ids") != failure_summary(manifest)[0]:
        errors.append("failed_ids disagrees with the assertions")
    if manifest.get("failed_checks") != failure_summary(manifest)[1]:
        errors.append("failed_checks disagrees with the checks")
    if not isinstance(manifest.get("companion"), dict) or not manifest["companion"]:
        errors.append("missing companion receipt")
    companion = _dict(manifest.get("companion"))
    errors.extend(
        _companion_errors(companion, identity[0], handoff, _dict(reference.get("companion")))
    )
    witness = manifest.get("witnesses")
    if manifest.get("witness_sha256") != digest_value(witness):
        errors.append("witness digest mismatch")
    errors.extend(witness_errors(witness))
    discovery = _dict(witness).get("companion_discovery")
    errors.extend(_discovery_errors(discovery, _dict(reference.get("companion")).get("digest")))
    # The witness's discovery ids and the integrated discovery receipt's are the same run.
    entered, _ = _rows(_dict(witness).get("assertions"), "id")
    integrated, _ = _rows(_dict(discovery).get("assertions"), "node_id")
    if sorted(
        (row["id"], row["outcome"])
        for row in entered
        if row["id"].startswith("tests.test_jevdrill_discovery::")
    ) != sorted((_dotted(row["node_id"]), row["outcome"]) for row in integrated):
        errors.append("the two discovery assertion lists disagree")
    static = _dict(manifest.get("host_static"))
    if (
        type(static.get("exit_code")) is not int
        or static["exit_code"] != 0
        or static.get("command") != list(HOST_STATIC_COMMAND)
        or not _is_digest(static.get("output_sha256"))
    ):
        errors.append("failed or wrong host static check")
    # Every range is checked before any arithmetic, so that no number can raise.
    errors.extend(_time_errors(manifest, inner.get("duration_seconds")))
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


class UnreadableReceipt:
    """A receipt file that could not be read as one unambiguous JSON object."""

    def __init__(self, reason):
        self.reason = reason


# Any of these, raised while one receipt is read or checked, is that receipt's error.
MALFORMED = (
    AttributeError,
    IndexError,
    KeyError,
    OverflowError,
    RecursionError,
    TypeError,
    ValueError,
)


def receipt_errors(manifests, reference, root=ROOT, *, required_platforms=None, names=None):
    """Every reason the receipts, the checkouts or the records cannot be accepted.

    `names`, when given, are the receipts' file names, in order; each must name the platform
    and minor its receipt states.
    """
    errors = []
    try:
        handoff = _handoff(root)
    except OSError, ValueError:
        handoff = {}
        errors.append("missing or malformed handoff record")
    reference = _dict(reference)
    if not _dict(reference.get("run")).get("run_id") or not _dict(reference.get("run")).get(
        "run_attempt"
    ):
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
    for index, manifest in enumerate(manifests):
        name = names[index] if names is not None and index < len(names) else None
        if isinstance(manifest, UnreadableReceipt):
            errors.append(f"unreadable HOST receipt {name or index}: {manifest.reason}")
            continue
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
        if nesting_depth(manifest) > MAX_RECEIPT_DEPTH:
            errors.append(
                f"{identity[0]}: malformed receipt (nesting deeper than {MAX_RECEIPT_DEPTH})"
            )
            continue
        if name is not None and name != f"{identity[0]}-{identity[1]}.json":
            errors.append(f"{identity[0]}: receipt file {name} names another platform")
        try:
            if "collection_error" in manifest:
                message = manifest["collection_error"]
                errors.append(
                    f"{identity[0]}: collection failed: "
                    + (message if isinstance(message, str) else "malformed collection error")
                )
                continue
            errors.extend(
                f"{identity[0]}: {error}"
                for error in _platform_errors(
                    manifest, identity, root, reference, handoff, route_digest
                )
            )
        except MALFORMED as error:
            # Reported, never raised: a number too large, nesting too deep, a wrong type.
            errors.append(f"{identity[0]}: malformed receipt ({type(error).__name__})")
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


# The deepest nesting a receipt may have. An honest receipt nests about ten levels (receipt,
# companion or witness, a list of records, a record, its runs, a run, its execution run).
# 64 leaves room for any honest growth while staying far below the depth at which any Python
# build's recursion (JSON parsing, digesting, rendering) could fail. Deeper input is refused by
# this explicit check, so no verdict depends on where an interpreter raises RecursionError.
MAX_RECEIPT_DEPTH = 64
# The most digits a JSON integer in a receipt may have; no honest field comes near it. Checked
# while parsing, so that no verdict depends on the interpreter's integer-string limit.
MAX_INTEGER_DIGITS = 100


class ReceiptFormatError(ValueError):
    """A receipt file that is valid JSON for no unambiguous, bounded reading."""


def _unique_keys(pairs):
    keys = [key for key, _ in pairs]
    if len(set(keys)) != len(keys):
        raise ReceiptFormatError("duplicate key")
    return dict(pairs)


def _bounded_integer(text):
    if len(text.lstrip("-")) > MAX_INTEGER_DIGITS:
        raise ReceiptFormatError(f"integer longer than {MAX_INTEGER_DIGITS} digits")
    return int(text)


def _no_constant(name):
    raise ReceiptFormatError(f"non-standard JSON constant {name}")


def nesting_depth(value):
    """The nesting depth of a JSON value, measured iteratively: no recursion, so no limit."""
    deepest, pending = 0, [(value, 1)]
    while pending:
        item, depth = pending.pop()
        if isinstance(item, dict | list):
            deepest = max(deepest, depth)
            if depth > MAX_RECEIPT_DEPTH:
                return depth
            pending.extend(
                (child, depth + 1) for child in (item.values() if isinstance(item, dict) else item)
            )
    return deepest


def read_receipts(directory):
    """(file name, receipt) for every receipt in the directory.

    A file that cannot be read as one unambiguous JSON object (unparsable, nested deeper than
    MAX_RECEIPT_DEPTH, an integer longer than MAX_INTEGER_DIGITS, a non-standard constant such
    as NaN, a duplicate key) is kept as an UnreadableReceipt and reported.
    """
    receipts = []
    for path in sorted(directory.glob("*.json")):
        try:
            value = json.loads(
                path.read_text(encoding="utf-8"),
                object_pairs_hook=_unique_keys,
                parse_int=_bounded_integer,
                parse_constant=_no_constant,
            )
            if nesting_depth(value) > MAX_RECEIPT_DEPTH:
                raise ReceiptFormatError(f"nesting deeper than {MAX_RECEIPT_DEPTH}")
        except ReceiptFormatError as error:
            value = UnreadableReceipt(str(error))
        # A backstop only: the explicit bounds above decide every case the tests name.
        except (OSError, RecursionError, ValueError) as error:
            value = UnreadableReceipt(type(error).__name__)
        receipts.append((path.name, value))
    return receipts


def verdict(manifests, reference, root=ROOT, *, names=None):
    errors = receipt_errors(manifests, reference, root, names=names)
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
            item["os"]
            for item in manifests
            if isinstance(item, dict)
            and isinstance(item.get("os"), str)
            and item.get("proof_cost_target_exceeded") is True
        ),
        "input_digest": reference.get("input_digest"),
        # The jevdrill commit this verdict judged, so that the artifact alone says so.
        "jevdrill": {
            key: _dict(reference.get("jevdrill")).get(key) for key in ("repository", "commit")
        },
        "companion": {
            key: _dict(reference.get("companion")).get(key)
            for key in ("repository", "commit", "digest")
        },
        "run": reference.get("run"),
        # Only a string is named: a malformed `os` is reported as an error, never rendered.
        "platforms": sorted(
            item["os"]
            for item in manifests
            if isinstance(item, dict) and isinstance(item.get("os"), str)
        ),
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
    receipts = read_receipts(platforms)
    report = verdict(
        [value for _, value in receipts], reference, ROOT, names=[name for name, _ in receipts]
    )
    (OUTPUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return int(report["status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
