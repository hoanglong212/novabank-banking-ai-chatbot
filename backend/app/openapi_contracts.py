"""Public success payloads. Additional fields are allowed for backwards-compatible extensions."""

from .documents.extract import MAX_BYTES


def obj(**fields):
    return {"type": "object", "required": list(fields), "properties": fields}


def array(items):
    return {"type": "array", "items": items}


STRING = {"type": "string"}
INTEGER = {"type": "integer"}
BOOLEAN = {"type": "boolean"}
OBJECT = {"type": "object"}
ROWS = array(OBJECT)
ITEMS = obj(items=ROWS)
PAGED = obj(items=ROWS, total=INTEGER, limit=INTEGER, offset=INTEGER)
MSG = obj(message=STRING)
ID = obj(id=STRING)
DELETED = obj(deleted=BOOLEAN)
CHANGE = obj(challenge_id=STRING, method=STRING, expires_in=INTEGER)
SESSION = obj(access_token=STRING, refresh_token=STRING, token_type=STRING)
SETTINGS = obj(transfer_fee_vnd=INTEGER, transfer_limit_vnd=INTEGER, daily_limit_vnd=INTEGER)
STEPUP = obj(required=BOOLEAN, new_recipient=BOOLEAN, verified=BOOLEAN)
TRANSFER = obj(id=STRING, amount_vnd=INTEGER, status=STRING)
DOCUMENT = obj(id=STRING, filename_display=STRING, size_bytes=INTEGER, status=STRING)
MAIL = obj(id=STRING, recipient=STRING, kind=STRING)

# Public operations are keyed by method and path so internal handler renames preserve the contract.
JSON_RESPONSES = {
    "GET /api/health": obj(status=STRING, llm_provider=STRING, demo_only=BOOLEAN),
    "GET /api/ready": obj(status=STRING, llm_provider=STRING),
    "GET /api/me": obj(id=STRING, name=STRING, role=STRING),
    "POST /api/actions/confirm": MSG,
    "GET /api/admin/accounts": ITEMS,
    "PATCH /api/admin/accounts/{account_id}": MSG,
    "GET /api/admin/agent-gateway": obj(gateway=STRING, lab=BOOLEAN, metrics=OBJECT),
    "PUT /api/admin/agent-gateway": obj(gateway=STRING),
    "GET /api/admin/agent-gateway/log": PAGED,
    "GET /api/admin/audit": PAGED,
    "POST /api/admin/knowledge": obj(id=STRING, message=STRING),
    "PUT /api/admin/knowledge/{document_id}": MSG,
    "POST /api/admin/knowledge-index": obj(indexed_documents=INTEGER, indexed_chunks=INTEGER),
    "GET /api/admin/overview": obj(users=INTEGER, accounts=INTEGER, transactions=INTEGER, dashboard=OBJECT),
    "POST /api/admin/reconcile": obj(id=STRING, balanced=BOOLEAN, ledger_total_vnd=INTEGER),
    "GET /api/admin/settings": SETTINGS,
    "PATCH /api/admin/settings": SETTINGS,
    "GET /api/admin/transactions": PAGED,
    "GET /api/admin/transfers/{transfer_id}/audit": ITEMS,
    "GET /api/admin/users": PAGED,
    "PATCH /api/admin/users/{user_id}": MSG,
    "GET /api/agent/approvals": ITEMS,
    "GET /api/agent/approvals/{approval_id}": obj(id=STRING, status=STRING, arguments=OBJECT),
    "POST /api/agent/approvals/{approval_id}": MSG,
    "GET /api/agent/context": obj(run_id=STRING, profile=STRING, messages=ROWS, tools=ROWS),
    "POST /api/agent/finish": obj(message=OBJECT, run_id=STRING, response_source=STRING),
    "POST /api/agent/preview": obj(text=STRING),
    "GET /api/agent/quarantine": ITEMS,
    "POST /api/agent/quarantine/{source_id}/release": MSG,
    "GET /api/agent/runs": ITEMS,
    "POST /api/agent/runs": obj(run_id=STRING, delegated_token=STRING, expires_in=INTEGER),
    "GET /api/agent/runs/{run_id}": obj(id=STRING, status=STRING, tool_calls=ROWS),
    "POST /api/agent/runs/{run_id}/cancel": obj(status=STRING),
    "POST /api/agent/tools": obj(decision=STRING, reason=STRING, halt=BOOLEAN),
    "GET /api/announcements": ITEMS,
    "POST /api/auth/activity": obj(idle_expires_at=INTEGER),
    "POST /api/auth/forgot-password": MSG,
    "POST /api/auth/login": {"anyOf": [CHANGE, SESSION]},
    "GET /api/auth/login-history": PAGED,
    "POST /api/auth/logout": MSG,
    "GET /api/auth/mfa": obj(totp_enabled=BOOLEAN, email_fallback=BOOLEAN, pin_set=BOOLEAN),
    "POST /api/auth/mfa/disable": MSG,
    "POST /api/auth/mfa/disable-request": CHANGE,
    "POST /api/auth/mfa/email": MSG,
    "POST /api/auth/mfa/enable": MSG,
    "POST /api/auth/mfa/setup": obj(secret=STRING, otpauth_uri=STRING, expires_in=INTEGER),
    "POST /api/auth/mfa/verify": SESSION,
    "POST /api/auth/pin": MSG,
    "POST /api/auth/refresh": SESSION,
    "POST /api/auth/register": MSG,
    "POST /api/auth/resend-verification": MSG,
    "POST /api/auth/reset-password": MSG,
    "GET /api/auth/sessions": ITEMS,
    "DELETE /api/auth/sessions/{session_id}": MSG,
    "POST /api/auth/verify-email": MSG,
    "PATCH /api/bills/{bill_id}/saved": MSG,
    "GET /api/conversations": ROWS,
    "POST /api/conversations": obj(id=STRING, title=STRING),
    "DELETE /api/conversations/{conversation_id}": DELETED,
    "POST /api/conversations/{conversation_id}/demo/tool-check": obj(decision=STRING),
    "GET /api/conversations/{conversation_id}/messages": ROWS,
    "POST /api/conversations/{conversation_id}/messages": obj(
        message=OBJECT, tool_events=ROWS, response_source=STRING
    ),
    "GET /api/conversations/{conversation_id}/tool-events": ROWS,
    "GET /api/customer/accounts": ITEMS,
    "PATCH /api/customer/accounts/{account_id}": MSG,
    "GET /api/customer/beneficiaries": ITEMS,
    "POST /api/customer/beneficiaries": obj(id=STRING, account_id=STRING, nickname=STRING),
    "POST /api/customer/beneficiaries/lookup": obj(account_id=STRING, bank=STRING, holder_name=STRING),
    "DELETE /api/customer/beneficiaries/{beneficiary_id}": MSG,
    "PATCH /api/customer/beneficiaries/{beneficiary_id}": obj(id=STRING, account_id=STRING, nickname=STRING),
    "GET /api/customer/notification-preferences": obj(bill_reminders=BOOLEAN, budget_alerts=BOOLEAN),
    "PUT /api/customer/notification-preferences": MSG,
    "GET /api/customer/profile": obj(id=STRING, name=STRING),
    "POST /api/customer/profile/change": CHANGE,
    "GET /api/dev/outbox": ITEMS,
    "POST /api/dev/outbox/challenge": MAIL,
    "GET /api/dev/outbox/{message_id}": MAIL,
    "GET /api/documents": obj(items=array(DOCUMENT)),
    "POST /api/documents": DOCUMENT,
    "GET /api/documents/{document_id}": DOCUMENT,
    "DELETE /api/documents/{document_id}": DELETED,
    "GET /api/insights": obj(month=STRING, income_vnd=INTEGER, expense_vnd=INTEGER, net_vnd=INTEGER),
    "PUT /api/insights/budgets": MSG,
    "GET /api/knowledge": ITEMS,
    "GET /api/knowledge/search": obj(retrieval_method=STRING, sources=ROWS),
    "GET /api/knowledge/{document_id}": obj(id=STRING, title=STRING, content=STRING, status=STRING),
    "GET /api/notifications": ITEMS,
    "POST /api/notifications/read-all": obj(updated=INTEGER),
    "PATCH /api/notifications/{notification_id}/read": ID,
    "POST /api/products/actions": CHANGE,
    "GET /api/products/{kind}": ITEMS,
    "POST /api/qr/decode": obj(source_origin=STRING, qr_security=OBJECT),
    "GET /api/research/runs": ITEMS,
    "POST /api/research/runs": MSG,
    "GET /api/research/runs/{run_id}": obj(status=STRING),
    "GET /api/research/runs/{run_id}/cases": obj(items=ROWS, total=INTEGER),
    "GET /api/savings-goals": ITEMS,
    "POST /api/savings-goals": obj(id=STRING, message=STRING),
    "PUT /api/savings-goals/{goal_id}": obj(id=STRING, message=STRING),
    "DELETE /api/savings-goals/{goal_id}": MSG,
    "GET /api/support/tickets": PAGED,
    "POST /api/support/tickets": obj(id=STRING, subject=STRING, status=STRING),
    "GET /api/support/tickets/{ticket_id}": obj(id=STRING, subject=STRING, status=STRING, messages=ROWS),
    "PATCH /api/support/tickets/{ticket_id}": MSG,
    "POST /api/support/tickets/{ticket_id}/attachments": obj(id=STRING, name=STRING, size_bytes=INTEGER),
    "POST /api/support/tickets/{ticket_id}/messages": MSG,
    "GET /api/transactions": PAGED,
    "GET /api/transactions/{transaction_id}": ID,
    "PATCH /api/transactions/{transaction_id}/category": MSG,
    "POST /api/transfers": TRANSFER,
    "GET /api/transfers/{transfer_id}": TRANSFER,
    "POST /api/transfers/{transfer_id}/confirm": TRANSFER,
    "POST /api/transfers/{transfer_id}/otp": TRANSFER,
    "GET /api/transfers/{transfer_id}/step-up": STEPUP,
    "POST /api/transfers/{transfer_id}/step-up": STEPUP,
    "POST /api/vietqr": obj(bank=STRING, account_no=STRING),
    "GET /api/vietqr/banks": array(OBJECT),
}

BINARY = {"type": "string", "format": "binary"}
OTHER_MEDIA = {
    "GET /api/admin/agent-gateway/log.csv": {"text/csv": STRING},
    "POST /api/conversations/{conversation_id}/stream": {"text/event-stream": STRING},
    "GET /api/transactions/{transaction_id}/receipt.pdf": {"application/pdf": BINARY},
    "GET /api/support/attachments/{attachment_id}": {"application/octet-stream": BINARY},
    "GET /api/statements.{fmt}": {"application/pdf": BINARY, "text/csv": STRING},
    "GET /api/research/runs/{run_id}/export/{filename}": {
        "text/csv": STRING,
        "application/json": {"type": ["object", "array"]},
    },
}


def install(app):
    """Fill success response metadata without filtering runtime payloads or changing serializers."""
    default_openapi = app.openapi

    def openapi():
        if app.openapi_schema is not None:
            return app.openapi_schema
        spec = default_openapi()
        for path, methods in spec["paths"].items():
            for method, op in methods.items():
                key = f"{method.upper()} {path}"
                if key in JSON_RESPONSES:
                    media = {"application/json": JSON_RESPONSES[key]}
                elif key in OTHER_MEDIA:
                    media = OTHER_MEDIA[key]
                else:
                    continue
                for code, response in op["responses"].items():
                    if code.startswith("2"):
                        response["content"] = {k: {"schema": v} for k, v in media.items()}
        upload = spec["paths"]["/api/documents"]["post"]
        upload["requestBody"] = {
            "required": True,
            "content": {"multipart/form-data": {"schema": obj(file={**BINARY, "x-max-bytes": MAX_BYTES})}},
        }
        for code, description in [
            ("415", "Expected multipart/form-data"),
            ("422", "Malformed multipart upload or file exceeds 5 MiB"),
        ]:
            upload["responses"][code] = {
                "description": description,
                "content": {"application/json": {"schema": obj(detail=STRING)}},
            }
        return spec

    app.openapi = openapi
