import asyncio
import json
from typing import Any, Optional

from dotenv import load_dotenv
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from .client import TastyTradeClient

load_dotenv()

app = Server("tastytrade")
_client: Optional[TastyTradeClient] = None


def _get_client() -> TastyTradeClient:
    global _client
    if _client is None:
        _client = TastyTradeClient()
    return _client


def _ok(data: Any) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=json.dumps(data, indent=2))]


def _err(tool: str, exc: Exception) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=f"Error in {tool}: {type(exc).__name__}: {exc}")]


def _build_order_body(args: dict) -> dict:
    body: dict = {
        "order-type": args["order_type"],
        "time-in-force": args["time_in_force"],
        "price-effect": args["price_effect"],
        "legs": [
            {
                "instrument-type": leg["instrument_type"],
                "symbol": leg["symbol"],
                "quantity": leg["quantity"],
                "action": leg["action"],
            }
            for leg in args["legs"]
        ],
    }
    if "price" in args:
        body["price"] = args["price"]
    return body


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_accounts",
            description="List all TastyTrade accounts for the authenticated customer.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="get_positions",
            description="Get current open positions for a TastyTrade account.",
            inputSchema={
                "type": "object",
                "properties": {
                    "account_number": {"type": "string", "description": "Account number (e.g. 5WX12345)"},
                },
                "required": ["account_number"],
            },
        ),
        types.Tool(
            name="get_balances",
            description="Get current balances and buying power for a TastyTrade account.",
            inputSchema={
                "type": "object",
                "properties": {
                    "account_number": {"type": "string"},
                },
                "required": ["account_number"],
            },
        ),
        types.Tool(
            name="get_orders",
            description="Get orders for a TastyTrade account, optionally filtered by status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "account_number": {"type": "string"},
                    "status": {
                        "type": "string",
                        "description": "Filter by order status",
                        "enum": ["Live", "Received", "Cancelled", "Filled", "Expired", "Rejected", "Contingent", "Routed"],
                    },
                },
                "required": ["account_number"],
            },
        ),
        types.Tool(
            name="place_order",
            description=(
                "Place a new order on a TastyTrade account. "
                "Use dry_run_order first to validate the order and check buying power impact."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "account_number": {"type": "string"},
                    "order_type": {
                        "type": "string",
                        "enum": ["Limit", "Market", "Stop", "Stop Limit", "Notional Market"],
                    },
                    "time_in_force": {
                        "type": "string",
                        "enum": ["Day", "GTC", "GTD", "Ext", "GTC Ext", "IOC"],
                    },
                    "price": {
                        "type": "string",
                        "description": "Limit price as a string (e.g. '1.50'). Required for Limit orders.",
                    },
                    "price_effect": {
                        "type": "string",
                        "description": "Debit = you pay; Credit = you receive.",
                        "enum": ["Debit", "Credit"],
                    },
                    "legs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "instrument_type": {
                                    "type": "string",
                                    "enum": ["Equity", "Equity Option", "Future", "Future Option"],
                                },
                                "symbol": {
                                    "type": "string",
                                    "description": (
                                        "For equities: 'AAPL'. "
                                        "For options use OCC format: 'AAPL  241220C00200000'."
                                    ),
                                },
                                "quantity": {"type": "integer"},
                                "action": {
                                    "type": "string",
                                    "enum": ["Buy to Open", "Buy to Close", "Sell to Open", "Sell to Close"],
                                },
                            },
                            "required": ["instrument_type", "symbol", "quantity", "action"],
                        },
                    },
                },
                "required": ["account_number", "order_type", "time_in_force", "price_effect", "legs"],
            },
        ),
        types.Tool(
            name="dry_run_order",
            description=(
                "Validate an order without placing it. "
                "Returns buying power effect, fees, and any warnings."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "account_number": {"type": "string"},
                    "order_type": {
                        "type": "string",
                        "enum": ["Limit", "Market", "Stop", "Stop Limit", "Notional Market"],
                    },
                    "time_in_force": {
                        "type": "string",
                        "enum": ["Day", "GTC", "GTD", "Ext", "GTC Ext", "IOC"],
                    },
                    "price": {"type": "string"},
                    "price_effect": {"type": "string", "enum": ["Debit", "Credit"]},
                    "legs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "instrument_type": {"type": "string"},
                                "symbol": {"type": "string"},
                                "quantity": {"type": "integer"},
                                "action": {"type": "string"},
                            },
                            "required": ["instrument_type", "symbol", "quantity", "action"],
                        },
                    },
                },
                "required": ["account_number", "order_type", "time_in_force", "price_effect", "legs"],
            },
        ),
        types.Tool(
            name="cancel_order",
            description="Cancel a live order on a TastyTrade account.",
            inputSchema={
                "type": "object",
                "properties": {
                    "account_number": {"type": "string"},
                    "order_id": {"type": "integer", "description": "The numeric order ID to cancel"},
                },
                "required": ["account_number", "order_id"],
            },
        ),
        types.Tool(
            name="get_option_chain",
            description=(
                "Get the option chain for an underlying symbol. "
                "Use format='nested' (default) for expirations grouped by date, "
                "or format='compact' for a flat list."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Underlying symbol, e.g. 'AAPL'"},
                    "format": {
                        "type": "string",
                        "enum": ["nested", "compact"],
                        "default": "nested",
                    },
                },
                "required": ["symbol"],
            },
        ),
        types.Tool(
            name="get_market_metrics",
            description=(
                "Get market metrics for one or more symbols: "
                "IV rank, IV percentile, 30-day IV, liquidity rating, and more."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "symbols": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Underlying symbols, e.g. ['AAPL', 'SPY', 'QQQ']",
                    },
                },
                "required": ["symbols"],
            },
        ),
        types.Tool(
            name="get_transactions",
            description="Get transaction history for a TastyTrade account.",
            inputSchema={
                "type": "object",
                "properties": {
                    "account_number": {"type": "string"},
                    "start_date": {"type": "string", "description": "Start date YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "End date YYYY-MM-DD"},
                    "per_page": {
                        "type": "integer",
                        "description": "Results per page (max 250, default 50)",
                        "default": 50,
                    },
                },
                "required": ["account_number"],
            },
        ),
        types.Tool(
            name="search_equities",
            description="Search for equity instruments by symbol.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Symbol or partial symbol to search"},
                    "lendability": {
                        "type": "string",
                        "description": "Filter by short-sell lendability",
                        "enum": ["Easy To Borrow", "Locate Required", "Preborrow Required"],
                    },
                },
                "required": ["symbol"],
            },
        ),
        types.Tool(
            name="get_watchlists",
            description="Get all watchlists for the authenticated customer.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    client = _get_client()

    try:
        if name == "get_accounts":
            data = await client.get("/customers/me/accounts")
            return _ok(data.get("data", data))

        elif name == "get_positions":
            acct = arguments["account_number"]
            data = await client.get(f"/accounts/{acct}/positions")
            return _ok(data.get("data", data))

        elif name == "get_balances":
            acct = arguments["account_number"]
            data = await client.get(f"/accounts/{acct}/balances")
            return _ok(data.get("data", data))

        elif name == "get_orders":
            acct = arguments["account_number"]
            params: dict = {}
            if "status" in arguments:
                params["status[]"] = arguments["status"]
            data = await client.get(f"/accounts/{acct}/orders", params=params or None)
            return _ok(data.get("data", data))

        elif name == "place_order":
            acct = arguments["account_number"]
            body = _build_order_body(arguments)
            data = await client.post(f"/accounts/{acct}/orders", body=body)
            return _ok(data.get("data", data))

        elif name == "dry_run_order":
            acct = arguments["account_number"]
            body = _build_order_body(arguments)
            data = await client.post(f"/accounts/{acct}/orders/dry-run", body=body)
            return _ok(data.get("data", data))

        elif name == "cancel_order":
            acct = arguments["account_number"]
            order_id = arguments["order_id"]
            data = await client.delete(f"/accounts/{acct}/orders/{order_id}")
            return _ok(data.get("data", data))

        elif name == "get_option_chain":
            symbol = arguments["symbol"]
            fmt = arguments.get("format", "nested")
            data = await client.get(f"/option-chains/{symbol}/{fmt}")
            return _ok(data.get("data", data))

        elif name == "get_market_metrics":
            data = await client.get(
                "/market-metrics",
                params={"symbols": ",".join(arguments["symbols"])},
            )
            return _ok(data.get("data", data))

        elif name == "get_transactions":
            acct = arguments["account_number"]
            params = {}
            if "start_date" in arguments:
                params["start-date"] = arguments["start_date"]
            if "end_date" in arguments:
                params["end-date"] = arguments["end_date"]
            params["per-page"] = arguments.get("per_page", 50)
            data = await client.get(f"/accounts/{acct}/transactions", params=params)
            return _ok(data.get("data", data))

        elif name == "search_equities":
            params = {"symbol[]": arguments["symbol"]}
            if "lendability" in arguments:
                params["lendability"] = arguments["lendability"]
            data = await client.get("/instruments/equities", params=params)
            return _ok(data.get("data", data))

        elif name == "get_watchlists":
            data = await client.get("/watchlists")
            return _ok(data.get("data", data))

        else:
            return _err(name, ValueError(f"Unknown tool: {name}"))

    except Exception as exc:
        return _err(name, exc)


def main() -> None:
    async def _run() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())

    asyncio.run(_run())


if __name__ == "__main__":
    main()
