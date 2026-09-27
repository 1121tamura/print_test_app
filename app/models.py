import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    mac_address: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # NIC の MAC アドレス。端末識別に使用
    hostname: Mapped[str] = mapped_column(String(255))                              # Agent が動作している端末のホスト名
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)            # 管理者が付ける表示名。後から編集可
    is_active: Mapped[bool] = mapped_column(default=True)                           # False の場合はジョブ作成を拒否する
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)          # 最後に状態通知を受けた時刻
    last_job_received_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)    # 最後に job を受信した時刻
    last_print_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)   # 最後に印刷を開始した時刻
    last_print_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True) # 最後に印刷が完了した時刻
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)           # 最後にエラーが発生した時刻
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)                              # 最後のエラー内容


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id: Mapped[str] = mapped_column(String(36), index=True)                   # 印刷を担当する Agent の id
    title: Mapped[str] = mapped_column(String(200))                                 # ジョブの表示名
    pdf_storage_key: Mapped[str | None] = mapped_column(String(255), nullable=True) # PDF のファイルパス。再印刷のため一定期間保持
    status: Mapped[str] = mapped_column(String(20), default="queued")               # queued → printing → success / error / timeout
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)          # status が error の場合のエラー内容
    reprint_from_job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # 再印刷元の job id。再印刷でない場合は null
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)
