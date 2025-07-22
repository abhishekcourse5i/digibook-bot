# erp_server.py
from typing import Dict, Any, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from mcp.server.fastmcp import FastMCP
import os
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()

mcp = FastMCP("ERP Database")

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
async def execute_query(query: str, params: Optional[List] = None) -> Dict[str, Any]:
    """
    Execute a custom SQL query on the ERP database.
    
    Args:
        query (str): SQL query to execute
        params (List, optional): Parameters for parameterized queries
    
    Returns:
        dict: Query results or error message
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        # Check if it's a SELECT query
        if query.strip().upper().startswith('SELECT'):
            results = cursor.fetchall()
            # Convert RealDictRow to regular dict for JSON serialization
            results = [dict(row) for row in results]
            if not results:
                return "No results found"
            return results
        else:
            # For INSERT, UPDATE, DELETE queries
            conn.commit()
            return f"Query executed successfully. {cursor.rowcount} rows affected."
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        if 'conn' in locals():
            conn.close()

@mcp.tool()
async def list_erp_tables() -> Dict[str, Any]:
    """
    List all ERP tables in the database.
    
    Returns:
        dict: List of ERP table names
    """
    query = """
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public'
    AND table_name LIKE 'erp_%'
    ORDER BY table_name;
    """
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query)
        results = cursor.fetchall()
        
        table_names = [row['table_name'] for row in results]
        if not table_names:
            return {
                "success": False,
                "message": "No ERP tables found",
                "tables": []
            }
        return {
            "success": True,
            "message": f"Found {len(table_names)} tables",
            "count": len(table_names),
            "tables": table_names
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        if 'conn' in locals():
            conn.close()

@mcp.tool()
async def get_order_status(order_id: int) -> Dict[str, Any]:
    """
    Get the status of an order by order ID.
    
    Args:
        order_id (int): The ID of the order to check
    
    Returns:
        dict: Order status information including shipping and destination countries
    """
    query = """
    SELECT o.*, c.name as customer_name, c.email as customer_email,
           o.shipping_country, o.destination_country
    FROM erp_orders o
    JOIN erp_customers c ON o.customer_id = c.customer_id
    WHERE o.order_id = %s;
    """
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, [order_id])
        order = cursor.fetchone()
        
        if not order:
            return {
                "success": False,
                "message": f"Order with ID {order_id} not found"
            }
        
        # Get order items
        items_query = """
        SELECT oi.order_item_id, oi.order_id, oi.product_id, oi.quantity, oi.unit_price, oi.subtotal,
               p.product_name, p.sku
        FROM erp_order_items oi
        JOIN erp_products p ON oi.product_id = p.product_id
        WHERE oi.order_id = %s;
        """
        cursor.execute(items_query, [order_id])
        items = cursor.fetchall()
        
        # Get order history
        history_query = """
        SELECT * FROM erp_order_history
        WHERE order_id = %s
        ORDER BY timestamp DESC;
        """
        cursor.execute(history_query, [order_id])
        history = cursor.fetchall()
        
        order_dict = dict(order)
        items_list = [dict(item) for item in items]
        history_list = [dict(entry) for entry in history]
        
        # Return JSON formatted response
        return {
            "success": True,
            "order": {
                "order_id": order_id,
                "customer": {
                    "customer_id": order_dict['customer_id'],
                    "name": order_dict['customer_name'],
                    "email": order_dict['customer_email']
                },
                "status": order_dict['status'],
                "shipping_address": order_dict.get('shipping_address', 'N/A'),
                "shipping_country": order_dict.get('shipping_country', 'N/A'),
                "destination_country": order_dict.get('destination_country', 'N/A'),
                "items": items_list,
                "history": history_list
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        if 'conn' in locals():
            conn.close()

@mcp.tool()
async def place_new_order(
    customer_id: int,
    items: List[Dict[str, Any]],
    shipping_address: str,
    shipping_country: str,
    destination_country: str,
    previous_order_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Place a new order in the ERP system, after ensuring there are no global disruptions affecting the shipment.
    
    Args:
        customer_id (int): ID of the customer placing the order
        items (List[Dict]): List of items to order, each with product_id and quantity
        shipping_address (str): Shipping address for the order
        shipping_country (str): Country where the order will be shipped from
        destination_country (str): Country where the order will be delivered to
        previous_order_id (int, optional): ID of a previous order this is replacing
    
    Returns:
        dict: New order information
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Calculate total amount based on the total items and their prices
        total_amount = 0
        for item in items:
            product_query = "SELECT price FROM erp_products WHERE product_id = %s;"
            cursor.execute(product_query, [item['product_id']])
            product = cursor.fetchone()
            if not product:
                return {
                    "success": False,
                    "error": f"Product with ID {item['product_id']} not found"
                }
            total_amount += product['price'] * item['quantity']
        
        # Insert new order into the erp_orders table for the customer
        order_query = """
        INSERT INTO erp_orders (
            customer_id, order_date, total_amount, status, 
            shipping_address, shipping_country, destination_country, previous_order_id,
            estimated_delivery, payment_status
        ) VALUES (
            %s, CURRENT_DATE, %s, 'Processing', 
            %s, %s, %s, %s,
            CURRENT_DATE + INTERVAL '7 days', 'Pending'
        ) RETURNING order_id;
        """
        cursor.execute(order_query, [
            customer_id, total_amount, shipping_address, shipping_country, destination_country, previous_order_id
        ])
        new_order_id = cursor.fetchone()['order_id']
        
        # Insert order items into erp_order_items table for the new order
        for item in items:
            # Get product price
            cursor.execute(product_query, [item['product_id']])
            product = cursor.fetchone()
            unit_price = product['price']
            subtotal = unit_price * item['quantity']
            
            item_query = """
            INSERT INTO erp_order_items (
                order_id, product_id, quantity, unit_price, subtotal
            ) VALUES (
                %s, %s, %s, %s, %s
            );
            """
            cursor.execute(item_query, [
                new_order_id, item['product_id'], item['quantity'], 
                unit_price, subtotal
            ])
            
            # Update product stock
            update_stock_query = """
            UPDATE erp_products 
            SET stock_quantity = stock_quantity - %s 
            WHERE product_id = %s;
            """
            cursor.execute(update_stock_query, [item['quantity'], item['product_id']])
        
        # Create order history entry into the erp_order_history for the new order
        history_query = """
        INSERT INTO erp_order_history (
            order_id, timestamp, status_change, notes, updated_by
        ) VALUES (
            %s, CURRENT_TIMESTAMP, 'Order Created', 'New order placed', 'System'
        );
        """
        cursor.execute(history_query, [new_order_id])
        
        # If this is a replacement order, add a note to the previous order
        if previous_order_id:
            prev_order_note_query = """
            INSERT INTO erp_order_history (
                order_id, timestamp, status_change, notes, updated_by
            ) VALUES (
                %s, CURRENT_TIMESTAMP, 'Replaced', 'Order replaced by order #%s', 'System'
            );
            """
            cursor.execute(prev_order_note_query, [previous_order_id, new_order_id])
        
        # Generate invoice for the new order
        invoice_query = """
        INSERT INTO erp_invoices (
            order_id, invoice_date, amount, payment_terms, due_date, is_paid, invoice_number
        ) VALUES (
            %s, CURRENT_DATE, %s, 'Net 30', CURRENT_DATE + INTERVAL '30 days', FALSE, 'INV-' || %s
        ) RETURNING invoice_id;
        """
        cursor.execute(invoice_query, [new_order_id, total_amount, new_order_id])
        invoice_id = cursor.fetchone()['invoice_id']
        
        conn.commit()
        
        # Get the complete new order details
        cursor.execute("SELECT * FROM erp_orders WHERE order_id = %s;", [new_order_id])
        order = cursor.fetchone()
        
        order_dict = dict(order)
        
        # Return JSON formatted response
        return {
            "success": True,
            "order": {
                "order_id": new_order_id,
                "invoice_id": invoice_id,
                "total_amount": float(total_amount),
                "status": order_dict['status'],
                "estimated_delivery": order_dict['estimated_delivery'].strftime("%Y-%m-%d") if order_dict['estimated_delivery'] else None,
                "customer_id": customer_id,
                "shipping_address": shipping_address,
                "shipping_country": shipping_country,
                "destination_country": destination_country,
                "previous_order_id": previous_order_id
            }
        }
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        if 'conn' in locals():
            conn.close()

@mcp.tool()
async def cancel_order(order_id: int, reason: str) -> Dict[str, Any]:
    """
    Cancel an existing order in the ERP system.
    
    Args:
        order_id (int): ID of the order to cancel
        reason (str): Reason for cancellation
    
    Returns:
        dict: Result of the cancellation operation
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if order exists and can be cancelled
        check_query = """
        SELECT status, customer_id FROM erp_orders WHERE order_id = %s;
        """
        cursor.execute(check_query, [order_id])
        order = cursor.fetchone()
        
        if not order:
            return {
                "success": False,
                "error": f"Order with ID {order_id} not found"
            }
        
        if order['status'] in ['Delivered', 'Cancelled']:
            return {
                "success": False,
                "error": f"Cannot cancel order with status '{order['status']}'"
            }
        
        # Get order items to restore stock
        items_query = """
        SELECT product_id, quantity FROM erp_order_items WHERE order_id = %s;
        """
        cursor.execute(items_query, [order_id])
        items = cursor.fetchall()
        
        # Update order status to Cancelled
        update_query = """
        UPDATE erp_orders SET status = 'Cancelled', payment_status = 'Cancelled'
        WHERE order_id = %s;
        """
        cursor.execute(update_query, [order_id])
        
        # Add entry to order history
        history_query = """
        INSERT INTO erp_order_history (
            order_id, timestamp, status_change, notes, updated_by
        ) VALUES (
            %s, CURRENT_TIMESTAMP, 'Cancelled', %s, 'System'
        );
        """
        cursor.execute(history_query, [order_id, f"Order cancelled: {reason}"])
        
        # Restore product stock quantities
        for item in items:
            restore_stock_query = """
            UPDATE erp_products 
            SET stock_quantity = stock_quantity + %s 
            WHERE product_id = %s;
            """
            cursor.execute(restore_stock_query, [item['quantity'], item['product_id']])
        
        # Update invoice if exists
        invoice_query = """
        UPDATE erp_invoices 
        SET is_paid = FALSE
        WHERE order_id = %s;
        """
        cursor.execute(invoice_query, [order_id])
        
        conn.commit()
        
        return {
            "success": True,
            "message": f"Order #{order_id} has been successfully cancelled",
            "reason": reason,
            "items_restored": len(items)
        }
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        if 'conn' in locals():
            conn.close()

@mcp.tool()
async def get_invoice_details(invoice_id: Optional[int] = None, order_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Get invoice details by invoice ID or order ID.
    
    Args:
        invoice_id (int, optional): ID of the invoice
        order_id (int, optional): ID of the order
    
    Returns:
        dict: Invoice details including customer and order information
    """
    if not invoice_id and not order_id:
        return {
            "success": False,
            "error": "Either invoice_id or order_id must be provided"
        }
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if invoice_id:
            query = """
            SELECT i.*, o.order_date, o.status as order_status, 
                   c.name as customer_name, c.email as customer_email, c.address as customer_address
            FROM erp_invoices i
            JOIN erp_orders o ON i.order_id = o.order_id
            JOIN erp_customers c ON o.customer_id = c.customer_id
            WHERE i.invoice_id = %s;
            """
            cursor.execute(query, [invoice_id])
        else:
            query = """
            SELECT i.*, o.order_date, o.status as order_status, 
                   c.name as customer_name, c.email as customer_email, c.address as customer_address
            FROM erp_invoices i
            JOIN erp_orders o ON i.order_id = o.order_id
            JOIN erp_customers c ON o.customer_id = c.customer_id
            WHERE i.order_id = %s;
            """
            cursor.execute(query, [order_id])
        
        invoice = cursor.fetchone()
        
        if not invoice:
            return {
                "success": False,
                "error": f"Invoice not found for the provided {'invoice_id' if invoice_id else 'order_id'}"
            }
        
        # Get order items
        items_query = """
        SELECT oi.*, p.product_name, p.sku
        FROM erp_order_items oi
        JOIN erp_products p ON oi.product_id = p.product_id
        WHERE oi.order_id = %s;
        """
        cursor.execute(items_query, [invoice['order_id']])
        items = cursor.fetchall()
        
        invoice_dict = dict(invoice)
        items_list = [dict(item) for item in items]
        
        # Return JSON formatted response
        return {
            "success": True,
            "invoice": {
                "invoice_id": invoice_dict['invoice_id'],
                "invoice_number": invoice_dict.get('invoice_number', ''),
                "order_id": invoice_dict['order_id'],
                "order_date": invoice_dict['order_date'].strftime("%Y-%m-%d") if invoice_dict['order_date'] else None,
                "order_status": invoice_dict['order_status'],
                "amount": float(invoice_dict['amount']),
                "due_date": invoice_dict['due_date'].strftime("%Y-%m-%d") if invoice_dict['due_date'] else None,
                "payment_status": "Paid" if invoice_dict['is_paid'] else "Unpaid",
                "customer": {
                    "name": invoice_dict['customer_name'],
                    "email": invoice_dict['customer_email'],
                    "address": invoice_dict['customer_address']
                },
                "items": items_list
            }
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
