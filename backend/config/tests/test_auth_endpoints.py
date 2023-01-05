import json

import pytest
from django.contrib.auth.hashers import check_password
from faker import Faker
from music_player_api.utils import ResetCodeManager


@pytest.mark.django_db
def test_signup(client, user_factory, django_user_model):
    fake = Faker()
    user_data = user_factory.build()
    password = fake.password()
    response = client.post(
        path="/api/auth/signup/",
        data={
            "email": user_data.email,
            "password": password,
            "confirmationPassword": password,
        },
    )
    assert response.status_code == 201

    response_data = response.json()
    user = django_user_model.objects.get(email=response_data["email"])
    assert (
        response_data["email"] == user.email
        and response_data.get("access", None) is not None
    )

    # Signup with existing email
    password = fake.password()
    response = client.post(
        path="/api/auth/signup/",
        data={
            "email": user_data.email,
            "password": password,
            "confirmation_password": password,
        },
    )
    assert response.status_code == 400
    assert len(django_user_model.objects.all()) == 1


@pytest.mark.django_db
def test_get_token(client, user_factory):
    user = user_factory.create()
    password = Faker().password()
    user.set_password(password)
    assert user.check_password(password)
    user.save()

    response = client.post(
        path="/api/auth/get-token/", data={"email": user.email, "password": password}
    )
    assert response.status_code == 200
    response_data = response.json()
    assert "access" in response_data.keys()


@pytest.mark.django_db
def test_change_password(client, user_factory):
    fake = Faker()
    user = user_factory.create()
    password = fake.password()
    new_password = fake.password()
    user.set_password(password)
    assert user.check_password(password)
    user.save()

    response = client.post(
        path="/api/auth/get-token/", data={"email": user.email, "password": password}
    )
    assert response.status_code == 200
    response_data = response.json()
    assert "access" in response_data.keys()
    access_token = response_data["access"]  # token obtained

    # Unauthorized
    response = client.patch(
        path="/api/auth/change-password/",
        data={
            "password": password,
            "newPassword": new_password,
            "confirmationPassword": new_password,
        },
    )
    assert response.status_code == 401

    # Normal request
    response = client.patch(
        path="/api/auth/change-password/",
        data={
            "password": password,
            "newPassword": new_password,
            "confirmationPassword": new_password,
        },
        content_type="application/json",
        **{
            "HTTP_AUTHORIZATION": f"JWT {access_token}",
        },
    )
    assert response.status_code == 200
    password = new_password
    user.refresh_from_db()
    assert user.check_password(password)

    # Non-matching passwords
    response = client.patch(
        path="/api/auth/change-password/",
        data={
            "password": password,
            "newPassword": new_password + "nonmatch",
            "confirmationPassword": new_password,
        },
        content_type="application/json",
        **{
            "HTTP_AUTHORIZATION": f"JWT {access_token}",
        },
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_reset_password_flow(client, user_factory):
    fake = Faker()
    user = user_factory.create()
    password = fake.password()
    new_password = fake.password()
    user.set_password(password)
    assert user.check_password(password)
    user.save()

    response = client.get(path=f"/api/auth/reset-password/?email={user.email}")
    assert response.status_code == 200
    code_received = ResetCodeManager.get_or_create_code(user.email)

    response = client.post(
        path="/api/auth/reset-password/",
        data={"email": user.email, "code": code_received},
    )
    assert response.status_code == 200
    response_data = response.json()
    session_token = response_data["sessionToken"]

    response = client.patch(
        path="/api/auth/reset-password/",
        data={
            "email": user.email,
            "sessionToken": session_token,
            "newPassword": new_password,
            "confirmationPassword": new_password,
        },
        content_type="application/json",
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert check_password(new_password, user.password)
