# 開発者向けガイド

## 必要条件

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

OpenAI Embedding（デフォルト）を使用する場合は `OPENAI_API_KEY` 環境変数が必要です。

## ソースからのセットアップ

```bash
git clone https://github.com/leCielEtoile/custom-docs-mcp
cd custom-docs-mcp
uv sync

# ローカルEmbeddingモデルを使う場合
uv sync --extra local
```

設定ファイルを準備します：

```bash
cp config.example.yaml config.yaml
cp .mcp.json.example .mcp.json
```

## 起動

```bash
# stdioモード（Claude Desktop / Claude Code連携）
uv run docs-mcp --config config.yaml
```

## HTTP モードでの起動

リモートやコンテナで動かす場合は `transport.mode: http` に設定します。

```yaml
transport:
  mode: http
  host: 0.0.0.0
  port: 8000
```

```bash
uv run docs-mcp --config config.yaml
```

MCP クライアントからは `http://localhost:8000` で接続します（Streamable HTTP トランスポート）。

## DXT ビルド

リリースワークフロー（`.github/workflows/release.yml`）が `v*` タグのプッシュ時に自動でビルドします。手動でビルドする場合：

```bash
VERSION=0.1.0
zip -r "docs-mcp-${VERSION}.dxt" manifest.json config.example.yaml README.md LICENSE
```
