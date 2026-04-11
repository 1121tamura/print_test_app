"""
テーブル作成スクリプト。
devcontainer 内で以下のコマンドで実行する:

    python scripts/create_tables.py
"""
from app.db import Base, engine
from app import models  # noqa: F401 - モデルをBaseに登録するために必要


def main():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Done.")


if __name__ == "__main__":
    main()
