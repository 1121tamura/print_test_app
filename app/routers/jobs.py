from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Job, utc_now

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobCreateRequest(BaseModel):
    agent_id: str
    title: str
    pdf_storage_key: str | None = None


class JobResponse(BaseModel):
    id: str
    agent_id: str
    title: str
    pdf_storage_key: str | None
    status: str
    error_message: str | None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class JobResultRequest(BaseModel):
    agent_id: str
    status: str
    error_message: str | None = None


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(body: JobCreateRequest, db: Session = Depends(get_db)):
    """
    印刷ジョブを作成する。検証用エンドポイント。
    実運用では業務システム側がジョブを作成し、Redis Stream に XADD する想定。
    pdf_storage_key にはローカルファイルパスを指定することで PDF 取得が可能。
    """
    job = Job(
        agent_id=body.agent_id,
        title=body.title,
        pdf_storage_key=body.pdf_storage_key,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _to_response(job)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    """
    ジョブ詳細を返す。
    Agent が Redis Stream から job_id を受信した後に呼び出す。
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return _to_response(job)


@router.get("/{job_id}/pdf")
def get_pdf(job_id: str, db: Session = Depends(get_db)):
    """
    PDF をバイナリで返す。
    pdf_storage_key をローカルファイルパスとして扱い、ファイルを返す。
    Agent は受信後に印刷し、一時ファイルを削除する。
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if not job.pdf_storage_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF not found")
    return FileResponse(job.pdf_storage_key, media_type="application/pdf")


@router.post("/{job_id}/result", status_code=status.HTTP_204_NO_CONTENT)
def post_result(job_id: str, body: JobResultRequest, db: Session = Depends(get_db)):
    """
    印刷結果を受け取り、ジョブのステータスを更新する。
    Agent が印刷完了または失敗時に呼び出す。
    status: "success" | "error"
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    job.status = body.status
    job.error_message = body.error_message
    job.updated_at = utc_now()
    db.commit()


def _to_response(job: Job) -> JobResponse:
    """Job モデルをレスポンス用スキーマに変換する。"""
    return JobResponse(
        id=job.id,
        agent_id=job.agent_id,
        title=job.title,
        pdf_storage_key=job.pdf_storage_key,
        status=job.status,
        error_message=job.error_message,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
    )
