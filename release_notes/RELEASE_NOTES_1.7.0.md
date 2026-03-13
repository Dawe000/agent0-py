# Release Notes — 1.7.0 (stable)

## Highlights

- **Native x402 support**: the Python SDK can now handle HTTP `402 Payment Required` responses without throwing, expose payment requirements to the caller, and retry requests after payment.
- **Native A2A support**: you can now send A2A messages, list tasks, load tasks, and work against either a loaded `Agent` or an `AgentSummary`.
- **Multichain x402 and A2A flows**: the SDK now supports default RPCs, per-chain RPC overrides, and loading agents from chains other than the SDK's primary chain.
- **Aligned with the TypeScript SDK**: the new Python APIs mirror the TypeScript rollout for x402 and A2A, with Python-specific payment helpers and examples.

## Changes in 1.7.0 (since 1.6.0)

### 1. x402 payment-required HTTP

- **New request entrypoint**
  - Added `sdk.request()` for HTTP requests with built-in x402 handling.

- **Non-throwing 402 flow**
  - On successful `2xx` responses, the SDK returns the parsed response body.
  - On HTTP `402`, the SDK now returns `X402RequiredResponse` instead of throwing.
  - This makes it easy to branch on `if result.x402Required:` and decide whether to pay, retry, or surface payment requirements to the caller.

- **Payment helpers**
  - `x402Payment.pay(accept=None)` pays with either:
    - the selected accept index,
    - a specific accept object, or
    - the default payment path when no argument is supplied.
  - `x402Payment.pay_first()` automatically selects the first accept with sufficient token balance when balance checking is available.
  - When a payment succeeds, the SDK retries the original request and resolves to the same shape as a normal successful response.

- **Pay with the initial request**
  - Request options now support optional `payment` data so callers can include payment on the first request when they already know the server's expected payment format.

- **Spec and protocol coverage**
  - Supports **x402 v1** and **x402 v2** response/payment formats.
  - Supports **EIP-3009-style TransferWithAuthorization** payload construction for EVM payments.
  - Supports **multiple payment options** (`accepts`) returned by the server.
  - Supports **multi-chain payment options** and selects the correct chain client for payment/retry.
  - Filters out **non-EVM accepts** (for example Solana options) when building the payment response, so only supported payment paths are surfaced.

### 2. A2A messaging and tasks

- **New high-level A2A methods on `Agent`**
  - Added `Agent.messageA2A()` to send a message to an A2A endpoint.
  - Added `Agent.listTasks()` to list tasks from an A2A server.
  - Added `Agent.loadTask(task_id)` to load a task by ID and return an `AgentTask` handle.

- **A2A client from search results**
  - Added `sdk.createA2AClient(agent_or_summary)`.
  - When passed a loaded `Agent`, it returns the agent as-is.
  - When passed an `AgentSummary`, it returns an `A2AClientFromSummary` wrapper that resolves the agent card lazily and exposes the same `messageA2A()`, `listTasks()`, and `loadTask()` workflow.

- **Interface and binding resolution**
  - The SDK normalizes A2A interfaces from both:
    - agent card v1 `supportedInterfaces`, and
    - older `url` plus `additionalInterfaces` shapes.
  - Binding resolution now supports:
    - `HTTP+JSON`
    - `JSON-RPC`
    - `GRPC`
    - `AUTO`
  - Preferred binding order is respected when multiple interfaces are available, with improved tie-breaking inside the same protocol version.

- **Authentication and tenancy**
  - Added support for A2A auth derived from agent-card security schemes.
  - Supports API key and HTTP auth flows.
  - Supports credential objects and first-available matching auth selection.
  - Added optional tenant handling for multi-tenant A2A endpoints.

- **402 on A2A flows**
  - `messageA2A()` and `loadTask()` can return `A2APaymentRequired` instead of throwing when the server responds with HTTP `402`.
  - `x402Payment.pay()` and `x402Payment.pay_first()` continue the flow and return the same shape as success.
  - For `loadTask()`, paying after a `402` yields an `AgentTask`, so callers can continue with `query()`, `message()`, or `cancel()` on the returned task handle.

### 3. Multichain and RPC improvements

- **Default RPC URLs**
  - The SDK now ships with built-in default RPC URLs for supported chains.
  - This reduces setup friction for read flows and multichain x402 use cases.

- **Per-chain overrides**
  - Added `overrideRpcUrls` to SDK config.
  - Override order is:
    - built-in defaults
    - `rpcUrl` for the primary chain
    - `overrideRpcUrls` for explicit per-chain overrides

- **Load agents across chains**
  - `SDK.loadAgent()` can now load agents from chains other than the SDK's primary chain, provided an RPC URL is available for the target chain.
  - This also means `loadAgent()` no longer fails just because the caller passes a cross-chain `chainId:agentId`.
  - This supports mixed-chain read flows without creating a separate SDK instance per chain.

### 4. Examples, tests, and documentation

- **New demo**
  - Added `examples/x402_a2a_demo.py`.
  - The demo covers:
    - pure x402 request + pay,
    - pure A2A message/task flows,
    - combined A2A + x402 payment-required flows.

- **Expanded automated coverage**
  - Added unit tests for:
    - x402 types
    - x402 request handling
    - x402 payment handling
    - A2A client behavior
  - Added live/public-server coverage for x402 and A2A flows.
  - Added parity updates so the Python example and docs match the shipped Python API naming and result shapes.

- **Documentation updates**
  - Public docs were expanded to cover:
    - x402 concepts and request flows,
    - A2A concepts and API usage,
    - updated Python examples,
    - API/model reference updates aligned with the shipped SDK surface.

## Migration notes

- **Handling HTTP 402**
  - If you previously expected request failures to raise immediately on payment-required responses, update callers to branch on `result.x402Required`.
  - Typical pattern:
    - call `sdk.request(...)`
    - if `result.x402Required`, inspect `result.x402Payment.accepts`
    - call `result.x402Payment.pay()` or `result.x402Payment.pay_first()`

- **Using A2A from summaries**
  - If you already have an `AgentSummary` from search or discovery, prefer `sdk.createA2AClient(summary)` instead of loading the full agent first.

- **Multichain configuration**
  - For payments or agent loads on non-primary chains, provide `overrideRpcUrls` when built-in defaults are not sufficient for your environment or throughput requirements.

## How to test

### All tests

```bash
cd agent0-py
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

### x402 and A2A unit tests only

```bash
pytest tests/test_x402_types.py tests/test_x402_request.py tests/test_x402_payment.py tests/test_a2a_client.py -v
```

### Live / integration

```bash
RUN_LIVE_TESTS=1 pytest tests/test_real_public_servers.py -v
```

### Demo

```bash
cp examples/.env.example examples/.env
python examples/x402_a2a_demo.py
```

### Debug x402 payment

```bash
X402_DEBUG=1 python examples/x402_a2a_demo.py
```
