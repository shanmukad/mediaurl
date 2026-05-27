import time
import requests
from dotenv import load_dotenv
import os

from Shared.ticket_processor import process_ticket

load_dotenv()

VM_URL = os.getenv("VM_URL")
WORKER_NAME = os.getenv("WORKER_NAME")

def get_next_job():

    try:

        response = requests.get(
            f"{VM_URL}/worker/next-job",
            params={
                "worker_name": WORKER_NAME
            }
        )

        return response.json()

    except Exception as e:

        print("Error fetching job:", e)

        return None


def update_status(ticket_id, status):

    try:

        requests.post(
            f"{VM_URL}/worker/update-status",
            params={
                "ticket_id": ticket_id,
                "status": status
            }
        )

    except Exception as e:

        print("Status update failed:", e)


print("🚀 Worker Started")

while True:

    try:

        data = get_next_job()

        if data and data.get("success"):

            job = data["job"]

            ticket_id = job["ticket_id"]

            print(f"Processing Ticket: {ticket_id}")

            try:

                update_status(ticket_id, "processing")

                process_ticket(ticket_id)

                update_status(ticket_id, "completed")

                print(f"Completed: {ticket_id}")

            except Exception as automation_error:

                print("Automation failed:", automation_error)

                update_status(ticket_id, "failed")

        else:

            print("No jobs available")

    except Exception as e:

        print("Worker Error:", e)

    time.sleep(10)