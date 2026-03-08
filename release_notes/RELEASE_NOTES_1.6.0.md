# Release Notes — 1.6.0 (stable)

## Highlights

- **FeedbackFile schema aligned with deployed subgraph**: feedback file fields now match the current subgraph `FeedbackFile` entity.
- **Legacy feedback fields removed**: legacy keys are no longer accepted or mapped by the SDK.
- **Note (TypeScript parity)**: the TypeScript SDK added an embedded Helia IPFS option (`ipfs: 'helia'`) and updated its Kubo-daemon client. The Python SDK’s `ipfs="node"` backend continues to connect via `ipfshttpclient`.
- **Fully on-chain registration files (ERC-8004 data URIs)**: the SDK now supports `agentURI`/`tokenURI` as `data:application/json;base64,...` for fully on-chain registration metadata.

## Changes in 1.6.0 (since 1.5.3)

- **On-chain registration file support (`data:` URI)**
  - **Read**: `SDK.loadAgent()` now supports `agentURI`/`tokenURI` values like `data:application/json;base64,...` (tolerant of optional params such as `;charset=utf-8`).
  - **Write**: new `Agent.registerOnChain()` publishes the registration file fully on-chain by encoding it into a `data:` URI and calling `register(...)` / `setAgentURI(...)`.
  - **Safety**: `registrationDataUriMaxBytes` limits decoded `data:` URI size (default **256 KiB**).
  - **Backwards compatible**: `registerIPFS()` and `register()` (HTTP/IPFS URIs) are unchanged.

- **Spec-aligned feedback fields only**
  - `Feedback` now includes (when built from subgraph feedback files):
    - `mcpTool`, `mcpPrompt`, `mcpResource`
    - `a2aSkills`, `a2aContextId`, `a2aTaskId`
    - `oasfSkills`, `oasfDomains`
  - Removed legacy fields:
    - `capability`, `name`, `skill`, `task`, `context`

- **`giveFeedback(...)` no longer accepts legacy keys**
  - Only spec fields are read from the feedback payload.

- **Subgraph selection and parsing updated**
  - Subgraph queries select the spec-aligned `FeedbackFile` fields.
  - Feedback mapping/parsing uses these fields (list-normalized for `a2aSkills`, `oasfSkills`, `oasfDomains`).

- **`getReputationSummary` subgraph path fixed**
  - Uses direct subgraph pagination for reputation summaries (avoids passing `first/skip` through `searchFeedback` in a way that could raise errors).

## Migration notes

- If you previously wrote feedback files like:
  - `capability: "tools"`, `name: "foo"`, `skill: "python"`, `task: "bar"`, `context: {...}`
  - Update to:
    - `mcpTool: "foo"` (or `mcpPrompt` / `mcpResource`)
    - `a2aSkills: ["python"]`
    - `a2aTaskId: "bar"` (if applicable)
    - `a2aContextId: "..."` (if applicable)

