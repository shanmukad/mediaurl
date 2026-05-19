from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from pathlib import Path
from Shared.ticket_actions import get_ticket_preview
import os
import uvicorn
from pathlib import Path
from Shared.ticket_validator import is_valid_media_request
from Shared.queue_manager import (
    start_worker,
    add_ticket,
    get_results,
    load_processed
)

from Shared.ticket_actions import (
    get_ticket_preview
)



# Local imports
from Shared.queue_manager import start_worker, add_ticket, get_results, load_processed

# =========================
# LOAD ENV & DIRS
# =========================
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

INPUT_DIR = os.getenv("INPUT_DIR")
OUTPUT_DIR = os.getenv("OUTPUT_DIR")

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


import requests
from requests.auth import HTTPBasicAuth

FRESHDESK_DOMAIN = os.getenv("FRESHDESK_DOMAIN")
FRESHDESK_API_KEY = os.getenv("FRESHDESK_API_KEY")

AUTH = HTTPBasicAuth(
    FRESHDESK_API_KEY,
    "X"
)

def fetch_ticket(ticket_id):

    url = (
        f"https://{FRESHDESK_DOMAIN}"
        f"/api/v2/tickets/{ticket_id}"
    )

    res = requests.get(
        url,
        auth=AUTH
    )

    if res.status_code != 200:
        return {}

    return res.json()

# =========================
# LIFESPAN (START WORKER)
# =========================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    start_worker()
    print("✅ Worker thread started")
    yield
    # SHUTDOWN
    print("🔌 Server shutting down")

# =========================
# APP SETUP
# =========================
app = FastAPI(lifespan=lifespan)

BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(
    directory=BASE_DIR / "templates"
)

# Static files
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static"
)


# =========================
# UI ROUTE (SINGLE ROOT)
# =========================
@app.get("/")
async def home():
    return FileResponse(
        str(BASE_DIR / "templates" / "index.html")
    )

# =========================
# TRIGGER ENDPOINT (QUEUE TICKETS)
# =========================
@app.post("/trigger")
async def trigger(ticket_id: str = Form(...)):
    ticket_ids = [t.strip() for t in ticket_id.split(",")]

    processed = load_processed()
    results = []

    for tid in ticket_ids:
        # Validation
        if not tid.isdigit():
            results.append({
                "ticket_id": tid,
                "status": "invalid"
            })
            continue

        tid_int = int(tid)

        # Block already processed
        if tid_int in processed:
            results.append({
                "ticket_id": tid,
                "status": "already_processed"
            })
            continue

        # Queue ticket
        add_ticket(tid_int)
        results.append({
            "ticket_id": tid,
            "status": "queued"
        })

    return {
        "status": "queued",
        "results": results
    }

# =========================
# STATUS ENDPOINT (READS WORKER STATUS)
# =========================
@app.get("/status/{ticket_id}")
def status(ticket_id: int):
    results = get_results()
    if ticket_id in results:
        return {"status": results[ticket_id]["status"]}
    return {"status": "queued"}

@app.post("/validate")
async def validate_ticket(ticket_id: str = Form(...)):

    ticket = fetch_ticket(ticket_id)

    subject = ticket.get("subject", "")
    body = ticket.get("description_text", "")

    validation = is_valid_media_request(
        subject,
        body
    )

    return {
        "ticket_id": ticket_id,
        "subject": subject,
        "validation": validation
    }

@app.get("/preview/{ticket_id}")
def preview(ticket_id: int):

    return get_ticket_preview(ticket_id)

if __name__ == "__main__":
    uvicorn.run(
        "webhook_server:app",
        host="127.0.0.1",
        port=8000,
    )