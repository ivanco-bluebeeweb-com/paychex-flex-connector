"""Generic entity read layer for Paychex Flex Connector -- companies,
workers, payrolls, time-off-requests, benefits, using paychex_client's
per-resource path map.

WHY READ-ONLY THIS RELEASE. Paychex's write verbs require specific
partner-approved endpoint/verb combinations granted during Paychex's own
Developer Partner review (developer.paychex.com/partner) -- not
universally available. This connector covers the read surface plus the
value-add reports in handlers_reports.py.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import paychex_client as pc
from app import chat
from handlers_connection import resolve_or_error
from schemas import (
    ListEntitiesParams, EntityList,
    GetEntityParams, EntityDetail,
)


@chat.function(
    "list_entities",
    "List Paychex Flex records of any resource type (companies, workers, payrolls, time-off-requests, "
    "benefits). Some resources are company-scoped -- pass the company id via scope_id.",
    action_type="read", chain_callable=True, data_model=EntityList,
)
async def list_entities(ctx, params: ListEntitiesParams) -> ActionResult:
    """List Paychex records of a given resource type."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if not conn:
        return err
    path = pc.entity_path(params.entity, company_id=params.scope_id)
    if not path:
        return ActionResult.error(
            f"Unknown Paychex resource '{params.entity}'. Known resources: {', '.join(pc.known_entities())}.",
            code="PAYCHEX_VALIDATION_FAILED",
        )
    data = await pc.request(ctx, conn, "GET", path, action="list " + params.entity)
    rows = []
    if isinstance(data, dict):
        for key in ("content", "companies", "workers", "payrolls", "timeOffRequests", "benefits"):
            if isinstance(data.get(key), list):
                rows = data[key]
                break
    elif isinstance(data, list):
        rows = data
    return ActionResult.ok(EntityList(entity=params.entity, count=len(rows), records=rows))


@chat.function(
    "get_entity",
    "Read one Paychex Flex record of any resource type in full by its id.",
    action_type="read", chain_callable=True, data_model=EntityDetail,
)
async def get_entity(ctx, params: GetEntityParams) -> ActionResult:
    """Read one Paychex record by id."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if not conn:
        return err
    path = pc.entity_path(params.entity, company_id=params.scope_id)
    if not path:
        return ActionResult.error(
            f"Unknown Paychex resource '{params.entity}'. Known resources: {', '.join(pc.known_entities())}.",
            code="PAYCHEX_VALIDATION_FAILED",
        )
    data = await pc.request(ctx, conn, "GET", f"{path}/{params.record_id}", action="get " + params.entity)
    return ActionResult.ok(EntityDetail(entity=params.entity, record=data if isinstance(data, dict) else {}))
