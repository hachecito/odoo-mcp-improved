# Changelog

All notable changes to this project will be documented in this file.

## [1.0.7] - 2026-11-18

### Fixed
- **Regression in 1.0.6**: every tool in `tools_sales.py`, `tools_purchase.py`, `tools_inventory.py` and `tools_accounting.py` was broken. 1.0.6 imported `Context`/`FastMCP` from the standalone `fastmcp` package in those files, but `server.py` still built the actual server with `mcp.server.fastmcp.FastMCP`. `fastmcp.Context` and `mcp.server.fastmcp.Context` are different classes, so the server no longer recognized `ctx: Context` as injectable and required MCP clients to supply it themselves, failing validation on every call
- Removed the `fastmcp` dependency and reverted all imports back to `mcp.server.fastmcp`; pinning `mcp<2.0` alone is enough to keep `mcp.server.fastmcp` available and avoid the `fastmcp` package's much larger transitive dependency tree
- `get_model_info()` passed its options dict as a positional argument instead of `**kwargs`, the same bug class fixed in 1.0.6 for `search_read()`/`read_records()`, breaking the `odoo://model/{model_name}` resource

### Added
- Implemented the sales/purchase/inventory/accounting resources documented in the README but missing from `resources.py` since June 2025 (`odoo://sales/orders`, `odoo://sales/order/{order_id}`, `odoo://sales/products`, `odoo://sales/customers`, `odoo://purchase/orders`, `odoo://purchase/order/{order_id}`, `odoo://purchase/suppliers`, `odoo://inventory/products`, `odoo://inventory/stock/{location_id}`, `odoo://inventory/movements`, `odoo://accounting/accounts`, `odoo://accounting/journal_entries`, `odoo://accounting/reports/{report_type}`, currently supporting `trial_balance`)
- `get_customer_insights` sales tool, documented in the README but missing from `tools_sales.py`
- `OdooClient.pick_available_field()`: resolves a field name across Odoo versions instead of hardcoding one (used for `account.account`'s type field, exposed as `user_type_id` on older versions and `account_type` on newer ones)
- `tests/`: offline regression tests, including one that asserts no tool requires `ctx` from the MCP client (would have caught the regression above before release)
- CI workflow running the test suite on every pull request

## [1.0.6] - 2026-11-18

### Fixed
- `search_read()` and `read_records()` passed their options dict as a positional argument instead of unpacking it as keyword arguments, breaking `fields`, `limit`, `offset` and `order` on every search (#5)
- Pinned `mcp>=1.6.0,<2.0` and added the missing `fastmcp>=2.0,<3` dependency; an unpinned `mcp` dependency resolved to `mcp` 2.x, which removed `mcp.server.fastmcp` and broke every fresh install (`pip install` / `uvx`)
- Removed the unused `pypi-xmlrpc` dependency; the project only ever used Python's built-in `xmlrpc.client`, and this package has no wheel, making installs slower and more fragile

### Changed
- Migrated from the bundled `mcp.server.fastmcp` to the standalone `fastmcp` package (#4)

## [0.0.3] - 2025-03-18

### Fixed
- Fixed `OdooClient` class by adding missing methods: `get_models()`, `get_model_info()`, `get_model_fields()`, `search_read()`, and `read_records()`
- Ensured compatibility with different Odoo versions by using only basic fields when retrieving model information

### Added
- Support for retrieving all models from an Odoo instance
- Support for retrieving detailed information about specific models
- Support for searching and reading records with various filtering options

## [0.0.2] - 2025-03-18

### Fixed
- Added missing dependencies in pyproject.toml: `mcp>=0.1.1`, `requests>=2.31.0`, `xmlrpc>=0.4.1`

## [0.0.1] - 2025-03-18

### Added
- Initial release with basic Odoo XML-RPC client support
- MCP Server integration for Odoo
- Command-line interface for quick setup and testing 