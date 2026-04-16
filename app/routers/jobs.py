from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import verify_api_key
from app.models import Agent, Job, utc_now
from app.redis_client import get_redis
from app.storage import get_storage

router = APIRouter(prefix="/jobs", tags=["jobs"], dependencies=[Depends(verify_api_key)])


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
    reprint_from_job_id: str | None
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

    job_id の発行フロー:
    1. このエンドポイントでジョブを作成 → サーバーが job_id（UUID）を採番して DB に保存
    2. Redis Stream（print_jobs:{agent_id}）に job_id を投入
    3. Agent が Redis Stream を監視し job_id を受信
    4. Agent が GET /jobs/{job_id} でジョブ詳細を取得
    5. 以降の POST /agents/{agent_id}/status で job_id を使って状態を通知

    事前チェック:
    - agent_id が存在しない → 404
    - is_active が False（利用不可端末） → 422

    pdf_storage_key にはローカルファイルパスを指定することで PDF 取得が可能。
    """
    agent = _get_active_agent(db, body.agent_id)

    job = Job(
        agent_id=agent.id,
        title=body.title,
        pdf_storage_key=body.pdf_storage_key,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    _xadd(job.agent_id, job.id)
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
    ストレージから pdf_storage_key に対応する PDF を取得して返す。
    Agent は受信後に印刷する。再印刷対応のため PDF は一定期間保持する。
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if not job.pdf_storage_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF not found")
    try:
        pdf_bytes = get_storage().get(job.pdf_storage_key)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF not found")
    return Response(content=pdf_bytes, media_type="application/pdf")


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


@router.post("/{job_id}/reprint", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def reprint(job_id: str, db: Session = Depends(get_db)):
    """
    再印刷を新規ジョブとして作成する。

    処理フロー:
    1. 元ジョブを取得
    2. pdf_storage_key を引き継ぐ
    3. reprint_from_job_id に元ジョブの id をセットして新規ジョブ作成
    4. Redis 投入（未実装）
    """
    original = db.query(Job).filter(Job.id == job_id).first()
    if not original:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    _get_active_agent(db, original.agent_id)

    new_job = Job(
        agent_id=original.agent_id,
        title=original.title,
        pdf_storage_key=original.pdf_storage_key,
        reprint_from_job_id=original.id,
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    _xadd(new_job.agent_id, new_job.id)
    return _to_response(new_job)


def _xadd(agent_id: str, job_id: str) -> None:
    """Redis Stream にジョブを投入する。Stream名は print_jobs:{agent_id}。"""
    r = get_redis()
    stream_name = f"print_jobs:{agent_id}"
    r.xadd(stream_name, {"job_id": job_id})


def _get_active_agent(db: Session, agent_id: str) -> Agent:
    """agent_id の存在と利用可否を確認する。"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not agent.is_active:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Agent is not active")
    return agent


def _to_response(job: Job) -> JobResponse:
    """Job モデルをレスポンス用スキーマに変換する。"""
    return JobResponse(
        id=job.id,
        agent_id=job.agent_id,
        title=job.title,
        pdf_storage_key=job.pdf_storage_key,
        status=job.status,
        error_message=job.error_message,
        reprint_from_job_id=job.reprint_from_job_id,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
    )
