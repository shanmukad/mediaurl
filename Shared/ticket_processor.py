from dotenv import load_dotenv
import os
import time
import requests
import glob
import logging
import zipfile
import shutil
from Shared.ticket_actions import (
    assign_ai_agent,
    resolve_ticket
)

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
            f"{ticket_id}_{attach_name}"
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
                            f"{ticket_id}_{clean_name(file)}"
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
# WAIT FOR OUTPUT
# =========================

def wait_for_ticket_output(
    ticket_id: int,
    timeout: int = 180
):

    start_time = time.time()

    pattern = os.path.join(
        OUTPUT_DIR,
        f"{ticket_id}_*.csv"
    )

    logging.info(
        f"Waiting for output file: {pattern}"
    )

    while time.time() - start_time < timeout:

        matching_files = glob.glob(pattern)

        valid_files = []

        for file in matching_files:

            try:

                modified_time = os.path.getmtime(file)

                if modified_time >= start_time:

                    valid_files.append(file)

            except Exception as e:

                logging.error(
                    f"Error checking file {file}: {e}"
                )

        if valid_files:

            latest_file = max(
                valid_files,
                key=os.path.getmtime
            )

            logging.info(
                f"Detected output file: {latest_file}"
            )

            return latest_file

        time.sleep(3)

    logging.error(
        f"No output generated for ticket {ticket_id}"
    )

    return None


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

    # =========================
    # FETCH TICKET DETAILS
    # =========================

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

    # =========================
    # FETCH REQUESTER EMAIL
    # =========================

    requester_email = ticket_data.get("email")

    # =========================
    # FETCH CC EMAILS
    # =========================

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

    # =========================
    # EMAIL BODY
    # =========================

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

            # =========================
            # ATTACHMENT PAYLOAD
            # =========================

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

            # =========================
            # MULTIPART FORM DATA
            # =========================

            data = [
                ("body", body)
            ]

            # =========================
            # TO EMAIL
            # =========================

            if requester_email:

                data.append(
                    ("to_emails[]", requester_email)
                )

            # =========================
            # CC EMAILS
            # =========================

            if cc_emails:

                for email in cc_emails:

                    data.append(
                        ("cc_emails[]", email)
                    )

            logging.info(
                f"Multipart payload: {data}"
            )

            # =========================
            # SEND REPLY
            # =========================

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
                f"✅ Reply sent for ticket {ticket_id}"
            )

            return True

        logging.error(
            f"❌ Reply failed for ticket {ticket_id}"
        )

        return False

    except Exception as e:

        logging.error(
            f"Reply exception for ticket {ticket_id}: {e}"
        )

        return False



from Shared.queue_manager import (
    update_status,
    load_processed,
    save_processed
)

# =========================
# MAIN PROCESSOR
# =========================


def process_ticket(ticket_id: int):

    logging.info(f"Starting processing for ticket {ticket_id}")

    # -------------------------
    # BLOCK IF ALREADY PROCESSED
    # -------------------------
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

        if assign_success:

            update_status(
                ticket_id,
                "Agent Assigned"
            )

        else:

            update_status(
                ticket_id,
                "Agent Assignment Failed"
            )

        # =========================
        # START
        # =========================
        update_status(ticket_id, "processing")

        # =========================
        # STAGING (DOWNLOAD)
        # =========================
        update_status(ticket_id, "staging")

        staged_files = stage_attachments(ticket_id)

        if not staged_files:

            update_status(ticket_id, "failed")

            return {
                "success": False,
                "message": "No usable attachments found"
            }

        # =========================
        # MOVE TO INPUT
        # =========================
        update_status(ticket_id, "uploading")

        moved_files = move_staging_to_input(staged_files)

        logging.info(
            f"Files moved to INPUT: {moved_files}"
        )

        # =========================
        # CSV WAIT
        # =========================
        update_status(ticket_id, "csv_processing")

        output_file = wait_for_ticket_output(ticket_id)

        if not output_file:

            update_status(ticket_id, "failed")

            return {
                "success": False,
                "message": "Output CSV not generated"
            }

        logging.info(
            f"Output file ready: {output_file}"
        )

        # =========================
        # SEND REPLY
        # =========================
        update_status(ticket_id, "reply_sending")

        reply_sent = send_reply(ticket_id, output_file)

        # =========================
        # FINAL FLOW
        # =========================
        if reply_sent:

            update_status(ticket_id, "reply_sent")

            # =====================
            # CLOSE TICKET
            # =====================
            update_status(ticket_id, "resolve_ticket")

            resolve_success = resolve_ticket(ticket_id)

            if resolve_success:

                update_status(
                    ticket_id,
                    "resolved"
                )

            else:

                update_status(
                    ticket_id,
                    "resolve_failed"
                )

            # SAVE PROCESSED
            save_processed(ticket_id)

            update_status(ticket_id, "completed")

            return {
                "success": True,
                "ticket_id": ticket_id,
                "reply_sent": True,
                "output_file": output_file,
                "message": "Processing completed successfully"
            }

        else:

            update_status(ticket_id, "reply_failed")

            return {
                "success": False,
                "ticket_id": ticket_id,
                "reply_sent": False,
                "message": "Reply failed"
            }

    except Exception as e:

        logging.error(f"Processing failed: {e}")

        update_status(ticket_id, "error")

        return {
            "success": False,
            "ticket_id": ticket_id,
            "message": str(e)
        }