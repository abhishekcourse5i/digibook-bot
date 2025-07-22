from langchain_core.tools import tool

@tool
def read_file_content(file_path: str) -> str:
    """Read and return the content of a file as a string. Used for providing documentation or schema to agents."""
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}" 