# examples — short lessons about Gogo itself

Each file here shows one thing and runs in one command.

| File | What it shows | Run it |
|---|---|---|
| [tiny_memory_agent.py](tiny_memory_agent.py) | the loop's three steps with memory, and nothing else in frame | `python examples/tiny_memory_agent.py` |
| [mcp.demo.json](mcp.demo.json) | connecting Gogo to an MCP server, with no remote host | `cp examples/mcp.demo.json .gogo/mcp.json && make dashboard` |

The MCP demo server itself is `evals/fixtures/mcp_demo_server.py`, because the
test suite runs the same server.

The rules for this folder are in
[conventions §6](../docs/context/conventions.md#6-examples-and-video-material).
