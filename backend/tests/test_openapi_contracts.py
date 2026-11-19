"""Contract results are attached to actual in-process HTTP observations for each operation."""

from contextlib import closing
import csv
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from starlette.routing import compile_path

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
import pytest

from tests.openapi_examples import agent, bank, exercise, TokenClient
from app.dependencies import get_db
from app.routes_documents import MULTIPART_OVERHEAD_BYTES

APPS = {"Bank": bank, "Agent": agent.app}
SCHEMAS = {name: app.openapi() for name, app in APPS.items()}
OPERATIONS = {
    (name, m.upper(), p): op
    for name, spec in SCHEMAS.items()
    for p, entries in spec["paths"].items()
    for m, op in entries.items()
}
MATRIX = json.loads((Path(__file__).parent / "route_matrix.json").read_text(encoding="utf-8"))
POLICIES = {(r["method"], r["path"]): r["roles"] for r in MATRIX}


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    directory = tmp_path_factory.mktemp("contracts")
    results = {}
    with pytest.MonkeyPatch.context() as mp:
        for name, value in {
            "DB_PATH": str(directory / "contract.sqlite3"),
            "ENV": "demo",
            "LLM_PROVIDER": "mock",
            "BANK_WORKER_ENABLED": "false",
            "BANK_REQUIRE_AGENT": "false",
            "LEGACY_AGENT_TEST_MODE": "true",
            "RESEARCH_SANDBOX_ENABLED": "true",
        }.items():
            mp.setenv(name, value)
        with (
            TokenClient(bank, raise_server_exceptions=False) as b,
            TestClient(agent.app, raise_server_exceptions=False) as a,
        ):
            samples, statuses, roles, resources = exercise(b, a, mp, directory, OPERATIONS)
            yield {
                "clients": {"Bank": b, "Agent": a},
                "samples": samples,
                "statuses": statuses,
                "roles": roles,
                "resources": resources,
                "results": results,
            }
    if destination := os.environ.get("NOVABANK_CONTRACT_RESULTS"):
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")


def success(responses, op):
    if not responses:
        return "BLOCKED successful response missing"
    for r in responses:
        content = op["responses"].get(str(r.status_code), {}).get("content", {})
        media = r.headers.get("content-type", "").split(";")[0]
        schema = content.get(media, {}).get("schema")
        if not schema:
            return f"FAIL missing declared schema for {r.status_code} {media}"
        if media == "application/json":
            try:
                value = r.json()
            except ValueError:
                return f"FAIL invalid JSON for {r.status_code}"
            errors = list(Draft202012Validator(schema).iter_errors(value))
            if errors:
                # Values may include credentials; only record the schema keyword.
                return "FAIL JSON field contract: " + str(errors[0].json_path) + " " + errors[0].validator
        elif not r.content or media == "application/pdf" and not r.content.startswith(b"%PDF-"):
            return f"FAIL invalid {media} body"
        elif media == "text/event-stream" and ("event: complete" not in r.text or "event: error" in r.text):
            return "FAIL incomplete SSE response"
        elif media == "text/csv" and not list(csv.reader(r.text.splitlines())):
            return "FAIL empty CSV"
        elif media.startswith("text/") and not Draft202012Validator(schema).is_valid(r.text):
            return f"FAIL text contract for {media}"
    return f"PASS {len(responses)} successful HTTP responses validated"


def resolve(spec, schema):
    if "$ref" in schema:
        schema = spec["components"]["schemas"][schema["$ref"].split("/")[-1]]
    if "anyOf" in schema:
        return next((s for s in schema["anyOf"] if s.get("type") != "null"), schema)
    return schema


def outside(schema):
    if "maxLength" in schema:
        return "x" * (schema["maxLength"] + 1)
    if "maximum" in schema:
        return int(schema["maximum"]) + 1
    if "maxItems" in schema:
        return [schema.get("items", {}).get("enum", ["item"])[0]] * (schema["maxItems"] + 1)
    return None


def invalid_inputs(spec, op, example):
    """Each variant changes one field of a real successful request; omitted nonrequired fields are valid."""
    params = dict(example.url.params)
    request = op.get("requestBody", {}).get("content", {})
    payload = None
    if "application/json" in request:
        payload = json.loads(example.content)
        schema = resolve(spec, request["application/json"]["schema"])
        if op["requestBody"].get("required"):
            yield "missing-body", params, None
        for field, raw in schema.get("properties", {}).items():
            prop = resolve(spec, raw)
            if field in schema.get("required", []):
                yield "missing:" + field, params, {k: v for k, v in payload.items() if k != field}
            wrong = [] if prop.get("type") == "object" else {}
            yield "type:" + field, params, {**payload, field: wrong}
            value = outside(prop)
            if value is not None:
                yield "bound:" + field, params, {**payload, field: value}
    for arg in op.get("parameters", []):
        if arg["in"] != "query":
            continue
        field = arg["name"]
        prop = resolve(spec, arg["schema"])
        if arg.get("required"):
            yield "missing:" + field, {k: v for k, v in params.items() if k != field}, payload
        if (
            prop.get("type") not in ("string", None)
            or "enum" in prop
            or "pattern" in prop
            or prop.get("format") == "date"
        ):
            yield "type:" + field, {**params, field: "invalid-contract-value"}, payload
        value = outside(prop)
        if value is not None:
            yield "bound:" + field, {**params, field: value}, payload


def wire_variants(spec, op, path, example):
    """Only wire representations ruled out by the published parameter schema are invalid."""
    captures = compile_path(path)[0].fullmatch(example.url.path)
    for parameter in op.get("parameters", []):
        location = parameter["in"]
        field = parameter["name"]
        if location not in ("path", "header") or field.lower() == "authorization":
            continue
        schema = resolve(spec, parameter["schema"])
        values = []
        if schema.get("type") not in ("string", None) or "enum" in schema or "pattern" in schema:
            values.append(("type", "invalid contract value"))
        if (limit := outside(schema)) is not None:
            values.append(("bound", str(limit)))
        for kind, value in values:
            concrete = example.url.path
            headers = {}
            if location == "path":
                start, end = captures.span(field)
                concrete = concrete[:start] + value + concrete[end:]
            else:
                headers[field] = value
            yield f"{kind}:{location}:{field}", concrete, headers


def fingerprints(conn):
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    return {
        table: hashlib.sha256(
            repr(conn.execute('SELECT * FROM "' + table.replace('"', '""') + '"').fetchall()).encode()
        ).digest()
        for (table,) in tables
    }


def roles_and_input(world, key):
    name, method, path = key
    samples = world["samples"].get(key, [])
    policies = (
        POLICIES[method, path] if name == "Bank" else ["delegated"] if path == "/run" else ["anonymous"]
    )
    roles = world["roles"]
    allowed = set(policies) & set(roles)
    forbidden = sorted(set(roles) - allowed) if allowed and "anonymous" not in policies else []
    example = samples[0].request if samples else None
    if example is None:
        return (
            "BLOCKED no fixture for role exercise" if forbidden else "N/A no forbidden login role",
            "BLOCKED no valid request fixture",
        )
    client = world["clients"][name]
    op = OPERATIONS[key]
    parsed = op.get("requestBody", {}).get("content", {})
    raw_body = json.loads(example.content) if "application/json" in parsed and example.content else None
    role_result = "N/A public, all session roles, or separate delegation credential"
    if forbidden:
        failed = []
        for role in forbidden:
            response = client.request(
                method, example.url.path, headers=roles[role], params=dict(example.url.params), json=raw_body
            )
            if response.status_code != 403:
                failed.append(f"{role} HTTP {response.status_code}")
        role_result = (
            "FAIL expected 403: " + ", ".join(failed)
            if failed
            else "PASS forbidden HTTP 403: " + ",".join(forbidden)
        )
    who = (
        world["resources"]["validation_delegation"]
        if "delegated" in policies
        else roles[
            next(
                (r for r in ("customer", "admin", "support", "operations", "auditor") if r in allowed),
                "customer",
            )
        ]
    )
    if "multipart/form-data" in parsed:
        maximum = parsed["multipart/form-data"]["schema"]["properties"]["file"]["x-max-bytes"]
        files = {
            "missing:file": {"note": ("note.txt", b"contract")},
            "type:file": {"file": (None, "ordinary field")},
            "bound:file-bytes": {"file": ("too-large.txt", b"x" * (maximum + 1), "text/plain")},
            "bound:multipart-stream": {
                "file": ("too-large.txt", b"x" * (maximum + MULTIPART_OVERHEAD_BYTES + 1), "text/plain")
            },
        }
        variants = [(label, {}, None, example.url.path, {}) for label in files]
    else:
        variants = [
            (label, params, payload, example.url.path, {})
            for label, params, payload in invalid_inputs(SCHEMAS[name], op, example)
        ]
    variants.extend(
        (label, dict(example.url.params), raw_body, url, headers)
        for label, url, headers in wire_variants(SCHEMAS[name], op, path, example)
    )
    if not variants:
        return role_result, "N/A no declared invalid business parameter or body variant"
    checks = []
    problems = []
    with closing(sqlite3.connect(get_db().path)) as conn:
        initial = fingerprints(conn)
        version = conn.execute("PRAGMA data_version").fetchone()[0]
        for label, params, payload, url, headers in variants:
            if "multipart/form-data" in parsed:
                resp = client.post(example.url.path, headers=who, files=files[label])
            else:
                resp = client.request(method, url, headers={**who, **headers}, params=params, json=payload)
            if resp.status_code != 422 or not resp.json().get("detail"):
                problems.append(f"{label} HTTP {resp.status_code} expected 422")
            elif label in ("bound:file-bytes", "bound:multipart-stream") and resp.json() != {
                "detail": "FILE_TOO_LARGE"
            }:
                problems.append(label + " wrong upload error")
            new_version = conn.execute("PRAGMA data_version").fetchone()[0]
            if new_version != version:
                after = fingerprints(conn)
                changed = [t for t, v in after.items() if v != initial.get(t)]
                if changed:
                    problems.append(label + " DB changed: " + ",".join(changed))
                initial = after
                version = new_version
            checks.append(f"{label} HTTP 422")
    if problems:
        return role_result, "FAIL " + "; ".join(problems)
    return role_result, f"PASS identical DB for {len(checks)} cases (" + ", ".join(checks) + ")"


@pytest.mark.parametrize("key", sorted(OPERATIONS), ids=lambda k: " ".join(k))
def test_openapi_operation(world, key):
    samples = world["samples"].get(key, [])
    good = success(samples, OPERATIONS[key])
    roles, invalid = roles_and_input(world, key)
    record = {"GEN01": good, "GEN04": roles, "GEN05": invalid}
    if not samples:
        record["positive_http"] = world["statuses"].get(key)
    world["results"][" ".join(key)] = record
    assert all(v.split()[0] in ("PASS", "N/A") for v in (good, roles, invalid)), record
