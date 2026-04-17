"""Entry point for python -m nantoken -- starts the MCP server."""

try:
    from nantoken.mcp_server import mcp
except ImportError as e:
    import sys
    print(f"Missing dependency: {e}")
    print("Install with: pip install 'mcp[cli]>=1.0.0'")
    sys.exit(1)

if __name__ == "__main__":
    mcp.run()
