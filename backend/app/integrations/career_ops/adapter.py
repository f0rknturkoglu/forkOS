"""Central Anti-Corruption Adapter for career-ops."""

from __future__ import annotations

from pathlib import Path

from app.config import settings
from app.integrations.career_ops.capabilities import (
    get_capability_status,
    get_declared_capabilities,
)
from app.integrations.career_ops.doctor import CareerOpsDoctor
from app.integrations.career_ops.models import (
    CareerOpsCapability,
    CareerOpsDoctorResult,
    CareerOpsStatusEnum,
)
from app.integrations.career_ops.runner import CareerOpsRunner, SubprocessCareerOpsRunner


class CareerOpsAdapter:
    def __init__(
        self,
        enabled: bool | None = None,
        checkout_dir: Path | None = None,
        runtime_dir: Path | None = None,
        node_bin: str | None = None,
        runner: CareerOpsRunner | None = None,
    ) -> None:
        self.enabled = enabled if enabled is not None else settings.career_ops_enabled
        self.checkout_dir = (
            checkout_dir.resolve()
            if checkout_dir is not None
            else settings.resolved_career_ops_root
        )
        self.runtime_dir = (
            runtime_dir.resolve()
            if runtime_dir is not None
            else settings.resolved_career_ops_runtime_dir
        )
        self.node_bin = node_bin if node_bin is not None else settings.career_ops_node_bin

        if runner is not None:
            self.runner = runner
        else:
            self.runner = SubprocessCareerOpsRunner(
                checkout_dir=self.checkout_dir,
                runtime_dir=self.runtime_dir,
                node_bin=self.node_bin,
                default_timeout_seconds=settings.career_ops_timeout_seconds,
                max_buffer_bytes=settings.career_ops_max_buffer_bytes,
            )

        self._doctor = CareerOpsDoctor(
            enabled=self.enabled,
            checkout_dir=self.checkout_dir,
            runtime_dir=self.runtime_dir,
            runner=self.runner,
            node_bin=self.node_bin,
        )

    async def doctor(self) -> CareerOpsDoctorResult:
        return await self._doctor.run_diagnostics()

    async def capabilities(self) -> list[CareerOpsCapability]:
        doc = await self.doctor()
        ready = doc.status == CareerOpsStatusEnum.READY
        return [
            CareerOpsCapability(
                id=c.id,
                domain=c.domain,
                name=c.name,
                description=c.description,
                status=get_capability_status(c.id, enabled=self.enabled, runtime_ready=ready),
            )
            for c in get_declared_capabilities()
        ]
