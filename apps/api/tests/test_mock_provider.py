"""Provider loading tests: the mock dataset must load, validate and be deterministic."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from costlab.config import Settings
from costlab.providers import build_providers
from costlab.providers.base import RealBillingProvider, RealUsageProvider
from costlab.providers.mock import MockBillingProvider, MockUsageProvider

MOCK_DIR = Path(__file__).resolve().parents[3] / "data" / "mock"


def test_mock_billing_provider_loads_snapshot() -> None:
    snapshot = MockBillingProvider(MOCK_DIR).load_snapshot()
    assert len(snapshot.services) == 4
    assert len(snapshot.projects) == 4
    assert len(snapshot.resources) == 12
    assert len(snapshot.cost_records) == 1164
    assert snapshot.source == f"mock:{MOCK_DIR}"


def test_mock_usage_provider_loads_usage() -> None:
    usage = MockUsageProvider(MOCK_DIR).load_usage()
    assert len(usage) == 1164
    # every environment must be represented in resources via cost rows; here we
    # check the idle-VM scenario data is actually present in the dataset
    idle = [u for u in usage if u.resource_id == "vm-report-dev-1"]
    assert idle, "idle VM must exist in the mock dataset"
    assert max(u.cpu_utilization for u in idle if u.cpu_utilization is not None) < 5.0


def test_mock_dataset_is_deterministic() -> None:
    snapshot_a = MockBillingProvider(MOCK_DIR).load_snapshot()
    snapshot_b = MockBillingProvider(MOCK_DIR).load_snapshot()
    assert snapshot_a == snapshot_b


def test_mock_provider_rejects_invalid_data(tmp_path: Path) -> None:
    """Valid JSON structure with an invalid value fails at the provider boundary."""
    (tmp_path / "services.json").write_text(json.dumps([]), encoding="utf-8")
    (tmp_path / "projects.json").write_text(json.dumps([]), encoding="utf-8")
    (tmp_path / "resources.json").write_text(json.dumps([]), encoding="utf-8")
    (tmp_path / "cost.json").write_text(
        json.dumps(
            [
                {
                    "resource_id": "vm-x",
                    "project_id": "p",
                    "service_id": "s",
                    "sku": "sku",
                    "region": "r",
                    "usage_date": "2026-01-01",
                    "usage_amount": 1,
                    "usage_unit": "hours",
                    "cost": -5,
                    "credits": 0,
                    "net_cost": -5,
                    "currency": "USD",
                    "environment": "production",
                }
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        MockBillingProvider(tmp_path).load_snapshot()


def test_mock_provider_missing_file_has_clear_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="generate_mock_data"):
        MockBillingProvider(tmp_path).load_snapshot()


def test_real_providers_fail_loudly() -> None:
    with pytest.raises(NotImplementedError, match="Phase 9"):
        RealBillingProvider().load_snapshot()
    with pytest.raises(NotImplementedError, match="Phase 9"):
        RealUsageProvider().load_usage()


def test_provider_factory_selects_by_demo_mode() -> None:
    mock_providers = build_providers(Settings(demo_mode=True, mock_data_dir=str(MOCK_DIR)))
    assert isinstance(mock_providers.billing, MockBillingProvider)
    assert isinstance(mock_providers.usage, MockUsageProvider)

    real_providers = build_providers(Settings(demo_mode=False))
    assert isinstance(real_providers.billing, RealBillingProvider)
    assert isinstance(real_providers.usage, RealUsageProvider)
