import pytest
from django.contrib.auth import get_user_model

from accounts.tests.factories import UserFactory


@pytest.mark.unit
def test_user_factory_build_does_not_access_database():
    user = UserFactory.build()

    assert user.pk is None
    assert user.username
    assert user.email


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_user_factory_create_persists_user():
    user = UserFactory.create()

    assert user.pk is not None
    assert get_user_model().objects.filter(pk=user.pk).exists()
