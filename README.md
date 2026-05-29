# docs-mcp

GitHub 上の公式ドキュメントを AI が直接参照できるようにする MCP サーバーです。
登録したリポジトリのドキュメントを取り込み、Claude が「公式ドキュメントをもとに」正確に回答できるようになります。

## インストール

### DXT（推奨）

Claude Desktop に直接インストールできます。

1. [最新リリース](https://github.com/leCielEtoile/custom-docs-mcp/releases/latest) から `docs-mcp-<version>.dxt` をダウンロード
2. Claude Desktop で **設定 → 拡張機能 → ファイルから追加**
3. `config.yaml` のパスと OpenAI API キーを入力して完了

PyPI・Docker によるインストールは [インストールガイド](docs/installation.md) を参照してください。

## 設定

`config.yaml` に取り込みたいリポジトリを登録します：

```yaml
sources:
  - id: react
    url: https://github.com/reactjs/react.dev
    paths:
      - src/content/

embedding:
  provider: openai
  model: text-embedding-3-small
```

設定の詳細は [設定ガイド](docs/configuration.md) を参照してください。

## 使えるツール

| ツール | できること |
|---|---|
| `search_docs` | 自然言語でドキュメントを横断検索 |
| `read_doc` | 検索結果のページ全文を取得 |
| `read_sections` | 特定の見出しセクションだけを取得 |

## ドキュメント

- [インストール](docs/installation.md) — DXT / PyPI / Docker
- [設定](docs/configuration.md) — ソース登録・Embedding・スケジュール
- [使い方](docs/usage.md) — Claude Desktop / Claude Code への登録

## 開発者向け

ソースからのビルド・HTTP モード・DXT のビルド方法は [開発者向けガイド](docs/development.md) を参照してください。

## ライセンス

[BSD 3-Clause License](LICENSE)
