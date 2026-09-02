import factory
from django.contrib.auth import get_user_model

from accounts.models import PlayerProfile


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()
        skip_postgeneration_save = True

    username = factory.Faker("user_name")
    email = factory.Faker("email")

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return

        self.set_password(extracted or "test-password")
        self.save(update_fields=["password"])


class PlayerProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PlayerProfile

    user = factory.SubFactory(UserFactory)
    display_name = factory.Faker("name")
    nickname = factory.Faker("user_name")
