import asyncio
import threading
import queue
import os
import json

# =========================
# GLOBALS
# =========================

task_queue = queue.Queue()
results_store = {}
lock = threading.Lock()

# =========================
# PERSISTENCE
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROCESSED_FILE = os.path.join(BASE_DIR, "processed_tickets.json")


def load_processed():
    if not os.path.exists(PROCESSED_FILE):
        return set()

    with open(PROCESSED_FILE, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = []

    return set(data)


def save_processed(ticket_id: int):
    data = list(load_processed())

    if ticket_id not in data:
        data.append(ticket_id)

    with open(PROCESSED_FILE, "w") as f:
        json.dump(data, f)


# =========================
# STATUS HELPERS
# =========================

def update_status(ticket_id: int, status: str):

    # 🔥 SAFETY: handle accidental dict input
    if isinstance(ticket_id, dict):
        ticket_id = ticket_id.get("ticket_id")

    if ticket_id is None:
        return

    with lock:
        results_store[ticket_id] = {
            "status": status,
            "ticket_id": ticket_id,
        }


def get_results():
    with lock:
        return dict(results_store)


# =========================
# QUEUE
# =========================

def add_ticket(ticket_id: int):
    task_queue.put(ticket_id)
    update_status(ticket_id, "queued")


# =========================
# WORKER
# =========================

def worker():
    from Shared.ticket_processor import process_ticket

    while True:
        ticket_id = task_queue.get()

        try:
            update_status(ticket_id, "processing")

            # ✅ correct async execution
            result = asyncio.run(process_ticket(ticket_id))

            # result must be a dict from process_ticket
            if isinstance(result, dict) and result.get("success"):
                update_status(ticket_id, "completed")
            else:
                # fallback status handling
                status = result.get("status", "failed") if isinstance(result, dict) else "failed"
                update_status(ticket_id, status)

        except Exception as e:
            print(f"Worker error for ticket {ticket_id}: {e}")
            update_status(ticket_id, "error")

        finally:
            task_queue.task_done()


# =========================
# START WORKER
# =========================

def start_worker():
    t = threading.Thread(target=worker, daemon=True)
    t.start()