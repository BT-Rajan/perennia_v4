from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_admin
from app.models import AdminUser, Appointment, Lead

router = APIRouter(prefix="/admin/api/stats", tags=["admin-stats"])


@router.get("/overview")
def overview(admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    today = dt.date.today().isoformat()
    week_end = (dt.date.today() + dt.timedelta(days=7)).isoformat()

    leads_by_status = dict(db.execute(select(Lead.status, func.count()).group_by(Lead.status)).all())
    appointments_by_status = dict(db.execute(select(Appointment.status, func.count()).group_by(Appointment.status)).all())

    upcoming_count = db.scalar(
        select(func.count()).select_from(Appointment)
        .where(Appointment.status == "confirmed", Appointment.date >= today)
    )
    this_week_count = db.scalar(
        select(func.count()).select_from(Appointment)
        .where(Appointment.status == "confirmed", Appointment.date >= today, Appointment.date <= week_end)
    )

    recent_leads = db.scalars(select(Lead).order_by(Lead.created_at.desc()).limit(5)).all()
    upcoming_appointments = db.scalars(
        select(Appointment)
        .where(Appointment.status == "confirmed", Appointment.date >= today)
        .order_by(Appointment.date, Appointment.time)
        .limit(5)
    ).all()

    return {
        "leads_total": sum(leads_by_status.values()),
        "leads_by_status": leads_by_status,
        "appointments_total": sum(appointments_by_status.values()),
        "appointments_by_status": appointments_by_status,
        "appointments_upcoming": upcoming_count or 0,
        "appointments_this_week": this_week_count or 0,
        "recent_leads": [
            {"id": l.id, "name": l.name, "email": l.email, "source": l.source,
             "status": l.status, "created_at": l.created_at.isoformat()}
            for l in recent_leads
        ],
        "upcoming_appointments": [
            {"id": a.id, "name": a.name, "email": a.email, "date": a.date, "time": a.time, "service": a.service}
            for a in upcoming_appointments
        ],
    }
