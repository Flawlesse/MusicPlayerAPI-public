import factory
from faker import Faker
from music_player_api.models import User
from pytest_factoryboy import register

fake = Faker()


@register
class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = fake.email()
    first_name = fake.first_name()
    last_name = fake.last_name()
    is_staff = "False"
    is_superuser = "False"
