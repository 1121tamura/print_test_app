# print_test_app

印刷エージェント連携確認用の検証プロジェクト。

現状は以下の方針にしている。

- Backend は `.devcontainer` 上で動かす
- Frontend はまだ作らない
- API確認は Postman で行う
- API仕様の正本はコード（FastAPIが `/docs` に自動生成）

## Backend 技術スタック

- Python 3.12
- FastAPI
- SQLAlchemy
- MySQL

## 開発開始手順

1. VS Code で Dev Container を開く
2. `.env.dev` を `.env` にコピーする
3. 別コンテナで MySQL を起動しておく
4. VS Code のデバッグパネルから `FastAPI` を実行する

```bash
cp .env.dev .env
```

## API確認

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Postman を使って Agent 登録、Heartbeat、Job 作成を確認する

## マイグレーション

Alembicを使用する。Django の makemigrations / migrate に相当する。

### 初期セットアップ（最初の1回だけ）

```bash
alembic init alembic
```

`alembic/` ディレクトリと `alembic.ini` が生成される。  
生成後、以下2箇所を手動で編集する必要がある（このリポジトリでは編集済み）。

| ファイル | 編集内容 |
|---|---|
| `alembic/env.py` | `Base.metadata` のインポートと、`.env` からDB URLを読む設定を追加 |
| `alembic.ini` | `sqlalchemy.url` を空にする（`.env` から読むため不要） |

### 通常の手順

```bash
# マイグレーションファイルを生成（Django の makemigrations 相当）
alembic revision --autogenerate -m "メッセージ"

# DBに適用（Django の migrate 相当）
alembic upgrade head

# 適用履歴を確認
alembic history
```

## 現時点の割り切り

- Job 作成時の Redis XADD はまだ未実装
- PDF は `pdf_storage_key` にローカルパスを渡した場合のみ取得できる
- 初期テーブル作成はアプリ起動時の `create_all` で行う