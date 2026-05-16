import sys

from dotenv import load_dotenv
import os
import time
import requests
import json
import logging

from datetime import datetime, timedelta, timezone
from typing import Set
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

MEDIAURL_PATH = os.path.abspath(
    os.path.join(
        CURRENT_DIR,
        "..",
        "MediaURL"
    )
)

sys.path.append(MEDIAURL_PATH)
from Shared.ticket_processor import process_ticket

load_dotenv()


# =========================
# CONFIG
# =========================

FRESHDESK_DOMAIN = os.getenv("FRESHDESK_DOMAIN")
FRESHDESK_API_KEY = os.getenv("FRESHDESK_API_KEY")

PROV_AI_AGENT_ID = os.getenv(
    "FRESHDESK_PROV_AI_AGENT_ID"
)

MEDIA_URL_CF_KEY = os.getenv(
    "MEDIA_URL_CF_KEY"
)

MEDIA_URL_CF_VALUE = os.getenv(
    "MEDIA_URL_CF_VALUE"
)

OUTPUT_DIR = os.getenv("OUTPUT_DIR")

PROCESSED_FILE = os.path.join(
    OUTPUT_DIR,
    "processed_tickets.json"
)

LAST_SEEN_FILE = os.path.join(
    OUTPUT_DIR,
    "last_seen_updated_at.txt"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(
        OUTPUT_DIR,
        "..",
        "poller.log"
    ),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logging.info(
    "=== Freshdesk Poller Started ==="
)


# =========================
# PROCESSED TICKETS
# =========================

def load_processed_tickets() -> Set[int]:

    if os.path.exists(PROCESSED_FILE):

        try:

            with open(PROCESSED_FILE, "r") as f:

                data = json.load(f)

                return set(
                    data.get("tickets", [])
                )

        except Exception:

            logging.warning(
                "Could not load processed tickets"
            )

    return set()


def save_processed_tickets(
    tickets: Set[int]
):

    with open(PROCESSED_FILE, "w") as f:

        json.dump(
            {
                "tickets": list(tickets),
                "last_updated": datetime.now().isoformat()
            },
            f
        )


# =========================
# LAST SEEN
# =========================

def load_last_seen():

    if os.path.exists(LAST_SEEN_FILE):

        try:

            with open(LAST_SEEN_FILE, "r") as f:

                return f.read().strip()

        except Exception:

            pass

    return None


def save_last_seen(timestamp: str):

    with open(LAST_SEEN_FILE, "w") as f:

        f.write(timestamp)


# =========================
# POLLER
# =========================

def poll_tickets():

    processed_tickets = (
        load_processed_tickets()
    )

    last_seen_updated_at = (
        load_last_seen()
    )

    logging.info(
        f"Loaded {len(processed_tickets)} "
        f"processed tickets"
    )

    LOOKBACK_MINUTES = 10

    while True:

        try:

            fallback_since = (
                datetime.now(timezone.utc)
                - timedelta(
                    minutes=LOOKBACK_MINUTES
                )
            ).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

            params = {
                "per_page": 100,
                "order_by": "updated_at",
                "order_type": "asc",
                "updated_since": (
                    last_seen_updated_at
                    or fallback_since
                ),
            }

            url = (
                f"https://{FRESHDESK_DOMAIN}"
                f"/api/v2/tickets"
            )

            auth = (
                FRESHDESK_API_KEY,
                "X"
            )

            resp = requests.get(
                url,
                auth=auth,
                params=params
            )

            if resp.status_code != 200:

                logging.error(
                    f"API error: "
                    f"{resp.status_code}"
                )

                time.sleep(300)

                continue

            tickets = resp.json()

            logging.info(
                f"Fetched "
                f"{len(tickets)} tickets"
            )

            # Track latest timestamp seen in this batch
            latest_updated_at = (
                last_seen_updated_at
            )

            for ticket in tickets:

                ticket_id = ticket.get("id")

                if not ticket_id:
                    continue

                # =========================
                # ADVANCE CURSOR FIRST
                # =========================

                updated_at = ticket.get(
                    "updated_at"
                )

                if (
                    updated_at
                    and (
                        not latest_updated_at
                        or updated_at
                        > latest_updated_at
                    )
                ):

                    latest_updated_at = (
                        updated_at
                    )

                # =========================
                # SKIP LOCAL CACHE
                # =========================

                if (
                    ticket_id
                    in processed_tickets
                ):

                    logging.info(
                        f"⏭️ Ticket already "
                        f"processed locally: "
                        f"{ticket_id}"
                    )

                    continue

                # =========================
                # AGENT VALIDATION
                # =========================

                responder_id = (
                    ticket.get("responder_id")
                    or ticket.get(
                        "responder",
                        {}
                    ).get("id")
                    or ticket.get(
                        "group_responder",
                        {}
                    ).get("id")
                )

                responder_id = (
                    str(responder_id)
                    if responder_id
                    else None
                )

                if (
                    responder_id
                    != PROV_AI_AGENT_ID
                ):
                    continue

                # =========================
                # CUSTOM FIELD VALIDATION
                # =========================

                custom_fields = (
                    ticket.get(
                        "custom_fields",
                        {}
                    )
                )

                request_type = (
                    custom_fields.get(
                        MEDIA_URL_CF_KEY
                    )
                )

                if (
                    request_type
                    != MEDIA_URL_CF_VALUE
                ):
                    continue

                logging.info(
                    f"Processing ticket "
                    f"{ticket_id}"
                )

                # =========================
                # PROCESS TICKET
                # =========================

                result = process_ticket(
                    ticket_id
                )

                logging.info(
                    f"Result: {result}"
                )

                already_processed = (
                    result.get("message")
                    == "Ticket already processed"
                )

                if (
                    result.get("success")
                    or already_processed
                ):

                    processed_tickets.add(
                        ticket_id
                    )

                    save_processed_tickets(
                        processed_tickets
                    )

                    logging.info(
                        f"✅ Completed "
                        f"ticket {ticket_id}"
                    )

                else:

                    logging.error(
                        f"❌ Failed "
                        f"ticket {ticket_id}: "
                        f"{result}"
                    )

            # =========================
            # MOVE CURSOR FORWARD
            # =========================

            if latest_updated_at:

                dt = datetime.strptime(
                    latest_updated_at,
                    "%Y-%m-%dT%H:%M:%SZ"
                )

                # Freshdesk updated_since
                # is inclusive
                next_cursor = (
                    dt + timedelta(seconds=1)
                ).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                )

                last_seen_updated_at = (
                    next_cursor
                )

                save_last_seen(
                    last_seen_updated_at
                )

                logging.info(
                    f"Updated cursor to "
                    f"{last_seen_updated_at}"
                )

            time.sleep(30)

        except Exception as e:

            logging.exception(
                f"Poller error: {e}"
            )

            time.sleep(30)

# =========================
# MAIN
# =========================

if __name__ == "__main__":

    poll_tickets()