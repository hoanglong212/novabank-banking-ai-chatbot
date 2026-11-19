"""Independently measure fresh Week 7 / Week 8 synthetic DBs without changing them.

Run both seed_realistic.py invocations with the same seed to independent files,
and point this script to the two clean checkout directories and the DB folder
using the commands recorded in the verification report. Output contains hashes,
counts and selected fictional transaction fields, never credential values.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing, ExitStack


def query(connection, sql):
    names = connection.execute(sql)
    return [dict(zip([column[0] for column in names.description], row)) for row in names]


def sha256_lines(lines):
    digest = hashlib.sha256()
    for line in lines:
        digest.update(line.encode("utf-8") + b"\n")
    return digest.hexdigest()


def counts(connection):
    return {name: connection.execute(f"select count(*) from {name}").fetchone()[0]
            for name in ("users", "accounts", "transactions")}


def current_results(connection):
    sql = {
        "roles": "select role, count(*) n from users group by role order by role",
        "user_statuses": "select status,count(*) n from users group by status",
        "account_statuses": "select status,count(*) n from accounts group by status",
        "zero_negative": """select sum(balance_vnd=0) zero_balance, sum(balance_vnd<0) negative_balance,
            sum(balance_vnd) account_total_vnd from accounts""",
        "accounts_per_owner": """select n accounts, count(*) owners from
            (select owner_id,count(*) n from accounts group by owner_id) group by n order by n""",
        "factors": """select count(*) users, count(m.secret_encrypted) enrolled_totp,
            count(p.pin_hash) configured_pin from users u left join mfa_settings m on m.user_id=u.id
            left join transaction_pins p on p.user_id=u.id""",
        "lockouts": """select (select count(*) from login_lockouts where locked_until>0) login_locks,
            (select count(*) from transaction_pins where locked_until>0) pin_locks""",
        "transfers": "select status,count(*) n from transfers group by status",
        "transactions": "select status,count(*) n from transactions group by status",
        "legacy_fixture": "select count(*) n from transactions where id='TX-PENTEST-E1'",
        "journal": """select count(*) journals, sum(n < 2 or net <> 0) unbalanced from
            (select journal_id,count(*) n,sum(amount_vnd) net from ledger_entries group by journal_id)""",
        "per_account": """with totals as (select a.id,a.balance_vnd,
            count(distinct l.id) links,coalesce(sum(e.amount_vnd),0) ledger_balance from accounts a
            left join ledger_accounts l on l.customer_account_id=a.id
            left join ledger_entries e on e.account_id=l.id group by a.id)
            select sum(links<>1 or balance_vnd<>ledger_balance) mismatches,
            sum(ledger_balance) customer_ledger_vnd from totals""",
        "global_ledger": "select count(*) entries, sum(amount_vnd) sum_vnd from ledger_entries",
        "email_domains": """select substr(email,instr(email,'@')+1) domain,count(*) n
            from users group by domain""",
        "ten_transaction_samples": """with ranked as (
            select date, direction, amount_vnd, description,
            row_number() over(order by date,id) seq,count(*) over() total from transactions)
            select date,direction,amount_vnd,description from ranked
            where (seq-1) % ((total-1)/9)=0 order by seq limit 10""",
        "integrity": "pragma integrity_check",
        "foreign_key_issues": "pragma foreign_key_check",
    }
    return {key: query(connection, stmt) for key, stmt in sql.items()}


def table_hashes(connection):
    table_names = [r[0] for r in connection.execute(
        "select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name")]
    hashes = {}
    for table in table_names:
        # Compare all stored values including BLOBs; expose hashes only.
        values = connection.execute(f'SELECT * FROM "{table}"')
        rows = sorted(json.dumps(row, ensure_ascii=False, default=lambda b: b.hex()) for row in values)
        hashes[table] = sha256_lines(rows)
    return hashes


def seed_databases(before, current, directory):
    subprocess.run([sys.executable, "-c",
                    "from app.database import Database; import sys; Database(sys.argv[1]).initialize()",
                    str(directory / "week7-default.sqlite3")], cwd=before / "backend", check=True)
    subprocess.run([sys.executable, "scripts/seed-demo.py", "--out", str(directory / "week7-rich.sqlite3")],
                   cwd=before, check=True)
    for name in ("a", "b"):
        subprocess.run([sys.executable, "scripts/seed_realistic.py", "--output",
                        str(directory / (name + ".sqlite3")), "--seed", "20261115"], cwd=current, check=True)


def measure(options):
    results = {}
    table_digests = {}
    for name in ["week7-default", "week7-rich", "a", "b"]:
        uri = (options.db_dir / (name + ".sqlite3")).resolve(strict=True).as_uri() + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True)) as conn:
            results[name] = {"counts": counts(conn)}
            if name in ("a", "b"):
                results[name]["dump_sha256"] = sha256_lines(conn.iterdump())
                columns = [row[1] for row in conn.execute("pragma table_info(users)") if row[1] != "password_hash"]
                result = conn.execute("select " + ",".join(columns) + " from users order by id")
                results[name]["user_fields_except_password_hash_sha256"] = sha256_lines(
                    json.dumps(row, ensure_ascii=False) for row in result)
                table_digests[name] = table_hashes(conn)
                if name == "a":
                    results[name].update(current_results(conn))
    results["different_tables"] = [table for table, value in table_digests["a"].items()
                                  if table_digests["b"].get(table) != value]
    for dataset, directory in [("week8", options.current), ("week7", options.before)]:
        results[dataset] = {"sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=directory, text=True).strip()}
    fixture_dir = options.current / "fixtures" / "documents"
    results["fixtures"] = sorted(p.name for p in fixture_dir.iterdir() if p.is_file())
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Wrote independent measurements to", options.output)


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--db-dir", type=Path, help="Inspect an already-generated folder. Without this, reseed four fresh DBs.")
    args.add_argument("--current", required=True, type=Path)
    args.add_argument("--before", required=True, type=Path)
    args.add_argument("--output", required=True, type=Path)
    options = args.parse_args()
    with ExitStack() as stack:
        if options.db_dir is None:
            options.db_dir = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="mentor-seed-audit-")))
            seed_databases(options.before, options.current, options.db_dir)
        measure(options)


if __name__ == "__main__":
    main()
