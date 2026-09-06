import pytest
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from accounts.api.permissions import IsOwner
from accounts.tests.factories import PlayerProfileFactory, UserFactory


class RequestStub:
    def __init__(self, user):
        self.user = user


class OwnerOnlyTestView(APIView):
    permission_classes = (IsAuthenticated, IsOwner)

    def get(self, request, profile):
        self.check_object_permissions(request, profile)
        return Response(status=status.HTTP_204_NO_CONTENT)


@pytest.mark.unit
def test_is_owner_allows_owner():
    user = UserFactory.build()
    profile = PlayerProfileFactory.build(user=user)
    request = RequestStub(user)

    permission = IsOwner()

    assert permission.has_object_permission(request, None, profile) is True


@pytest.mark.unit
def test_is_owner_denies_other_user():
    owner = UserFactory.build()
    other_user = UserFactory.build()
    profile = PlayerProfileFactory.build(user=owner)
    request = RequestStub(other_user)

    permission = IsOwner()

    assert permission.has_object_permission(request, None, profile) is False


@pytest.mark.unit
def test_owner_only_view_returns_403_for_other_user():
    owner = UserFactory.build()
    other_user = UserFactory.build()
    profile = PlayerProfileFactory.build(user=owner)

    request = APIRequestFactory().get("/test-owner/")
    force_authenticate(request, user=other_user)

    response = OwnerOnlyTestView.as_view()(request, profile=profile)

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_submitted_user_id_cannot_replace_request_user(api_client):
    user_a = UserFactory.create()
    profile_a = PlayerProfileFactory.create(user=user_a)

    user_b = UserFactory.create()
    profile_b = PlayerProfileFactory.create(user=user_b)

    api_client.force_authenticate(user=user_a)

    response = api_client.get(f"/api/profile/?user_id={user_b.pk}")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == profile_a.id
    assert response.data["id"] != profile_b.id
