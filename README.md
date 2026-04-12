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

### 認証

全エンドポイント（`/health` を除く）に `X-API-Key` ヘッダーが必要。

| Header | Value |
|---|---|
| `X-API-Key` | `dev-api-key` |

キーが不正または未指定の場合は `403 Forbidden` が返る。

### エンドポイント一覧

#### Agent登録

```
POST /agents/register
Content-Type: application/json

{ "mac": "AA:BB:CC:DD:EE:FF", "hostname": "PC-01" }
```

同一 `mac` で再登録した場合は既存の UUID をそのまま返す（べき等）。

#### 状態通知

```
POST /agents/{agent_id}/status
Content-Type: application/json

{ "status": "online" }
```

`status` の種類: `online` / `job_received` / `printing` / `success` / `error`

`printing` / `success` / `error` は `job_id` も付ける。

```json
{ "status": "printing", "job_id": "uuid..." }
```

#### ジョブ作成

```
POST /jobs
Content-Type: application/json

{ "agent_id": "uuid...", "title": "テスト印刷", "pdf_storage_key": "/path/to/file.pdf" }
```

作成と同時に Redis Stream (`print_jobs:{agent_id}`) に `job_id` を投入する。

#### ジョブ詳細取得

```
GET /jobs/{job_id}
```

#### PDF取得

```
GET /jobs/{job_id}/pdf
```

`pdf_storage_key` をローカルファイルパスとして扱い、PDF バイナリを返す。

#### 印刷結果受け取り

```
POST /jobs/{job_id}/result
Content-Type: application/json

{ "agent_id": "uuid...", "status": "success" }
```

`status`: `success` または `error`。エラー時は `error_message` も付ける。

#### 再印刷

```
POST /jobs/{job_id}/reprint
```

元ジョブの `pdf_storage_key` を引き継いだ新規ジョブを作成し、Redis に投入する。

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

- PDF は `pdf_storage_key` にローカルパスを渡した場合のみ取得できる
- 初期テーブル作成はアプリ起動時の `create_all` で行う

## 残実装

### Agent管理API

運用確認用。現状は登録・状態通知のみ実装済み。

| エンドポイント | 内容 |
|---|---|
| `GET /agents` | Agent 一覧取得 |
| `PATCH /agents/{agent_id}` | 表示名（`name`）編集・`is_active` 切替 |

### Jobタイムアウト検知

`queued` のまま一定時間経過したジョブを `timeout` に更新するバックグラウンドタスク。

```
queued のまま N分経過
    ↓
バックグラウンドタスクが検知
    ↓
job.status = "timeout"
    ↓
POST /jobs/{job_id}/reprint で再印刷
```

以下は未確定のため実装前に要検討：

- タイムアウトまでの時間（何分で `timeout` にするか）
- ユーザーへの通知手段
- 別端末への振り替えが必要なケースの考慮