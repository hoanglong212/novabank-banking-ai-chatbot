import pytest


class Client:
    def __init__(self):
        self.puts = []

    def put(self, path, headers, json):
        self.puts.append((path, json))
        return type('R', (), {'raise_for_status': lambda self: None})()


def test_benign_utility_selects_only_registered_defended_configs(monkeypatch):
    from research import promptguard_utility as utility
    monkeypatch.setattr(utility, 'login', lambda client, db, user: {'user': user})
    client = Client()
    assert utility.select_config(client, 'db', 'C') == {'user': 'alice'}
    assert client.puts == [('/api/admin/agent-gateway', {'config': 'C', 'users': ['alice'], 'minutes': 120})]
    with pytest.raises(ValueError):
        utility.select_config(client, 'db', 'A')
