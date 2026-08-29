"""Pydantic params/result models for Paychex Flex Connector.

All params models are module-scope (V17 federal invariant, same rule as
Gusto/ADP/Xero/Sage Intacct Connector's schemas.py).
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class NoParams(BaseModel):
    """Explicit empty params model -- V17 disallows untyped handlers."""
    pass


class ConnectionScoped(BaseModel):
    connection_id: str = Field(
        "",
        description="Which connected Paychex Flex company to use (see list_connections). Omit if only one is connected.",
    )


# ──────────────────────────────────────────────────────────────────────────
# Connection -- Client Credentials, no browser redirect (same shape as ADP,
# minus the mTLS certificate requirement).
# ──────────────────────────────────────────────────────────────────────────


class ConnectPaychexParams(BaseModel):
    client_id: str = Field("", description="Your Paychex Developer Partner application's Client ID.")
    client_secret: str = Field("", description="Your Paychex Developer Partner application's Client Secret.")
    label: str = Field("", description="Optional friendly label for this connection, e.g. 'Acme Inc Paychex'.")


class ProviderConnection(BaseModel):
    id: str = ""
    label: str = ""
    company_name: str = ""


class ProviderConnectionList(BaseModel):
    connections: list[ProviderConnection] = Field(default_factory=list)


class DisconnectPaychexParams(BaseModel):
    connection_id: str = Field(description="Which connection to disconnect (see list_connections).")


class DeleteResult(BaseModel):
    deleted: bool = False
    id: str = ""


# ──────────────────────────────────────────────────────────────────────────
# Generic entity layer
# ──────────────────────────────────────────────────────────────────────────


class ListEntitiesParams(ConnectionScoped):
    entity: str = Field(description="Resource type: companies, workers, payrolls, time-off-requests, benefits.")
    scope_id: str = Field("", description="Company id, required for company-scoped resources (workers, payrolls, time-off-requests, benefits).")
    filter_expr: str = Field("", description="Optional filter expression supported by the resource (e.g. companyId).")
    limit: int = Field(50, ge=1, le=200, description="Maximum records to return.")


class EntityList(BaseModel):
    entity: str = ""
    count: int = 0
    records: list[dict] = Field(default_factory=list)


class GetEntityParams(ConnectionScoped):
    entity: str = Field(description="Resource type, same values as list_entities.")
    scope_id: str = Field("", description="Company id, required for company-scoped resources.")
    record_id: str = Field(description="The record's Paychex id.")


class EntityDetail(BaseModel):
    entity: str = ""
    record: dict = Field(default_factory=dict)


# ──────────────────────────────────────────────────────────────────────────
# Org info + value-add reports
# ──────────────────────────────────────────────────────────────────────────


class GetCompanyInfoParams(ConnectionScoped):
    pass


class CompanyInfo(BaseModel):
    company_name: str = ""
    worker_count: int = 0


class HeadcountReport(BaseModel):
    total_workers: int = 0
    by_status: dict[str, int] = Field(default_factory=dict)


class UpcomingPayrollReport(BaseModel):
    found: bool = False
    pay_date: str = ""
    period_start: str = ""
    period_end: str = ""
    status: str = ""
