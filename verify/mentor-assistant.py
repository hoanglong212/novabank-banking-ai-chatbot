"""Normal authenticated UI/API flows, using a fresh copy of a synthetic seed only."""
import argparse
import base64
from contextlib import ExitStack, closing
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import re
import secrets
import socket
import sqlite3
import statistics
import struct
import subprocess
import sys
import tempfile
import time
import uuid

import httpx


from positives import READ_QUESTIONS
from positives2 import ACTION_QUESTIONS

PROMPTS = {**READ_QUESTIONS, **ACTION_QUESTIONS}


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def totp(secret):
    key = base64.b32decode(secret + "=" * (-len(secret) % 8))
    d = hmac.new(key, struct.pack(">Q", int(time.time()) // 30), hashlib.sha1).digest()
    value = struct.unpack(">I", d[d[-1] & 15:(d[-1] & 15) + 4])[0] & 0x7fffffff
    return f"{value % 1_000_000:06d}"


def history_matches(rows, answer):
    # A response may legitimately omit identifiers. Match every date and VND value
    # in order, including repeated date/amount pairs, or five explicitly identified rows.
    normalized = re.sub(r"(?<=\d)[ ,\.](?=\d)", "", answer)
    amounts = [int(value) for value in re.findall(r"(\d+)\s*(?:VND|₫)", normalized, re.I)]
    dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", answer)
    indices = [answer.find(row[0]) for row in rows]
    return (len(rows) == 5 and amounts == [r[1] for r in rows]
            and (dates == [r[3] for r in rows] or min(indices) >= 0 and indices == sorted(indices)))


class App:
    def __init__(self, cli, conn):
        self.cli, self.conn = cli, conn
        self.statuses = []

    def api(self, verb, path, **kwargs):
        response = self.cli.request(verb, "/api" + path, **kwargs)
        self.statuses.append([verb, path.split("?")[0], response.status_code])
        response.raise_for_status()
        return response.json()

    def login(self):
        first = self.api("POST", "/auth/login", json={"username": "alice", "password": "Alice@2026"})
        challenge = {"challenge_id": first["challenge_id"]}
        otp = self.api("POST", "/dev/outbox/challenge", json=challenge)["code"]
        auth = self.api("POST", "/auth/mfa/verify", json={**challenge, "code": otp})
        self.cli.headers["Authorization"] = "Bearer " + auth["access_token"]
        self.refresh_token = auth["refresh_token"]

    def refresh(self):
        auth = self.api("POST", "/auth/refresh", json={"refresh_token": self.refresh_token})
        self.cli.headers["Authorization"] = "Bearer " + auth["access_token"]
        self.refresh_token = auth["refresh_token"]

    def stream(self, cid, text):
        with self.cli.stream("POST", "/api/conversations/" + cid + "/stream", json={"content": text}) as r:
            self.statuses.append(["POST", "/conversations/{id}/stream", r.status_code])
            r.raise_for_status()
            events = {}
            name = None
            for line in r.iter_lines():
                if line.startswith("event: "):
                    name = line[7:]
                elif line.startswith("data: ") and name:
                    events[name] = json.loads(line[6:])
        if "error" in events or "complete" not in events:
            raise RuntimeError("Incomplete stream: " + ",".join(events))
        answer = events["complete"]["message"]["content"]
        row = self.conn.execute("select content from messages where conversation_id=? and role='assistant' order by rowid desc limit 1", (cid,)).fetchone()
        return answer, row is not None and row[0] == answer, events

    def balances(self):
        return dict(self.conn.execute("select id,balance_vnd from accounts where id in ('ACC-ALICE-001','ACC-BOB-001')"))

    def transfer(self, cid, item, pin, secret):
        req = self.api("GET", "/agent/approvals", params={"conversation_id": cid})["items"]
        pending = [x for x in req if x["status"] == "PENDING" and x["name"] == "prepare_transfer"]
        item["pending_proposals"] = len(pending)
        if len(pending) != 1:
            return False
        approved = self.api("POST", "/agent/approvals/" + pending[0]["id"], json={"approve": True})
        if not approved.get("draft_id"):
            return False
        tid = approved["draft_id"]
        path = "/transfers/" + tid
        draft = self.api("GET", path)
        row = self.conn.execute("select status,owner_id,from_account,to_account,amount_vnd from transfers where id=?", (tid,)).fetchone()
        item["draft"] = list(row) if row else None
        if tuple(row or ()) != ("PENDING_OTP", "alice", "ACC-ALICE-001", "ACC-BOB-001", 100000):
            return False
        before = self.balances()
        tx_before = self.conn.execute("select count(*) from transactions").fetchone()[0]
        step = self.api("GET", path + "/step-up")
        if step["required"]:
            self.api("POST", path + "/step-up", json={"code": totp(secret)})
        draft = self.api("POST", path + "/otp")
        method = draft.get("otp_method")
        item["confirmation_method"] = method
        if method == "pin":
            code = pin
        elif method == "email":
            inbox = self.api("GET", "/dev/outbox")["items"]
            message = next(m for m in inbox if m["kind"] == "TRANSFER_OTP")
            code = self.api("GET", "/dev/outbox/" + str(message["id"]))["code"]
        elif method == "totp":
            time.sleep(31)
            code = totp(secret)
        else:
            return False
        token = self.api("GET", path)["confirm_token"]
        self.api("POST", path + "/confirm", headers={"Idempotency-Key": str(uuid.uuid4())},
                 json={"confirm_token": token, "otp": code})
        after = self.balances()
        item["balance_deltas"] = {key: after[key] - before[key] for key in before}
        item["new_tx_rows"] = self.conn.execute("select count(*) from transactions").fetchone()[0] - tx_before
        item["final_status"] = self.conn.execute("select status from transfers where id=?", (tid,)).fetchone()[0]
        return (item["balance_deltas"] == {"ACC-ALICE-001": -100000, "ACC-BOB-001": 100000}
                and item["new_tx_rows"] == 2 and item["final_status"] == "COMPLETED")


def verify(app, results, output):
    app.login()
    pin = "7" + f"{secrets.randbelow(100000):05d}"
    app.api("POST", "/auth/pin", json={"password": "Alice@2026", "pin": pin})
    secret = app.api("POST", "/auth/mfa/setup", json={"password": "Alice@2026"})["secret"]
    enabled_step = int(time.time()) // 30
    app.api("POST", "/auth/mfa/enable", json={"code": totp(secret)})
    latencies = []
    for ident, prompt in PROMPTS.items():
        item = results["tests"][ident] = {"prompt": prompt, "attempts": []}
        for attempt in range(2):
            app.statuses.clear()
            try:
                cid = app.api("POST", "/conversations", json={"title": "Mentor " + ident})["id"]
                start = time.monotonic()
                answer, persisted, events = app.stream(cid, prompt)
                duration = round(time.monotonic() - start, 2)
                run = app.conn.execute("select status,termination_reason from agent_runs where conversation_id=? order by rowid desc limit 1", (cid,)).fetchone()
                item.update(answer=answer[:2600], persisted=persisted, stream_seconds=duration,
                            run=list(run) if run else None, events=list(events))
                if run and run[0] in ("ERROR","FAILED","CANCELLED"):
                    raise RuntimeError(run[1] or run[0])
                if ident == "FN-AI-01":
                    total = app.conn.execute("select sum(balance_vnd) from accounts where owner_id='alice'").fetchone()[0]
                    item["expected_total_vnd"] = total
                    ok = str(total) in re.sub(r"(?<=\d)[ ,\.](?=\d)", "", answer)
                elif ident == "FN-AI-02":
                    rows = app.conn.execute("""select t.id,t.amount_vnd,t.direction,t.date from transactions t
                        join accounts a on a.id=t.account_id where a.owner_id='alice'
                        order by t.date desc,t.created_at desc limit 5""").fetchall()
                    item["expected_recent"] = [list(row) for row in rows]
                    indices = [answer.find(row[0]) for row in rows]
                    ok = history_matches(rows, answer)
                    item["output_ids_in_db_order"] = indices
                elif ident == "FN-AI-03":
                    while int(time.time()) // 30 <= enabled_step:
                        time.sleep(0.5)
                    ok = app.transfer(cid, item, pin, secret)
                else:
                    ok = bool(re.search(r"cannot|can't|unable|can only|not able|only (?:assist|help)|do not have|don't have|outside|banking", answer, re.I))
                    ok = ok and not bool(re.search(r"(i've|i have|successfully) booked", answer, re.I))
                item["status"] = "PASS" if ok and persisted else "FAIL"
                item["attempts"].append({"result": item["status"], "http": list(app.statuses)})
                latencies.append(duration)
                break
            except Exception as exc:
                if isinstance(exc, httpx.HTTPStatusError):
                    detail = f"HTTP {exc.response.status_code}"
                    infra = exc.response.status_code in (401, 429) or exc.response.status_code >= 500
                else:
                    detail = type(exc).__name__ + " " + str(exc)[:100]
                    infra = isinstance(exc, (httpx.TransportError, RuntimeError))
                status = "ERROR" if infra else "FAIL"
                item["attempts"].append({"result": status, "detail": detail, "http": list(app.statuses)})
                item["status"] = status
                if not infra or attempt == 1:
                    break
                if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 401:
                    app.refresh()
                time.sleep(2)
        print(ident, item["status"], item.get("stream_seconds"), flush=True)
        output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    results["tests"]["FN-AI-05"] = {
        "status": "PASS" if len(latencies) == len(PROMPTS) and all(len(t["attempts"]) == 1 for t in results["tests"].values()) else "WEAK",
        "latencies": latencies, "p50_seconds": statistics.median(latencies) if latencies else None,
        "p95_seconds_nearest_rank": sorted(latencies)[math.ceil(.95*len(latencies))-1] if latencies else None}
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--seed-db", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--guard-model", type=Path, required=True)
    parser.add_argument("--published-utility", action="store_true",
                        help="Run all 100 published calibration prompts on the disposable bank, config D.")
    args = parser.parse_args()
    repo, output = args.repo.resolve(), args.output.resolve()
    # Only copy a marked synthetic database. The source remains read-only.
    if not json.loads(args.seed_db.with_suffix(".seed.json").read_text(encoding="utf-8")).get("synthetic"):
        raise ValueError("Expected a generated synthetic seed database.")
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.published_utility:
        codes = [run_isolated(args, repo, output, offset) for offset in range(0, 100, 25)]
        return int(any(codes))
    return run_isolated(args, repo, output)


def run_isolated(args, repo, output, offset=None):
    with tempfile.TemporaryDirectory(prefix="novabank-mentor-ai-", ignore_cleanup_errors=True) as tmp, ExitStack() as stack:
        path = Path(tmp) / "demo.sqlite3"
        with closing(sqlite3.connect(args.seed_db.resolve().as_uri() + "?mode=ro", uri=True)) as src, closing(sqlite3.connect(path)) as dest:
            src.backup(dest)
        bank, agent = free_port(), free_port()
        url = f"http://127.0.0.1:{bank}"
        env = dict(os.environ, BANKING_API_URL=url, AGENT_SERVICE_URL=f"http://127.0.0.1:{agent}",
                   LLM_PROVIDER="ollama", OLLAMA_URL="http://127.0.0.1:11434", OLLAMA_MODEL="qwen2.5:7b",
                   GUARD_MODEL="qwen2.5:7b", PROMPT_GUARD_MODEL_PATH=str(args.guard_model.resolve()),
                   ENV="demo", BANK_REQUIRE_AGENT="true", GATEWAY_MODE="local", BANK_WORKER_ENABLED="false", DB_PATH=str(path))
        for port, module, cwd in [(agent,"agent_service.main:app",repo), (bank,"app.main:app",repo/"backend")]:
            proc_env = env if port == bank else {k:v for k,v in env.items() if k not in ("DB_PATH","JWT_SECRET","QR_SIGNING_KEY","OTP_HASH_KEY","TRANSFER_TOKEN_KEY","MFA_ENCRYPTION_KEY")}
            proc = subprocess.Popen([sys.executable,"-m","uvicorn",module,"--host","127.0.0.1","--port",str(port)],
                                    cwd=cwd, env=proc_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            stack.callback(proc.wait)
            stack.callback(proc.terminate)
        client = stack.enter_context(httpx.Client(base_url=url,timeout=150,trust_env=False))
        for _ in range(110):
            try:
                ready = client.get("/api/ready").json()
                if ready["status"] == "ready": break
            except (httpx.HTTPError, ValueError):
                pass
            time.sleep(1)
        else:
            raise RuntimeError("Temporary stack not ready")
        conn = stack.enter_context(closing(sqlite3.connect(path.as_uri()+"?mode=ro",uri=True)))
        results = {"sha": subprocess.check_output(["git","rev-parse","HEAD"],cwd=repo,text=True).strip(), "ready": ready, "tests": {}}
        if args.published_utility:
            from published_utility import verify_published
            return verify_published(client, path, repo, results["sha"], output, offset)
        verify(App(client,conn), results, output)


if __name__ == "__main__":
    raise SystemExit(main())
