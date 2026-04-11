from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Agent, utc_now

router = APIRouter(prefix="/agents", tags=["agents"])


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
    Agent の状態を受け取り、last_seen_at を更新する。
    定期送信ではなくイベント発生時に送信される。

    status の種類:
    - online   : Agent 起動時（job_id なし）
    - printing : 印刷開始直前（job_id あり）
    - success  : 印刷完了時（job_id あり）
    - error    : 印刷失敗時 / PDF取得失敗時（job_id あり）
    """
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    agent.last_seen_at = utc_now()
    db.commit()
