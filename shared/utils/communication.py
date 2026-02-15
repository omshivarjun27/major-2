"""
Communication tools for Ally Vision Assistant

Local contacts (JSON) + standard IMAP/SMTP email.
Zero Google SDK dependencies.
"""

import os
import re
import json
import logging
import smtplib
import imaplib
import email as email_lib
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import parsedate_to_datetime
from shared.config import get_config
from shared.utils.helpers import get_current_date_time

# Simple logger without custom handler
logger = logging.getLogger("communication-tool")

# Default path for the local contacts store
_DEFAULT_CONTACTS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "contacts.json",
)


class CommunicationTool:
    """Handler for local contacts and IMAP/SMTP email."""

    def __init__(self, contacts_file: Optional[str] = None):
        """Initialise the Communication handler."""
        config = get_config()
        self.is_ready = False
        self.contacts_file = contacts_file or _DEFAULT_CONTACTS_FILE

        try:
            # Email credentials (SMTP send + IMAP read)
            self.sender_email = config.get("GMAIL_MAIL") or os.getenv("GMAIL_MAIL")
            self.app_password = config.get("GMAIL_APP_PASSWORD") or os.getenv("GMAIL_APP_PASSWORD")

            # IMAP settings – defaults to Gmail IMAP but works with any provider
            self.imap_host = config.get("IMAP_HOST") or os.getenv("IMAP_HOST", "imap.gmail.com")
            self.imap_port = int(config.get("IMAP_PORT") or os.getenv("IMAP_PORT", "993"))

            # SMTP settings
            self.smtp_host = config.get("SMTP_HOST") or os.getenv("SMTP_HOST", "smtp.gmail.com")
            self.smtp_port = int(config.get("SMTP_PORT") or os.getenv("SMTP_PORT", "465"))

            if not self.sender_email or not self.app_password:
                logger.warning("Email credentials not found. Email functionality will be limited.")

            self._ensure_contacts_file()
            self.is_ready = True
            logger.info("Communication tool initialised successfully")
        except Exception as e:
            logger.error(f"Failed to initialise communication tool: {e}")

    # ------------------------------------------------------------------
    # Contacts helpers (local JSON)
    # ------------------------------------------------------------------

    def _ensure_contacts_file(self):
        if not os.path.exists(self.contacts_file):
            with open(self.contacts_file, "w") as f:
                json.dump([], f)

    def _load_contacts(self) -> List[Dict[str, Any]]:
        try:
            with open(self.contacts_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def manage_communication(self, action: str, **kwargs) -> str:
        """
        Unified method to manage communication operations.

        Args:
            action: "find_contact", "read_emails", or "send_email"
            **kwargs: Action-specific arguments
        """
        if not self.is_ready:
            return "Communication tool is not properly initialised."

        try:
            if action == "read_emails":
                if "from_date" not in kwargs or not kwargs["from_date"]:
                    now = datetime.now()
                    kwargs["from_date"] = datetime(now.year, now.month, now.day).isoformat()
                if "to_date" not in kwargs or not kwargs["to_date"]:
                    kwargs["to_date"] = datetime.now().isoformat()

            if action == "find_contact":
                return await self._find_contact(**kwargs)
            elif action == "read_emails":
                return await self._read_emails(**kwargs)
            elif action == "send_email":
                return await self._send_email(**kwargs)
            else:
                return f"Unsupported communication action: {action}"
        except Exception as e:
            error_msg = f"Unexpected error in communication action {action}: {e}"
            logger.error(error_msg)
            return f"An unexpected error occurred: {str(e)}"

    # ------------------------------------------------------------------
    # Find contact (local JSON)
    # ------------------------------------------------------------------

    async def _find_contact(self, name: str) -> str:
        """Find contact information by name from local contacts store."""
        try:
            contacts = self._load_contacts()

            if not contacts:
                return (
                    f"No contacts stored yet. Add contacts to {self.contacts_file} "
                    f"in the format: "
                    '[{"name": "John Doe", "emails": ["j@example.com"], "phone_numbers": ["123"]}]'
                )

            name_lower = name.lower()
            matching = []
            for c in contacts:
                stored_name = c.get("name", "").lower()
                # Match first name, last name, or full name
                first_name_pattern = r"^(\w+)"
                last_name_pattern = r"(\w+)$"
                first_match = re.search(first_name_pattern, stored_name)
                last_match = re.search(last_name_pattern, stored_name)

                if (
                    name_lower == stored_name
                    or (first_match and name_lower == first_match.group(1))
                    or (last_match and name_lower == last_match.group(1))
                ):
                    matching.append(c)

            if not matching:
                return f"No contact found with the name: {name}"

            formatted = []
            for i, c in enumerate(matching, 1):
                info = [f"Contact {i}: {c.get('name', 'N/A')}"]
                if c.get("emails"):
                    info.append(f"Emails: {', '.join(c['emails'])}")
                if c.get("phone_numbers"):
                    info.append(f"Phones: {', '.join(c['phone_numbers'])}")
                formatted.append("\n".join(info))

            return "\n\n".join(formatted)

        except Exception as error:
            error_msg = f"Error finding contact: {error}"
            logger.error(error_msg)
            return f"An error occurred: {error}"

    # ------------------------------------------------------------------
    # Read emails (IMAP)
    # ------------------------------------------------------------------

    async def _read_emails(
        self, from_date: str, to_date: str, email: Optional[str] = None
    ) -> str:
        """Read emails from inbox via IMAP within a date range."""
        if not self.sender_email or not self.app_password:
            return "Cannot read emails: credentials not configured. Set GMAIL_MAIL and GMAIL_APP_PASSWORD (or IMAP_HOST)."

        try:
            # Connect via IMAP
            mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            mail.login(self.sender_email, self.app_password)
            mail.select("inbox")

            # Build IMAP search criteria
            from_dt = datetime.fromisoformat(from_date)
            to_dt = datetime.fromisoformat(to_date)
            since_str = from_dt.strftime("%d-%b-%Y")
            before_str = to_dt.strftime("%d-%b-%Y")

            criteria = f'(SINCE {since_str} BEFORE {before_str})'
            if email:
                criteria = f'(SINCE {since_str} BEFORE {before_str} FROM "{email}")'

            _, message_ids = mail.search(None, criteria)
            ids = message_ids[0].split()

            if not ids:
                mail.logout()
                return "No emails found in the specified time range."

            email_list = []
            for msg_id in ids[:10]:  # Limit to 10
                _, msg_data = mail.fetch(msg_id, "(RFC822)")
                raw = msg_data[0][1]
                msg = email_lib.message_from_bytes(raw)

                subject = msg.get("Subject", "No Subject")
                from_addr = msg.get("From", "Unknown Sender")
                date_str = msg.get("Date", "")

                try:
                    date_obj = parsedate_to_datetime(date_str)
                    if date_obj.tzinfo is None:
                        date_obj = date_obj.replace(tzinfo=timezone.utc)
                    formatted_date = date_obj.strftime("%Y-%m-%d %H:%M:%S %Z")
                except Exception:
                    formatted_date = date_str

                # Extract snippet (first 200 chars of body)
                snippet = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            snippet = part.get_payload(decode=True).decode(errors="replace")[:200]
                            break
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        snippet = payload.decode(errors="replace")[:200]

                email_list.append(
                    f"From: {from_addr}\n"
                    f"Subject: {subject}\n"
                    f"Date: {formatted_date}\n"
                    f"Snippet: {snippet}\n"
                )

            mail.logout()
            logger.info(f"Retrieved {len(email_list)} emails")

            if len(ids) > 10:
                email_list.append(
                    f"\n(Showing 10 of {len(ids)} emails. Narrow your search to see more.)"
                )

            return "\n".join(email_list)

        except Exception as error:
            error_msg = f"Error reading emails: {error}"
            logger.error(error_msg)
            return f"An error occurred: {error}"

    # ------------------------------------------------------------------
    # Send email (SMTP – unchanged protocol)
    # ------------------------------------------------------------------

    async def _send_email(self, to: str, subject: str, body: str) -> str:
        """Send an email to a recipient via SMTP."""
        try:
            if not self.sender_email or not self.app_password:
                return "Cannot send email: credentials not configured. Set GMAIL_MAIL and GMAIL_APP_PASSWORD."

            msg = MIMEMultipart()
            msg["From"] = self.sender_email
            msg["To"] = to
            msg["Subject"] = subject

            body_with_timestamp = f"{body}\n\nSent: {get_current_date_time()}"
            msg.attach(MIMEText(body_with_timestamp, "plain"))

            server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
            server.login(self.sender_email, self.app_password)
            server.sendmail(self.sender_email, to, msg.as_string())
            server.quit()

            logger.info(f"Email sent to {to} with subject: {subject}")
            return f"Email sent successfully to {to}."

        except Exception as e:
            error_msg = f"Error sending email: {e}"
            logger.error(error_msg)
            return f"Email was not sent successfully, error: {str(e)}"