import time
import requests
from playwright.sync_api import sync_playwright

VM_URL = "http://<YOUR_VM_IP>:8000"
WORKER_NAME = "vpn-worker-1"


# =========================
# FETCH JOB FROM VM
# =========================
def get_job():
    try:
        res = requests.get(
            f"{VM_URL}/worker/next-job",
            params={"worker_name": WORKER_NAME},
            timeout=10
        )
        return res.json()
    except Exception as e:
        print("Error fetching job:", e)
        return None


# =========================
# SEND RESULT BACK TO VM
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
        print("Error sending result:", e)


# =========================
# CORE AUTOMATION LOGIC
# =========================
def process_ticket(ticket_id):
    print(f"Processing ticket: {ticket_id}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # 🔐 STEP 1: OPEN INTERNAL UI (VPN REQUIRED)
            page.goto("http://192.168.253.176:1002/login")

            # =========================
            # 🔧 YOU MUST ADJUST BELOW
            # =========================

            # login
            page.fill("#username", "YOUR_USERNAME")
            page.fill("#password", "YOUR_PASSWORD")
            page.click("button[type=submit]")

            page.wait_for_timeout(3000)

            # upload step (example)
            # page.set_input_files("input[type=file]", "/path/to/file")

            # submit / process
            # page.click("text=Process")

            page.wait_for_timeout(5000)

            browser.close()

        return "completed"

    except Exception as e:
        print("Automation error:", e)
        return "failed"


# =========================
# WORKER LOOP
# =========================
def run_worker():
    print("🚀 VPN Worker Started...")

    while True:
        job = get_job()

        if job and job.get("status") not in ["no_job", None]:
            ticket_id = job["ticket_id"]

            status = process_ticket(ticket_id)

            complete_job(ticket_id, status)

        time.sleep(5)


if __name__ == "__main__":
    run_worker()