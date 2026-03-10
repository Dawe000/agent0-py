#!/usr/bin/env python3
"""
x402 and A2A demo: three flows.

1. Pure x402: GET a paid resource with sdk.request() and optional pay.
2. Pure A2A: message, task ops, list_tasks, load_task via sdk.createA2AClient(agent_or_summary).
3. A2A + 402: same as (2) when the A2A server returns 402; pay then continue.

Loads env from .env (examples/.env or project root .env). Set PRIVATE_KEY, RPC_URL.
Optional: CHAIN_ID (default 84532), AGENT_ID_PURE_A2A (default 84532:1298),
AGENT_ID_A2A_X402 (default 84532:1301), BASE_MAINNET_RPC_URL, X402_DEMO_URL.
Run: python examples/x402_a2a_demo.py
"""

import os
import json
import sys
from pathlib import Path

# Add project root for imports when run as script
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

# Load .env from examples/ or project root (requires python-dotenv)
try:
    from dotenv import load_dotenv
    _env_file = Path(__file__).resolve().parent / ".env"
    if not _env_file.exists():
        _env_file = _root / ".env"
    load_dotenv(dotenv_path=_env_file)
except ImportError:
    pass  # run without .env; use exported env vars only

from agent0_sdk import SDK


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

    chain_id = int(_env("CHAIN_ID", "84532"))
    sdk = SDK(
        chainId=chain_id,
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

    # --- Flow 2: Pure A2A (load agent by ID, same as TS: 84532:1298) ---
    agent_id_pure = _env("AGENT_ID_PURE_A2A", "84532:1298")
    print("\n--- 2. Pure A2A ---")
    try:
        agent = sdk.loadAgent(agent_id_pure)
        client = sdk.createA2AClient(agent)
        out = client.messageA2A("Hello, this is a demo message.")
        print("  messageA2A:", type(out).__name__)
        if getattr(out, "x402Required", False):
            print("  402: payment required; use out.x402Payment.pay() then retry.")
        elif hasattr(out, "task") and out.task:
            task = out.task
            print("  task.query():", type(task.query()).__name__)
            task.message("Follow-up message.")
            print("  task.cancel(): ok")
        tasks = client.listTasks()
        if getattr(tasks, "x402Required", False):
            print("  listTasks: 402 payment required")
        else:
            print("  listTasks: count =", len(tasks) if isinstance(tasks, list) else 0)
            if isinstance(tasks, list) and tasks:
                loaded = client.loadTask(tasks[0].taskId)
                if not getattr(loaded, "x402Required", False):
                    print("  loadTask + query(): ok")
    except Exception as e:
        print("  Error:", e)

    # --- Flow 3: A2A with x402 (agent 84532:1301 returns 402; pay then get response) ---
    agent_id_x402 = _env("AGENT_ID_A2A_X402", "84532:1301")
    print("\n--- 3. A2A with x402 ---")
    try:
        agent = sdk.loadAgent(agent_id_x402)
        client = sdk.createA2AClient(agent)
        result = client.messageA2A("Hello, please charge me once.")
        if getattr(result, "x402Required", False):
            paid = result.x402Payment.pay()
            print("  Paid; result:", type(paid).__name__)
        else:
            print("  messageA2A:", type(result).__name__)
    except Exception as e:
        print("  Error:", e)

    print("\nDone.")


if __name__ == "__main__":
    main()
