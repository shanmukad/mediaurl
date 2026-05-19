import os
import requests
import logging
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    filename="log.txt",
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)

FRESHDESK_DOMAIN = os.getenv("FRESHDESK_DOMAIN")
FRESHDESK_API_KEY = os.getenv("FRESHDESK_API_KEY")

AUTH = HTTPBasicAuth(FRESHDESK_API_KEY, "X")

# 👇 THIS IS YOUR AI AGENT ID (from Freshdesk)
PROVISIONING_AI_AGENT_ID = int(os.getenv("FRESHDESK_PROV_AI_AGENT_ID"))


# =========================
# ASSIGN AI AGENT
# =========================
def assign_ai_agent(ticket_id: int):

    url = (
        f"https://{FRESHDESK_DOMAIN}"
        f"/api/v2/tickets/{ticket_id}"
    )

    payload = {

    "responder_id":
        PROVISIONING_AI_AGENT_ID,

    "type":
        "Service Request",

    "custom_fields":
        MEDIA_URL_CUSTOM_FIELDS
}

    print("\n======================")
    print("ASSIGNING AGENT")
    print("======================")

    print("Payload:", payload)

    res = requests.put(
        url,
        json=payload,
        auth=AUTH
    )

    print("Status Code:", res.status_code)
    print("Response:", res.text)

    if res.status_code == 200:

        logging.info(
            f"Assigned AI Agent: {ticket_id}"
        )

        return True

    logging.error(
        f"Assign failed: {res.text}"
    )

    return False

# =========================
# RESOLVE TICKET
# =========================
def resolve_ticket(ticket_id: int):

    # =========================
    # FETCH EXISTING TICKET
    # =========================

    get_url = (
        f"https://{FRESHDESK_DOMAIN}"
        f"/api/v2/tickets/{ticket_id}"
    )

    get_res = requests.get(
        get_url,
        auth=AUTH
    )

    if get_res.status_code != 200:

        logging.error(
            f"Unable to fetch ticket before resolve: "
            f"{get_res.text}"
        )

        return False

    ticket = get_res.json()

    existing_type = ticket.get(
        "type"
    ) or "Service Request"

    existing_priority = ticket.get(
        "priority"
    ) or 2

    # =========================
    # RESOLVE PAYLOAD
    # =========================

    payload = {

        # RESOLVED
        "status": 4,

        # KEEP EXISTING PRIORITY
        "priority": existing_priority,

        # KEEP VALID TYPE
        "type": existing_type,

        # AGENT
        "responder_id":
            PROVISIONING_AI_AGENT_ID,

        # CUSTOM FIELDS
        "custom_fields":
            MEDIA_URL_CUSTOM_FIELDS
    }

    print("\n======================")
    print("RESOLVING TICKET")
    print("======================")

    print("Payload:", payload)

    put_url = (
        f"https://{FRESHDESK_DOMAIN}"
        f"/api/v2/tickets/{ticket_id}"
    )

    res = requests.put(
        put_url,
        json=payload,
        auth=AUTH
    )

    print("Status Code:", res.status_code)
    print("Response:", res.text)

    if res.status_code == 200:

        logging.info(
            f"Ticket resolved: {ticket_id}"
        )

        return True

    logging.error(
        f"Resolve failed: {res.text}"
    )

    return False

MEDIA_URL_CUSTOM_FIELDS = {

    "cf_parent_ticket_id_k_pro": "NA",
    "cf_child_ticket_id_k_pro": "NA",
    "cf_escalation_tagging_k_pro": "No",
    "cf_service_prov_k_pro": "WhatsApp",
    "cf_product_prov_k_pro": "WhatsApp Services",
    "cf_problem_prov_k_pro": "WhatsApp Sify",
    "cf_description_prov_k_pro": "WhatsApp Media URL",
    "cf_company_name_k_camp": "AWS",
    "cf_company_name_k_pro": "NA",
    "cf_testing": "NA",
    "cf_reopen_ticket": "New Request",
    "cf_sop_referred": True,
    "cf_severity": "Major",
    "cf_group_fields_test": "Provisioning Team",
    "cf_send_survey_to_customer": False
}

#Keyword Validation

MEDIA_KEYWORDS = [
    "aws link",
    "media url",
    "card links",
    "share the link",
    "attached catalogue",
    "attached cards"
]

# =========================
# FETCH TICKET PREVIEW
# =========================
def get_ticket_preview(ticket_id: int):

    url = (
        f"https://{FRESHDESK_DOMAIN}"
        f"/api/v2/tickets/{ticket_id}"
    )

    res = requests.get(
        url,
        auth=AUTH
    )

    if res.status_code != 200:

        return {
            "success": False,
            "message": "Unable to fetch ticket"
        }

    ticket = res.json()

    subject = ticket.get("subject", "")

    description = (
        ticket.get("description_text", "")
        or ""
    )

    group_id = ticket.get("group_id")

    attachments = ticket.get("attachments", [])

    attachment_count = len(attachments)

    # -------------------------
    # KEYWORD VALIDATION
    # -------------------------

    combined_text = (
        f"{subject} {description}"
    ).lower()

    keyword_match = any(
        k in combined_text
        for k in MEDIA_KEYWORDS
    )

    # -------------------------
    # FINAL VALIDATION
    # -------------------------

    is_valid = (
        attachment_count > 0 and
        keyword_match
    )

    return {

        "success": True,

        "ticket_id":
            ticket_id,

        "subject":
            subject,

        "attachments":
            attachment_count,

        "group_id":
            group_id,

        "is_valid":
            is_valid
    }
# =========================
# FINAL WORKFLOW
# =========================
# =========================
# FINALIZE TICKET
# =========================
def finalize_ticket(
    ticket_id: int,
    from_ui: bool = False
):

    url = (
        f"https://{FRESHDESK_DOMAIN}"
        f"/api/v2/tickets/{ticket_id}"
    )

    payload = {

        # RESOLVED
        "status": 4,

        # HIGH PRIORITY
        "priority": 3,

        # ASSIGN AGENT
        "responder_id":
            PROVISIONING_AI_AGENT_ID,

        "custom_fields":
            MEDIA_URL_CUSTOM_FIELDS
    }

    print("\n======================")
    print("FINALIZING TICKET")
    print("======================")

    print("Payload:", payload)

    res = requests.put(
        url,
        json=payload,
        auth=AUTH
    )

    print("Status Code:", res.status_code)
    print("Response:", res.text)

    if res.status_code == 200:

        logging.info(
            f"Ticket finalized: {ticket_id}"
        )

        return True

    logging.error(
        f"Finalize failed: {res.text}"
    )

    return False