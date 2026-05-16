import threading
import queue
import os
import json

# =========================
# GLOBALS
# =========================

# Single task queue for worker
task_queue = queue.Queue()

# In-memory status store
results_store = {}

# Thread-safety for updates
lock = threading.Lock()

# =========================
# PERSISTENCE FOR PROCESSED
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROCESSED_FILE = os.path.join(BASE_DIR, "processed_tickets.json")


def load_processed():
    """
    Load already processed ticket IDs from JSON file.
    Returns a set of ints.
    """
    if not os.path.exists(PROCESSED_FILE):
        return set()

    with open(PROCESSED_FILE, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = []
    return set(data)


def save_processed(ticket_id: int):
    """
    Append a ticket_id to processed_tickets.json.
    """
    data = list(load_processed())
    if ticket_id not in data:
        data.append(ticket_id)

    with open(PROCESSED_FILE, "w") as f:
        json.dump(data, f)

# =========================
# STATUS HELPERS
# =========================


def update_status(ticket_id: int, status: str):
    """
    Update status for a given ticket in the in-memory store.
    """
    with lock:
        results_store[ticket_id] = {
            "status": status,
            "ticket_id": ticket_id,
        }


def get_results():
    """
    Return the whole results store (dict).
    UI / API can read from here.
    """
    with lock:
        # return a shallow copy to avoid threading issues
        return dict(results_store)

# =========================
# QUEUE MANAGEMENT
# =========================


def add_ticket(ticket_id: int):
    """
    Add a ticket ID to the processing queue and mark as queued.
    """
    task_queue.put(ticket_id)
    update_status(ticket_id, "queued")


# =========================
# WORKER THREAD
# =========================


def worker():
    """
    Worker loop that pulls ticket IDs from the queue and processes them.
    """
    # Local import to avoid circular dependency
    from Shared.ticket_processor import process_ticket

    while True:
        ticket_id = task_queue.get()
        try:
            update_status(ticket_id, "processing")
            result = process_ticket(ticket_id)

            if result.get("success"):
                update_status(ticket_id, "completed")
            else:
                # Let process_ticket set more granular statuses too,
                # but if it returns failure, mark as failed here.
                current = get_results().get(ticket_id, {})
                if current.get("status") not in ("error", "failed"):
                    update_status(ticket_id, "failed")

        except Exception as e:
            print(f"Worker error for ticket {ticket_id}: {e}")
            update_status(ticket_id, "error")
        finally:
            task_queue.task_done()


def start_worker():
    """
    Start a single daemon worker thread.
    Call this once on app startup.
    """
    t = threading.Thread(target=worker, daemon=True)
    t.start()