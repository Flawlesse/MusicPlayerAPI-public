import pytest
from faker import Faker


@pytest.mark.django_db
def test_user_settings(client, user_factory):
    user = user_factory.create()
    password = Faker().password()
    user.set_password(password)
    assert user.check_password(password)
    user.save()

    access_token = client.post(
        "/api/auth/get-token/", {"email": user.email, "password": password}
    ).json()["access"]

    response = client.get(
        "/api/users/settings/",
        content_type="application/json",
        **{
            "HTTP_AUTHORIZATION": f"JWT {access_token}",
        },
    )
    assert response.status_code == 200
    user_data = response.json()
    assert (
        user_data["email"] == user.email
        and user_data["firstName"] == user.first_name
        and user_data["lastName"] == user.last_name
    )

    fake = Faker()
    new_first_name = fake.first_name()
    new_last_name = fake.last_name()

    response = client.patch(
        path="/api/users/settings/",
        data={
            "first_name": new_first_name,
            "last_name": new_last_name,
        },
        content_type="application/json",
        **{
            "HTTP_AUTHORIZATION": f"JWT {access_token}",
        },
    )
    assert response.status_code == 200
    user_data = response.json()
    user.refresh_from_db()
    assert (
        user_data["email"] == user.email
        and user_data["firstName"] == user.first_name
        and user_data["lastName"] == user.last_name
    )

    new_last_name = "Sidorovich"
    response = client.patch(
        path="/api/users/settings/",
        data={
            "last_name": new_last_name,
        },
        content_type="application/json",
        **{
            "HTTP_AUTHORIZATION": f"JWT {access_token}",
        },
    )
    assert response.status_code == 200
    user_data = response.json()
    user.refresh_from_db()
    assert (
        user_data["email"] == user.email
        and user_data["firstName"] == user.first_name
        and user_data["lastName"] == user.last_name
    )
