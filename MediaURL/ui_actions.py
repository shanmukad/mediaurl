from fastapi import APIRouter
from pydantic import BaseModel
from Shared.ticket_actions import assign_ai_agent, resolve_ticket, finalize_ticket

router = APIRouter()


# =========================
# REQUEST MODEL
# =========================
class TicketRequest(BaseModel):
    ticket_id: int



# =========================
# ASSIGN AGENT
# =========================
@router.post("/assign")
def assign(req: TicketRequest):

    result = assign_ai_agent(req.ticket_id)

    return {
        "success": result,
        "ticket_id": req.ticket_id,
        "action": "assigned"
    }


# =========================
# CLOSE TICKET
# =========================
@router.post("/close")
def close(req: TicketRequest):

    result = resolve_ticket(req.ticket_id)

    return {
        "success": result,
        "ticket_id": req.ticket_id,
        "action": "resolved"
    }


# =========================
# AUTO COMPLETE (ASSIGN + CLOSE)
# =========================
@router.post("/auto_complete")
def auto_complete(req: TicketRequest):

    result = finalize_ticket(req.ticket_id)

    return {
        "success": result.get("success"),
        "ticket_id": req.ticket_id,
        "step": result.get("step")
    }