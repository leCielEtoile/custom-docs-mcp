# インストール

docs-mcp は3通りの方法でインストールできます。

## 1. DXT（Claude Desktop 拡張）

最も簡単な方法です。Claude Desktop に直接インストールできます。

1. [GitHub Releases](https://github.com/leCielEtoile/custom-docs-mcp/releases/latest) から `docs-mcp-<version>.dxt` をダウンロード
2. Claude Desktop を開き、メニューから **設定 → 拡張機能 → ファイルから追加** で `.dxt` ファイルを選択
3. インストール時に以下を入力：
   - **Config File**: `config.yaml` のパス（[設定ガイド](configuration.md)を参照）
   - **OpenAI API Key**: `sk-...`（ローカルモデルを使う場合は不要）

## 2. PyPI（uvx / pip）

Python 環境がある場合はパッケージとして利用できます。

```bash
# インストール不要で直接実行（推奨）
uvx docs-mcp --config /path/to/config.yaml

# または pip でインストール
pip install docs-mcp
docs-mcp --config /path/to/config.yaml
```

Claude Desktop / Claude Code への登録方法は [usage.md](usage.md) を参照してください。

## 3. Docker

コンテナで動かす場合は Docker イメージを使用できます。

```bash
docker pull ghcr.io/lecielEtoile/custom-docs-mcp:latest

docker run \
  -v ./config.yaml:/app/config.yaml \
  -e OPENAI_API_KEY=sk-... \
  ghcr.io/lecielEtoile/custom-docs-mcp:latest
```

HTTP モードで外部公開する場合：

```bash
docker run \
  -v ./config.yaml:/app/config.yaml \
  -e OPENAI_API_KEY=sk-... \
  -p 8000:8000 \
  ghcr.io/lecielEtoile/custom-docs-mcp:latest
```

> `config.yaml` で `transport.mode: http` に変更が必要です。詳細は [configuration.md](configuration.md) を参照してください。
