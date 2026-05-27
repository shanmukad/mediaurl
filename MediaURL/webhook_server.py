from fastapi import FastAPI, Form, Request, Body
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from pathlib import Path
import os
import uvicorn
import requests
from requests.auth import HTTPBasicAuth

from Shared.ticket_actions import get_ticket_preview
from Shared.ticket_validator import is_valid_media_request
from Shared.queue_manager import (
    get_results,
    load_processed
)

# =========================
# ENV
# =========================
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

INPUT_DIR = os.getenv("INPUT_DIR")
OUTPUT_DIR = os.getenv("OUTPUT_DIR")

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

FRESHDESK_DOMAIN = os.getenv("FRESHDESK_DOMAIN")
FRESHDESK_API_KEY = os.getenv("FRESHDESK_API_KEY")

AUTH = HTTPBasicAuth(FRESHDESK_API_KEY, "X")


def fetch_ticket(ticket_id):
    url = f"https://{FRESHDESK_DOMAIN}/api/v2/tickets/{ticket_id}"

    res = requests.get(url, auth=AUTH)

    if res.status_code != 200:
        return {}

    return res.json()


# =========================
# VM → WORKER JOB STORE
# =========================
worker_jobs = {}
worker_lock = __import__("threading").Lock()


# =========================
# FASTAPI APP
# =========================
app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static"
)


# =========================
# HOME UI
# =========================
@app.get("/")
async def home():
    return FileResponse(str(BASE_DIR / "templates" / "index.html"))


# =========================
# TRIGGER (UI → VM QUEUE)
# =========================
@app.post("/trigger")
async def trigger(ticket_id: str = Form(...)):
    ticket_ids = [t.strip() for t in ticket_id.split(",")]

    processed = load_processed()
    results = []

    for tid in ticket_ids:

        if not tid.isdigit():
            results.append({"ticket_id": tid, "status": "invalid"})
            continue

        tid_int = int(tid)

        if tid_int in processed:
            results.append({"ticket_id": tid, "status": "already_processed"})
            continue

        # 🔥 IMPORTANT CHANGE: send to worker queue
        with worker_lock:
            worker_jobs[tid_int] = {
                "ticket_id": tid_int,
                "status": "queued"
            }

        results.append({"ticket_id": tid, "status": "queued"})

    return {"status": "queued", "results": results}


# =========================
# WORKER: FETCH NEXT JOB
# =========================
@app.get("/worker/next-job")
def next_job(worker_name: str):

    with worker_lock:
        for job_id, job in worker_jobs.items():
            if job["status"] == "queued":
                job["status"] = "assigned"
                job["worker"] = worker_name
                return job

    return {"status": "no_job"}


# =========================
# WORKER: COMPLETE JOB
# =========================
@app.post("/worker/complete-job")
def complete_job(payload: dict = Body(...)):

    ticket_id = payload.get("ticket_id")
    status = payload.get("status")

    with worker_lock:
        if ticket_id in worker_jobs:
            worker_jobs[ticket_id]["status"] = status

    return {"success": True}


# =========================
# STATUS (UI POLLING)
# =========================
@app.get("/status/{ticket_id}")
def status(ticket_id: int):

    with worker_lock:
        job = worker_jobs.get(ticket_id)

    if not job:
        return {"status": "not_found"}

    return {"status": job["status"]}


# =========================
# VALIDATION (UNCHANGED)
# =========================
@app.post("/validate")
async def validate_ticket(ticket_id: str = Form(...)):

    ticket = fetch_ticket(ticket_id)

    subject = ticket.get("subject", "")
    body = ticket.get("description_text", "")

    validation = is_valid_media_request(subject, body)

    return {
        "ticket_id": ticket_id,
        "subject": subject,
        "validation": validation
    }


# =========================
# PREVIEW (UNCHANGED)
# =========================
@app.get("/preview/{ticket_id}")
def preview(ticket_id: int):
    return get_ticket_preview(ticket_id)


# =========================
# START
# =========================
if __name__ == "__main__":
    uvicorn.run(
        "webhook_server:app",
        host="0.0.0.0",
        port=8000
    )