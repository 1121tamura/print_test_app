from app.storage.base import AbstractStorage
from app.storage.local import LocalStorage


def get_storage() -> AbstractStorage:
    from app.config import get_settings
    settings = get_settings()

    if settings.storage_type == "local":
        return LocalStorage(base_dir=settings.storage_base_dir)

    raise ValueError(f"Unsupported storage type: {settings.storage_type}")
