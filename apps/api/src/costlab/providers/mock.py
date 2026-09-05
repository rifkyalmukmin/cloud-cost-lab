"""Mock providers: read the deterministic dataset in `data/mock/` (ADR-003).

The JSON files are validated through the input schemas, so a malformed
dataset fails here — at the boundary — with a clear error, not later inside
PostgreSQL.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import TypeAdapter

from costlab.providers.base import BillingDataProvider, UsageDataProvider
from costlab.schemas.input import (
    BillingSnapshot,
    CostRecordInput,
    ProjectInput,
    ResourceInput,
    ServiceInput,
    UsageRecordInput,
)

_project_list = TypeAdapter(list[ProjectInput])
_service_list = TypeAdapter(list[ServiceInput])
_resource_list = TypeAdapter(list[ResourceInput])
_cost_list = TypeAdapter(list[CostRecordInput])
_usage_list = TypeAdapter(list[UsageRecordInput])


def _read_json(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Mock data file not found: {path}. Generate it with "
            "`python scripts/generate_mock_data.py` (see docs/local-development.md)."
        )
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"Mock data file must contain a JSON array: {path}")
    return payload


class MockBillingProvider(BillingDataProvider):
    name = "mock"

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    def load_snapshot(self) -> BillingSnapshot:
        services = _service_list.validate_python(_read_json(self.data_dir / "services.json"))
        projects = _project_list.validate_python(_read_json(self.data_dir / "projects.json"))
        resources = _resource_list.validate_python(_read_json(self.data_dir / "resources.json"))
        cost_records = _cost_list.validate_python(_read_json(self.data_dir / "cost.json"))
        return BillingSnapshot(
            source=f"mock:{self.data_dir}",
            services=services,
            projects=projects,
            resources=resources,
            cost_records=cost_records,
        )


class MockUsageProvider(UsageDataProvider):
    name = "mock"

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    def load_usage(self) -> list[UsageRecordInput]:
        return _usage_list.validate_python(_read_json(self.data_dir / "usage.json"))
