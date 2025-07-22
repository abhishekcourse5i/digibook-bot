# global_disruptions_server.py
from typing import Dict, Any, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from mcp.server.fastmcp import FastMCP
import os
from dotenv import load_dotenv
from datetime import datetime, date

load_dotenv()

mcp = FastMCP("Global Disruptions Database")

def get_db_connection():
    """Get database connection using environment variables."""
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            database=os.getenv("POSTGRES_DB", "erp_db"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            port=os.getenv("POSTGRES_PORT", "5432")
        )
        return conn
    except Exception as e:
        raise Exception(f"Database connection failed: {str(e)}")

@mcp.tool()
async def get_active_disruptions(source_country: Optional[str] = None, destination_country: Optional[str] = None) -> Dict[str, Any]:
    """
    Get active global disruptions that might affect orders between countries.
    
    Args:
        source_country (str, optional): The country of origin for the shipment
        destination_country (str, optional): The destination country for the shipment
    
    Returns:
        dict: Information about current disruptions that might affect shipping
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Base query to get disruptions
        query = """
        SELECT 
            disruption_id,
            source_country,
            destination_country,
            disruption_type,
            severity,
            start_date,
            expected_end_date,
            actual_end_date,
            is_active,
            description,
            impact_hours,
            created_at,
            updated_at
        FROM 
            live_global_disruptions
        WHERE 
            is_active = TRUE
        """
        
        params = []
        
        # Add filters for specific countries if provided
        if source_country and destination_country:
            query += """
            AND (
                (source_country = %s AND destination_country = %s) OR
                (source_country = %s) OR
                (destination_country = %s)
            )
            """
            params.extend([source_country, destination_country, source_country, destination_country])
        elif source_country:
            query += """
            AND (source_country = %s)
            """
            params.append(source_country)
        elif destination_country:
            query += """
            AND (destination_country = %s)
            """
            params.append(destination_country)
        
        # Order by severity and recency
        query += """
        ORDER BY 
            severity DESC,
            updated_at DESC;
        """

        print(query, params)  # Debugging line to see the query and parameters
        
        cursor.execute(query, params)
        disruptions = cursor.fetchall()
        
        now = datetime.now()
        
        # Create message based on filter criteria
        if source_country and destination_country:
            message = f"Disruptions affecting shipments between {source_country} and {destination_country}"
        elif source_country:
            message = f"Disruptions affecting shipments from {source_country}"
        elif destination_country:
            message = f"Disruptions affecting shipments to {destination_country}"
        else:
            message = "All active global disruptions"
        
        if not disruptions:
            return {
                "success": True,
                "message": f"No active disruptions found for {message.lower()}.",
                "source_country": source_country,
                "destination_country": destination_country,
                "disruptions": [],
                "count": 0,
                "has_critical": False,
                "max_severity": 0,
                "recommendation": "No disruptions found. Shipping should proceed normally."
            }
        
        # Format the response
        formatted_disruptions = []
        for disruption in disruptions:
            d = dict(disruption)
            
            # Format severity level as text
            severity = d['severity']
            severity_text = "Critical" if severity == 5 else "High" if severity == 4 else "Medium" if severity == 3 else "Low" if severity == 2 else "Minimal"
            
            # Calculate days active
            days_active = (now.date() - d['start_date']).days if d['start_date'] else None
            
            # Format dates for JSON
            formatted_disruption = {
                "disruption_id": d['disruption_id'],
                "source_country": d['source_country'],
                "destination_country": d['destination_country'],
                "disruption_type": d['disruption_type'],
                "severity": d['severity'],
                "severity_text": severity_text,
                "start_date": d['start_date'].strftime("%Y-%m-%d") if d['start_date'] else None,
                "expected_end_date": d['expected_end_date'].strftime("%Y-%m-%d") if d['expected_end_date'] else None,
                "actual_end_date": d['actual_end_date'].strftime("%Y-%m-%d") if d['actual_end_date'] else None,
                "days_active": days_active,
                "is_active": d['is_active'],
                "description": d['description'],
                "impact_hours": d['impact_hours'],
                "created_at": d['created_at'].strftime("%Y-%m-%d %H:%M:%S") if d['created_at'] else None,
                "updated_at": d['updated_at'].strftime("%Y-%m-%d %H:%M:%S") if d['updated_at'] else None
            }
            formatted_disruptions.append(formatted_disruption)
        
        # Add recommendations based on disruptions
        max_severity = max(d['severity'] for d in disruptions)
        has_critical = any(d['severity'] >= 4 for d in disruptions)
        
        if max_severity >= 4:
            recommendation = "Consider alternative shipping routes or delaying shipments until disruptions are resolved."
        elif max_severity == 3:
            recommendation = "Expect delays and consider adding buffer time to delivery estimates."
        else:
            recommendation = "Monitor situation for changes. Minor delays possible."
        
        return {
            "success": True,
            "message": message,
            "source_country": source_country,
            "destination_country": destination_country,
            "disruptions": formatted_disruptions,
            "count": len(formatted_disruptions),
            "has_critical": has_critical,
            "max_severity": max_severity,
            "recommendation": recommendation
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    mcp.run(transport="stdio")
