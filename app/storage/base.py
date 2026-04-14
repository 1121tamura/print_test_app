from abc import ABC, abstractmethod


class AbstractStorage(ABC):
    @abstractmethod
    def get(self, key: str) -> bytes:
        """key に対応する PDF バイナリを返す。存在しない場合は FileNotFoundError を送出する。"""
        ...

    @abstractmethod
    def exists(self, key: str) -> bool:
        """key に対応する PDF が存在するか確認する。"""
        ...
