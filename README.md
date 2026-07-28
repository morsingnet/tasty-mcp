# mcp-tastytrade-server

An [MCP](https://modelcontextprotocol.io/) server that exposes the [TastyTrade](https://tastytrade.com) brokerage API as tools for Claude and other MCP-compatible clients.

## Features

| Tool | Description |
|---|---|
| `get_accounts` | List all accounts |
| `get_positions` | Open positions for an account |
| `get_balances` | Balances and buying power |
| `get_orders` | Orders (filterable by status) |
| `dry_run_order` | Validate an order — fees, BP impact, warnings |
| `place_order` | Place a live order |
| `cancel_order` | Cancel a live order |
| `get_option_chain` | Option chain (nested by expiry or compact flat list) |
| `get_market_metrics` | IV rank, IV percentile, 30-day IV, liquidity |
| `get_transactions` | Transaction history |
| `search_equities` | Search equity instruments by symbol |
| `get_watchlists` | Customer watchlists |

## Setup

### 1. Install dependencies

```bash
pip install -e .
# or with uv:
uv pip install -e .
```

### 2. Configure credentials

```bash
cp .env.example .env
# Edit .env with your TastyTrade username and password
```

Credentials are read **only from environment variables** — they are never stored in code:

| Variable | Required | Description |
|---|---|---|
| `TASTYTRADE_USERNAME` | Yes | Your TastyTrade login username |
| `TASTYTRADE_PASSWORD` | Yes | Your TastyTrade login password |
| `TASTYTRADE_SANDBOX` | No | Set to `true` to use the certification environment (default: `false`) |

### 3. Configure Claude Desktop

Add the following to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "tastytrade": {
      "command": "mcp-tastytrade",
      "env": {
        "TASTYTRADE_USERNAME": "your_username",
        "TASTYTRADE_PASSWORD": "your_password"
      }
    }
  }
}
```

Or using `uv run` without installing:

```json
{
  "mcpServers": {
    "tastytrade": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/mcp-tastytrade-server", "mcp-tastytrade"],
      "env": {
        "TASTYTRADE_USERNAME": "your_username",
        "TASTYTRADE_PASSWORD": "your_password"
      }
    }
  }
}
```

## Option symbol format

Options use the OCC 21-character format: `SYMBOL  YYMMDDCPRICE`

Examples:
- `AAPL  241220C00200000` — AAPL $200 call expiring 2024-12-20
- `SPY   241220P00580000` — SPY $580 put expiring 2024-12-20

The `get_option_chain` tool returns symbols already formatted correctly.

## Development

```bash
# Run directly
python -m mcp_tastytrade.server

# Or via the installed script
mcp-tastytrade
```

## Security

- Credentials are passed via environment variables only.
- The `.env` file is in `.gitignore` and must never be committed.
- Session tokens are held in memory for the lifetime of the server process and are deleted on shutdown.
- Use `TASTYTRADE_SANDBOX=true` for testing — the certification environment uses separate accounts with no real money.
