from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app import chat_service
from app.config import settings
from app.db import get_db
from app.rate_limit import limiter

router = APIRouter(prefix="/api/chat", tags=["public-chat"])


class HistoryEntry(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(alias="from")
    text: str = Field(default="", max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    lang: str = Field(default="en", max_length=8)
    history: list[HistoryEntry] = Field(default_factory=list, max_length=50)
    leadCaptured: bool = False


@router.post("")
@limiter.limit(settings.RATE_LIMIT_APPOINTMENT)  # same conservative per-IP budget as booking actions
def chat(request: Request, body: ChatRequest, db: Session = Depends(get_db)):
    reply, lead_captured = chat_service.get_reply(
        db, message=body.message, lang=body.lang,
        history=[{"from": h.from_, "text": h.text} for h in body.history],
        lead_captured=body.leadCaptured,
    )
    db.commit()
    return {"reply": reply, "leadCaptured": lead_captured}
