"""
Implementación de herramientas (tools) para contabilidad en MCP-Odoo
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from fastmcp import FastMCP, Context

from .models import (
    JournalEntryFilter,
    JournalEntryCreate,
    FinancialRatioInput
)

def register_accounting_tools(mcp: FastMCP) -> None:
    """Registra herramientas relacionadas con contabilidad"""
    
    @mcp.tool(description="Busca asientos contables con filtros")
    def search_journal_entries(
        ctx: Context,
        filters: JournalEntryFilter
    ) -> Dict[str, Any]:
        """
        Busca asientos contables según los filtros especificados
        
        Args:
            filters: Filtros para la búsqueda de asientos
            
        Returns:
            Diccionario con resultados de la búsqueda
        """
        odoo = ctx.request_context.lifespan_context.odoo
        
        try:
            # Construir dominio de búsqueda
            domain = []
            
            if filters.date_from:
                try:
                    datetime.strptime(filters.date_from, "%Y-%m-%d")
                    domain.append(("date", ">=", filters.date_from))
                except ValueError:
                    return {"success": False, "error": f"Formato de fecha inválido: {filters.date_from}. Use YYYY-MM-DD."}
                
            if filters.date_to:
                try:
                    datetime.strptime(filters.date_to, "%Y-%m-%d")
                    domain.append(("date", "<=", filters.date_to))
                except ValueError:
                    return {"success": False, "error": f"Formato de fecha inválido: {filters.date_to}. Use YYYY-MM-DD."}
                
            if filters.journal_id:
                domain.append(("journal_id", "=", filters.journal_id))
                
            if filters.state:
                domain.append(("state", "=", filters.state))
            
            # Campos a recuperar
            fields = [
                "name", "ref", "date", "journal_id", "state", 
                "amount_total", "amount_total_signed", "line_ids"
            ]
            
            # Ejecutar búsqueda
            entries = odoo.search_read(
                "account.move", 
                domain, 
                fields=fields, 
                limit=filters.limit,
                offset=filters.offset
            )
            
            # Obtener el conteo total sin límite para paginación
            total_count = odoo.execute_method("account.move", "search_count", domain)
            
            # Para cada asiento, obtener información resumida de las líneas
            for entry in entries:
                if entry.get("line_ids"):
                    line_ids = entry["line_ids"]
                    lines = odoo.search_read(
                        "account.move.line",
                        [("id", "in", line_ids)],
                        fields=["name", "account_id", "partner_id", "debit", "credit", "balance"]
                    )
                    entry["lines"] = lines
                    # Eliminar la lista de IDs para reducir tamaño
                    entry.pop("line_ids", None)
            
            return {
                "success": True, 
                "result": {
                    "count": len(entries),
                    "total_count": total_count,
                    "entries": entries
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @mcp.tool(description="Crea un nuevo asiento contable")
    def create_journal_entry(
        ctx: Context,
        entry: JournalEntryCreate
    ) -> Dict[str, Any]:
        """
        Crea un nuevo asiento contable
        
        Args:
            entry: Datos del asiento a crear
            
        Returns:
            Respuesta con el resultado de la operación
        """
        odoo = ctx.request_context.lifespan_context.odoo
        
        try:
            # Verificar que el debe y el haber cuadran
            total_debit = sum(line.debit for line in entry.lines)
            total_credit = sum(line.credit for line in entry.lines)
            
            if round(total_debit, 2) != round(total_credit, 2):
                return {
                    "success": False, 
                    "error": f"El asiento no está cuadrado. Debe: {total_debit}, Haber: {total_credit}"
                }
            
            # Preparar valores para el asiento
            move_vals = {
                "journal_id": entry.journal_id,
                "line_ids": []
            }
            
            if entry.ref:
                move_vals["ref"] = entry.ref
                
            if entry.date:
                try:
                    datetime.strptime(entry.date, "%Y-%m-%d")
                    move_vals["date"] = entry.date
                except ValueError:
                    return {"success": False, "error": f"Formato de fecha inválido: {entry.date}. Use YYYY-MM-DD."}
            
            # Preparar líneas del asiento
            for line in entry.lines:
                line_vals = [
                    0, 0, {
                        "account_id": line.account_id,
                        "name": line.name or "/",
                        "debit": line.debit,
                        "credit": line.credit
                    }
                ]
                
                if line.partner_id:
                    line_vals[2]["partner_id"] = line.partner_id
                    
                move_vals["line_ids"].append(line_vals)
            
            # Crear asiento
            move_id = odoo.execute_method("account.move", "create", move_vals)
            
            # Obtener información del asiento creado
            move_info = odoo.execute_method("account.move", "read", [move_id], ["name", "state"])[0]
            
            return {
                "success": True,
                "result": {
                    "move_id": move_id,
                    "name": move_info["name"],
                    "state": move_info["state"]
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @mcp.tool(description="Calcula ratios financieros clave")
    def analyze_financial_ratios(
        ctx: Context,
        params: FinancialRatioInput
    ) -> Dict[str, Any]:
        """
        Calcula ratios financieros clave para un período específico
        
        Args:
            params: Parámetros para el análisis
            
        Returns:
            Diccionario con los ratios calculados
        """
        odoo = ctx.request_context.lifespan_context.odoo
        
        try:
            # Validar fechas
            try:
                datetime.strptime(params.date_from, "%Y-%m-%d")
                datetime.strptime(params.date_to, "%Y-%m-%d")
            except ValueError:
                return {"success": False, "error": "Formato de fecha inválido. Use YYYY-MM-DD."}
            
            # Verificar qué ratios se solicitan
            requested_ratios = params.ratios
            
            # Inicializar resultado
            ratios = {}
            
            # Obtener datos del balance general
            # Activos
            assets_domain = [
                ("account_id.user_type_id.internal_group", "=", "asset"),
                ("date", ">=", params.date_from),
                ("date", "<=", params.date_to),
                ("parent_state", "=", "posted")
            ]
            
            assets_data = odoo.search_read(
                "account.move.line",
                assets_domain,
                fields=["account_id", "balance"]
            )
            
            total_assets = sum(line["balance"] for line in assets_data)
            
            # Activos corrientes
            current_assets_domain = [
                ("account_id.user_type_id.internal_group", "=", "asset"),
                ("account_id.user_type_id.type", "=", "liquidity"),
                ("date", ">=", params.date_from),
                ("date", "<=", params.date_to),
                ("parent_state", "=", "posted")
            ]
            
            current_assets_data = odoo.search_read(
                "account.move.line",
                current_assets_domain,
                fields=["account_id", "balance"]
            )
            
            current_assets = sum(line["balance"] for line in current_assets_data)
            
            # Pasivos
            liabilities_domain = [
                ("account_id.user_type_id.internal_group", "=", "liability"),
                ("date", ">=", params.date_from),
                ("date", "<=", params.date_to),
                ("parent_state", "=", "posted")
            ]
            
            liabilities_data = odoo.search_read(
                "account.move.line",
                liabilities_domain,
                fields=["account_id", "balance"]
            )
            
            total_liabilities = sum(line["balance"] for line in liabilities_data)
            
            # Pasivos corrientes
            current_liabilities_domain = [
                ("account_id.user_type_id.internal_group", "=", "liability"),
                ("account_id.user_type_id.type", "=", "payable"),
                ("date", ">=", params.date_from),
                ("date", "<=", params.date_to),
                ("parent_state", "=", "posted")
            ]
            
            current_liabilities_data = odoo.search_read(
                "account.move.line",
                current_liabilities_domain,
                fields=["account_id", "balance"]
            )
            
            current_liabilities = sum(line["balance"] for line in current_liabilities_data)
            
            # Patrimonio
            equity_domain = [
                ("account_id.user_type_id.internal_group", "=", "equity"),
                ("date", ">=", params.date_from),
                ("date", "<=", params.date_to),
                ("parent_state", "=", "posted")
            ]
            
            equity_data = odoo.search_read(
                "account.move.line",
                equity_domain,
                fields=["account_id", "balance"]
            )
            
            total_equity = sum(line["balance"] for line in equity_data)
            
            # Ingresos
            income_domain = [
                ("account_id.user_type_id.internal_group", "=", "income"),
                ("date", ">=", params.date_from),
                ("date", "<=", params.date_to),
                ("parent_state", "=", "posted")
            ]
            
            income_data = odoo.search_read(
                "account.move.line",
                income_domain,
                fields=["account_id", "balance"]
            )
            
            total_income = sum(line["balance"] for line in income_data)
            
            # Gastos
            expense_domain = [
                ("account_id.user_type_id.internal_group", "=", "expense"),
                ("date", ">=", params.date_from),
                ("date", "<=", params.date_to),
                ("parent_state", "=", "posted")
            ]
            
            expense_data = odoo.search_read(
                "account.move.line",
                expense_domain,
                fields=["account_id", "balance"]
            )
            
            total_expenses = sum(line["balance"] for line in expense_data)
            
            # Calcular beneficio neto
            net_income = total_income - total_expenses
            
            # Calcular ratios solicitados
            if "liquidity" in requested_ratios:
                # Ratio de liquidez corriente
                current_ratio = 0
                if current_liabilities != 0:
                    current_ratio = current_assets / abs(current_liabilities)
                
                ratios["liquidity"] = {
                    "current_ratio": current_ratio,
                    "current_assets": current_assets,
                    "current_liabilities": abs(current_liabilities)
                }
            
            if "profitability" in requested_ratios:
                # Rentabilidad sobre activos (ROA)
                roa = 0
                if total_assets != 0:
                    roa = (net_income / total_assets) * 100
                
                # Rentabilidad sobre patrimonio (ROE)
                roe = 0
                if total_equity != 0:
                    roe = (net_income / total_equity) * 100
                
                # Margen de beneficio neto
                profit_margin = 0
                if total_income != 0:
                    profit_margin = (net_income / total_income) * 100
                
                ratios["profitability"] = {
                    "return_on_assets": roa,
                    "return_on_equity": roe,
                    "net_profit_margin": profit_margin,
                    "net_income": net_income,
                    "total_income": total_income
                }
            
            if "debt" in requested_ratios:
                # Ratio de endeudamiento
                debt_ratio = 0
                if total_assets != 0:
                    debt_ratio = (abs(total_liabilities) / total_assets) * 100
                
                # Ratio de apalancamiento
                leverage_ratio = 0
                if total_equity != 0:
                    leverage_ratio = (abs(total_liabilities) / total_equity)
                
                ratios["debt"] = {
                    "debt_ratio": debt_ratio,
                    "leverage_ratio": leverage_ratio,
                    "total_liabilities": abs(total_liabilities),
                    "total_equity": total_equity
                }
            
            if "efficiency" in requested_ratios:
                # Rotación de activos
                asset_turnover = 0
                if total_assets != 0:
                    asset_turnover = total_income / total_assets
                
                ratios["efficiency"] = {
                    "asset_turnover": asset_turnover
                }
            
            # Preparar resultado
            result = {
                "period": {
                    "from": params.date_from,
                    "to": params.date_to
                },
                "summary": {
                    "total_assets": total_assets,
                    "total_liabilities": abs(total_liabilities),
                    "total_equity": total_equity,
                    "total_income": total_income,
                    "total_expenses": abs(total_expenses),
                    "net_income": net_income
                },
                "ratios": ratios
            }
            
            return {"success": True, "result": result}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
