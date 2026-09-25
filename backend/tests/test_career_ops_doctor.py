import pytest
from app.integrations.career_ops.adapter import CareerOpsAdapter
from app.integrations.career_ops.models import CareerOpsStatusEnum


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_doctor_disabled_status():
    adapter = CareerOpsAdapter(enabled=False)
    report = await adapter.doctor()
    assert report.status == CareerOpsStatusEnum.DISABLED


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_doctor_missing_checkout_status(tmp_path):
    adapter = CareerOpsAdapter(
        enabled=True,
        checkout_dir=tmp_path / "nonexistent",
        runtime_dir=tmp_path / "runtime",
    )
    report = await adapter.doctor()
    assert report.status == CareerOpsStatusEnum.UNAVAILABLE


@pytest.mark.no_database
@pytest.mark.asyncio
async def test_doctor_version_mismatch(tmp_path):
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text('{"name": "career-ops", "version": "9.9.9"}')
    (tmp_path / "doctor.mjs").write_text('console.log("{}");')
    (tmp_path / "path-resolver.mjs").write_text('export {};')

    adapter = CareerOpsAdapter(
        enabled=True,
        checkout_dir=tmp_path,
        runtime_dir=tmp_path / "runtime",
    )
    report = await adapter.doctor()
    assert report.status == CareerOpsStatusEnum.VERSION_MISMATCH
