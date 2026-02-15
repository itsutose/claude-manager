# Claude Session Manager - 仕様書 v2

## 概要

Claude Code CLIのセッション管理を改善するローカルWebダッシュボード。
SlackライクなUIで、プロジェクトの切り替え・セッション一覧・会話内容の閲覧を直感的に行える。
同一プロジェクトの複数クローンも統合管理する。

---

## 背景・課題

### 現状の問題点
1. **セッション検索が困難**: `claude --resume`はカレントディレクトリのセッションしか表示しない。`Ctrl+A`で全表示可能だが使いにくい。履歴に現れないセッションも存在する
2. **セッション命名が面倒**: `/rename`を手動で行う必要があり、つけ忘れが頻発。コンテキストが変わっても名前が更新されない
3. **並行セッションの混乱**: 複数プロジェクト・複数セッションを同時進行すると、どのセッションが何をしていたか把握できなくなる
4. **進捗管理が不在**: プロジェクト横断でのセッション進捗を俯瞰する手段がない
5. **クローン管理の煩雑さ**: 同一プロジェクトを複数クローンして並行作業するが、それらの関係性が管理できない

### ユーザーの開発スタイル
- 同じプロジェクトを複数cloneして同時並行で作業する（環境汚染回避＋並列処理）
- 例: `refund-hub/`, `refund-hub-2/`, `refund-hub-3/` は同じリポジトリのクローン
- 例: `hyogo-medical-1/`, `hyogo-medical-2/`, `hyogo-medical-3/` も同様
- 各クローン内で複数のClaude Codeセッションが存在する

### 解決目標
- SlackライクなUIでプロジェクト・セッションを直感的にナビゲートできる
- 同一プロジェクトの複数クローンをグループとして統合管理できる
- セッションの会話内容をブラウザで閲覧でき、ターミナルを開かずに状況把握できる
- セッション完了時に通知を受け取れる

---

## UI設計: Slack UIとの対応関係

```
Slack                          Claude Session Manager
─────────────────────────────────────────────────────
ワークスペース切替バー(左端)  →  プロジェクトグループ切替バー
サイドバー(チャンネルリスト)   →  クローン別セッション一覧
メインエリア(メッセージ表示)   →  セッション会話内容表示
チャンネルヘッダーバー        →  セッションタイトル + アクション
ワークスペース名 + 検索バー   →  プロジェクト設定 + 検索バー
```

---

## 画面レイアウト

### 全体構成（3カラム）

```
┌──┬──────────────────┬──────────────────────────────────────┐
│  │                  │                                      │
│  │                  │                                      │
│P │   サイドバー       │         メインエリア                  │
│R │                  │                                      │
│O │  クローン別       │    セッション会話内容                  │
│J │  セッション一覧    │                                      │
│  │                  │                                      │
│B │                  │                                      │
│A │                  │                                      │
│R │                  │                                      │
│  │                  │                                      │
└──┴──────────────────┴──────────────────────────────────────┘
 48    240px               残り全部
 px
```

---

### カラム1: プロジェクトグループバー（左端 48px）

Slackのワークスペース切替バーに相当。プロジェクトグループをイニシャル/略称で表示。

```
┌──┐
│RH│  ← refund-hub (active)
├──┤
│HM│  ← hyogo-medical
├──┤
│DF│  ← dotfiles
├──┤
│CE│  ← chrome-ex
├──┤
│SS│  ← sony-sonpo
├──┤
│  │
│  │
├──┤
│⚙ │  ← 設定
└──┘
```

**仕様:**
- 各アイコンは2文字のイニシャル（プロジェクト名から自動生成）
- アクティブなプロジェクトは左にアクセントカラーのボーダー
- 未読通知（セッション完了等）がある場合はバッジ表示
- 最下部に設定アイコン
- ホバーでプロジェクト名のツールチップ

---

### カラム2: サイドバー（240px）

Slackのチャンネルリストに相当。選択中のプロジェクトグループ内のクローンとセッションを表示。

```
┌─────────────────────┐
│ refund-hub      🔍  │  ← プロジェクト名 + 検索
│ ⚙ プロジェクト設定    │  ← 設定バー
├─────────────────────┤
│                     │
│ 📌 ピン留め          │  ← ピン留めセッション
│  # e2eテスト環境構築  │
│  # API設計レビュー    │
│                     │
│ ▼ refund-hub (本体)  │  ← クローン1 (セクション)
│  # research clp/klp │     セッション一覧
│  # エラー解決策の備考  │
│  # メモリ使用量確認   │
│  ○ (名前なし)       │     名前なしセッション
│  ○ (名前なし)       │
│                     │
│ ▼ refund-hub-2      │  ← クローン2
│  # scraping修正      │
│  # batch処理改善     │
│                     │
│ ▼ refund-hub-3      │  ← クローン3
│  # フロントエンド実装  │
│                     │
│ ▼ refund-hub-4      │  ← クローン4
│  ○ (名前なし)       │
│                     │
└─────────────────────┘
```

**仕様:**

#### セクション構成
1. **ピン留めセッション**: 重要なセッションをピン留めして常にアクセスしやすく
2. **クローン別セッション**: 各クローンをセクション（折りたたみ可能）として表示
   - セクションヘッダー: クローン名 + セッション数
   - セッション項目: `# セッション名` or `○ (名前なし)` + ステータスインジケーター

#### セッション表示
- アクティブ（直近1h）: 太字 + 緑ドット
- 最近（直近24h）: 通常 + 黄ドット
- それ以外: 薄いテキスト
- 未読（前回閲覧後に更新あり）: 太字表示
- 名前なしセッション: firstPromptの先頭を薄いテキストで表示

#### 検索
- サイドバー上部の検索ボックスでプロジェクト内セッションをフィルタ
- セッション名、firstPrompt、ブランチ名で絞り込み

---

### カラム3: メインエリア（残り全幅）

Slackのメッセージ表示エリアに相当。選択中のセッションの会話内容を表示。

#### ヘッダーバー

```
┌──────────────────────────────────────────────────────┐
│ # research clp/klp                     🔍 ⭐ ⚙      │
│ branch: my-dev | 13 msgs | Jan 31 16:20 - 16:29    │
├──────────────────────────────────────────────────────┤
│  [メッセージ]  [ファイル変更]  [関連ページ]  [ピン]  +  │
└──────────────────────────────────────────────────────┘
```

- セッションタイトル（自動生成 or customTitle）
- メタデータ（ブランチ、メッセージ数、期間）
- アクションボタン: 検索、ピン留め、設定
- タブ: メッセージ / ファイル変更 / 関連ページ / ピン（将来拡張）

#### メッセージ表示エリア（メインタブ）

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│  ─── 2026年1月31日（水）───                            │
│                                                      │
│  👤 User  16:20                                      │
│  "salon_id" 19 33 52 76 77 85 90 108 142 150        │
│  170 329 403 409 489 494 528 609 610 641 656 675    │
│  683 684 685 686 687 690 755 940 965 990 995...     │
│                                                      │
│  🤖 Claude  16:21                                    │
│  これらのsalon_idについて調査します。                    │
│  まず、対象のsalon_idのデータを確認します。              │
│                                                      │
│  📎 ツール使用: Bash                                  │
│  ┌────────────────────────────────────┐              │
│  │ SELECT * FROM salons              │              │
│  │ WHERE id IN (19, 33, 52, ...);    │              │
│  └────────────────────────────────────┘              │
│                                                      │
│  結果: 38件のサロンデータを取得しました。               │
│  ┌────────────────────────────────────┐              │
│  │ id | name          | status       │              │
│  │ 19 | サロンA        | active       │              │
│  │ 33 | サロンB        | inactive     │              │
│  │ ...                               │              │
│  └────────────────────────────────────┘              │
│                                                      │
│  👤 User  16:25                                      │
│  staff_equipmentsのデータも確認して                     │
│                                                      │
│  🤖 Claude  16:26                                    │
│  staff_equipmentsテーブルを確認します。                  │
│  ...                                                │
│                                                      │
└──────────────────────────────────────────────────────┘
```

**メッセージ表示仕様:**
- Slackと同様の日付セパレーター
- ユーザーメッセージ: 左寄せ、ユーザーアイコン
- Claudeメッセージ: 左寄せ、Claudeアイコン
- ツール使用: 折りたたみ可能なコードブロックとして表示
- ツール結果: 折りたたみ可能な結果ブロック
- コード: シンタックスハイライト付き
- タイムスタンプ: 各メッセージに表示
- メッセージは読み取り専用（編集不可）

#### アクションバー（下部）

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│  [セッションを再開 ▶]  [コマンドをコピー 📋]            │
│                                                      │
└──────────────────────────────────────────────────────┘
```

- 「セッションを再開」: tmuxに新ウィンドウを作成してclaude --resume実行
- 「コマンドをコピー」: `cd /path && claude --resume <id>` をクリップボードにコピー

---

### セッション未選択時のメインエリア

プロジェクトグループの概要ダッシュボードを表示。

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│  refund-hub プロジェクト概要                           │
│                                                      │
│  ┌────────┐ ┌────────┐ ┌────────┐                   │
│  │総セッション│ │アクティブ│ │ 総メッセージ│                   │
│  │   39   │ │   3    │ │   487  │                   │
│  └────────┘ └────────┘ └────────┘                   │
│                                                      │
│  🕐 最近のアクティビティ                                │
│  ┌──────────────────────────────────────────────┐    │
│  │ [refund-hub-2] scraping修正       2h ago     │    │
│  │ [refund-hub]   research clp/klp   1d ago     │    │
│  │ [refund-hub-3] フロントエンド実装    3d ago     │    │
│  └──────────────────────────────────────────────┘    │
│                                                      │
│  📊 クローン別状況                                    │
│  ┌──────────────────────────────────────────────┐    │
│  │ refund-hub    16 sessions  branch: my-dev    │    │
│  │ refund-hub-2  11 sessions  branch: feature-x │    │
│  │ refund-hub-3  11 sessions  branch: fix-bug   │    │
│  │ refund-hub-4   1 session   branch: main      │    │
│  └──────────────────────────────────────────────┘    │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

### グローバル検索（Slack Cmd+K相当）

`Cmd+K` でオーバーレイ検索を開く。全プロジェクト横断で検索。

```
┌──────────────────────────────────────────────┐
│  🔍 セッションを検索...                       │
│                                              │
│  検索対象: [全て ▼]                           │
│                                              │
│  最近のセッション                              │
│  ┌──────────────────────────────────────┐    │
│  │ [RH] research clp/klp       1d ago  │    │
│  │ [HM] フロントエンド修正        5h ago  │    │
│  │ [DF] Neovim LSP設定          1d ago  │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  キーワード入力後:                             │
│  ┌──────────────────────────────────────┐    │
│  │ [RH] scraping修正   "selenium..."    │    │
│  │ [DF] nvim設定       "treesitter..."  │    │
│  └──────────────────────────────────────┘    │
└──────────────────────────────────────────────┘
```

---

## データモデル

### ProjectGroup（Slackのワークスペース相当）

同一プロジェクトの複数クローンをまとめるグループ。

```python
@dataclass
class ProjectGroup:
    group_id: str              # 一意識別子（例: "refund-hub"）
    display_name: str          # 表示名（例: "refund-hub"）
    initials: str              # アイコン用イニシャル（例: "RH"）
    clones: list[ProjectClone] # 所属するクローン一覧

    # 集計
    total_sessions: int
    active_sessions: int       # 直近1h内にmodifiedされたもの
    latest_modified: datetime
    total_messages: int
```

### ProjectClone（サイドバーのセクション相当）

プロジェクトグループ内の個別クローン（= `~/.claude/projects/`の1ディレクトリ）。

```python
@dataclass
class ProjectClone:
    clone_id: str              # encodedパスのキー
    clone_name: str            # 表示名（例: "refund-hub-2"）
    project_path: str          # 実際のディレクトリパス
    sessions: list[SessionEntry]
    session_count: int
    latest_modified: datetime
    current_branch: str | None # 最新セッションのgitブランチ
```

### SessionEntry（サイドバーのチャンネル相当）

```python
@dataclass
class SessionEntry:
    session_id: str            # UUID
    clone_id: str              # 所属するクローンのID
    group_id: str              # 所属するプロジェクトグループのID
    custom_title: str | None   # /renameで付けた名前
    first_prompt: str          # 最初のユーザー入力
    message_count: int         # メッセージ数
    created: datetime
    modified: datetime
    git_branch: str | None
    is_sidechain: bool
    full_path: str             # JSONLファイルへのフルパス
    is_pinned: bool            # ピン留め状態

    # 算出フィールド
    display_name: str          # custom_title or first_promptの先頭50文字
    status: SessionStatus      # active / recent / idle / archived
    has_unread: bool           # 前回閲覧以降に更新があるか
```

### SessionMessage（メインエリアのメッセージ相当）

```python
@dataclass
class SessionMessage:
    message_id: str
    role: str                  # "user" / "assistant"
    content: str               # メッセージ本文
    timestamp: datetime
    tool_uses: list[ToolUse]   # ツール使用情報

@dataclass
class ToolUse:
    tool_name: str             # "Bash", "Read", "Edit" 等
    input_summary: str         # 入力の要約
    output_summary: str        # 出力の要約（折りたたみ用）
    is_collapsed: bool         # デフォルト折りたたみ状態
```

---

## プロジェクトグループの自動検出ロジック

同一プロジェクトのクローンを自動的にグループ化する。

### グルーピングルール

```
実際のパス構造:
  ~/Desktop/refund-hub-project/
    ├── refund-hub/       → クローン1
    ├── refund-hub-2/     → クローン2
    ├── refund-hub-3/     → クローン3
    └── refund-hub-4/     → クローン4

  ~/Desktop/hyogo-medical/
    ├── hyogo-medical-1/           → クローン1
    ├── hyogo-medical-2/           → クローン2
    └── hyogo-medical-3/frontend/  → クローン3

  ~/dotfiles/
    ├── (root)        → メイン
    ├── nvim/         → サブプロジェクト
    ├── ghostty/      → サブプロジェクト
    └── zsh/          → サブプロジェクト
```

### 検出アルゴリズム

1. `~/.claude/projects/`内の全ディレクトリを列挙
2. `sessions-index.json`からprojectPathを取得
3. projectPathの**親ディレクトリ**でグルーピング
   - 同じ親ディレクトリ配下 → 同一グループ
   - 例: `/Desktop/refund-hub-project/refund-hub` と `/Desktop/refund-hub-project/refund-hub-2` → 親が同じなのでグループ化
4. サブプロジェクト（dotfiles/nvimなど）は親のベース名で判定
   - `/dotfiles/nvim` の親は `/dotfiles` → dotfilesグループ
5. 単独プロジェクト（グループ化不要）はそのまま1クローンのグループとして扱う

### グループ名の決定
- グループ内クローンの共通プレフィックスから導出
- 例: `refund-hub`, `refund-hub-2`, `refund-hub-3` → グループ名: `refund-hub`
- 例: `hyogo-medical-1`, `hyogo-medical-2` → グループ名: `hyogo-medical`
- フォールバック: 親ディレクトリ名

### イニシャルの生成
- ハイフン区切りの各単語の頭文字を最大2文字
- `refund-hub` → `RH`
- `hyogo-medical` → `HM`
- `dotfiles` → `DF`
- `chrome-ex` → `CE`
- 衝突時はサフィックス番号

---

## ステータス定義

### セッションステータス

`modified`タイムスタンプから自動判定:

| ステータス | 条件 | サイドバー表示 | 色 |
|-----------|------|-------------|-----|
| `active` | 直近1時間以内 | 太字 + 緑ドット | `#22c55e` |
| `recent` | 直近24時間以内 | 通常 + 黄ドット | `#eab308` |
| `idle` | 直近7日以内 | 薄テキスト | `#6b7280` |
| `archived` | 7日以上前 | 最薄テキスト | `#374151` |

---

## 通知システム

### セッション完了通知

Claude Codeのセッションが出力を終えた際（idle状態に遷移した際）にブラウザ通知を送る。

**検出方法:**
- バックエンドが定期的に（5秒間隔）sessions-index.jsonのmtimeを監視
- mtimeが更新された場合、エントリのmodifiedを確認
- 直近で`active`だったセッションが更新停止した場合 → 完了とみなす

**通知内容:**
```
[refund-hub] scraping修正 セッションが完了
最終メッセージ: "修正が完了しました。テストも通っています。"
```

**通知方式:**
- ブラウザのNotification API（Permission要求）
- サイドバーのセッション横にバッジ表示
- プロジェクトグループバーのアイコンにもバッジ

---

## API設計

### エンドポイント一覧

| Method | Path | 説明 |
|--------|------|------|
| GET | `/api/groups` | プロジェクトグループ一覧（サイドバー用サマリー） |
| GET | `/api/groups/{id}` | プロジェクトグループ詳細（クローン一覧 + 統計） |
| GET | `/api/groups/{id}/sessions` | グループ内の全セッション（クローン別にグルーピング） |
| GET | `/api/sessions/{id}` | セッション詳細（メタデータ） |
| GET | `/api/sessions/{id}/messages` | セッション会話メッセージ一覧 |
| GET | `/api/search?q=xxx` | グローバル検索 |
| POST | `/api/sessions/{id}/resume` | セッション再開（tmux連携） |
| PUT | `/api/sessions/{id}/title` | セッション名の変更 |
| PUT | `/api/sessions/{id}/pin` | ピン留めトグル |
| GET | `/api/notifications` | 未読通知一覧 |
| GET | `/api/events` | SSE: リアルタイム更新ストリーム |

### SSE (Server-Sent Events)

リアルタイム更新のためにSSEを使用:

```
GET /api/events

data: {"type": "session_updated", "session_id": "xxx", "status": "active"}
data: {"type": "session_completed", "session_id": "xxx", "last_message": "..."}
data: {"type": "index_refreshed", "group_id": "refund-hub"}
```

---

## メッセージパース仕様

### JSONL構造の読み取り

セッションの`.jsonl`ファイルからメッセージを抽出する。

**対象レコードタイプ:**
- `type: "human"` → ユーザーメッセージ
- `type: "assistant"` → Claudeメッセージ
- `type: "file-history-snapshot"` → スキップ（ファイル変更記録）

**Claudeメッセージ内のツール使用:**
- `content`配列内の`type: "tool_use"`要素を検出
- ツール名と入力を抽出、結果は対応する`type: "tool_result"`から取得
- デフォルトで折りたたみ表示（ユーザーがクリックで展開）

**表示の最適化:**
- 長いメッセージ（1000文字超）は折りたたみ
- コードブロックはシンタックスハイライト
- ツール使用は件数サマリーのみ表示（展開で詳細）

---

## 永続化データ（ユーザー設定）

Claude Codeの`~/.claude/`には書き込まないが、マネージャー独自の設定は別ファイルに保存。

```
~/.claude-manager/
├── config.json        # アプリ設定
├── pins.json          # ピン留めセッション一覧
├── read_state.json    # 各セッションの最終閲覧タイムスタンプ（未読管理用）
├── group_config.json  # グループ設定（カスタム名、順序、手動グルーピング）
└── notifications.json # 通知履歴
```

### config.json
```json
{
  "claude_dir": "~/.claude",
  "port": 8420,
  "poll_interval_sec": 5,
  "theme": "dark",
  "notification_enabled": true
}
```

### group_config.json
```json
{
  "custom_groups": {
    "refund-hub": {
      "display_name": "Refund Hub",
      "initials": "RH",
      "order": 0
    }
  },
  "manual_mappings": {
    "/path/to/special-clone": "refund-hub"
  }
}
```

---

## アーキテクチャ

```
┌──────────────────────────────────────────────────────┐
│                Browser (localhost:8420)                │
│  ┌───────────────────────────────────────────────┐   │
│  │  SPA (HTML + Tailwind CSS + Alpine.js)         │   │
│  │  - 3カラムレイアウト                             │   │
│  │  - SSEでリアルタイム更新                          │   │
│  │  - Cmd+K グローバル検索                          │   │
│  │  - Browser Notification API                     │   │
│  └────────────────────┬──────────────────────────┘   │
│                       │ HTTP/JSON + SSE               │
└───────────────────────┼──────────────────────────────┘
                        │
┌───────────────────────┼──────────────────────────────┐
│  ┌────────────────────┴──────────────────────────┐   │
│  │          FastAPI Backend                        │   │
│  │  ┌─────────────┐  ┌─────────────────────────┐ │   │
│  │  │ API Routers  │  │ Background Tasks         │ │   │
│  │  │ - groups     │  │ - File watcher (5s poll) │ │   │
│  │  │ - sessions   │  │ - SSE broadcaster        │ │   │
│  │  │ - search     │  │ - Notification manager   │ │   │
│  │  │ - events     │  │                          │ │   │
│  │  └──────┬──────┘  └──────────┬──────────────┘ │   │
│  │         │                     │                 │   │
│  │  ┌──────┴─────────────────────┴──────────────┐ │   │
│  │  │         Services Layer                      │ │   │
│  │  │  - SessionIndexReader                       │ │   │
│  │  │  - MessageParser (JSONL)                    │ │   │
│  │  │  - GroupDetector (auto-grouping)            │ │   │
│  │  │  - SearchEngine                             │ │   │
│  │  │  - TerminalBridge (tmux)                    │ │   │
│  │  └──────┬─────────────────────┬──────────────┘ │   │
│  │         │                     │                 │   │
│  └─────────┼─────────────────────┼─────────────────┘   │
│            │                     │                      │
│  ┌─────────┴───────┐  ┌─────────┴───────────────┐     │
│  │ ~/.claude/       │  │ ~/.claude-manager/       │     │
│  │ (Read-Only)      │  │ (Read-Write)             │     │
│  │ - projects/      │  │ - config.json            │     │
│  │ - history.jsonl  │  │ - pins.json              │     │
│  │                  │  │ - read_state.json        │     │
│  └──────────────────┘  └─────────────────────────┘     │
│                  Python Backend                         │
└─────────────────────────────────────────────────────────┘
```

### 技術スタック

| レイヤー | 技術 | 理由 |
|---------|------|------|
| バックエンド | Python 3.12+ / FastAPI | 高速開発、JSON処理に適する、SSE対応 |
| フロントエンド | HTML + Tailwind CSS + Alpine.js | PoC向け軽量構成。ビルドステップ不要 |
| リアルタイム | SSE (Server-Sent Events) | WebSocketより簡素。サーバー→クライアント片方向で十分 |
| データソース | `~/.claude/` (読み取り専用) | 既存データをそのまま利用 |
| ユーザーデータ | `~/.claude-manager/` | ピン、未読状態等のマネージャー固有データ |
| セッション再開 | tmux send-keys | ターミナルへのコマンド送信 |
| 通知 | Browser Notification API | ブラウザネイティブ通知 |

---

## ファイル構成（PoC）

```
claude-manager/
├── pyproject.toml
├── src/
│   └── claude_manager/
│       ├── __init__.py
│       ├── main.py              # FastAPIアプリ起点 + サーバー起動
│       ├── config.py            # 設定管理
│       ├── models.py            # データモデル定義
│       ├── services/
│       │   ├── __init__.py
│       │   ├── index_reader.py  # sessions-index.json読み取り
│       │   ├── message_parser.py # JSONL会話データのパース
│       │   ├── group_detector.py # プロジェクトグループ自動検出
│       │   ├── search.py        # 検索エンジン
│       │   ├── watcher.py       # ファイル変更監視 + SSE
│       │   ├── terminal.py      # tmux連携
│       │   └── user_data.py     # pins, read_state等の永続化
│       ├── routers/
│       │   ├── __init__.py
│       │   ├── groups.py        # プロジェクトグループAPI
│       │   ├── sessions.py      # セッションAPI
│       │   ├── search.py        # 検索API
│       │   └── events.py        # SSE + 通知API
│       └── static/
│           ├── index.html       # SPA エントリポイント
│           ├── app.js           # Alpine.js メインアプリ
│           ├── components/      # UIコンポーネント
│           │   ├── project-bar.js
│           │   ├── sidebar.js
│           │   ├── main-area.js
│           │   ├── search-modal.js
│           │   └── message-view.js
│           └── style.css        # カスタムスタイル（Tailwind CDN併用）
└── tests/
    ├── test_index_reader.py
    ├── test_group_detector.py
    └── test_message_parser.py
```

---

## 制約事項

- **`~/.claude/`は読み取り専用**: セッションデータへの書き込みは一切行わない
- **ローカル専用**: `localhost`でのみ動作。外部ネットワークへの通信なし
- **セキュリティ**: セッションデータには機密情報が含まれる可能性があるため外部公開しない
- **パフォーマンス**: セッション数は数百〜数千程度を想定。起動時にインデックスをメモリに読み込み、ファイル変更を定期ポーリングで検出

---

## 起動方法

```bash
# インストール
cd claude-manager && pip install -e .

# 起動（ブラウザも自動で開く）
claude-manager serve

# オプション
claude-manager serve --port 8420 --no-browser
```

---

## 今後の拡張案（PoC後）

### Phase 2: 自動化・統合
- **Hook連携**: Claude Codeのhook機能でセッション開始/終了を検知し、自動更新
- **自動要約**: セッション内容をHaiku等で要約し、タイトルを自動生成
- **tmuxペイン名同期**: セッション名変更時にtmuxのウィンドウ名を自動更新

### Phase 3: 高度な管理
- **タグ・ラベル機能**: セッションにタグを付けて分類
- **セッション間リンク**: 関連セッションのグループ化
- **ファイル変更タブ**: セッションで変更されたファイルの一覧・diffビュー
- **関連ページタブ**: Slackの「canvas」のような自由メモエリア
- **MCP設定**: プロジェクトごとのMCP設定の管理UI
- **プロジェクト設定**: CLAUDE.md、hook設定の管理UI

### Phase 4: TUI / CLI統合
- PoC検証結果を元にターミナルTUI版を検討
- `cm search`, `cm list`, `cm resume` 等のCLIコマンド
