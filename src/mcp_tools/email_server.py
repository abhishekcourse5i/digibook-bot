# email_server.py
from typing import Dict, Any, List, Optional
import os
import mimetypes
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
import smtplib
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("Email")

@mcp.tool()
async def send_email(
    subject: str,
    body: str,
    to_email: str,
    format_type: str = "plain",
    file_path: Optional[str] = None,
    inline_images: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send emails with optional attachments and inline images.

    Args:
        subject (str): The subject of the email
        body (str): The body of the email
        to_email (str): Comma-separated list of recipient emails
        format_type (str): Email format type - "plain" (default), "html", or "rtf"
        file_path (str, optional): Comma-separated list of file paths to attach
        inline_images (str, optional): Path to an image file to include inline (for HTML emails)

    Returns:
        dict: Result of the email operation
    """
    try:
        # Get email configuration from environment
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_username = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")
        
        if not all([smtp_username, smtp_password]):
            return {
                "success": False,
                "error": "SMTP credentials not found in environment variables"
            }

        # Create message
        msg = MIMEMultipart('alternative' if format_type.lower() == 'html' else 'mixed')
        msg['Subject'] = subject
        msg['From'] = smtp_username
        msg['To'] = to_email

        # Handle different format types
        if format_type.lower() == "html":
            msg.attach(MIMEText(body, 'html'))
        elif format_type.lower() == "rtf":
            msg.attach(MIMEText("This email contains RTF content. Please see the attachment.", 'plain'))
            rtf_attachment = MIMEApplication(body.encode(), _subtype='rtf')
            rtf_attachment.add_header('Content-Disposition', 'attachment', filename='message.rtf')
            msg.attach(rtf_attachment)
        else:  # plain text
            msg.attach(MIMEText(body, 'plain'))

        # Handle inline images (for HTML emails)
        if inline_images and format_type.lower() == "html":
            try:
                with open(inline_images, 'rb') as img:
                    image_data = img.read()
                    content_id = "image1"
                    mime_type = mimetypes.guess_type(inline_images)[0] or 'image/jpeg'
                    subtype = mime_type.split('/')[1]
                    
                    mime_image = MIMEImage(image_data, _subtype=subtype)
                    mime_image.add_header('Content-ID', f'<{content_id}>')
                    mime_image.add_header('Content-Disposition', 'inline', filename=os.path.basename(inline_images))
                    msg.attach(mime_image)
            except FileNotFoundError:
                return {
                    "success": False,
                    "error": f"Inline image not found: {inline_images}"
                }

        # Handle file attachments
        if file_path:
            file_paths = [p.strip() for p in file_path.split(",")]
            for path in file_paths:
                try:
                    with open(path, 'rb') as f:
                        mime_type, _ = mimetypes.guess_type(path)
                        if mime_type is None:
                            mime_type = 'application/octet-stream'
                        
                        maintype, subtype = mime_type.split('/')
                        if maintype == 'text':
                            attachment = MIMEText(f.read().decode(), _subtype=subtype)
                        elif maintype == 'image':
                            attachment = MIMEImage(f.read(), _subtype=subtype)
                        else:
                            attachment = MIMEApplication(f.read(), _subtype=subtype)
                        
                        attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(path))
                        msg.attach(attachment)
                except FileNotFoundError:
                    return {
                        "success": False,
                        "error": f"Attachment file not found: {path}"
                    }

        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)

        # Format a detailed response
        response = f"Email sent successfully\n"
        response += f"To: {to_email}\n"
        response += f"Subject: {subject}\n"
        response += f"Format: {format_type}\n"
        
        if file_path:
            response += "\nAttachments:\n"
            for path in file_path.split(","):
                response += f"- {os.path.basename(path.strip())}\n"
                
        if inline_images and format_type.lower() == "html":
            response += f"\nInline Images:\n- {os.path.basename(inline_images)}\n"
            
        return response

    except Exception as e:
        error_msg = f"Failed to send email: {str(e)}"
        return {
            "success": False,
            "error": error_msg
        }

if __name__ == "__main__":
    mcp.run(transport="stdio")
