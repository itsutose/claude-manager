# Claude Session Manager

Claude Code のセッションをブラウザで一覧・閲覧・操作するローカルWebダッシュボード。

## 前提条件

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Node.js 20+ / [pnpm](https://pnpm.io/)
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (`claude` コマンドが使える状態)

## セットアップ

```bash
# バックエンド依存のインストール
uv sync

# フロントエンドビルド
cd frontend && pnpm install && pnpm run build && cd ..
```

## 起動

```bash
# 方法1: CLIから（ブラウザ自動起動）
uv run claude-manager serve

# 方法2: uvicornで直接
uv run uvicorn --factory claude_manager.main:create_app --host 127.0.0.1 --port 8420

# オプション
uv run claude-manager serve --port 9000 --no-browser
```

http://127.0.0.1:8420 でアクセス。

## フロントエンド開発

```bash
cd frontend
pnpm dev       # Vite dev server (HMR)
pnpm build     # プロダクションビルド → ../src/claude_manager/static/
```

dev server 使用時は Vite のプロキシ設定で API を `localhost:8420` に転送する。

## アーキテクチャ

```
~/.claude/projects/          ← Claude Code のセッションデータ（読み取り元）
~/.claude-manager/           ← 本アプリの永続データ（ピン・非表示・カスタムタイトル）

src/claude_manager/
  main.py                    ← FastAPI app / CLI エントリポイント
  models.py                  ← データモデル（SessionEntry, ProjectGroup 等）
  config.py                  ← 設定
  routers/                   ← API エンドポイント
    groups.py                ← プロジェクトグループ一覧・詳細
    sessions.py              ← セッション操作（送信・リネーム・非表示等）
    search.py                ← 全文検索
    events.py                ← SSE（リアルタイム更新）
  services/
    index_reader.py          ← セッション読み取り（JSONL直接スキャン）
    group_detector.py        ← プロジェクトグループ検出
    session_manager.py       ← タイトル管理（sessions-index.json書き込み）
    session_interactor.py    ← claude CLI 呼び出し（メッセージ送信・タイトル生成）
    asset_reader.py          ← CLAUDE.md / rules / skills 読み取り
    user_data.py             ← ピン・非表示の永続化
    watcher.py               ← ファイル監視（SSE通知）
    terminal.py              ← tmux連携

frontend/src/
  App.tsx                    ← メインレイアウト（3カラム）
  hooks/useGroups.ts         ← グループ・セッション状態管理
  components/
    GroupBar.tsx              ← 左カラム（プロジェクト一覧）
    Sidebar.tsx               ← 中カラム（セッション一覧）
    MessageArea.tsx           ← 右カラム（メッセージ表示・送信）
    ProjectOverview.tsx       ← プロジェクト概要
    AssetsPanel.tsx           ← CLAUDE.md / Rules / Skills 表示
    SearchModal.tsx           ← 検索ダイアログ
```

## セッションデータの読み取り方式

本アプリは **JONLファイルの直接スキャン** を採用している。

Claude Code の `sessions-index.json` は v2.1.31以降で更新が停止するバグがあり（[#22205](https://github.com/anthropics/claude-code/issues/22205)）、CLI自体も既にJSONLファイルの直接スキャンに移行している。本アプリもこれに倣い:

1. `~/.claude/projects/*/` 配下の `.jsonl` ファイルをスキャン（存在 = セッション存在）
2. `sessions-index.json` はメタデータキャッシュとして利用（あれば高速、なくても動作）
3. indexに無い「orphan」セッションはJSONLヘッダーから直接パース

### 推奨設定

Claude Code のデフォルトでは30日で古いセッションが自動削除される。これを防ぐには:

```json
// ~/.claude/settings.json
{
  "cleanupPeriodDays": 99999
}
```

## 主な機能

- セッション一覧・メッセージ閲覧（Slack風3カラムUI）
- プロジェクトグループ自動検出
- セッション検索（全文）
- メッセージ送信（`claude -p --resume` 経由）
- 自動命名（Haiku LLM でタイトル生成）
- 手動リネーム / ピン留め / 非表示（ゴミ箱）
- プロジェクトアセット表示（CLAUDE.md / rules / skills）
- tmux連携（ターミナルで再開）
- SSEによるリアルタイム更新
