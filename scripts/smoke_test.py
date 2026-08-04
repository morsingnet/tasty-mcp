#!/usr/bin/env python3
"""
Standalone smoke test for the TastyTrade MCP server.

Exercises the same list_tools()/call_tool() interface that Claude Desktop
(or any MCP client) uses, so a pass here means the server is wired up
correctly end to end — not just that the HTTP client works.

Usage:
    cp .env.example .env   # fill in TASTYTRADE_USERNAME / TASTYTRADE_PASSWORD
    python scripts/smoke_test.py

Only read-only tools are exercised. Nothing here places or cancels orders.
"""

import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

load_dotenv()

from mcp_tastytrade.server import call_tool  # noqa: E402

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
SKIP = "\033[33mSKIP\033[0m"


def _first_text(result) -> str:
    return result[0].text if result else ""


def _is_error(text: str) -> bool:
    return text.startswith("Error in ")


async def run() -> bool:
    all_ok = True
    account_number = None
    symbol = None

    print("== TastyTrade MCP server smoke test ==\n")

    print("-> get_accounts")
    result = await call_tool("get_accounts", {})
    text = _first_text(result)
    if _is_error(text):
        print(f"  {FAIL}  {text}")
        all_ok = False
    else:
        accounts = json.loads(text)
        items = accounts if isinstance(accounts, list) else accounts.get("items", [])
        if not items:
            print(f"  {FAIL}  no accounts returned")
            all_ok = False
        else:
            entry = items[0].get("account", items[0])
            account_number = entry.get("account-number")
            print(f"  {PASS}  {len(items)} account(s), using {account_number}")

    if account_number:
        for tool in ("get_balances", "get_positions", "get_orders"):
            print(f"-> {tool}")
            result = await call_tool(tool, {"account_number": account_number})
            text = _first_text(result)
            if _is_error(text):
                print(f"  {FAIL}  {text}")
                all_ok = False
            else:
                print(f"  {PASS}")
    else:
        print(f"-> get_balances / get_positions / get_orders  {SKIP}  (no account number)")

    print("-> search_equities (AAPL)")
    result = await call_tool("search_equities", {"symbol": "AAPL"})
    text = _first_text(result)
    if _is_error(text):
        print(f"  {FAIL}  {text}")
        all_ok = False
    else:
        items = json.loads(text)
        items = items if isinstance(items, list) else items.get("items", [])
        if items:
            symbol = items[0].get("symbol", "AAPL")
        print(f"  {PASS}")

    print("-> get_market_metrics (AAPL, SPY)")
    result = await call_tool("get_market_metrics", {"symbols": ["AAPL", "SPY"]})
    text = _first_text(result)
    if _is_error(text):
        print(f"  {FAIL}  {text}")
        all_ok = False
    else:
        print(f"  {PASS}")

    print(f"-> get_option_chain ({symbol or 'AAPL'})")
    result = await call_tool("get_option_chain", {"symbol": symbol or "AAPL", "format": "compact"})
    text = _first_text(result)
    if _is_error(text):
        print(f"  {FAIL}  {text}")
        all_ok = False
    else:
        print(f"  {PASS}")

    print("-> get_watchlists")
    result = await call_tool("get_watchlists", {})
    text = _first_text(result)
    if _is_error(text):
        print(f"  {FAIL}  {text}")
        all_ok = False
    else:
        print(f"  {PASS}")

    print()
    print("All checks passed." if all_ok else "Some checks failed — see above.")
    return all_ok


def main() -> None:
    ok = asyncio.run(run())
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
