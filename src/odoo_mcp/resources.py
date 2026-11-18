"""
Odoo data resources for the MCP server, grouped by business domain
"""

import json

from mcp.server.fastmcp import FastMCP

from .odoo_client import get_odoo_client


def register_sales_resources(mcp: FastMCP) -> None:
    """Register sales-related resources"""

    @mcp.resource("odoo://sales/orders", description="List sales orders")
    def list_sales_orders() -> str:
        """Returns the 20 most recent sales orders"""
        client = get_odoo_client()
        try:
            orders = client.search_read(
                "sale.order",
                [],
                fields=["name", "partner_id", "date_order", "amount_total", "state"],
                limit=20,
                order="date_order desc",
            )
            return json.dumps(orders, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.resource(
        "odoo://sales/order/{order_id}",
        description="Get details of a specific sales order, including its lines",
    )
    def get_sales_order(order_id: str) -> str:
        """Returns one sales order with its order lines. Params: order_id"""
        client = get_odoo_client()
        try:
            order_id_int = int(order_id)
            orders = client.read_records(
                "sale.order",
                [order_id_int],
                fields=[
                    "name", "partner_id", "date_order", "amount_total",
                    "state", "order_line",
                ],
            )
            if not orders:
                return json.dumps(
                    {"error": f"Sales order not found: {order_id}"}, indent=2
                )

            order = orders[0]
            line_ids = order.pop("order_line", [])
            order["lines"] = (
                client.read_records(
                    "sale.order.line",
                    line_ids,
                    fields=["product_id", "product_uom_qty", "price_unit", "price_subtotal"],
                )
                if line_ids
                else []
            )
            return json.dumps(order, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.resource("odoo://sales/products", description="List sellable products")
    def list_sellable_products() -> str:
        """Returns up to 50 products marked as sellable (sale_ok)"""
        client = get_odoo_client()
        try:
            products = client.search_read(
                "product.product",
                [("sale_ok", "=", True)],
                fields=["name", "default_code", "list_price", "qty_available"],
                limit=50,
            )
            return json.dumps(products, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.resource("odoo://sales/customers", description="List customers")
    def list_customers() -> str:
        """Returns up to 50 partners with customer_rank > 0"""
        client = get_odoo_client()
        try:
            customers = client.search_read(
                "res.partner",
                [("customer_rank", ">", 0)],
                fields=["name", "email", "phone"],
                limit=50,
            )
            return json.dumps(customers, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)


def register_purchase_resources(mcp: FastMCP) -> None:
    """Register purchase-related resources"""

    @mcp.resource("odoo://purchase/orders", description="List purchase orders")
    def list_purchase_orders() -> str:
        """Returns the 20 most recent purchase orders"""
        client = get_odoo_client()
        try:
            orders = client.search_read(
                "purchase.order",
                [],
                fields=["name", "partner_id", "date_order", "amount_total", "state"],
                limit=20,
                order="date_order desc",
            )
            return json.dumps(orders, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.resource(
        "odoo://purchase/order/{order_id}",
        description="Get details of a specific purchase order, including its lines",
    )
    def get_purchase_order(order_id: str) -> str:
        """Returns one purchase order with its order lines. Params: order_id"""
        client = get_odoo_client()
        try:
            order_id_int = int(order_id)
            orders = client.read_records(
                "purchase.order",
                [order_id_int],
                fields=[
                    "name", "partner_id", "date_order", "amount_total",
                    "state", "order_line",
                ],
            )
            if not orders:
                return json.dumps(
                    {"error": f"Purchase order not found: {order_id}"}, indent=2
                )

            order = orders[0]
            line_ids = order.pop("order_line", [])
            order["lines"] = (
                client.read_records(
                    "purchase.order.line",
                    line_ids,
                    fields=["product_id", "product_qty", "price_unit", "price_subtotal"],
                )
                if line_ids
                else []
            )
            return json.dumps(order, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.resource("odoo://purchase/suppliers", description="List suppliers")
    def list_suppliers() -> str:
        """Returns up to 50 partners with supplier_rank > 0"""
        client = get_odoo_client()
        try:
            suppliers = client.search_read(
                "res.partner",
                [("supplier_rank", ">", 0)],
                fields=["name", "email", "phone"],
                limit=50,
            )
            return json.dumps(suppliers, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)


def register_inventory_resources(mcp: FastMCP) -> None:
    """Register inventory-related resources"""

    @mcp.resource(
        "odoo://inventory/products", description="List products in inventory"
    )
    def list_inventory_products() -> str:
        """Returns up to 50 products with their on-hand and forecast quantities"""
        client = get_odoo_client()
        try:
            products = client.search_read(
                "product.product",
                [],
                fields=["name", "default_code", "qty_available", "virtual_available"],
                limit=50,
            )
            return json.dumps(products, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.resource(
        "odoo://inventory/stock/{location_id}",
        description="Get stock levels at a specific location",
    )
    def get_stock_at_location(location_id: str) -> str:
        """Returns stock quants at one location. Params: location_id"""
        client = get_odoo_client()
        try:
            location_id_int = int(location_id)
            quants = client.search_read(
                "stock.quant",
                [("location_id", "=", location_id_int)],
                fields=["product_id", "quantity", "reserved_quantity"],
                limit=100,
            )
            return json.dumps(quants, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.resource(
        "odoo://inventory/movements", description="List inventory movements"
    )
    def list_inventory_movements() -> str:
        """Returns the 20 most recent stock moves"""
        client = get_odoo_client()
        try:
            moves = client.search_read(
                "stock.move",
                [],
                fields=[
                    "product_id", "location_id", "location_dest_id",
                    "product_uom_qty", "date", "state",
                ],
                limit=20,
                order="date desc",
            )
            return json.dumps(moves, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)


# account.account's type was exposed as user_type_id (a relation to
# account.account.type) on older Odoo versions, and as a plain account_type
# selection field on newer ones. Resolved at call time so this works either
# way instead of assuming one or the other.
_ACCOUNT_TYPE_FIELD_CANDIDATES = ["account_type", "user_type_id"]

# Report types supported by odoo://accounting/reports/{report_type}
_SUPPORTED_REPORTS = ["trial_balance"]


def register_accounting_resources(mcp: FastMCP) -> None:
    """Register accounting-related resources"""

    @mcp.resource("odoo://accounting/accounts", description="List accounting accounts")
    def list_accounts() -> str:
        """Returns up to 200 chart-of-accounts entries, ordered by code"""
        client = get_odoo_client()
        try:
            type_field = (
                client.pick_available_field(
                    "account.account", _ACCOUNT_TYPE_FIELD_CANDIDATES
                )
                or _ACCOUNT_TYPE_FIELD_CANDIDATES[0]
            )
            accounts = client.search_read(
                "account.account",
                [],
                fields=["code", "name", type_field],
                limit=200,
                order="code",
            )
            return json.dumps(accounts, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.resource(
        "odoo://accounting/journal_entries", description="List journal entries"
    )
    def list_journal_entries() -> str:
        """Returns the 20 most recent journal entries"""
        client = get_odoo_client()
        try:
            entries = client.search_read(
                "account.move",
                [],
                fields=["name", "journal_id", "date", "state", "amount_total", "move_type"],
                limit=20,
                order="date desc",
            )
            return json.dumps(entries, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    @mcp.resource(
        "odoo://accounting/reports/{report_type}",
        description="Get a financial report. Supported: trial_balance",
    )
    def get_financial_report(report_type: str) -> str:
        """Returns a financial report. Params: report_type ('trial_balance')"""
        if report_type not in _SUPPORTED_REPORTS:
            return json.dumps(
                {
                    "error": f"Unknown report type '{report_type}'",
                    "supported_report_types": _SUPPORTED_REPORTS,
                },
                indent=2,
            )

        client = get_odoo_client()
        try:
            # Sum debit/credit per account across posted journal entries
            groups = client.execute_method(
                "account.move.line",
                "read_group",
                [("parent_state", "=", "posted")],
                ["debit:sum", "credit:sum"],
                ["account_id"],
            )
            rows = [
                {
                    "account_id": g["account_id"][0] if g["account_id"] else None,
                    "account_name": g["account_id"][1] if g["account_id"] else None,
                    "debit": g["debit"],
                    "credit": g["credit"],
                    "balance": round(g["debit"] - g["credit"], 2),
                }
                for g in groups
            ]
            return json.dumps(rows, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)


def register_all_resources(mcp: FastMCP) -> None:
    """Register every resource available"""
    register_sales_resources(mcp)
    register_purchase_resources(mcp)
    register_inventory_resources(mcp)
    register_accounting_resources(mcp)
