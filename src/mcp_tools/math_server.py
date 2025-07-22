# math_server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Math")

mcp.settings.port = 8000

@mcp.tool()
async def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@mcp.tool()
async def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    return a * b

@mcp.tool()
async def subtract(a: int, b: int) -> int:
    """Subtract two numbers"""
    return a - b

if __name__ == "__main__":
    mcp.run(transport="stdio")
