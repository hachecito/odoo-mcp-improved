"""
Implementación de herramientas (tools) para inventario en MCP-Odoo
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from fastmcp import FastMCP, Context

from .models import (
    ProductAvailabilityInput,
    InventoryAdjustmentCreate,
    InventoryTurnoverInput
)

def register_inventory_tools(mcp: FastMCP) -> None:
    """Registra herramientas relacionadas con inventario"""
    
    @mcp.tool(description="Verifica la disponibilidad de stock para uno o más productos")
    def check_product_availability(
        ctx: Context,
        params: ProductAvailabilityInput
    ) -> Dict[str, Any]:
        """
        Verifica la disponibilidad de stock para uno o más productos
        
        Args:
            params: Parámetros con IDs de productos y ubicación opcional
            
        Returns:
            Diccionario con información de disponibilidad
        """
        odoo = ctx.request_context.lifespan_context.odoo
        
        try:
            # Verificar que los productos existen
            products = odoo.search_read(
                "product.product",
                [("id", "in", params.product_ids)],
                fields=["name", "default_code", "type", "uom_id"]
            )
            
            if not products:
                return {"success": False, "error": "No se encontraron productos con los IDs proporcionados"}
            
            # Mapear IDs a nombres para referencia
            product_names = {p["id"]: p["name"] for p in products}
            
            # Obtener disponibilidad
            availability = {}
            
            for product_id in params.product_ids:
                # Construir contexto para la consulta
                context = {}
                if params.location_id:
                    context["location"] = params.location_id
                
                # Obtener cantidad disponible usando el método qty_available
                try:
                    product_data = odoo.execute_method(
                        "product.product", 
                        "read", 
                        [product_id], 
                        ["qty_available", "virtual_available", "incoming_qty", "outgoing_qty"],
                        context
                    )
                    
                    if product_data:
                        product_info = product_data[0]
                        availability[product_id] = {
                            "name": product_names.get(product_id, f"Producto {product_id}"),
                            "qty_available": product_info["qty_available"],
                            "virtual_available": product_info["virtual_available"],
                            "incoming_qty": product_info["incoming_qty"],
                            "outgoing_qty": product_info["outgoing_qty"]
                        }
                    else:
                        availability[product_id] = {
                            "name": product_names.get(product_id, f"Producto {product_id}"),
                            "error": "Producto no encontrado"
                        }
                except Exception as e:
                    availability[product_id] = {
                        "name": product_names.get(product_id, f"Producto {product_id}"),
                        "error": str(e)
                    }
            
            # Obtener información de la ubicación si se especificó
            location_info = None
            if params.location_id:
                try:
                    location_data = odoo.search_read(
                        "stock.location",
                        [("id", "=", params.location_id)],
                        fields=["name", "complete_name"]
                    )
                    if location_data:
                        location_info = location_data[0]
                except Exception:
                    location_info = {"id": params.location_id, "name": "Ubicación desconocida"}
            
            return {
                "success": True,
                "result": {
                    "products": availability,
                    "location": location_info
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @mcp.tool(description="Crea un ajuste de inventario para corregir el stock")
    def create_inventory_adjustment(
        ctx: Context,
        adjustment: InventoryAdjustmentCreate
    ) -> Dict[str, Any]:
        """
        Crea un ajuste de inventario para corregir el stock
        
        Args:
            adjustment: Datos del ajuste a crear
            
        Returns:
            Respuesta con el resultado de la operación
        """
        odoo = ctx.request_context.lifespan_context.odoo
        
        try:
            # Verificar la versión de Odoo para determinar el modelo correcto
            # En Odoo 13.0+, se usa 'stock.inventory'
            # En Odoo 15.0+, se usa 'stock.quant' directamente
            
            # Intentar obtener el modelo stock.inventory
            inventory_model_exists = odoo.execute_method(
                "ir.model",
                "search_count",
                [("model", "=", "stock.inventory")]
            ) > 0
            
            if inventory_model_exists:
                # Usar el flujo de stock.inventory (Odoo 13.0, 14.0)
                # Crear el inventario
                inventory_vals = {
                    "name": adjustment.name,
                    "line_ids": []
                }
                
                if adjustment.date:
                    try:
                        datetime.strptime(adjustment.date, "%Y-%m-%d")
                        inventory_vals["date"] = adjustment.date
                    except ValueError:
                        return {"success": False, "error": f"Formato de fecha inválido: {adjustment.date}. Use YYYY-MM-DD."}
                
                # Crear el inventario
                inventory_id = odoo.execute_method("stock.inventory", "create", inventory_vals)
                
                # Añadir líneas al inventario
                for line in adjustment.adjustment_lines:
                    line_vals = {
                        "inventory_id": inventory_id,
                        "product_id": line.product_id,
                        "location_id": line.location_id,
                        "product_qty": line.product_qty
                    }
                    
                    odoo.execute_method("stock.inventory.line", "create", line_vals)
                
                # Confirmar el inventario
                odoo.execute_method("stock.inventory", "action_validate", [inventory_id])
                
                return {
                    "success": True,
                    "result": {
                        "inventory_id": inventory_id,
                        "name": adjustment.name
                    }
                }
            else:
                # Usar el flujo de stock.quant (Odoo 15.0+)
                result_ids = []
                
                for line in adjustment.adjustment_lines:
                    # Buscar el quant existente
                    quant_domain = [
                        ("product_id", "=", line.product_id),
                        ("location_id", "=", line.location_id)
                    ]
                    
                    quants = odoo.search_read(
                        "stock.quant",
                        quant_domain,
                        fields=["id", "quantity"]
                    )
                    
                    if quants:
                        # Actualizar quant existente
                        quant_id = quants[0]["id"]
                        odoo.execute_method(
                            "stock.quant",
                            "write",
                            [quant_id],
                            {"inventory_quantity": line.product_qty}
                        )
                        result_ids.append(quant_id)
                    else:
                        # Crear nuevo quant
                        quant_vals = {
                            "product_id": line.product_id,
                            "location_id": line.location_id,
                            "inventory_quantity": line.product_qty
                        }
                        quant_id = odoo.execute_method("stock.quant", "create", quant_vals)
                        result_ids.append(quant_id)
                
                # Aplicar el inventario
                odoo.execute_method("stock.quant", "action_apply_inventory", result_ids)
                
                return {
                    "success": True,
                    "result": {
                        "quant_ids": result_ids,
                        "name": adjustment.name
                    }
                }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @mcp.tool(description="Calcula y analiza la rotación de inventario")
    def analyze_inventory_turnover(
        ctx: Context,
        params: InventoryTurnoverInput
    ) -> Dict[str, Any]:
        """
        Calcula y analiza la rotación de inventario
        
        Args:
            params: Parámetros para el análisis
            
        Returns:
            Diccionario con resultados del análisis
        """
        odoo = ctx.request_context.lifespan_context.odoo
        
        try:
            # Validar fechas
            try:
                date_from = datetime.strptime(params.date_from, "%Y-%m-%d")
                date_to = datetime.strptime(params.date_to, "%Y-%m-%d")
            except ValueError:
                return {"success": False, "error": "Formato de fecha inválido. Use YYYY-MM-DD."}
            
            # Construir dominio para productos
            product_domain = [("type", "=", "product")]  # Solo productos almacenables
            
            if params.product_ids:
                product_domain.append(("id", "in", params.product_ids))
                
            if params.category_id:
                product_domain.append(("categ_id", "=", params.category_id))
            
            # Obtener productos
            products = odoo.search_read(
                "product.product",
                product_domain,
                fields=["name", "default_code", "categ_id", "standard_price"]
            )
            
            if not products:
                return {"success": False, "error": "No se encontraron productos con los criterios especificados"}
            
            # Calcular rotación para cada producto
            product_turnover = {}
            
            for product in products:
                product_id = product["id"]
                
                # 1. Obtener movimientos de salida (ventas) en el período
                outgoing_domain = [
                    ("product_id", "=", product_id),
                    ("date", ">=", params.date_from),
                    ("date", "<=", params.date_to),
                    ("location_dest_id.usage", "=", "customer")  # Destino: cliente
                ]
                
                outgoing_moves = odoo.search_read(
                    "stock.move",
                    outgoing_domain,
                    fields=["product_uom_qty", "price_unit"]
                )
                
                # Calcular costo de ventas
                cogs = sum(move["product_uom_qty"] * (move.get("price_unit") or product["standard_price"]) for move in outgoing_moves)
                
                # 2. Obtener valor de inventario promedio
                # Intentar obtener valoración de inventario al inicio y fin del período
                
                # Método 1: Usar informes de valoración si están disponibles
                try:
                    # Valoración al inicio del período
                    context_start = {
                        "to_date": params.date_from
                    }
                    
                    valuation_start = odoo.execute_method(
                        "product.product",
                        "read",
                        [product_id],
                        ["stock_value"],
                        context_start
                    )
                    
                    # Valoración al final del período
                    context_end = {
                        "to_date": params.date_to
                    }
                    
                    valuation_end = odoo.execute_method(
                        "product.product",
                        "read",
                        [product_id],
                        ["stock_value"],
                        context_end
                    )
                    
                    start_value = valuation_start[0]["stock_value"] if valuation_start else 0
                    end_value = valuation_end[0]["stock_value"] if valuation_end else 0
                    
                    avg_inventory_value = (start_value + end_value) / 2
                    
                except Exception:
                    # Método 2: Estimación basada en precio estándar y cantidad
                    # Obtener cantidad al inicio
                    context_start = {
                        "to_date": params.date_from
                    }
                    
                    qty_start = odoo.execute_method(
                        "product.product",
                        "read",
                        [product_id],
                        ["qty_available"],
                        context_start
                    )
                    
                    # Obtener cantidad al final
                    context_end = {
                        "to_date": params.date_to
                    }
                    
                    qty_end = odoo.execute_method(
                        "product.product",
                        "read",
                        [product_id],
                        ["qty_available"],
                        context_end
                    )
                    
                    start_qty = qty_start[0]["qty_available"] if qty_start else 0
                    end_qty = qty_end[0]["qty_available"] if qty_end else 0
                    
                    avg_qty = (start_qty + end_qty) / 2
                    avg_inventory_value = avg_qty * product["standard_price"]
                
                # 3. Calcular métricas de rotación
                turnover_ratio = 0
                days_inventory = 0
                
                if avg_inventory_value > 0:
                    turnover_ratio = cogs / avg_inventory_value
                    
                    # Días de inventario (basado en el período analizado)
                    days_in_period = (date_to - date_from).days + 1
                    if turnover_ratio > 0:
                        days_inventory = days_in_period / turnover_ratio
                
                # Guardar resultados
                product_turnover[product_id] = {
                    "name": product["name"],
                    "default_code": product["default_code"],
                    "category": product["categ_id"][1] if product["categ_id"] else "Sin categoría",
                    "cogs": cogs,
                    "avg_inventory_value": avg_inventory_value,
                    "turnover_ratio": turnover_ratio,
                    "days_inventory": days_inventory
                }
            
            # Ordenar productos por rotación (de mayor a menor)
            sorted_products = sorted(
                product_turnover.items(),
                key=lambda x: x[1]["turnover_ratio"],
                reverse=True
            )
            
            # Calcular promedios generales
            total_cogs = sum(data["cogs"] for _, data in product_turnover.items())
            total_avg_value = sum(data["avg_inventory_value"] for _, data in product_turnover.items())
            
            overall_turnover = 0
            overall_days = 0
            
            if total_avg_value > 0:
                overall_turnover = total_cogs / total_avg_value
                days_in_period = (date_to - date_from).days + 1
                if overall_turnover > 0:
                    overall_days = days_in_period / overall_turnover
            
            # Preparar resultado
            result = {
                "period": {
                    "from": params.date_from,
                    "to": params.date_to,
                    "days": (date_to - date_from).days + 1
                },
                "summary": {
                    "product_count": len(products),
                    "total_cogs": total_cogs,
                    "total_avg_inventory_value": total_avg_value,
                    "overall_turnover_ratio": overall_turnover,
                    "overall_days_inventory": overall_days
                },
                "products": [
                    {"id": k, **v} for k, v in sorted_products
                ]
            }
            
            return {"success": True, "result": result}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
