"""Reusable query dependencies.

Keeping the filter parsing in one place guarantees every /api/cost route
validates query parameters identically (CLAUDE.md §39).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Annotated

from fastapi import Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy.orm import Session

from costlab.db.session import get_session
from costlab.schemas.common import Environment
from costlab.schemas.cost import CostFilters
from costlab.schemas.resources import ResourceFilters

SessionDep = Annotated[Session, Depends(get_session)]


def cost_filters(
    start_date: Annotated[
        date | None,
        Query(description="Inclusive start (ISO date). Defaults to oldest available data."),
    ] = None,
    end_date: Annotated[
        date | None,
        Query(description="Inclusive end (ISO date). Defaults to newest available data."),
    ] = None,
    project_id: Annotated[
        str | None,
        Query(max_length=64, description="GCP-style project id, e.g. cc-lab-shop-prod."),
    ] = None,
    service: Annotated[
        str | None,
        Query(max_length=64, description="Service slug, e.g. compute-engine."),
    ] = None,
    environment: Annotated[
        Environment | None,
        Query(description="development | staging | production"),
    ] = None,
    region: Annotated[
        str | None,
        Query(max_length=64, description="GCP region, e.g. us-central1."),
    ] = None,
    resource_id: Annotated[
        str | None,
        Query(max_length=128, description="Mock resource id, e.g. vm-shop-api-prod-1."),
    ] = None,
) -> CostFilters:
    try:
        return CostFilters(
            start_date=start_date,
            end_date=end_date,
            project_id=project_id,
            service=service,
            environment=environment,
            region=region,
            resource_id=resource_id,
        )
    except ValidationError as exc:
        # CostFilters is built here, not parsed by FastAPI, so surface its
        # validation errors as proper 422s instead of unhandled 500s.
        raise HTTPException(
            status_code=422, detail=f"Invalid filters: {exc.errors()[0]['msg']}"
        ) from exc


CostFiltersDep = Annotated[CostFilters, Depends(cost_filters)]


@dataclass(frozen=True)
class Pagination:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def pagination(
    page: Annotated[int, Query(ge=1, le=10_000, description="1-based page number.")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page (cap 100).")] = 25,
) -> Pagination:
    return Pagination(page=page, page_size=page_size)


PaginationDep = Annotated[Pagination, Depends(pagination)]


def resource_filters(
    project_id: Annotated[
        str | None, Query(max_length=64, description="GCP-style project id.")
    ] = None,
    service: Annotated[
        str | None, Query(max_length=64, description="Service slug, e.g. compute-engine.")
    ] = None,
    region: Annotated[
        str | None, Query(max_length=64, description="GCP region, e.g. us-central1.")
    ] = None,
    environment: Annotated[
        Environment | None, Query(description="development | staging | production")
    ] = None,
    status: Annotated[
        str | None, Query(max_length=32, description="Exact status, e.g. RUNNING.")
    ] = None,
    owner: Annotated[str | None, Query(max_length=64, description="Exact owner label.")] = None,
    team: Annotated[str | None, Query(max_length=64, description="Exact team label.")] = None,
    unallocated: Annotated[
        bool, Query(description="Only resources missing owner or team (UNALLOCATED).")
    ] = False,
) -> ResourceFilters:
    return ResourceFilters(
        project_id=project_id,
        service=service,
        region=region,
        environment=environment,
        status=status,
        owner=owner,
        team=team,
        unallocated=unallocated,
    )


ResourceFiltersDep = Annotated[ResourceFilters, Depends(resource_filters)]
