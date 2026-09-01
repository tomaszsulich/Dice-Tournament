import pytest
from django.conf import settings
from django.db import connection


@pytest.mark.django_db
def test_project_boots_with_postgresql():
    """Verify that the project boots and connects to PostgreSQL."""
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        assert cursor.fetchone() == (1,)
