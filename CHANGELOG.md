# Changelog

All notable changes to this project will be documented in this file.

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