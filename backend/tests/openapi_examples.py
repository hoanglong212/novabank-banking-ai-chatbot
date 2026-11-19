"""Successful requests for operation-contract tests on an isolated SQLite database."""

import json
import re
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
from starlette.routing import compile_path

from app import knowledge, routes_research, vietqr
from app.database import now
from app.dependencies import get_db
from app.identity import digest
from app.main import app as bank
from agent_service import main as agent
from tests.acceptance_helpers import login
from tests.conftest import TokenClient
from tests.stepup_helpers import fixed_known_payees
from tests.test_identity import NEW_PASSWORD, register, request_reset, reset, token
from tests.test_week8_api_matrix import prepare_owned_resources


def exercise(bank_client, agent_client, monkeypatch, directory, operations):
    samples = {}
    statuses = {}
    patterns = {key: compile_path(key[2])[0] for key in operations}
    for service, client in [("Bank", bank_client), ("Agent", agent_client)]:

        def record(request, *, original_send=client.send, name=service, **kwargs):
            response = original_send(request, **kwargs)
            for key, pattern in patterns.items():
                if key[:2] == (name, request.method) and pattern.fullmatch(request.url.path):
                    statuses[key] = response.status_code
                    if response.is_success:
                        response.read()
                        samples.setdefault(key, []).append(response)
                    break
            return response

        monkeypatch.setattr(client, "send", record)
    with get_db().connect() as conn:
        fixed_known_payees(conn)
    data = prepare_owned_resources(bank_client, monkeypatch)
    roles = {r: login(bank_client, r) for r in ("admin", "operations", "support", "auditor")}
    roles["customer"] = data["alice"]
    alice, admin = data["alice"], roles["admin"]

    def call(method, path, *, who=alice, body=None, **kwargs):
        return bank_client.request(method, path, headers=who, json=body, **kwargs)

    # Email identity lifecycle, confined to the new fixture account.
    register(bank_client)
    call("POST", "/api/auth/resend-verification", body={"email": "dana@example.test"})
    call("POST", "/api/auth/verify-email", body={"token": token("VERIFY_EMAIL")})
    reset(bank_client, request_reset(bank_client), NEW_PASSWORD)
    me = call("POST", "/api/auth/login", body={"username": "dana", "password": NEW_PASSWORD}).json()
    ch = me["challenge_id"]
    # A resend interval is part of the contract. Age only this fixture's last-sent timestamp.
    with get_db().connect() as conn:
        conn.execute("UPDATE mfa_challenges SET sent_at=sent_at-61 WHERE id=?", (digest(ch),))
    call("POST", "/api/auth/mfa/email", body={"challenge_id": ch})
    mail = call("POST", "/api/dev/outbox/challenge", body={"challenge_id": ch}).json()
    session = call("POST", "/api/auth/mfa/verify", body={"challenge_id": ch, "code": mail["code"]}).json()
    more = call("POST", "/api/auth/refresh", body={"refresh_token": session["refresh_token"]}).json()
    dana = {"Authorization": "Bearer " + more["access_token"]}
    call("POST", "/api/auth/activity", who=dana)
    sessions = call("GET", "/api/auth/sessions", who=data["bob"]).json()["items"]
    call("DELETE", "/api/auth/sessions/" + next(x["id"] for x in sessions if x["current"]), who=data["bob"])
    change = call(
        "POST",
        "/api/customer/profile/change",
        who=dana,
        body={"field": "email", "value": "dana-contract@example.test", "password": NEW_PASSWORD},
    ).json()
    with get_db().connect() as conn:
        secret = conn.execute(
            "SELECT secret_text FROM dev_outbox WHERE challenge_id=? ORDER BY rowid DESC LIMIT 1",
            (digest(change["challenge_id"]),),
        ).fetchone()
    call(
        "POST",
        "/api/actions/confirm",
        who={**dana, "Idempotency-Key": "contract-profile-confirm"},
        body={"challenge_id": change["challenge_id"], "code": secret[0]},
    )
    call("POST", "/api/auth/logout", who=dana)

    # Benign deterministic embeddings and bank directory. Test request parsing and response serialization.
    async def embed(texts):
        return "contract-fixture", [[1.0, 0.0] for _ in texts]

    async def directory_rows():
        return vietqr.DEMO_BANKS

    monkeypatch.setattr(knowledge, "embed", embed)
    monkeypatch.setattr(vietqr, "banks", directory_rows)
    new_doc = bank_client.post(
        "/api/documents",
        headers=alice,
        files={"file": ("schedule.txt", b"The library opens on Tuesday.", "text/plain")},
    ).json()
    data["document_id"] = new_doc["id"]
    call("GET", "/api/documents/" + new_doc["id"])
    article = {
        "title": "Library hours",
        "content": "The library opens on Tuesday.",
        "source": "demo",
        "trust_level": "approved",
        "status": "PUBLISHED",
    }
    article_id = call("POST", "/api/admin/knowledge", who=admin, body=article).json()["id"]
    call("PUT", "/api/admin/knowledge/" + article_id, who=admin, body=article)
    call("POST", "/api/admin/knowledge-index", who=admin)
    call("GET", "/api/knowledge/" + article_id)
    call("GET", "/api/knowledge/search", params={"q": "library"})
    qr = call(
        "POST", "/api/vietqr", body={"bank": "NovaBank", "account_no": "ACC-ALICE-001", "amount_vnd": 5000}
    ).json()
    call("POST", "/api/qr/decode", body={"payload": qr["payload"]})
    for path, body in [
        ("/api/admin/accounts/ACC-CHARLIE-001", {"status": "ACTIVE", "reason": "Contract check"}),
        ("/api/admin/users/charlie", {"kyc_status": "VERIFIED", "reason": "Contract check"}),
        ("/api/admin/settings", {"transfer_fee_vnd": 0}),
    ]:
        call("PATCH", path, who=admin, body={k: v for k, v in body.items() if k != "reason"})
    call("PUT", "/api/admin/agent-gateway", who=admin, body={"config": "D"})
    call("POST", "/api/admin/reconcile", who=admin)
    call("PATCH", "/api/customer/accounts/ACC-ALICE-001", body={"nickname": "My account"})
    beneficiary = "/api/customer/beneficiaries/" + data["beneficiary_id"]
    call("PATCH", beneficiary, body={"nickname": "Bob"})
    call("POST", "/api/customer/beneficiaries/lookup", body={"account_id": "ACC-BOB-001", "bank": "NovaBank"})
    call(
        "PUT", "/api/customer/notification-preferences", body={"bill_reminders": True, "budget_alerts": False}
    )
    call("PATCH", "/api/notifications/" + data["notification_id"] + "/read")
    call("POST", "/api/notifications/read-all")
    call(
        "PUT",
        "/api/savings-goals/" + data["goal_id"],
        body={"label": "Holiday", "target_vnd": 150000, "target_date": "2035-02-01"},
    )
    call("PUT", "/api/insights/budgets", body={"month": "2026-11", "category": "other", "amount_vnd": 5000})
    call("PATCH", "/api/bills/" + data["bill_id"] + "/saved", params={"saved": "true"})
    call("PATCH", "/api/transactions/" + data["transaction_id"] + "/category", params={"category": "other"})
    ticket = "/api/support/tickets/" + data["ticket_id"]
    call("POST", ticket + "/messages", body={"body": "Thank you for the update."})
    call("PATCH", ticket, who=roles["support"], body={"assigned_to": "support", "status": "OPEN"})
    # Seed a neutral, already-isolated resource to exercise the staff release endpoint.
    with get_db().connect() as conn:
        conn.execute(
            "INSERT INTO quarantined_sources (source_id,owner_id,reason,rule_id,created_at) VALUES (?,?,?,?,?)",
            ("contract-note", "alice", "fixture", "fixture", now()),
        )
    call(
        "POST",
        "/api/agent/quarantine/contract-note/release",
        who=admin,
        body={"reason": "Reviewed fixture note"},
    )

    query = {"conversation_id": data["cid"]}
    call("GET", "/api/agent/runs", params=query)
    call("GET", "/api/agent/approvals", params=query)
    call("GET", "/api/agent/approvals/" + data["approval_id"])
    call("POST", "/api/agent/approvals/" + data["approval_id"], body={"approve": False})
    call("GET", "/api/agent/context", who=data["delegated"])
    call("POST", "/api/agent/preview", who=data["delegated"], body={"answer": "Thanks."})
    call("POST", "/api/agent/finish", who=data["delegated"], body={"answer": "Thanks.", "latency_ms": 1})
    granted = call(
        "POST", "/api/agent/runs", body={"conversation_id": data["cid"], "content": "What is my balance?"}
    ).json()
    call("POST", "/api/agent/runs/" + granted["run_id"] + "/cancel")
    cid = call("POST", "/api/conversations", body={"title": "API contract"}).json()["id"]
    call("POST", f"/api/conversations/{cid}/messages", body={"content": "What is my balance?"})
    call(
        "POST",
        f"/api/conversations/{cid}/demo/tool-check",
        body={"tool_name": "get_account_balance", "arguments": {}},
    )

    # In-process cross-service HTTP using the same bank authorization code; no external model or service.
    original_client = httpx.AsyncClient

    def local_client(*args, **kwargs):
        kwargs["transport"] = httpx.ASGITransport(app=bank)
        return original_client(*args, **kwargs)

    with monkeypatch.context() as local:
        local.setattr(
            agent,
            "httpx",
            SimpleNamespace(
                AsyncClient=local_client,
                HTTPError=httpx.HTTPError,
                Timeout=httpx.Timeout,
                TimeoutException=httpx.TimeoutException,
            ),
        )
        newgrant = call(
            "POST", "/api/agent/runs", body={"conversation_id": cid, "content": "What is my balance?"}
        ).json()
        agent_client.post("/run", headers={"Authorization": "Bearer " + newgrant["delegated_token"]})
    from app.faq import FAQ

    # A bank-owned exact FAQ avoids external transport and still returns a complete SSE frame.
    call("POST", f"/api/conversations/{cid}/stream", body={"content": FAQ[0][1]})
    agent_client.get("/health")

    reports = directory / "reports"
    sample = reports / "run-20261119-000000-aaaaaa"
    sample.mkdir(parents=True)
    (sample / "summary.json").write_text(json.dumps({"status": "COMPLETED"}), encoding="utf-8")
    (sample / "metrics.csv").write_text("metric,value\ncount,1\n", encoding="utf-8")
    monkeypatch.setattr(routes_research, "REPORTS", reports)
    with monkeypatch.context() as local:
        # Verify the HTTP scheduler accepts the fixture; never start research jobs from contract tests.
        local.setattr(
            routes_research,
            "subprocess",
            SimpleNamespace(Popen=Mock(return_value=Mock()), STDOUT=-2, DEVNULL=-3, CREATE_NO_WINDOW=0),
        )
        local.setattr(routes_research, "_process", None)
        call("POST", "/api/research/runs", who=admin, body={"models": ["qwen2.5:7b"], "repetitions": 1})
    selectors = {
        **data,
        "conversation_id": data["cid"],
        "kind": "cards",
        "fmt": "csv",
        "user_id": "alice",
        "account_id": "ACC-ALICE-001",
        "filename": "metrics.csv",
        "source_id": "contract-note",
    }
    for key in operations:
        name, method, path = key
        if name != "Bank" or method != "GET" or key in samples:
            continue
        replace = {**selectors}
        if path.startswith("/api/research/"):
            replace["run_id"] = sample.name
        concrete = re.sub(r"\{(\w+)\}", lambda m: str(replace[m[1]]), path)
        params = {
            "/api/insights": {"month": "2026-11"},
            "/api/statements.{fmt}": {"from_date": "2026-11-01", "to_date": "2026-11-30"},
        }.get(path, {})
        who = admin if path.startswith(("/api/admin/", "/api/research/", "/api/agent/quarantine")) else alice
        call(method, concrete, who=who, params=params)
    call("GET", "/api/statements.pdf", params={"from_date": "2026-11-01", "to_date": "2026-11-30"})
    call("GET", "/api/research/runs/" + sample.name + "/export/summary.json", who=admin)
    call("DELETE", beneficiary)
    call("DELETE", "/api/savings-goals/" + data["goal_id"])
    call("DELETE", "/api/documents/" + new_doc["id"])
    call("DELETE", "/api/conversations/" + cid)
    disable = call("POST", "/api/auth/mfa/disable-request", body={"password": "Alice@2026"}).json()
    with get_db().connect() as conn:
        email = conn.execute(
            "SELECT secret_text FROM dev_outbox WHERE challenge_id=?", (digest(disable["challenge_id"]),)
        ).fetchone()[0]
    call("POST", "/api/auth/mfa/disable", body={"challenge_id": disable["challenge_id"], "code": email})
    fresh = call(
        "POST", "/api/agent/runs", body={"conversation_id": data["cid"], "content": "What is my balance?"}
    ).json()
    data["validation_delegation"] = {"Authorization": "Bearer " + fresh["delegated_token"]}
    return {k: list(v) for k, v in samples.items()}, dict(statuses), roles, data
