from dotenv import load_dotenv
import os
import requests
import logging
import zipfile
import shutil

from Shared.ticket_actions import (
    assign_ai_agent,
    resolve_ticket
)

from Shared.queue_manager import (
    update_status,
    load_processed,
    save_processed
)

from MediaAutomation.automation_runner import run_bulk_automation

load_dotenv()

# =========================
# CONFIG
# =========================

STAGING_DIR = os.getenv("STAGING_DIR")
INPUT_DIR = os.getenv("INPUT_DIR")
OUTPUT_DIR = os.getenv("OUTPUT_DIR")

FRESHDESK_DOMAIN = os.getenv("FRESHDESK_DOMAIN")
FRESHDESK_API_KEY = os.getenv("FRESHDESK_API_KEY")

os.makedirs(STAGING_DIR, exist_ok=True)
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# =========================
# HELPERS
# =========================

def clean_name(name: str):

    return (
        name
        .replace("/", "_")
        .replace("\\", "_")
        .strip()
    )

# =========================
# DOWNLOAD ATTACHMENTS
# =========================

def stage_attachments(ticket_id: int):

    url = f"https://{FRESHDESK_DOMAIN}/api/v2/tickets/{ticket_id}"

    auth = (FRESHDESK_API_KEY, "X")

    resp = requests.get(url, auth=auth)

    if resp.status_code != 200:

        logging.error(
            f"Failed to fetch ticket {ticket_id}"
        )

        return []

    ticket = resp.json()

    attachments = ticket.get("attachments", [])

    if not attachments:

        logging.warning(
            f"No attachments found for ticket {ticket_id}"
        )

        return []

    ticket_stage_dir = os.path.join(
        STAGING_DIR,
        str(ticket_id)
    )

    os.makedirs(ticket_stage_dir, exist_ok=True)

    final_files = []

    for attach in attachments:

        attach_name = attach.get("name")
        attach_url = attach.get("attachment_url")

        if not attach_name or not attach_url:
            continue

        attach_name = clean_name(attach_name)

        local_path = os.path.join(
            ticket_stage_dir,
            attach_name
        )

        try:

            r = requests.get(attach_url)

            if r.status_code != 200:

                logging.warning(
                    f"Failed download: {attach_name}"
                )

                continue

            with open(local_path, "wb") as f:
                f.write(r.content)

            logging.info(
                f"Downloaded: {local_path}"
            )

        except Exception as e:

            logging.error(
                f"Download failed for {attach_name}: {e}"
            )

            continue

        # =========================
        # ZIP SUPPORT
        # =========================

        if local_path.lower().endswith(".zip"):

            extract_dir = os.path.join(
                ticket_stage_dir,
                "extracted"
            )

            os.makedirs(extract_dir, exist_ok=True)

            try:

                with zipfile.ZipFile(local_path, "r") as zf:
                    zf.extractall(extract_dir)

                for root, _, files in os.walk(extract_dir):

                    for file in files:

                        src = os.path.join(root, file)

                        dst = os.path.join(
                            ticket_stage_dir,
                            clean_name(file)
                        )

                        if os.path.abspath(src) != os.path.abspath(dst):

                            shutil.move(src, dst)

                        final_files.append(dst)

                        logging.info(
                            f"Prepared ZIP file: {dst}"
                        )

            except Exception as e:

                logging.error(
                    f"ZIP extraction failed: {e}"
                )

        else:

            final_files.append(local_path)

    logging.info(
        f"Prepared {len(final_files)} files for ticket {ticket_id}"
    )

    return final_files

# =========================
# MOVE FILES TO INPUT
# =========================

def move_staging_to_input(file_list):

    final_inputs = []

    for f in file_list:

        dst = os.path.join(
            INPUT_DIR,
            os.path.basename(f)
        )

        try:

            if os.path.abspath(f) != os.path.abspath(dst):

                shutil.move(f, dst)

            final_inputs.append(dst)

            logging.info(
                f"Moved to INPUT: {dst}"
            )

        except Exception as e:

            logging.error(
                f"Move failed for {f}: {e}"
            )

    return final_inputs

# =========================
# SEND REPLY
# =========================

def send_reply(
    ticket_id: int,
    file_path: str
):

    ticket_url = (
        f"https://{FRESHDESK_DOMAIN}"
        f"/api/v2/tickets/{ticket_id}"
    )

    reply_url = (
        f"https://{FRESHDESK_DOMAIN}"
        f"/api/v2/tickets/{ticket_id}/reply"
    )

    auth = (FRESHDESK_API_KEY, "X")

    ticket_resp = requests.get(
        ticket_url,
        auth=auth
    )

    if ticket_resp.status_code != 200:

        logging.error(
            f"Failed fetching ticket {ticket_id}"
        )

        return False

    ticket_data = ticket_resp.json()

    requester_email = ticket_data.get("email")

    cc_emails = ticket_data.get(
        "cc_emails",
        []
    )

    logging.info(
        f"Requester Email: {requester_email}"
    )

    logging.info(
        f"CC Emails: {cc_emails}"
    )

    body = """
    Hi,<br><br>

    Please find the requested media URL output attached.<br><br>

    Regards,<br>
    Provisioning AI
    """

    try:

        logging.info(
            f"Sending attachment: {file_path}"
        )

        with open(file_path, "rb") as f:

            files = [
                (
                    "attachments[]",
                    (
                        os.path.basename(file_path),
                        f,
                        "text/csv"
                    )
                )
            ]

            data = [
                ("body", body)
            ]

            if requester_email:

                data.append(
                    ("to_emails[]", requester_email)
                )

            if cc_emails:

                for email in cc_emails:

                    data.append(
                        ("cc_emails[]", email)
                    )

            resp = requests.post(
                reply_url,
                auth=auth,
                data=data,
                files=files
            )

        logging.info(
            f"Freshdesk response: "
            f"{resp.status_code} - {resp.text}"
        )

        if resp.status_code in (200, 201):

            logging.info(
                f"Reply sent for ticket {ticket_id}"
            )

            return True

        logging.error(
            f"Reply failed for ticket {ticket_id}"
        )

        return False

    except Exception as e:

        logging.error(
            f"Reply exception for ticket {ticket_id}: {e}"
        )

        return False

# =========================
# MAIN PROCESSOR
# =========================

import os
import logging

async def process_ticket(ticket_id: int):

    logging.info(f"Starting processing for ticket {ticket_id}")

    processed = load_processed()

    if ticket_id in processed:

        logging.info(f"Ticket {ticket_id} already processed")

        update_status(ticket_id, "Already Processed")

        return {
            "success": False,
            "message": "Ticket already processed",
            "reply_sent": False
        }

    try:

        # =========================
        # ASSIGN AI AGENT
        # =========================

        update_status(ticket_id, "Assigning Agent")

        assign_success = assign_ai_agent(ticket_id)

        update_status(
            ticket_id,
            "Agent Assigned" if assign_success else "Agent Assignment Failed"
        )

        # =========================
        # DOWNLOAD FILES
        # =========================

        update_status(ticket_id, "Downloading")

        staged_files = stage_attachments(ticket_id)

        if not staged_files:

            update_status(ticket_id, "failed")

            return {
                "success": False,
                "message": "No usable attachments found"
            }

        # =========================
        # MOVE FILES
        # =========================

        update_status(ticket_id, "Uploading")

        moved_files = move_staging_to_input(staged_files)

        logging.info(f"Files moved to INPUT: {moved_files}")

        # =========================
        # RUN AUTOMATION (FIX HERE)
        # =========================

        automation_result = await run_bulk_automation(moved_files,ticket_id)

        logging.info(f"Automation Result: {automation_result}")

        # =========================
        # CSV RESULT
        # =========================

        update_status(ticket_id, "csv_processing")

        output_file = automation_result.get("output_file")

        if not output_file or not os.path.exists(output_file):

            update_status(ticket_id, "failed")

            return {
                "success": False,
                "message": "Output CSV not generated"
            }

        logging.info(f"Output file ready: {output_file}")

        # =========================
        # SEND REPLY
        # =========================

        update_status(ticket_id, "reply_sending")

        reply_sent = send_reply(ticket_id, output_file)

        if not reply_sent:

            update_status(ticket_id, "reply_failed")

            return {
                "success": False,
                "ticket_id": ticket_id,
                "reply_sent": False,
                "message": "Reply failed"
            }

        update_status(ticket_id, "reply_sent")

        # =========================
        # RESOLVE TICKET
        # =========================

        update_status(ticket_id, "resolve_ticket")

        resolve_success = resolve_ticket(ticket_id)

        update_status(
            ticket_id,
            "resolved" if resolve_success else "resolve_failed"
        )

        # =========================
        # SAVE PROCESSED
        # =========================

        save_processed(ticket_id)

        update_status(ticket_id, "completed")

        return {
            "success": True,
            "ticket_id": ticket_id,
            "reply_sent": True,
            "output_file": output_file,
            "message": "Processing completed successfully"
        }

    except Exception as e:

        logging.error(f"Processing failed: {e}")

        update_status(ticket_id, "error")

        return {
            "success": False,
            "ticket_id": ticket_id,
            "message": str(e)
        }