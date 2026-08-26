from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.services.resource_service import resource_service

router = APIRouter(prefix="/api/resources", tags=["resources"])


@router.get("")
def list_resources(
    project: Optional[str] = Query(None, description="Filter by project ID"),
    service: Optional[str] = Query(None, description="Filter by service ID"),
    region: Optional[str] = Query(None, description="Filter by region"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    status: Optional[str] = Query(None, description="Filter by status"),
    owner: Optional[str] = Query(None, description="Filter by owner"),
    team: Optional[str] = Query(None, description="Filter by team"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """List cloud resources with filtering and pagination."""
    return resource_service.list_resources(
        project=project,
        service=service,
        region=region,
        environment=environment,
        status=status,
        owner=owner,
        team=team,
        page=page,
        page_size=page_size,
    )


@router.get("/{resource_id}")
def get_resource(resource_id: str):
    """Get detailed resource information including cost and utilization history."""
    result = resource_service.get_resource(resource_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Resource '{resource_id}' not found")
    return result
