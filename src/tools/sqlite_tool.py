import sqlite3
import os
from typing import Any
from langchain_core.tools import tool

@tool
def sqlite_tool(query: str) -> str:
    """Execute a SQL query on the digibook.db SQLite database and return the results as a string. Expects only a SQL query from the user."""
    db_path = os.path.join(os.path.dirname(__file__), '../database/digibook.db')
    if not query.strip():
        return "No SQL query provided."
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        print(f"Executing query: {query}")
        cursor.execute(query)
        # Fetch all results
        results = cursor.fetchall()
        # Get column names
        columns = [description[0] for description in cursor.description] if cursor.description else []
        conn.close()
        if not results:
            return "No results found."
        # Format results as a table-like string
        output = '\t'.join(columns) + '\n'
        for row in results:
            output += '\t'.join(str(item) for item in row) + '\n'
        return output.strip()
    except Exception as e:
        return f"Error executing query: {e}" 