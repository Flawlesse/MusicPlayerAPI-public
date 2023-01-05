import pytest
from django.contrib.auth.hashers import check_password
from faker import Faker
from music_player_api.models import User
from music_player_api.serializers import (
    ChangePasswordForgotSerializer,
    ChangePasswordSerializer,
    CodeWithEmailSerializer,
    FindEmailSerializer,
    RegisterUserSerializer,
    UserInfoSerializer,
)
from music_player_api.utils import ResetCodeManager, SessionTokenManager


@pytest.mark.django_db
def test_register_user_serializer(user_factory):
    user_data = user_factory.build()
    password = "123456789"
    serializer = RegisterUserSerializer(
        data={
            "email": user_data.email,
            "password": password,
            "confirmation_password": password,
        }
    )
    assert serializer.is_valid()
    new_user = serializer.save()
    assert User.objects.filter(email=new_user.email).exists()


@pytest.mark.django_db
def test_user_info_serializer(user_factory):
    test_user = user_factory.create()
    password = "123456789"

    old_email = test_user.email
    old_fname = test_user.first_name
    old_lname = test_user.last_name

    test_user.set_password(password)
    assert test_user.check_password(password)

    fake = Faker()
    serializer = UserInfoSerializer(
        instance=test_user,
        data={
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
        },
    )
    assert serializer.is_valid()
    serializer.save()
    assert (
        test_user.email == old_email
        and test_user.first_name != old_fname
        and test_user.last_name != old_lname
    )

    serializer = UserInfoSerializer(
        instance=test_user,
        data={
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
        },
    )
    assert serializer.is_valid()
    serializer.save()
    assert (
        test_user.email == old_email
        and test_user.first_name != old_fname
        and test_user.last_name != old_lname
    )


@pytest.mark.django_db
def test_change_password_serializer(user_factory):
    test_user = user_factory.create()
    password = "123456789"
    test_user.set_password(password)
    assert test_user.check_password(password)

    # Check for normal behavior
    new_password = "234567890"
    serializer = ChangePasswordSerializer(
        instance=test_user,
        data={
            "password": password,
            "new_password": new_password,
            "confirmation_password": new_password,
        },
    )
    assert serializer.is_valid()
    assert check_password(new_password, serializer.save().password)
    password = new_password

    # Check for blank password
    new_password = ""
    serializer = ChangePasswordSerializer(
        instance=test_user,
        data={
            "password": password,
            "new_password": new_password,
            "confirmation_password": new_password,
        },
    )
    assert serializer.is_valid() is False

    # Check for setting the same password that user owns
    serializer = ChangePasswordSerializer(
        instance=test_user,
        data={
            "password": password,
            "new_password": password,
            "confirmation_password": password,
        },
    )
    assert serializer.is_valid() is False

    # Check for non-matching passwords
    new_password = "234567890"
    confirmation_password = "123456789"
    serializer = ChangePasswordSerializer(
        instance=test_user,
        data={
            "password": password,
            "new_password": new_password,
            "confirmation_password": confirmation_password,
        },
    )
    assert serializer.is_valid() is False

    # Check for wrong old password
    new_password = "234567890"
    serializer = ChangePasswordSerializer(
        instance=test_user,
        data={
            "password": "definetly_not_a_password",
            "new_password": new_password,
            "confirmation_password": confirmation_password,
        },
    )
    assert serializer.is_valid() is False


@pytest.mark.django_db
def test_password_reset_serializers(user_factory):
    test_user = user_factory.create()
    password = "123456789"
    test_user.set_password(password)
    assert test_user.check_password(password)

    # Cannot find email
    serializer1 = FindEmailSerializer(
        data={
            "email": "emaildoesnotexist@email.rx",
        }
    )
    assert not serializer1.is_valid()
    # Must be right
    serializer1 = FindEmailSerializer(
        data={
            "email": test_user.email,
        }
    )
    assert serializer1.is_valid()
    user_found = serializer1.save()
    assert user_found == test_user

    code_provided = ResetCodeManager.get_or_create_code(user_found.email)
    # Try providing wrong code
    wrong_code = code_provided[:3] + chr((int(code_provided[3]) + 1) % 10)
    serializer2 = CodeWithEmailSerializer(
        data={"email": user_found.email, "code": wrong_code}
    )
    assert not serializer2.is_valid()
    # Must be right
    serializer2 = CodeWithEmailSerializer(
        data={"email": user_found.email, "code": code_provided}
    )
    assert serializer2.is_valid()
    session_token = serializer2.save()
    assert session_token == SessionTokenManager.get_or_create_token(user_found.email)

    # Try providing wrong session token
    wrong_token = SessionTokenManager.get_or_create_token("emaildoesnotexist@email.rx")
    new_password = "new_password"
    serializer3 = ChangePasswordForgotSerializer(
        data={
            "email": user_found.email,
            "session_token": wrong_token,
            "new_password": new_password,
            "confirmation_password": new_password,
        }
    )
    assert not serializer3.is_valid()

    # Try providing different passwords
    serializer3 = ChangePasswordForgotSerializer(
        data={
            "email": user_found.email,
            "session_token": session_token,
            "new_password": new_password,
            "confirmation_password": new_password + "321",
        }
    )
    assert not serializer3.is_valid()

    # Must be right
    serializer3 = ChangePasswordForgotSerializer(
        data={
            "email": user_found.email,
            "session_token": session_token,
            "new_password": new_password,
            "confirmation_password": new_password,
        }
    )
    assert serializer3.is_valid()
    user_found = serializer3.save()
    test_user.refresh_from_db()
    assert user_found == test_user
    assert check_password(new_password, test_user.password)
