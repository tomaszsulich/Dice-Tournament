import pytest
from django.db import connection


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_database_uses_postgresql():
    assert connection.vendor == "postgresql"
