from langchain_core.tools import tool

@tool
def multiply(a: int, b: int) -> int:
    """
    A simple function that multiplies two integers.
    
    Args:
        a (int): The first integer.
        b (int): The second integer.
        
    Returns:
        int: The product of the two integers.
    """
    return a * b
