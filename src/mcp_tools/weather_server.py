# weather_server.py
from typing import Dict, Any, Optional
import requests
from mcp.server.fastmcp import FastMCP
import os
from dotenv import load_dotenv
load_dotenv()

mcp = FastMCP("Weather")

mcp.settings.port = 8001

@mcp.tool()
async def get_weather(location: str, lang: str = 'en') -> Dict[str, Any]:
    """
    Get current weather for a given location using WeatherAPI.

    Args:
        location (str): Location query, e.g., city name or "latitude,longitude".
        lang (str): Language code for the response (default is 'en').

    Returns:
        dict: JSON response from WeatherAPI.
    """
    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key:
        return {"error": "WEATHER_API_KEY not found in environment variables"}
    
    base_url = "http://api.weatherapi.com/v1"
    endpoint = "/current.json"
    
    params = {
        'key': api_key,
        'q': location,
        'lang': lang
    }

    try:
        response = requests.get(base_url + endpoint, params=params)
        response.raise_for_status()  # Raise exception for HTTP errors
        data = response.json()
        return data
    except requests.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

if __name__ == "__main__":
    mcp.run(transport="stdio")
