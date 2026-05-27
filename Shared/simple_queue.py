import json
import os
from threading import Lock

QUEUE_FILE = "queue_store.json"
lock = Lock()


def load_jobs():
    if not os.path.exists(QUEUE_FILE):
        return []
    with open(QUEUE_FILE, "r") as f:
        return json.load(f)


def save_jobs(jobs):
    with open(QUEUE_FILE, "w") as f:
        json.dump(jobs, f, indent=2)


def add_job(ticket_id):
    with lock:
        jobs = load_jobs()

        job = {
            "ticket_id": ticket_id,
            "status": "queued",
            "assigned_to": "Shanmuka-Laptop"
        }

        jobs.append(job)
        save_jobs(jobs)
        return job


def update_job(ticket_id, status):
    with lock:
        jobs = load_jobs()

        for job in jobs:
            if job["ticket_id"] == ticket_id:
                job["status"] = status

        save_jobs(jobs)


def get_jobs():
    return load_jobs()