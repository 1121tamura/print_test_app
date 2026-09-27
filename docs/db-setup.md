# DB 接続方針（MySQL）

このプロジェクトでは、MySQL はこのリポジトリとは別のコンテナで起動する。

## 接続先

- Backend から MySQL へは `host.docker.internal:13306` で接続する
- 接続先ホスト名は Backend がコンテナ内で動く前提のため `localhost` ではなく `host.docker.internal` を使う

## 環境変数ファイルを作成

プロジェクトルートで `.env.dev` を `.env` にコピーする。

```bash
cp .env.dev .env
```

## 接続確認の考え方

- DB コンテナ自体の起動や停止は別プロジェクト側で管理する
- このリポジトリでは `DB_HOST` `DB_PORT` `DB_NAME` `DB_USER` `DB_PASSWORD` を持つ
- MySQL が起動済みで、ホスト側の 13306 が公開されていることを前提とする

## Backend 側の接続設定

`.env.dev` では以下の環境変数を使う。

```env
DB_HOST=host.docker.internal
DB_PORT=13306
DB_NAME=print_test
DB_USER=print_test
DB_PASSWORD=print_test
```

## 現在のDBコンテナ設定

現在は別コンテナ側で、以下のような設定で MySQL を起動している。

```yaml
services:
	db:
		image: mysql:8.4
		container_name: print_test_mysql
		restart: unless-stopped
		ports:
			- "13306:3306"
		environment:
			MYSQL_ROOT_PASSWORD: root
			MYSQL_DATABASE: print_test
			MYSQL_USER: print_test
			MYSQL_PASSWORD: print_test
			TZ: Asia/Tokyo
		volumes:
			- mysql_data:/var/lib/mysql

volumes:
	mysql_data:
```
