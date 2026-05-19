import os
import requests
import logging

logger = logging.getLogger(__name__)

FRESHDESK_DOMAIN = os.getenv("FRESHDESK_DOMAIN")
FRESHDESK_API_KEY = os.getenv("FRESHDESK_API_KEY")


# Safety check (IMPORTANT)
if not FRESHDESK_DOMAIN or not FRESHDESK_API_KEY:
    raise ValueError("Missing Freshdesk environment variables")


def build_validation_reply():
    return """Hi,

We were unable to process your request due to one or more file issues:

- File size exceeds allowed limit (15MB)
- Invalid or unsupported file format
- Missing, corrupted, or inaccessible attachments
- External link could not be processed

Please re-submit the request with valid files.

Regards,
Provisioning AI
"""


def send_failure_reply(ticket_id: int, message: str):
    """
    Sends validation failure reply to Freshdesk ticket.
    """

    url = f"https://{FRESHDESK_DOMAIN}/api/v2/tickets/{ticket_id}/reply"

    safe_message = (message or build_validation_reply()).replace("\n", "<br>")

    body = f"""
    Hi,<br><br>

    {safe_message}<br><br>

    Regards,<br>
    Provisioning AI
    """

    try:
        res = requests.post(
            url,
            auth=(FRESHDESK_API_KEY, "X"),
            data=[("body", body)]
        )

        if res.status_code in (200, 201):
            logger.info(f"Failure reply sent for ticket {ticket_id}")
            return True

        logger.error(f"Failure reply failed: {res.text}")
        return False

    except Exception as e:
        logger.error(f"Failure reply exception: {e}")
        return False