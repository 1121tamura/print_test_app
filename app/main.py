from fastapi import FastAPI

from .config import get_settings
from .routers import agents, jobs

app = FastAPI(
    title="Print Test Backend API",
    version=get_settings().app_version,
    description="print-agent 連携確認用の検証API",
)

app.include_router(agents.router)
app.include_router(jobs.router)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
