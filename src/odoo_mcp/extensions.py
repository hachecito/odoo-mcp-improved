"""
Integración de todos los módulos en el servidor MCP principal
"""

from fastmcp import FastMCP

from .prompts import register_all_prompts
from .resources import register_all_resources
from .tools_sales import register_sales_tools
from .tools_purchase import register_purchase_tools
from .tools_inventory import register_inventory_tools
from .tools_accounting import register_accounting_tools

def register_all_extensions(mcp: FastMCP) -> None:
    """
    Registra todas las extensiones (prompts, recursos y herramientas)
    en el servidor MCP
    """
    # Registrar prompts
    register_all_prompts(mcp)
    
    # Registrar recursos
    register_all_resources(mcp)
    
    # Registrar herramientas
    register_sales_tools(mcp)
    register_purchase_tools(mcp)
    register_inventory_tools(mcp)
    register_accounting_tools(mcp)
