def test_qr_camera_and_local_image_preview_permissions(client):
    response = client.get('/api/health')
    permissions = response.headers['Permissions-Policy']
    policy = response.headers['Content-Security-Policy']
    assert 'camera=(self)' in permissions
    assert 'microphone=()' in permissions and 'geolocation=()' in permissions
    assert "img-src 'self' data: blob:" in policy
    assert 'https://cdn.vietqr.io' in policy
    assert "connect-src 'self';" in policy
    assert "worker-src 'self'" in policy
    assert "'wasm-unsafe-eval'" in policy
    assert "frame-ancestors 'none'" in policy
    assert "object-src 'none'" in policy
    assert "'unsafe-eval'" not in policy
