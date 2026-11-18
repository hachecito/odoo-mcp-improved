"""
Integración de recursos para MCP-Odoo
"""

from fastmcp import FastMCP

def register_sales_resources(mcp: FastMCP) -> None:
    """Registra recursos relacionados con ventas"""
    pass

def register_purchase_resources(mcp: FastMCP) -> None:
    """Registra recursos relacionados con compras"""
    pass

def register_inventory_resources(mcp: FastMCP) -> None:
    """Registra recursos relacionados con inventario"""
    pass

def register_accounting_resources(mcp: FastMCP) -> None:
    """Registra recursos relacionados con contabilidad"""
    pass

def register_all_resources(mcp: FastMCP) -> None:
    """Registra todos los recursos disponibles"""
    register_sales_resources(mcp)
    register_purchase_resources(mcp)
    register_inventory_resources(mcp)
    register_accounting_resources(mcp)
