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

### 2. OAuth2 setup

This server authenticates with OAuth2 — a scoped, revocable refresh token —
instead of your TastyTrade account password. Your actual login credentials
are never entered anywhere in this project.

1. Go to [my.tastytrade.com](https://my.tastytrade.com) → **Manage → My Profile → API → OAuth Applications**.
2. Click **+ New OAuth Client**, give it any name, and set a redirect URI (e.g. `http://localhost`) — it's required but unused by the personal-grant flow below.
3. Save the app, then note the **Client Secret** shown (it's only displayed once).
4. Click **Manage** on the new app → **Create Grant** to issue yourself a **Personal Grant**. Copy the **Refresh Token** shown (also only displayed once).
5. Copy the env template and fill in those two values:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `TASTYTRADE_CLIENT_SECRET` | Yes | Client secret from the OAuth application |
| `TASTYTRADE_REFRESH_TOKEN` | Yes | Refresh token from the personal grant |
| `TASTYTRADE_SANDBOX` | No | Set to `true` to use the certification environment (default: `false`) |

The refresh token doesn't expire on its own — if you ever want to cut off
access, revoke the grant at my.tastytrade.com and generate a new one, no
password change required.

### 3. Test the connection

```bash
python scripts/smoke_test.py
```

This runs every read-only tool (`get_accounts`, `get_balances`, `get_positions`,
`get_orders`, `search_equities`, `get_market_metrics`, `get_option_chain`,
`get_watchlists`) through the same `list_tools()`/`call_tool()` interface a
real MCP client uses, and prints PASS/FAIL for each. It never places or
cancels orders. Requires `.env` to be filled in (step 2).

### 4. Configure Claude Desktop

Add the following to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "tastytrade": {
      "command": "mcp-tastytrade",
      "env": {
        "TASTYTRADE_CLIENT_SECRET": "your_client_secret",
        "TASTYTRADE_REFRESH_TOKEN": "your_refresh_token"
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
        "TASTYTRADE_CLIENT_SECRET": "your_client_secret",
        "TASTYTRADE_REFRESH_TOKEN": "your_refresh_token"
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

- Authentication uses OAuth2 (client secret + refresh token) — your TastyTrade account password is never used or stored anywhere in this project.
- Credentials are passed via environment variables only.
- The `.env` file is in `.gitignore` and must never be committed.
- Access tokens are short-lived (~15 minutes), held in memory only, and refreshed automatically.
- To revoke access at any time, delete the grant at my.tastytrade.com — no password change needed.
- Use `TASTYTRADE_SANDBOX=true` for testing — the certification environment uses separate accounts with no real money.
