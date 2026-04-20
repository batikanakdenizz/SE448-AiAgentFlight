"""
Long-lived MCP client for the agent backend.

Spawns `mcp_server.py` as a subprocess over stdio at FastAPI startup and keeps
the session open for the lifetime of the process, so each /chat request reuses
the same connection instead of paying the subprocess-spawn cost per turn.

Public surface:
    await init_mcp()             -> spawn server, discover tools
    get_tool_definitions()       -> Ollama-compatible tool schemas (cached)
    await call_mcp_tool(name, args) -> str (tool result text)
    await shutdown_mcp()         -> graceful close
"""
import os
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_exit_stack: Optional[AsyncExitStack] = None
_session: Optional[ClientSession] = None
_tool_definitions: list[dict] = []

_SERVER_SCRIPT = str(Path(__file__).parent / "mcp_server.py")


def _convert_mcp_tool_to_ollama(tool) -> dict:
    """Convert an MCP Tool object into the OpenAI/Ollama function-calling schema."""
    input_schema = tool.inputSchema or {"type": "object", "properties": {}}
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": (tool.description or "").strip(),
            "parameters": input_schema,
        },
    }


async def init_mcp() -> None:
    """Spawn the MCP server subprocess and open a persistent session."""
    global _exit_stack, _session, _tool_definitions

    if _session is not None:
        return  # already initialized

    _exit_stack = AsyncExitStack()

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[_SERVER_SCRIPT],
        env=os.environ.copy(),
    )

    read, write = await _exit_stack.enter_async_context(stdio_client(server_params))
    _session = await _exit_stack.enter_async_context(ClientSession(read, write))
    await _session.initialize()

    tools_result = await _session.list_tools()
    _tool_definitions = [_convert_mcp_tool_to_ollama(t) for t in tools_result.tools]


async def shutdown_mcp() -> None:
    """Close the MCP session and terminate the server subprocess."""
    global _exit_stack, _session, _tool_definitions
    if _exit_stack is not None:
        try:
            await _exit_stack.aclose()
        except Exception:
            pass
    _exit_stack = None
    _session = None
    _tool_definitions = []


def get_tool_definitions() -> list[dict]:
    """Ollama-format tool schemas discovered from the MCP server."""
    return _tool_definitions


async def call_mcp_tool(tool_name: str, tool_args: dict[str, Any]) -> str:
    """Invoke a tool on the MCP server and return its text content."""
    if _session is None:
        return "MCP client is not initialized."

    try:
        result = await _session.call_tool(tool_name, tool_args)
    except Exception as e:
        return f"MCP tool error: {e}"

    # Concatenate any text content blocks the server returned.
    parts: list[str] = []
    for block in result.content or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)

    if not parts:
        return "" if not result.isError else "MCP tool returned an error with no content."

    joined = "\n".join(parts)
    if result.isError:
        return f"MCP tool error: {joined}"
    return joined
