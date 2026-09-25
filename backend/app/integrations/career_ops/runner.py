"""Subprocess execution boundary and workspace isolation for career-ops."""

from __future__ import annotations

import asyncio
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.integrations.career_ops.errors import (
    CareerOpsExecutionError,
    CareerOpsInvalidOutputError,
    CareerOpsSecurityError,
    CareerOpsTimeoutError,
    CareerOpsUnavailableError,
)

ALLOWLISTED_SCRIPTS: frozenset[str] = frozenset({
    "doctor.mjs",
})


@dataclass(frozen=True)
class ExecutionResult:
    script_name: str
    exit_code: int
    stdout: str
    stderr: str


class CareerOpsRunner(Protocol):
    async def run_script(
        self,
        script_name: str,
        args: list[str],
        timeout_seconds: float | None = None,
    ) -> ExecutionResult:
        ...


class _BufferExceededError(Exception):
    """Internal sentinel when stream reading exceeds bounded budget."""


async def _read_stream_bounded(
    stream: asyncio.StreamReader,
    max_bytes: int,
) -> bytearray:
    buf = bytearray()
    chunk_size = 4096
    while True:
        chunk = await stream.read(chunk_size)
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) > max_bytes:
            raise _BufferExceededError()
    return buf


class SubprocessCareerOpsRunner:
    def __init__(
        self,
        checkout_dir: Path,
        runtime_dir: Path,
        node_bin: str = "node",
        default_timeout_seconds: float = 30.0,
        max_buffer_bytes: int = 512 * 1024,
    ) -> None:
        self.checkout_dir = checkout_dir.resolve()
        self.runtime_dir = runtime_dir.resolve()
        self.node_bin = node_bin
        self.default_timeout_seconds = default_timeout_seconds
        self.max_buffer_bytes = max_buffer_bytes

    def _ensure_workspace(self) -> tuple[Path, Path, Path]:
        gen_in = self.runtime_dir / "generated-input"
        temp_out = self.runtime_dir / "temporary-output"
        cache = self.runtime_dir / "cache"
        gen_in.mkdir(parents=True, exist_ok=True)
        temp_out.mkdir(parents=True, exist_ok=True)
        cache.mkdir(parents=True, exist_ok=True)
        return gen_in, temp_out, cache

    def _build_env(self) -> dict[str, str]:
        # Clean environment: keep essential path variables, strip credentials
        safe_keys = {"PATH", "HOME", "USER", "TMPDIR", "LANG", "LC_ALL"}
        clean_env = {k: v for k, v in os.environ.items() if k in safe_keys}

        # Inject isolated workspace overrides
        clean_env["CAREER_OPS_ROOT"] = str(self.runtime_dir)
        clean_env["CAREER_OPS_DATA_DIR"] = str(self.runtime_dir)
        clean_env["CAREER_OPS_TRACKER"] = str(self.runtime_dir / "ephemeral-tracker.md")
        clean_env["NODE_ENV"] = "production"
        return clean_env

    async def run_script(
        self,
        script_name: str,
        args: list[str],
        timeout_seconds: float | None = None,
    ) -> ExecutionResult:
        if script_name not in ALLOWLISTED_SCRIPTS:
            raise CareerOpsSecurityError(f"Script '{script_name}' is not in allowlisted operations.")

        target_script = self.checkout_dir / script_name
        if not target_script.exists():
            raise CareerOpsUnavailableError(f"Script file '{target_script}' does not exist.")

        node_path = shutil.which(self.node_bin)
        if not node_path:
            raise CareerOpsUnavailableError(f"Node executable '{self.node_bin}' not found on PATH.")

        self._ensure_workspace()
        env = self._build_env()
        cmd = [node_path, str(target_script)] + list(args)

        timeout = timeout_seconds if timeout_seconds is not None else self.default_timeout_seconds

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.checkout_dir),
                env=env,
            )
        except OSError as exc:
            raise CareerOpsUnavailableError(f"Failed to spawn node process: {exc}") from exc

        stdout_buf = bytearray()
        stderr_buf = bytearray()

        async def _drain_proc() -> None:
            nonlocal stdout_buf, stderr_buf
            assert proc.stdout is not None
            assert proc.stderr is not None
            out_res, err_res = await asyncio.gather(
                _read_stream_bounded(proc.stdout, self.max_buffer_bytes),
                _read_stream_bounded(proc.stderr, self.max_buffer_bytes),
            )
            stdout_buf = out_res
            stderr_buf = err_res
            await proc.wait()

        async def _kill_process() -> None:
            if proc.returncode is None:
                try:
                    proc.terminate()
                    await asyncio.wait_for(proc.wait(), timeout=0.5)
                except Exception:
                    try:
                        proc.kill()
                        await proc.wait()
                    except Exception:
                        pass

        try:
            await asyncio.wait_for(_drain_proc(), timeout=timeout)
        except _BufferExceededError:
            await _kill_process()
            raise CareerOpsInvalidOutputError(
                f"Script '{script_name}' exceeded maximum output buffer ({self.max_buffer_bytes} bytes)."
            )
        except TimeoutError as exc:
            await _kill_process()
            raise CareerOpsTimeoutError(
                f"Script '{script_name}' timed out after {timeout} seconds."
            ) from exc
        except Exception:
            await _kill_process()
            raise

        stdout_str = stdout_buf.decode("utf-8", errors="replace")
        stderr_str = stderr_buf.decode("utf-8", errors="replace")

        return ExecutionResult(
            script_name=script_name,
            exit_code=proc.returncode if proc.returncode is not None else -1,
            stdout=stdout_str,
            stderr=stderr_str,
        )
