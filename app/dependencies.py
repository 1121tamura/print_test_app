from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from .config import get_settings

_api_key_header = APIKeyHeader(name="X-API-Key")
"""リクエストヘッダー ``X-API-Key`` からAPIキーを取得するスキーマ。

キーが存在しない場合、FastAPI が自動的に 403 を返す。
"""


def verify_api_key(api_key: str = Security(_api_key_header)) -> None:
    """APIキーを検証する FastAPI Dependency。

    リクエストヘッダー ``X-API-Key`` の値を ``.env`` の ``API_KEY`` と照合する。
    不一致の場合は HTTP 403 を返す。

    各ルーターの ``dependencies=[Depends(verify_api_key)]`` に指定することで、
    ルーター配下の全エンドポイントに認証を適用できる。
    """
    if api_key != get_settings().api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
