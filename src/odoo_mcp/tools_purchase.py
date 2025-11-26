"""
Implementación de herramientas (tools) para compras en MCP-Odoo
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from fastmcp import FastMCP, Context

from .models import (
    PurchaseOrderFilter,
    PurchaseOrderCreate,
    SupplierPerformanceInput
)

def register_purchase_tools(mcp: FastMCP) -> None:
    """Registra herramientas relacionadas con compras"""
    
    @mcp.tool(description="Busca órdenes de compra con filtros avanzados")
    def search_purchase_orders(
        ctx: Context,
        filters: PurchaseOrderFilter
    ) -> Dict[str, Any]:
        """
        Busca órdenes de compra según los filtros especificados
        
        Args:
            filters: Filtros para la búsqueda de órdenes
            
        Returns:
            Diccionario con resultados de la búsqueda
        """
        odoo = ctx.request_context.lifespan_context.odoo
        
        try:
            # Construir dominio de búsqueda
            domain = []
            
            if filters.partner_id:
                domain.append(("partner_id", "=", filters.partner_id))
                
            if filters.date_from:
                try:
                    datetime.strptime(filters.date_from, "%Y-%m-%d")
                    domain.append(("date_order", ">=", filters.date_from))
                except ValueError:
                    return {"success": False, "error": f"Formato de fecha inválido: {filters.date_from}. Use YYYY-MM-DD."}
                
            if filters.date_to:
                try:
                    datetime.strptime(filters.date_to, "%Y-%m-%d")
                    domain.append(("date_order", "<=", filters.date_to))
                except ValueError:
                    return {"success": False, "error": f"Formato de fecha inválido: {filters.date_to}. Use YYYY-MM-DD."}
                
            if filters.state:
                domain.append(("state", "=", filters.state))
            
            # Campos a recuperar
            fields = [
                "name", "partner_id", "date_order", "amount_total", 
                "state", "invoice_status", "user_id", "order_line",
                "date_planned", "date_approve"
            ]
            
            # Ejecutar búsqueda
            orders = odoo.search_read(
                "purchase.order", 
                domain, 
                fields=fields, 
                limit=filters.limit,
                offset=filters.offset,
                order=filters.order
            )
            
            # Obtener el conteo total sin límite para paginación
            total_count = odoo.execute_method("purchase.order", "search_count", domain)
            
            return {
                "success": True, 
                "result": {
                    "count": len(orders),
                    "total_count": total_count,
                    "orders": orders
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @mcp.tool(description="Crear una nueva orden de compra")
    def create_purchase_order(
        ctx: Context,
        order: PurchaseOrderCreate
    ) -> Dict[str, Any]:
        """
        Crea una nueva orden de compra
        
        Args:
            order: Datos de la orden a crear
            
        Returns:
            Respuesta con el resultado de la operación
        """
        odoo = ctx.request_context.lifespan_context.odoo
        
        try:
            # Preparar valores para la orden
            order_vals = {
                "partner_id": order.partner_id,
                "order_line": []
            }
            
            if order.date_order:
                try:
                    datetime.strptime(order.date_order, "%Y-%m-%d")
                    order_vals["date_order"] = order.date_order
                except ValueError:
                    return {"success": False, "error": f"Formato de fecha inválido: {order.date_order}. Use YYYY-MM-DD."}
            
            # Preparar líneas de orden
            for line in order.order_lines:
                line_vals = [
                    0, 0, {
                        "product_id": line.product_id,
                        "product_qty": line.product_qty
                    }
                ]
                
                if line.price_unit is not None:
                    line_vals[2]["price_unit"] = line.price_unit
                    
                order_vals["order_line"].append(line_vals)
            
            # Crear orden
            order_id = odoo.execute_method("purchase.order", "create", order_vals)
            
            # Obtener información de la orden creada
            order_info = odoo.execute_method("purchase.order", "read", [order_id], ["name"])[0]
            
            return {
                "success": True,
                "result": {
                    "order_id": order_id,
                    "order_name": order_info["name"]
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @mcp.tool(description="Analiza el rendimiento de los proveedores")
    def analyze_supplier_performance(
        ctx: Context,
        params: SupplierPerformanceInput
    ) -> Dict[str, Any]:
        """
        Analiza el rendimiento de los proveedores en un período específico
        
        Args:
            params: Parámetros para el análisis
            
        Returns:
            Diccionario con resultados del análisis
        """
        odoo = ctx.request_context.lifespan_context.odoo
        
        try:
            # Validar fechas
            try:
                datetime.strptime(params.date_from, "%Y-%m-%d")
                datetime.strptime(params.date_to, "%Y-%m-%d")
            except ValueError:
                return {"success": False, "error": "Formato de fecha inválido. Use YYYY-MM-DD."}
            
            # Construir dominio para órdenes confirmadas
            domain = [
                ("date_order", ">=", params.date_from),
                ("date_order", "<=", params.date_to),
                ("state", "in", ["purchase", "done"])
            ]
            
            # Filtrar por proveedores específicos si se proporcionan
            if params.supplier_ids:
                domain.append(("partner_id", "in", params.supplier_ids))
            
            # Obtener datos de compras
            purchase_data = odoo.search_read(
                "purchase.order",
                domain,
                fields=[
                    "name", "partner_id", "date_order", "amount_total", 
                    "date_approve", "date_planned", "effective_date"
                ]
            )
            
            # Agrupar por proveedor
            supplier_data = {}
            for order in purchase_data:
                supplier_id = order["partner_id"][0] if order["partner_id"] else 0
                supplier_name = order["partner_id"][1] if order["partner_id"] else "Desconocido"
                
                if supplier_id not in supplier_data:
                    supplier_data[supplier_id] = {
                        "name": supplier_name,
                        "order_count": 0,
                        "total_amount": 0,
                        "orders": [],
                        "on_time_delivery_count": 0,
                        "late_delivery_count": 0,
                        "avg_delay_days": 0
                    }
                
                supplier_data[supplier_id]["order_count"] += 1
                supplier_data[supplier_id]["total_amount"] += order["amount_total"]
                
                # Calcular métricas de entrega a tiempo
                if order.get("effective_date") and order.get("date_planned"):
                    effective_date = datetime.strptime(order["effective_date"].split(" ")[0], "%Y-%m-%d")
                    planned_date = datetime.strptime(order["date_planned"].split(" ")[0], "%Y-%m-%d")
                    
                    delay_days = (effective_date - planned_date).days
                    
                    order_info = {
                        "id": order["id"],
                        "name": order["name"],
                        "amount": order["amount_total"],
                        "date_order": order["date_order"],
                        "planned_date": order["date_planned"],
                        "effective_date": order["effective_date"],
                        "delay_days": delay_days
                    }
                    
                    supplier_data[supplier_id]["orders"].append(order_info)
                    
                    if delay_days <= 0:
                        supplier_data[supplier_id]["on_time_delivery_count"] += 1
                    else:
                        supplier_data[supplier_id]["late_delivery_count"] += 1
            
            # Calcular métricas adicionales
            for supplier_id, data in supplier_data.items():
                # Calcular promedio de días de retraso
                delay_days = [order["delay_days"] for order in data["orders"] if "delay_days" in order]
                if delay_days:
                    data["avg_delay_days"] = sum(delay_days) / len(delay_days)
                
                # Calcular porcentaje de entregas a tiempo
                total_deliveries = data["on_time_delivery_count"] + data["late_delivery_count"]
                if total_deliveries > 0:
                    data["on_time_delivery_rate"] = (data["on_time_delivery_count"] / total_deliveries) * 100
                else:
                    data["on_time_delivery_rate"] = 0
                
                # Eliminar lista detallada de órdenes para reducir tamaño de respuesta
                data.pop("orders", None)
            
            # Ordenar proveedores por monto total
            top_suppliers = sorted(
                supplier_data.items(),
                key=lambda x: x[1]["total_amount"],
                reverse=True
            )
            
            # Preparar resultado
            result = {
                "period": {
                    "from": params.date_from,
                    "to": params.date_to
                },
                "summary": {
                    "supplier_count": len(supplier_data),
                    "order_count": len(purchase_data),
                    "total_amount": sum(order["amount_total"] for order in purchase_data)
                },
                "suppliers": [
                    {"id": k, **v} for k, v in top_suppliers
                ]
            }
            
            return {"success": True, "result": result}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
