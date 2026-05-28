import time
import requests
from playwright.sync_api import sync_playwright


# =========================
# CONFIG
# =========================
VM_URL = "http://10.20.89.11:8000"

WORKER_NAME = "shanmukad"

POLL_INTERVAL = 5


# =========================
# FETCH NEXT JOB
# =========================
def get_job():

    try:

        response = requests.get(
            f"{VM_URL}/worker/next-job",
            params={
                "worker_name": WORKER_NAME
            },
            timeout=10
        )

        return response.json()

    except Exception as e:

        print(f"❌ Error fetching job: {e}")

        return None


# =========================
# UPDATE STATUS
# =========================
def complete_job(ticket_id, status):

    try:

        requests.post(
            f"{VM_URL}/worker/complete-job",
            json={
                "ticket_id": ticket_id,
                "status": status
            },
            timeout=10
        )

    except Exception as e:

        print(f"❌ Error updating status: {e}")


# =========================
# PLAYWRIGHT AUTOMATION
# =========================
def process_ticket(ticket_id):

    print(f"\n🚀 Processing Ticket: {ticket_id}")

    browser = None

    try:

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=False
            )

            context = browser.new_context()

            page = context.new_page()

            print("🌐 Opening internal portal...")

            page.goto(
                "http://192.168.253.176:1002/login",
                timeout=60000
            )

            page.wait_for_load_state("networkidle")

            print("✅ Portal opened successfully")

            # =========================
            # LOGIN
            # =========================

            page.fill(
                "#username",
                "YOUR_USERNAME"
            )

            page.fill(
                "#password",
                "YOUR_PASSWORD"
            )

            page.click(
                "button[type=submit]"
            )

            page.wait_for_timeout(3000)

            print("✅ Login successful")

            # =========================
            # TODO:
            # FETCH FILE FROM VM
            # =========================

            # Example:
            #
            # download_url =
            #   f"{VM_URL}/download/{ticket_id}"
            #
            # file_path = ...

            # =========================
            # TODO:
            # UPLOAD FILE
            # =========================

            # page.set_input_files(
            #     "input[type=file]",
            #     file_path
            # )

            # =========================
            # TODO:
            # SUBMIT
            # =========================

            # page.click("text=Process")

            page.wait_for_timeout(5000)

            print(f"✅ Ticket {ticket_id} completed")

            browser.close()

            return "completed"

    except Exception as e:

        print(f"❌ Automation failed: {e}")

        try:

            if browser:
                browser.close()

        except:
            pass

        return "failed"


# =========================
# MAIN LOOP
# =========================
def run_worker():

    print(f"\n🚀 Worker Started: {WORKER_NAME}")

    while True:

        try:

            job = get_job()

            if (
              job
              and "ticket_id" in job
               ):

                ticket_id = job["ticket_id"]

                print(f"\n📥 Job received: {ticket_id}")

                status = process_ticket(ticket_id)

                complete_job(
                    ticket_id,
                    status
                )

            time.sleep(POLL_INTERVAL)

        except Exception as e:

            print(f"❌ Worker loop error: {e}")

            time.sleep(POLL_INTERVAL)


# =========================
# START
# =========================
if __name__ == "__main__":

    run_worker()