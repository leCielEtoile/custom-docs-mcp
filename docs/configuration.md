# 設定

設定ファイルとMCP接続設定はいずれも環境固有のため `.gitignore` に含まれています。
各 `.example` ファイルをコピーして環境に合わせて編集してください。

```bash
cp config.example.yaml config.yaml
cp .mcp.json.example .mcp.json
```

## config.yaml

```yaml
sources:
  - id: react
    description: "React公式ドキュメント（v18+）。フック・コンポーネント・APIリファレンスを含む"
    url: https://github.com/reactjs/react.dev
    branch: main
    paths:
      - src/content/
    extensions:
      - .md
      - .mdx

  - id: fastapi
    url: https://github.com/tiangolo/fastapi
    branch: master
    paths:
      - docs/en/docs/
    extensions:
      - .md

# プライベートリポジトリは token を指定（環境変数参照可）
#   - id: internal
#     url: https://github.com/my-org/private-repo
#     token: ${GITHUB_TOKEN}
#     paths:
#       - docs/

# 定期更新スケジュール（5フィールド cron）
schedule: "0 2 * * *"   # 毎日 02:00

# Embeddingプロバイダー
embedding:
  provider: openai                  # または local
  model: text-embedding-3-small

# トランスポート（stdio または http）
transport:
  mode: stdio

db_path: ~/.docs-mcp/index.db
chunk_max_tokens: 512
```

## Embeddingプロバイダー

| プロバイダー | 設定例 | 備考 |
|---|---|---|
| OpenAI（デフォルト） | `provider: openai` / `model: text-embedding-3-small` | `OPENAI_API_KEY` 必須 |
| ローカル | `provider: local` / `model: all-MiniLM-L6-v2` | `uv sync --extra local` 必須。初回起動時にモデルを自動ダウンロード（約90MB） |

APIコストなしで使いたい場合：

```bash
uv sync --extra local
uv run docs-mcp --config config.local.yaml
```

`config.local.yaml` は `all-MiniLM-L6-v2`（384次元）をローカルで実行する設定です。OpenAI APIキーは不要です。

### ローカルモデルの選択肢

| モデル | 次元数 | 特徴 |
|---|---|---|
| `all-MiniLM-L6-v2` | 384 | 軽量・高速（推奨） |
| `all-mpnet-base-v2` | 768 | 高精度・やや重い |
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 | 多言語対応（日本語ドキュメントに有効） |
