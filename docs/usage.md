# 使い方

## 起動

```bash
# stdioモード（Claude Desktop / Claude Code連携）
uv run docs-mcp --config config.yaml

# HTTPモード（config.yaml で transport.mode: http に変更）
uv run docs-mcp --config config.yaml
```

サーバー起動時に全ソースのインジェストが自動実行され、設定したスケジュールで定期更新されます。

## Claude Desktop への登録

`claude_desktop_config.json` に追加します（場所: `~/Library/Application Support/Claude/` または `%APPDATA%\Claude\`）。

```json
{
  "mcpServers": {
    "docs-mcp": {
      "command": "uv",
      "args": [
        "run",
        "--project", "/absolute/path/to/docs-mcp",
        "docs-mcp",
        "--config", "/absolute/path/to/config.yaml"
      ],
      "env": {
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

## Claude Code（CLI）への登録

```bash
claude mcp add docs-mcp -- uv run --project /path/to/docs-mcp docs-mcp --config /path/to/config.yaml
```

