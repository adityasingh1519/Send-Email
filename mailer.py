import html
import os
import smtplib
import ssl
from email.header import Header
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path
from typing import Optional, Tuple

from config import config


def format_body_to_html(plain_text: str) -> str:
    """Converts plain text email into clean, email-client-friendly HTML."""
    paragraphs = plain_text.strip().split("\n\n")
    html_paragraphs = []
    for p in paragraphs:
        escaped = html.escape(p).replace("\n", "<br>")
        html_paragraphs.append(f"<p>{escaped}</p>")

    content_html = "\n".join(html_paragraphs)
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
    font-size: 14.5px;
    line-height: 1.6;
    color: #202124;
    margin: 0;
    padding: 10px;
  }}
  .container {{
    max-width: 640px;
  }}
  p {{
    margin: 0 0 14px 0;
  }}
</style>
</head>
<body>
<div class="container">
{content_html}
</div>
</body>
</html>"""


class EmailSender:
    def __init__(self):
        self.server: Optional[smtplib.SMTP] = None
        self._cached_attachment_data: Optional[bytes] = None
        self._cached_attachment_name: str = ""

    def _get_attachment_data(self) -> Tuple[Optional[bytes], str]:
        if not config.attachment_path.exists():
            return None, ""
        
        display_name = config.attachment_display_name or config.attachment_path.name
        if self._cached_attachment_data is None or self._cached_attachment_name != display_name:
            with open(config.attachment_path, "rb") as f:
                self._cached_attachment_data = f.read()
            self._cached_attachment_name = display_name
        return self._cached_attachment_data, self._cached_attachment_name

    def connect(self) -> Tuple[bool, str]:
        """Establishes authenticated connection to the SMTP server."""
        if not config.is_configured():
            return False, "Sender email and password are not configured in .env."

        try:
            context = ssl.create_default_context()
            if config.smtp_use_ssl or config.smtp_port == 465:
                self.server = smtplib.SMTP_SSL(
                    config.smtp_server, config.smtp_port, context=context, timeout=30
                )
            else:
                self.server = smtplib.SMTP(
                    config.smtp_server, config.smtp_port, timeout=30
                )
                self.server.ehlo()
                self.server.starttls(context=context)
                self.server.ehlo()

            # Clean Google App Password (strip any accidental spaces)
            cleaned_password = config.sender_password.replace(" ", "")
            self.server.login(config.sender_email, cleaned_password)
            return True, "Successfully connected and authenticated!"

        except smtplib.SMTPAuthenticationError as e:
            return (
                False,
                f"Authentication failed ({e.smtp_code}): Invalid username or password.\n"
                "If using Gmail, you MUST use a 16-character App Password (not your normal Google password).\n"
                "Generate one at: https://myaccount.google.com/apppasswords"
            )
        except smtplib.SMTPConnectError as e:
            return False, f"Could not connect to SMTP server: {e}"
        except Exception as e:
            return False, f"Connection error: {e}"

    def ensure_connected(self):
        """Checks if connection is alive; reconnects if socket dropped."""
        connected = False
        if self.server:
            try:
                status = self.server.noop()[0]
                if status == 250:
                    connected = True
            except Exception:
                connected = False

        if not connected:
            success, msg = self.connect()
            if not success:
                raise ConnectionError(f"Failed to reconnect to SMTP server: {msg}")

    def send_email(
        self,
        recipient_email: str,
        subject: str,
        body_text: str,
        attachment_filename: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Composes and sends an individual email with the resume PDF attached."""
        try:
            self.ensure_connected()

            msg = MIMEMultipart("mixed")
            # Set From header with proper UTF-8 name encoding
            msg["From"] = formataddr((str(Header(config.sender_name, "utf-8")), config.sender_email))
            msg["To"] = recipient_email
            msg["Subject"] = Header(subject, "utf-8")
            msg["Reply-To"] = config.sender_email

            # Alternative container for plain text + HTML
            alt_part = MIMEMultipart("alternative")

            # Plain text part
            text_part = MIMEText(body_text, "plain", "utf-8")
            alt_part.attach(text_part)

            # HTML part
            html_content = format_body_to_html(body_text)
            html_part = MIMEText(html_content, "html", "utf-8")
            alt_part.attach(html_part)

            msg.attach(alt_part)

            # Attach Resume PDF
            pdf_bytes, default_name = self._get_attachment_data()
            if pdf_bytes:
                target_filename = attachment_filename or default_name
                pdf_attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
                pdf_attachment.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=target_filename
                )
                msg.attach(pdf_attachment)

            self.server.sendmail(config.sender_email, [recipient_email], msg.as_string())
            return True, "Delivered"

        except smtplib.SMTPException as e:
            return False, f"SMTP Error: {e}"
        except Exception as e:
            return False, f"Error: {e}"

    def close(self):
        if self.server:
            try:
                self.server.quit()
            except Exception:
                try:
                    self.server.close()
                except Exception:
                    pass
            finally:
                self.server = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
