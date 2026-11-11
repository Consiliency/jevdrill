"""Restricted execution of copied development inputs in an existing Linux image."""

import json
import subprocess
import sys
import tempfile
from threading import Thread
from time import monotonic, time
from typing import Any
from uuid import UUID, uuid4

from ..contracts import ContractError

NODE_EVALUATOR = """
const fs = require('node:fs');
const {source, inputs} = JSON.parse(fs.readFileSync(0, 'utf8'));
const original = JSON.stringify(inputs);
const solve = new Function(source + '; return solve;')();
const answers = inputs.map(args => solve(...args));
process.stdout.write(JSON.stringify({answers, inputs_unchanged: JSON.stringify(inputs) === original}));
"""


class RestrictedContainerRunner:
    def __init__(self, image_id: str) -> None:
        if not image_id.startswith("sha256:") or len(image_id) != 71:
            raise ContractError("an inspected immutable container image is required")
        self.image_id = image_id

    @staticmethod
    def container_name(run_id: str) -> str:
        return "jevdrill-development-" + UUID(run_id).hex

    def cleanup(self, run_id: str) -> None:
        cleanup = subprocess.run(
            ["docker", "rm", "--force", self.container_name(run_id)],
            capture_output=True,
            timeout=2,
            check=False,
        )
        if cleanup.returncode and b"No such container" not in cleanup.stderr:
            raise ContractError("container cleanup unverified; stop experiments")

    def evaluate(
        self,
        source: str,
        inputs: list[Any],
        deadline: float,
        *,
        run_id: str | None = None,
        custody_fd: int | None = None,
    ) -> dict[str, Any]:
        if sys.platform != "linux":
            raise ContractError("restricted_linux_runtime_required")
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise ContractError("experiment deadline expired")
        name = self.container_name(run_id) if run_id else "jevdrill-pilot-" + uuid4().hex
        command = [
            "docker",
            "run",
            "--rm",
            "--pull=never",
            "--name",
            name,
            "--network=none",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--pids-limit=64",
            "--cpus=2",
            "--memory=2g",
            "--memory-swap=2g",
            "--user=65534:65534",
            "--log-driver=none",
            "--ulimit=nofile=64:64",
            "-i",
            "--entrypoint=sh",
            self.image_id,
        ]
        if run_id:
            # The trusted PID-1 watchdog outlives the Python worker and kills the
            # whole PID namespace at the deadline, even for synchronous loops.
            command.extend(
                [
                    "-c",
                    (
                        'remaining=$(( $1 - $(date +%s) )); [ "$remaining" -gt 0 ] || exit 124; '
                        'exec timeout --foreground -s KILL "$remaining" node --max-old-space-size=1024 -e "$2"'
                    ),
                    "jevdrill-deadline",
                    str(int(time() + remaining)),
                    NODE_EVALUATOR,
                ]
            )
        else:
            command.extend(
                [
                    "-c",
                    'exec timeout -s KILL "$1" node --max-old-space-size=1024 -e "$2"',
                    "jevdrill-deadline",
                    str(max(1, int(remaining))),
                    NODE_EVALUATOR,
                ]
            )
        started = monotonic()
        try:
            with tempfile.TemporaryFile() as stdin:
                stdin.write(json.dumps({"source": source, "inputs": inputs}).encode())
                stdin.seek(0)
                process = subprocess.Popen(
                    command,
                    stdin=stdin,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    pass_fds=() if custody_fd is None else (custody_fd,),
                )
                output: list[bytes] = []

                def read_output() -> None:
                    assert process.stdout is not None
                    output.append(process.stdout.read(65_537))
                    if len(output[0]) > 65_536 and process.poll() is None:
                        process.kill()

                reader = Thread(target=read_output, daemon=True)
                reader.start()
                try:
                    process.wait(timeout=remaining)
                finally:
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=5)
                    reader.join(timeout=5)
                    if reader.is_alive():
                        raise ContractError("container output collection did not stop")
                    assert process.stdout is not None
                    process.stdout.close()
                payload = output[0]
                if process.returncode or len(payload) > 65_536:
                    return {"status": "failed", "answers": None}
                try:
                    decoded = json.loads(payload)
                except (ValueError, UnicodeError):
                    return {"status": "invalid_output", "answers": None}
                if not isinstance(decoded, dict) or set(decoded) != {"answers", "inputs_unchanged"}:
                    return {"status": "invalid_output", "answers": None}
                return {
                    "status": "completed" if monotonic() <= deadline else "timeout",
                    "answers": decoded["answers"],
                    "inputs_unchanged": decoded["inputs_unchanged"],
                    "duration_ms": int((monotonic() - started) * 1000),
                    "image_id": self.image_id,
                }
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "answers": None}
        finally:
            cleanup = subprocess.run(
                ["docker", "rm", "--force", name], capture_output=True, timeout=10, check=False
            )
            if cleanup.returncode and b"No such container" not in cleanup.stderr:
                raise ContractError("container cleanup unverified; stop experiments")
