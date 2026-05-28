import json
import os
from threading import Lock

QUEUE_FILE = "queue_store.json"

lock = Lock()


# =========================
# LOAD JOBS
# =========================
def load_jobs():

    if not os.path.exists(QUEUE_FILE):
        return []

    with open(QUEUE_FILE, "r") as f:
        return json.load(f)


# =========================
# SAVE JOBS
# =========================
def save_jobs(jobs):

    with open(QUEUE_FILE, "w") as f:
        json.dump(jobs, f, indent=2)


# =========================
# ADD NEW JOB
# =========================
def add_job(ticket_id):

    with lock:

        jobs = load_jobs()

        # avoid duplicate queueing
        for job in jobs:

            if (
                job["ticket_id"] == ticket_id
                and job["status"] not in [
                    "completed",
                    "failed",
                    "resolved"
                ]
            ):

                return job

        job = {
            "ticket_id": ticket_id,
            "status": "queued",
            "assigned_to": None
        }

        jobs.append(job)

        save_jobs(jobs)

        return job


# =========================
# WORKER PICKS NEXT JOB
# =========================
def get_next_job(worker_name):

    with lock:

        jobs = load_jobs()

        for job in jobs:

            if (
                job["status"] == "queued"
                and job["assigned_to"] is None
            ):

                job["status"] = "processing"

                job["assigned_to"] = worker_name

                save_jobs(jobs)

                return job

    return None


# =========================
# UPDATE JOB STATUS
# =========================
def update_job(ticket_id, status):

    with lock:

        jobs = load_jobs()

        for job in jobs:

            if job["ticket_id"] == ticket_id:

                job["status"] = status

        save_jobs(jobs)


# =========================
# COMPLETE JOB
# =========================
def complete_job(ticket_id, status):

    with lock:

        jobs = load_jobs()

        for job in jobs:

            if job["ticket_id"] == ticket_id:

                job["status"] = status

        save_jobs(jobs)


# =========================
# GET ALL JOBS
# =========================
def get_jobs():

    return load_jobs()