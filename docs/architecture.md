# アーキテクチャ

## データフロー

```
config.yaml
    │
    ▼
fetcher.py ──► GitHub API（ファイル一覧）
    │               └─► Raw HTTPフェッチ（並列）
    │                       │
    │                       ▼
    │               parser.py（md/mdx/rst/txt）
    │                       └─► チャンク分割（見出し単位 + トークン上限）
    ▼
embeddings.py ──► OpenAI / ローカルモデル
    │
    ▼
db.py ──► SQLite
    │       ├─ sqlite-vec（ベクトル検索）
    │       └─ FTS5（全文検索）
    │
    ▼
search.py ──► ハイブリッド検索（ベクトル + FTS 並列） + RRF マージ
    │
    ▼
server.py ──► FastMCP（search_docs / read_doc / read_sections）
```

## プロジェクト構成

```
docs-mcp/
├── pyproject.toml
├── config.example.yaml
├── docs/
│   ├── installation.md
│   ├── configuration.md
│   ├── usage.md
│   ├── development.md
│   └── architecture.md
└── src/docs_mcp/
    ├── config.py        # 設定ローダー
    ├── parser.py        # パース・チャンク分割（md/mdx/rst/txt）
    ├── fetcher.py       # GitHub フェッチ・並列インジェスト実行
    ├── db.py            # SQLite + sqlite-vec + FTS5
    ├── embeddings.py    # Embeddingプロバイダー抽象
    ├── search.py        # ハイブリッド検索 + RRF
    ├── server.py        # MCPツール定義
    ├── app.py           # アプリケーション初期化（DB・Provider・スケジューラ）
    └── __main__.py      # エントリーポイント
```
