"""Org info + value-add reports for Paychex Flex Connector -- same
"value-add on top of raw API" shape as ADP/Gusto Connector's
handlers_reports.py.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import paychex_client as pc
from app import chat
from handlers_connection import resolve_or_error
from schemas import (
    GetCompanyInfoParams, CompanyInfo,
    HeadcountReport,
    UpcomingPayrollReport,
)


@chat.function(
    "get_company_info",
    "Read the connected Paychex Flex company's own profile: company name and total worker count.",
    action_type="read", chain_callable=True, data_model=CompanyInfo,
)
async def get_company_info(ctx, params: GetCompanyInfoParams) -> ActionResult:
    """Read basic company profile info."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if not conn:
        return err
    data = await pc.request(ctx, conn, "GET", "/companies", action="get company info")
    companies = data.get("content", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    name = companies[0].get("companyName", "") if companies else ""
    return ActionResult.ok(CompanyInfo(company_name=name, worker_count=len(companies)))


@chat.function(
    "get_headcount_report",
    "Value-add report: one-glance headcount for the connected Paychex Flex company -- total worker count "
    "broken down by employment status.",
    action_type="read", chain_callable=True, data_model=HeadcountReport,
)
async def get_headcount_report(ctx, params: GetCompanyInfoParams) -> ActionResult:
    """Scan workers and bucket them by employment status."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if not conn:
        return err
    data = await pc.request(ctx, conn, "GET", "/companies", action="list companies for headcount")
    companies = data.get("content", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    by_status: dict[str, int] = {}
    total = 0
    for co in companies:
        cid = co.get("companyId") or co.get("id")
        if not cid:
            continue
        wdata = await pc.request(ctx, conn, "GET", f"/companies/{cid}/workers", action="list workers for headcount")
        workers = wdata.get("content", []) if isinstance(wdata, dict) else (wdata if isinstance(wdata, list) else [])
        for w in workers:
            status = (w.get("status") or w.get("employmentStatus") or "unknown")
            by_status[status] = by_status.get(status, 0) + 1
            total += 1
    return ActionResult.ok(HeadcountReport(total_workers=total, by_status=by_status))


@chat.function(
    "get_upcoming_payroll_report",
    "Value-add report: read the next unprocessed (upcoming) payroll's pay date and period for the "
    "connected Paychex Flex company.",
    action_type="read", chain_callable=True, data_model=UpcomingPayrollReport,
)
async def get_upcoming_payroll_report(ctx, params: GetCompanyInfoParams) -> ActionResult:
    """Find the next upcoming payroll by pay date."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if not conn:
        return err
    data = await pc.request(ctx, conn, "GET", "/companies", action="list companies for payroll")
    companies = data.get("content", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    for co in companies:
        cid = co.get("companyId") or co.get("id")
        if not cid:
            continue
        pdata = await pc.request(ctx, conn, "GET", f"/companies/{cid}/payrolls", action="list payrolls for upcoming report")
        payrolls = pdata.get("content", []) if isinstance(pdata, dict) else (pdata if isinstance(pdata, list) else [])
        for p in payrolls:
            if (p.get("status") or "").lower() in ("scheduled", "pending", "upcoming", "draft"):
                return ActionResult.ok(UpcomingPayrollReport(
                    found=True,
                    pay_date=p.get("payDate", ""),
                    period_start=p.get("periodStart", "") or p.get("startDate", ""),
                ))
    return ActionResult.ok(UpcomingPayrollReport(found=False))
