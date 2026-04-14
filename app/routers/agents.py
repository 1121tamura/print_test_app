from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.dependencies import verify_api_key
from app.models import Agent, Job, utc_now

router = APIRouter(prefix="/agents", tags=["agents"], dependencies=[Depends(verify_api_key)])


class RegisterRequest(BaseModel):
    mac: str
    hostname: str


class RegisterResponse(BaseModel):
    agent_id: str


class StatusRequest(BaseModel):
    status: str
    job_id: str | None = None
    error_message: str | None = None


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_200_OK)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """
    Agent を登録し、UUID を返す。
    同一 mac_address で再登録が来た場合は既存の UUID をそのまま返す（べき等）。
    Agent の初回起動時に呼ばれる。
    """
    agent = db.query(Agent).filter(Agent.mac_address == body.mac).first()
    if agent:
        return RegisterResponse(agent_id=agent.id)

    agent = Agent(mac_address=body.mac, hostname=body.hostname)
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return RegisterResponse(agent_id=agent.id)


@router.post("/{agent_id}/status", status_code=status.HTTP_204_NO_CONTENT)
def update_status(agent_id: str, body: StatusRequest, db: Session = Depends(get_db)):
    """
    Agent の状態を受け取り、対応するカラムを更新する。
    定期送信ではなくイベント発生時に送信される。

    status の種類と更新カラム:
    - online        : Agent 起動時        → last_seen_at
    - job_received  : job 受信時          → last_seen_at, last_job_received_at
    - printing      : 印刷開始直前        → last_seen_at, last_print_started_at, jobs.status
    - success       : 印刷完了時          → last_seen_at, last_print_completed_at, jobs.status
    - error         : 印刷失敗時          → last_seen_at, last_error_at, last_error_message, jobs.status
    """
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    now = utc_now()
    agent.last_seen_at = now

    if body.status == "job_received":
        agent.last_job_received_at = now

    elif body.status == "printing":
        agent.last_print_started_at = now
        _update_job_status(db, body.job_id, "printing")

    elif body.status == "success":
        agent.last_print_completed_at = now
        _update_job_status(db, body.job_id, "success")

    elif body.status == "error":
        agent.last_error_at = now
        agent.last_error_message = body.error_message
        _update_job_status(db, body.job_id, "error", body.error_message)

    db.commit()


class PdfItem(BaseModel):
    job_id: str
    title: str
    status: str
    created_at: str


@router.get("/{agent_id}/pdfs", response_model=list[PdfItem])
def list_pdfs(agent_id: str, db: Session = Depends(get_db)):
    """
    agent_id に紐づく PDF 一覧を返す。
    pdf_storage_key が存在し、かつ PDF_RETENTION_DAYS 日以内に作成されたジョブが対象。
    再印刷時は返された job_id を使って POST /jobs/{job_id}/reprint を呼ぶ。
    """
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    retention_days = get_settings().pdf_retention_days
    cutoff = utc_now().replace(tzinfo=None) - timedelta(days=retention_days)

    jobs = (
        db.query(Job)
        .filter(
            Job.agent_id == agent_id,
            Job.pdf_storage_key.isnot(None),
            Job.created_at >= cutoff,
        )
        .order_by(Job.created_at.desc())
        .all()
    )

    return [
        PdfItem(
            job_id=job.id,
            title=job.title,
            status=job.status,
            created_at=job.created_at.isoformat(),
        )
        for job in jobs
    ]


def _update_job_status(
    db: Session,
    job_id: str | None,
    new_status: str,
    error_message: str | None = None,
) -> None:
    """job_id が指定されている場合に jobs.status を更新する。"""
    if not job_id:
        return
    job = db.query(Job).filter(Job.id == job_id).first()
    if job:
        job.status = new_status
        job.error_message = error_message
