from langchain_core.tools import tool

@tool
def subtract(a: int, b: int) -> int:
    """
    A simple tool that subtracts two integers.
    """
    return a - b