import factory
from django.contrib.auth import get_user_model

from accounts.models import PlayerProfile


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = factory.Faker("user_name")
    email = factory.Faker("email")
    password = factory.PostGenerationMethodCall("set_password", "test-password")


class PlayerProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PlayerProfile

    user = factory.SubFactory(UserFactory)
    display_name = factory.Faker("name")
    nickname = factory.Faker("user_name")
