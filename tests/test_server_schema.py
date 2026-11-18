"""
Offline regression tests for the MCP server's tool/resource schemas.

No Odoo connection needed: these only check that the server builds and
that its declared tool schemas are sane. They exist because a prior release
(1.0.6) shipped with every tool in tools_sales/purchase/inventory/accounting
silently broken: `ctx: Context` was no longer auto-injected because those
modules imported Context from a different package than the one server.py
used to build the actual FastMCP instance, so MCP clients were required to
supply `ctx` themselves and every call failed validation.
"""
import asyncio
import os

os.environ.setdefault("ODOO_URL", "http://localhost")
os.environ.setdefault("ODOO_DB", "test")
os.environ.setdefault("ODOO_USERNAME", "test")
os.environ.setdefault("ODOO_PASSWORD", "test")

from odoo_mcp.server import mcp  # noqa: E402  (env vars must be set first)


def test_server_imports():
    """Importing odoo_mcp.server must not raise."""
    assert mcp is not None


def test_no_tool_requires_ctx_from_the_client():
    """
    A Context-typed parameter must be auto-injected by FastMCP, never
    something the MCP client is asked to supply.
    """
    tools = asyncio.run(mcp.list_tools())
    assert len(tools) > 0

    offenders = [
        tool.name
        for tool in tools
        if "ctx" in tool.inputSchema.get("properties", {})
        or "ctx" in tool.inputSchema.get("required", [])
    ]
    assert not offenders, f"Tools requiring 'ctx' from the client: {offenders}"


def test_customer_insights_tool_is_registered():
    """get_customer_insights (README's Sales Tools table) must exist."""
    tools = asyncio.run(mcp.list_tools())
    names = {tool.name for tool in tools}
    assert "get_customer_insights" in names
