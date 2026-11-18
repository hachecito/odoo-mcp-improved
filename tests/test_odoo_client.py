"""
Unit tests for OdooClient's XML-RPC argument passing, mocked (no live Odoo).

These exist because search_read/read_records/get_model_info each passed
their options as a positional dict instead of **kwargs at some point,
silently dropping fields/limit/offset/order.
"""
from unittest.mock import MagicMock

from odoo_mcp.odoo_client import OdooClient


def make_client():
    client = OdooClient.__new__(OdooClient)
    client._execute = MagicMock(return_value=[])
    return client


def test_search_read_passes_options_as_kwargs():
    client = make_client()
    client.search_read("res.partner", [], fields=["id", "name"], limit=5)

    args, kwargs = client._execute.call_args
    assert args[:3] == ("res.partner", "search_read", [])
    assert kwargs == {"fields": ["id", "name"], "limit": 5}


def test_read_records_passes_options_as_kwargs():
    client = make_client()
    client.read_records("res.partner", [1, 2], fields=["id", "name"])

    args, kwargs = client._execute.call_args
    assert args[:3] == ("res.partner", "read", [1, 2])
    assert kwargs == {"fields": ["id", "name"]}


def test_get_model_info_passes_options_as_kwargs():
    client = make_client()
    client._execute.return_value = [{"id": 1, "name": "Contact", "model": "res.partner"}]

    client.get_model_info("res.partner")

    args, kwargs = client._execute.call_args
    assert args[:3] == ("ir.model", "search_read", [("model", "=", "res.partner")])
    assert kwargs == {"fields": ["name", "model"]}
