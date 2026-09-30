from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import leads_service
from app.db import get_db
from app.deps import get_current_admin, require_csrf
from app.models import AdminUser

router = APIRouter(prefix="/admin/api/leads", tags=["admin-leads"], dependencies=[Depends(require_csrf)])


class LeadOut(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    source: str
    status: str
    notes: str
    transcript: list[dict]
    created_at: str
    updated_at: str


class LeadUpdateIn(BaseModel):
    status: str | None = None
    notes: str | None = None


class LeadCreateIn(BaseModel):
    name: str = ""
    email: str
    phone: str = ""
    notes: str = ""
    status: str = "new"


def _serialize(lead) -> LeadOut:
    return LeadOut(
        id=lead.id, name=lead.name, email=lead.email, phone=lead.phone,
        source=lead.source, status=lead.status, notes=lead.notes, transcript=lead.transcript,
        created_at=lead.created_at.isoformat(), updated_at=lead.updated_at.isoformat(),
    )


@router.get("", response_model=list[LeadOut])
def list_leads(
    status_filter: str | None = None, source: str | None = None,
    admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db),
):
    return [_serialize(l) for l in leads_service.list_leads(db, status=status_filter, source=source)]


@router.post("", response_model=LeadOut)
def create_lead(body: LeadCreateIn, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    try:
        lead = leads_service.create_lead(
            db, name=body.name, email=body.email, phone=body.phone, notes=body.notes, status=body.status,
        )
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    db.refresh(lead)
    return _serialize(lead)


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: str, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    lead = leads_service.get_lead(db, lead_id)
    if lead is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No lead {lead_id!r}")
    return _serialize(lead)


@router.patch("/{lead_id}", response_model=LeadOut)
def update_lead(lead_id: str, body: LeadUpdateIn, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    try:
        lead = leads_service.update_lead(db, lead_id, status=body.status, notes=body.notes)
        db.commit()
    except KeyError as e:
        db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except ValueError as e:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    db.refresh(lead)
    return _serialize(lead)


@router.delete("/{lead_id}")
def delete_lead(lead_id: str, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    ok = leads_service.delete_lead(db, lead_id)
    db.commit()
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No lead {lead_id!r}")
    return {"ok": True}
