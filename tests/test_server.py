import asyncio
import json

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from ghidra_mcp.backend import GhidraBackend
from ghidra_mcp.server import GUI_ONLY_TOOLS, create_server


def tool_names(mcp) -> set[str]:
    return {t.name for t in asyncio.run(mcp.list_tools())}


def call(mcp, tool, **args):
    result = asyncio.run(mcp.call_tool(tool, args))
    if isinstance(result, tuple):
        return result[1]
    return json.loads(result[0].text)


@pytest.mark.parametrize("capabilities", [None, {"gui_context"}])
def test_gui_tools_registered_when_available_or_unknown(capabilities):
    names = tool_names(create_server(GhidraBackend(), capabilities=capabilities))
    assert set(GUI_ONLY_TOOLS) <= names


def test_gui_tools_hidden_in_headless():
    names = tool_names(create_server(GhidraBackend(), capabilities=set()))
    assert not set(GUI_ONLY_TOOLS) & names
    assert {"get_program_info", "read_memory", "get_function_calls", "list_functions"} <= names


def test_backend_error_becomes_tool_error(fake_backend):
    fake_backend.fail("/decompile", 409, "AMBIGUOUS_NAME", "'f' matches 2 functions")
    mcp = create_server(GhidraBackend(fake_backend.url))
    with pytest.raises(ToolError, match="AMBIGUOUS_NAME"):
        asyncio.run(mcp.call_tool("decompile_function", {"name": "f"}))


def test_structured_result_is_passed_through(fake_backend):
    page = {"items": [{"name": "main", "address": "00401000"}], "offset": 0, "limit": 100,
            "total": 1, "has_more": False}
    fake_backend.ok("/functions", page)
    mcp = create_server(GhidraBackend(fake_backend.url))
    assert call(mcp, "list_functions", filter="ma") == page
    assert fake_backend.requests[-1][2]["filter"] == "ma"


def test_list_methods_is_alias_returning_names(fake_backend):
    fake_backend.ok("/functions", {"items": [{"name": "a", "address": "1"}, {"name": "b", "address": "2"}],
                                   "offset": 0, "limit": 100, "total": 2, "has_more": False})
    mcp = create_server(GhidraBackend(fake_backend.url))
    assert call(mcp, "list_methods") == {"result": ["a", "b"]}


def test_rename_variable_requires_function_identity():
    mcp = create_server(GhidraBackend("http://127.0.0.1:1/"))
    with pytest.raises(ToolError, match="MISSING_PARAMETER"):
        asyncio.run(mcp.call_tool("rename_variable", {"old_name": "a", "new_name": "b"}))


def test_create_function_posts_address_and_name(fake_backend):
    fake_backend.ok("/create_function", {"name": "decrypt", "address": "00401000"})
    mcp = create_server(GhidraBackend(fake_backend.url))
    assert call(mcp, "create_function", address="0x401000", name="decrypt")["name"] == "decrypt"
    method, path, params = fake_backend.requests[-1]
    assert (method, path) == ("POST", "/create_function")
    assert params == {"address": "0x401000", "name": "decrypt"}


def test_create_function_omits_none_name(fake_backend):
    fake_backend.ok("/create_function", {"name": "FUN_00401000"})
    mcp = create_server(GhidraBackend(fake_backend.url))
    call(mcp, "create_function", address="0x401000")
    assert fake_backend.requests[-1][2] == {"address": "0x401000"}


def test_disassemble_range_posts_pagination_and_follow_flow(fake_backend):
    fake_backend.ok("/disassemble_range", {"start": "0x401000", "end": "0x401010"})
    mcp = create_server(GhidraBackend(fake_backend.url))
    call(mcp, "disassemble_range", start_address="0x401000", end_address="0x401010")
    method, path, params = fake_backend.requests[-1]
    assert (method, path) == ("POST", "/disassemble_range")
    assert params["follow_flow"] == "True"
    assert params["offset"] == "0"
    assert params["limit"] == "500"
    call(mcp, "disassemble_range", start_address="0x401000", end_address="0x401010",
         follow_flow=False)
    assert fake_backend.requests[-1][2]["follow_flow"] == "False"


def test_define_data_posts_type_count_and_overwrite(fake_backend):
    fake_backend.ok("/define_data", {"address": "0x404000", "size": 8})
    mcp = create_server(GhidraBackend(fake_backend.url))
    call(mcp, "define_data", address="0x404000", data_type="dword", count=2)
    method, path, params = fake_backend.requests[-1]
    assert (method, path) == ("POST", "/define_data")
    assert params == {
        "address": "0x404000",
        "data_type": "dword",
        "count": "2",
        "overwrite": "False",
    }
    call(mcp, "define_data", address="0x404000", data_type="dword", overwrite=True)
    assert fake_backend.requests[-1][2]["overwrite"] == "True"
