import socket

import pytest


@pytest.fixture(autouse=True)
def block_external_network(monkeypatch):
    """Block unindented external network access during tests."""
    original_create_connection = socket.create_connection

    def guarded_create_connection(address, *args, **kwargs):
        host, _port = address

        if host not in {"localhost", "127.0.0.1", "::1"}:
            pytest.fail(f"External network access blocked: {host}")

        return original_create_connection(address, *args, **kwargs)

    monkeypatch.setattr(socket, "create_connection", guarded_create_connection)
