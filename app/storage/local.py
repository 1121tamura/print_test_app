import os

from app.storage.base import AbstractStorage


class LocalStorage(AbstractStorage):
    """
    ローカルファイルシステム（NFSマウントを含む）からPDFを取得するストレージ実装。
    key はベースディレクトリからの相対パスとして扱う。
    STORAGE_BASE_DIR が空の場合は key をそのまま絶対パスとして扱う（後方互換）。
    """

    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir

    def _resolve(self, key: str) -> str:
        if self.base_dir:
            return os.path.join(self.base_dir, key)
        return key

    def get(self, key: str) -> bytes:
        path = self._resolve(key)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"PDF not found: {path}")
        with open(path, "rb") as f:
            return f.read()

    def exists(self, key: str) -> bool:
        return os.path.isfile(self._resolve(key))
