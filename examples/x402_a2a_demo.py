#!/usr/bin/env python3
"""
x402 and A2A demo: three flows.

1. Pure x402: GET a paid resource with sdk.request() and optional pay.
2. Pure A2A: message, task ops, list_tasks, load_task via sdk.createA2AClient(agent_or_summary).
3. A2A + 402: same as (2) when the A2A server returns 402; pay then continue.

Uses env: PRIVATE_KEY, RPC_URL, (optional) BASE_MAINNET_RPC_URL, (optional) OVERRIDE_RPC_URLS (JSON map).
Run: python examples/x402_a2a_demo.py
"""

import os
import json
import sys

# Add project root for imports when run as script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent0_sdk import SDK
from agent0_sdk.core.models import AgentSummary


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def main() -> None:
    private_key = _env("PRIVATE_KEY")
    rpc_url = _env("RPC_URL")
    if not private_key or not rpc_url:
        print("Set PRIVATE_KEY and RPC_URL to run this demo.")
        print("Optional: BASE_MAINNET_RPC_URL, OVERRIDE_RPC_URLS (JSON e.g. {\"1\": \"https://...\"})")
        return

    override_rpc = {}
    if _env("OVERRIDE_RPC_URLS"):
        try:
            override_rpc = json.loads(_env("OVERRIDE_RPC_URLS"))
        except json.JSONDecodeError:
            pass
    if _env("BASE_MAINNET_RPC_URL"):
        override_rpc.setdefault(1, _env("BASE_MAINNET_RPC_URL"))

    sdk = SDK(
        chainId=11155111,
        rpcUrl=rpc_url,
        signer=private_key,
        overrideRpcUrls=override_rpc if override_rpc else None,
    )

    # --- Flow 1: Pure x402 GET ---
    print("Flow 1: x402 request")
    try:
        result = sdk.request({
            "url": os.environ.get("X402_DEMO_URL", "https://httpbin.org/get"),
            "method": "GET",
            "headers": {},
        })
        print("  Result (2xx):", type(result).__name__, "keys" if isinstance(result, dict) else str(result)[:80])
        if getattr(result, "x402Required", False):
            print("  402: pay options available:", result.x402Payment and len(result.x402Payment.accepts))
    except Exception as e:
        print("  Error:", e)

    # --- Flow 2 & 3: A2A client from summary ---
    a2a_url = _env("A2A_DEMO_URL")
    if not a2a_url:
        print("Flow 2/3: Set A2A_DEMO_URL to an A2A endpoint URL to run message/list/load_task.")
        return

    summary = AgentSummary(
        chainId=sdk.chainId,
        agentId="0",
        name="Demo Agent",
        image=None,
        description="Demo",
        owners=[],
        operators=[],
        ens=None,
        did=None,
        walletAddress=None,
        supportedTrusts=[],
        a2aSkills=[],
        mcpTools=[],
        mcpPrompts=[],
        mcpResources=[],
        active=True,
        a2a=a2a_url,
    )
    client = sdk.createA2AClient(summary)
    print("Flow 2/3: A2A client created for", a2a_url)

    try:
        out = client.messageA2A("Hello")
        if getattr(out, "x402Required", False):
            print("  402: payment required; use out.x402Payment.pay() then retry.")
        else:
            print("  messageA2A result:", type(out).__name__)
    except Exception as e:
        print("  messageA2A error:", e)

    try:
        tasks = client.listTasks()
        if getattr(tasks, "x402Required", False):
            print("  listTasks: 402 payment required")
        else:
            print("  listTasks: count =", len(tasks) if isinstance(tasks, list) else "?")
    except Exception as e:
        print("  listTasks error:", e)

    print("Done.")


if __name__ == "__main__":
    main()
