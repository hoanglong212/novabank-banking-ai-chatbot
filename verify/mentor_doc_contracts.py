"""Score the offline HTTP and SQLite evidence collected by mentor-rag-api."""


def rejected_files(cases, *, require_current_upload=False):
    reasons = {
        'textless': 'NO_TEXT', 'pages': 'TOO_MANY_PAGES',
        'encrypted': 'ENCRYPTED_PDF',
    }
    if set(cases) != set(reasons) | {'oversize'}:
        return False
    for label, expected in reasons.items():
        row = cases[label]
        if not (row['http'] == 201 and row['state'] == 'rejected'
                and row['reason'] == row['db_reason'] == expected and row['chunks'] == 0):
            return False
    large = cases['oversize']
    if large.get('contract_version') == 2:
        counts = [large[key] for key in ('documents_before', 'documents_after', 'chunks_before', 'chunks_after')]
        return (large['http'] == 422 and large['body'] == {'detail': 'FILE_TOO_LARGE'}
                and all(type(count) is int and count >= 0 for count in counts)
                and large['documents_before'] == large['documents_after']
                and large['chunks_before'] == large['chunks_after'])
    # The original collector at 0548e99 recorded a persisted rejected row. Only
    # an archived, unversioned observation may use that historical contract.
    return (not require_current_upload and 'contract_version' not in large
            and large['http'] == 201 and large['state'] == 'rejected'
            and large['reason'] == large['db_reason'] == 'FILE_TOO_LARGE' and large['chunks'] == 0)


def intact_owner_document(row):
    return (row['other_http'] == [404, 404] and
            row['other_body'] == [{'detail': 'DOCUMENT_UNAVAILABLE'}] * 2 and
            row['owner_get'] == 200 and row['deleted_at'] is None and
            row['owner'] == 'bob' and row['chunk_count'] > 0)


def quota_enforced(row):
    burst = row['sequential_upload_statuses']
    return (row['cap_http'] == [201, 409] and row['cap_body'] == 'DOCUMENT_LIMIT'
            and row['db_active_after'] == 20 and burst[-1] == 429
            and all(status == 201 for status in burst[:-1]))


PREDICATES = {
    'DOC-API-01': lambda r: (r['http'] == 201 and r['body_status'] == r['db_status'] == 'ready'
                            and r['hash_correct'] and r['detail'] == 200 and r['preview_present']),
    'DOC-API-02': lambda r: r['anonymous_upload'] == r['expired_http'] == 401,
    'DOC-API-03': lambda r: (r['http'] == 201 and r['status'] == 'rejected'
                            and r['db_reason'] == r['reason'] == 'UNSUPPORTED_FILE'),
    'DOC-API-04': rejected_files,
    'DOC-API-05': lambda r: r['http'] == 201 and r['filename'] == 'Demo.txt',
    'DOC-API-06': intact_owner_document,
    'DOC-API-07': lambda r: (r['valid_uuid4'] and not r['owner_file_visible_to_second_customer']
                            and r['absent_uuid_http'] == 404 and r['list_http'] == 200),
    'DOC-API-08': lambda r: r['http'] == 201 and r['db_owner'] == 'alice',
    'DOC-API-09': quota_enforced,
    'DOC-API-10': lambda r: (r['delete'] == 200 and r['delete_body'] == {'deleted': True}
                            and r['detail_after'] == 404 and r['chunks_after'] == 0),
    'DOC-API-11': lambda r: r['anonymous_http'] == 401 and r['normal_customer_http'] in (401, 403),
    'DOC-API-12': lambda r: (r['bad_media_http'] == 415 and r['bad_media_body'] == {'detail': 'MULTIPART_REQUIRED'}
                            and not r['malformed_paths_or_traces']),
}


def offline_checks(results, *, require_current_upload=False):
    checks = {}
    for case_id, predicate in PREDICATES.items():
        try:
            if case_id == 'DOC-API-04':
                checks[case_id] = rejected_files(results[case_id], require_current_upload=require_current_upload)
            else:
                checks[case_id] = bool(predicate(results[case_id]))
        except (AttributeError, IndexError, KeyError, TypeError):
            checks[case_id] = False
    return checks
