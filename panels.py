"""Panel UI -- connections list/connect form + the one required "App
settings" entry point, same shape as Gusto/ADP/Xero Connector's panels.py.

SIDEBAR CONTENT -- NO CARDS ANYWHERE, per ~/UI_INTERFACE_STANDARD.md's
"left sidebar, no decorated cards" rule. Disconnect lives only in the
"App settings" screen (panels_settings.py). The one secondary "App
settings" button is always the LAST element at the bottom of the sidebar.

PER ~/UI_INTERFACE_STANDARD.md (2026-08-21 addendum): every Input carries
its own visible label (a ui.Text wrapping the ui.Input in a Stack -- ui.Input
itself does not accept label=), the placeholder text is always contextually
specific. The "How do I set this up?" instructions live ONLY in the help
overlay below -- never duplicated as static sidebar text.
"""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
import handlers_connection as h


def _settings_button() -> ui.UINode:
    return ui.Button(
        "App settings", variant="secondary", size="sm", full_width=True,
        icon="settings", on_click=ui.Call("__panel__paychex_settings"),
    )


def _connection_row(c: dict) -> ui.UINode:
    label = c.get("label") or "Paychex Flex connection"
    return ui.Stack(direction="v", gap=1, children=[
        ui.Text(label, variant="body"),
        ui.Text("Connected", variant="caption"),
    ])


def _connections_section(connections: list[dict]) -> ui.UINode:
    if not connections:
        return ui.Text("No Paychex Flex companies connected yet.", variant="caption")
    children: list[ui.UINode] = []
    for i, c in enumerate(connections):
        if i > 0:
            children.append(ui.Divider())
        children.append(_connection_row(c))
    return ui.Stack(direction="v", gap=2, children=children)


def _connect_section() -> ui.UINode:
    return ui.Stack(direction="v", gap=3, children=[
        ui.Button("How do I set this up?", variant="ghost", size="sm",
                  icon="HelpCircle",
                  on_click=ui.Call("__panel__paychex_connect_help")),
        ui.Form(
            action="connect_paychex",
            submit_label="Connect Paychex Flex",
            children=[
                ui.Stack(direction="v", gap=1, children=[
                    ui.Text("Paychex application Client ID", variant="caption"),
                    ui.Input(param_name="client_id", placeholder="Paste your Paychex app's Client ID"),
                ]),
                ui.Stack(direction="v", gap=1, children=[
                    ui.Text("Paychex application Client Secret", variant="caption"),
                    ui.Password(param_name="client_secret", placeholder="Paste your Paychex app's Client Secret"),
                ]),
                ui.Stack(direction="v", gap=1, children=[
                    ui.Text("Label (optional)", variant="caption"),
                    ui.Input(param_name="label", placeholder="e.g. Acme Inc Paychex"),
                ]),
            ],
        ),
    ])


@ext.panel("paychex_connect", slot="left", title="Paychex Flex")
async def paychex_connect_panel(ctx, **kwargs) -> object:
    connections = await h._load_connections(ctx)
    return ui.Stack(direction="v", gap=4, align="stretch", children=[
        ui.Header("Paychex Flex", level=2, subtitle="HR & payroll data, connected to your own company"),
        _connections_section(connections),
        ui.Divider(),
        _connect_section(),
        ui.Divider(),
        _settings_button(),
    ])


@ext.panel("paychex_connect_help", slot="overlay", title="How do I set this up?")
async def paychex_connect_help(ctx, **kwargs) -> object:
    content = ui.Stack(direction="v", gap=3, children=[
        ui.Text("1. Go to developer.paychex.com and apply to become a Paychex Developer Partner (partner approval is required before production API keys are issued)."),
        ui.Text("2. Once approved, register an application and copy its Client ID and Client Secret into the form on the left."),
        ui.Text("3. Click \"Connect Paychex Flex\" -- no browser login needed, the connection is validated immediately."),
        ui.Divider(),
        ui.Alert(
            title="Read-heavy in this release",
            message=(
                "Companies, workers, payrolls, time-off requests, and benefits are all "
                "covered for reading. Write operations (e.g. running payroll) require "
                "specific partner-approved verbs granted during Paychex's own review -- "
                "not automated here yet."
            ),
            type="info",
        ),
    ])
    return ui.Stack(direction="v", gap=2, children=[content])
