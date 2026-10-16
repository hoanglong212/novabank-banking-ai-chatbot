# Architecture and data flow

```text
React + TypeScript UI
  -> FastAPI (authenticated demo principal from bearer token)
     -> SQLite (conversation ownership, messages, tool decisions, tickets)
     -> Agent (mock or Ollama /api/chat)
        -> Proposed tool name + validated arguments
           -> ToolDispatcher -> PolicyGateway.authorize(...) -> ALLOW/DENY audit
              -> On ALLOW only: simulated tool executor
              -> Tool result to Agent -> final assistant message
```

The `mock` agent chooses actions deterministically for offline demos; **it is not a generative AI**. With `LLM_PROVIDER=ollama`, the Ollama model selects tools and sees the returned tool observations. The agent is limited to 5 chat iterations and 4 tool requests per iteration to avoid unbounded loops. Each new conversation sends up to the last 24 user/assistant messages as model context while full history remains in SQLite.

A dedicated `PolicyGateway` class decides, but does not execute tools. Local mode performs allowlist, schema, and ownership checks. Remote mode performs the same local checks and then sends an adapter request to a hypothetical `/authorize` endpoint; it FAILS CLOSED if remote gateway fails. The proposed API contract is NOT guaranteed to match Group 10's actual runtime security gateway.

Audit records ALLOW and DENY and whether execution happened. `demo/tool-check` evaluates policy but never executes, even for ALLOW. Frontend displays the latest events to help demonstrate decisions. No payment API, real customer records, real OTP, credential-handling or bank integration are implemented.
