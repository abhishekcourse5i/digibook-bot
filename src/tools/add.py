from langchain_core.tools import tool

@tool
def add(a: int, b: int) -> int:
    """
    A simple tool that adds two integers.
    
    Args:
        a (int): The first integer.
        b (int): The second integer.
        
    Returns:
        int: The sum of the two integers.
    """
    return a + b