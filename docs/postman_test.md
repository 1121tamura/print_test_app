# Postman テスト手順

## テストの種類

| # | 内容 | print-agent |
|---|------|------------|
| **テスト1** | API フローのみ。Postman が print-agent の代わりにリクエストを送り、DB・Redis・API の動作を確認する | 不要 |
| **テスト2** | 実印刷テスト。print-agent を実際に起動し、Redis 経由でジョブを受信させて実機印刷まで確認する | 必要 |

---

## 共通設定

**Backend Base URL:** `http://localhost:8000`

**共通ヘッダー（Backend への全リクエストに付ける）:**

| Key | Value |
|-----|-------|
| `X-API-Key` | `dev-api-key` |
| `Content-Type` | `application/json` |

**Postman Environment 変数:**

| 変数名 | 初期値 | 説明 |
|--------|--------|------|
| `base_url` | `http://localhost:8000` | Backend Base URL |
| `api_key` | `dev-api-key` | APIキー |
| `agent_id` | （登録後に設定） | Agent 登録レスポンスから取得 |
| `job_id` | （作成後に設定） | ジョブ作成レスポンスから取得 |

Tests タブのスクリプトで自動セットできます。

```javascript
// POST /agents/register の Tests タブ
const res = pm.response.json();
pm.environment.set("agent_id", res.agent_id);
```

```javascript
// POST /jobs の Tests タブ
const res = pm.response.json();
pm.environment.set("job_id", res.id);
```

---

## テスト1: API フローのみ（print-agent なし）

### 前提条件・起動順

**必要なサービス:** MySQL・Redis・FastAPI（print-agent は不要）

**1. MySQL・Redis を起動する**（別コンテナ、Dev Container より先に起動しておく）

| サービス | ホスト | ポート |
|---------|--------|--------|
| MySQL | `host.docker.internal` | `33306` |
| Redis | `host.docker.internal` | `16379` |

MySQL の docker-compose 設定（別コンテナ側）:
```yaml
services:
  db:
    image: mysql:8.4
    container_name: print_test_mysql
    ports:
      - "33306:3306"
    environment:
      MYSQL_DATABASE: print_test
      MYSQL_USER: print_test
      MYSQL_PASSWORD: print_test
```

**2. Dev Container を開く**

VS Code で本プロジェクトを Dev Container として開く。

**3. `.env.dev` を `.env` にコピーする**（初回のみ）

```bash
cp .env.dev .env
```

**4. DB テーブルを作成する**（初回のみ）

```bash
alembic upgrade head
```

**5. FastAPI を起動する**

VS Code のデバッグパネルから `FastAPI` を実行する。

| URL | 説明 |
|-----|------|
| `http://localhost:8000/health` | ヘルスチェック |
| `http://localhost:8000/docs` | Swagger UI |

### テストフロー

Postman が print-agent の代わりに全リクエストを手動送信します。

```
1.  GET  /health
    → {"status": "ok"} が返ることを確認

2.  POST /agents/register
    Body: {"mac": "AA:BB:CC:DD:EE:FF", "hostname": "printer-01"}
    → agent_id を取得（Environment 変数にセット）

3.  POST /agents/{agent_id}/status
    Body: {"status": "online"}
    → 204

4.  POST /jobs
    Body: {"agent_id": "...", "title": "テスト印刷", "pdf_storage_key": "/path/to/test.pdf"}
    → job_id を取得（Environment 変数にセット）
    → Redis Stream に job_id が投入される

5.  GET  /jobs/{job_id}
    → status: "queued" であることを確認

6.  POST /agents/{agent_id}/status
    Body: {"status": "job_received"}
    → 204

7.  POST /agents/{agent_id}/status
    Body: {"status": "printing", "job_id": "..."}
    → 204

8.  GET  /jobs/{job_id}/pdf
    → PDF バイナリが返ることを確認（Send and Download で保存可）

9.  POST /agents/{agent_id}/status
    Body: {"status": "success", "job_id": "..."}
    → 204

10. POST /jobs/{job_id}/result
    Body: {"agent_id": "...", "status": "success"}
    → 204

11. GET  /agents/{agent_id}/pdfs
    → 作成したジョブが一覧に含まれることを確認

12. POST /jobs/{job_id}/reprint
    → 再印刷ジョブが作成され、Redis に再投入されることを確認
```

---

## テスト2: 実印刷テスト（print-agent あり）

### 前提条件・起動順

**必要なサービス:** MySQL・Redis・FastAPI・print-agent（Windows 端末）

**1〜5はテスト1と同じ**（MySQL・Redis・FastAPI の起動）

**6. Windows 端末で print-agent を起動する**

- `C:\ProgramData\PrintAgent\config.yaml` の以下が設定済みであること

  | 設定項目 | 内容 |
  |---------|------|
  | `backend.base_url` | FastAPI サーバーの URL |
  | `redis.addr` | Redis サーバーのアドレス |

- Windows の「通常使うプリンター」が設定済みであること
- Windows 端末から Backend サーバーと Redis にアクセスできること

print-agent が初回起動時に自動で `POST /agents/register` を叩き、取得した `agent_id` を `config.yaml` に書き込みます。以降の起動ではスキップされます。

### テストフロー

**【事前確認】** Windows 端末上の Postman から送る

```
1. GET  http://localhost:18181/health
   → print-agent の起動確認

2. GET  http://localhost:18181/info
   → agent_id・バージョン・設定概要を確認
   → 表示された agent_id を Postman の Environment 変数にセット

3. GET  http://localhost:8000/health
   → Backend の起動確認
```

**【ジョブ投入】** Backend に向けて送る

```
4. POST http://localhost:8000/jobs
   Header: X-API-Key: dev-api-key
   Body: {
     "agent_id": "（手順2で確認した agent_id）",
     "title": "実印刷テスト",
     "pdf_storage_key": "/path/to/test.pdf"
   }
   → Redis Stream に job_id が投入される
```

**【print-agent が自動処理】** Postman 操作不要

```
print-agent が Redis から job_id を受信
  → GET  /jobs/{job_id}          （ジョブ詳細取得）
  → POST /agents/{agent_id}/status  （status: "job_received"）
  → GET  /jobs/{job_id}/pdf      （PDF 取得・temp 保存）
  → POST /agents/{agent_id}/status  （status: "printing"）
  → 実際に印刷
  → POST /agents/{agent_id}/status  （status: "success" or "error"）
  → temp ファイル削除
  → Redis ACK
```

**【結果確認】** Backend に向けて送る

```
5. GET  http://localhost:8000/jobs/{job_id}
   → status が "success" になっていることを確認
```

### テスト印刷（単体確認用）

ジョブ投入を経由せず、print-agent に直接テスト印刷を指示できます。
Windows 端末上の Postman から送ります。

```
POST http://localhost:18181/test-print
```

> Backend への通知は行われません。プリンター単体の動作確認に使います。

---

## エンドポイントリファレンス

### GET /health

ヘッダー不要。

**Response (200):**
```json
{"status": "ok"}
```

---

### POST /agents/register

**Body:**
```json
{"mac": "AA:BB:CC:DD:EE:FF", "hostname": "printer-01"}
```

**Response (200):**
```json
{"agent_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"}
```

同じ `mac` で再送するとべき等で同じ `agent_id` が返ります。

---

### POST /agents/{agent_id}/status

**status の種類:**

| status | 追加フィールド | 更新されるカラム |
|--------|--------------|-----------------|
| `online` | なし | `last_seen_at` |
| `job_received` | なし | `last_seen_at`, `last_job_received_at` |
| `printing` | `job_id` | `last_seen_at`, `last_print_started_at`, `jobs.status` |
| `success` | `job_id` | `last_seen_at`, `last_print_completed_at`, `jobs.status` |
| `error` | `job_id`, `error_message` | `last_seen_at`, `last_error_at`, `last_error_message`, `jobs.status` |

**Response:** 204 No Content

---

### GET /agents/{agent_id}/pdfs

`pdf_storage_key` が存在し、かつ `PDF_RETENTION_DAYS`（デフォルト30日）以内のジョブが対象。

**Response (200):**
```json
[
  {
    "job_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "title": "テスト印刷",
    "status": "success",
    "created_at": "2026-04-14T00:00:00"
  }
]
```

---

### POST /jobs

**Body:**
```json
{
  "agent_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "title": "テスト印刷",
  "pdf_storage_key": "/path/to/file.pdf"
}
```

`pdf_storage_key` は省略可能。`STORAGE_BASE_DIR` が空の場合はキーがそのまま絶対パスとして使われます。

**Response (201):**
```json
{
  "id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "agent_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "title": "テスト印刷",
  "pdf_storage_key": "/path/to/file.pdf",
  "status": "queued",
  "error_message": null,
  "reprint_from_job_id": null,
  "created_at": "2026-04-14T00:00:00",
  "updated_at": "2026-04-14T00:00:00"
}
```

---

### GET /jobs/{job_id}

**Response (200):** POST /jobs と同じ JobResponse 形式

---

### GET /jobs/{job_id}/pdf

**Response:** `application/pdf` のバイナリ

Postman の `Send and Download` ボタンで PDF ファイルとして保存できます。

---

### POST /jobs/{job_id}/result

**Body (成功時):**
```json
{"agent_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", "status": "success"}
```

**Body (失敗時):**
```json
{
  "agent_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "status": "error",
  "error_message": "プリンターが応答しません"
}
```

**Response:** 204 No Content

---

### POST /jobs/{job_id}/reprint

Body なし。元ジョブの `pdf_storage_key` を引き継いで新規ジョブを作成し、Redis Stream に投入します。

**Response (201):** JobResponse（`reprint_from_job_id` に元ジョブの ID がセットされる）
