from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView

from music_player_api.views import (
    ForgotPasswordViewSet,
    GetAvailableGenres,
    PlaylistViewSet,
    RegisterAPIView,
    SearchAllPlayliststAPIView,
    SearchAllSongsAPIView,
    SearchMyPlaylistsAPIView,
    SearchMySongsAPIView,
    SongViewSet,
    UserInfoViewSet,
    change_my_password,
)

urlpatterns = [
    path("auth/get-token/", TokenObtainPairView.as_view(), name="get_token_pair"),
    path("auth/signup/", RegisterAPIView.as_view(), name="register"),
    path("auth/change-password/", change_my_password, name="change_password"),
    path(
        "auth/reset-password/",
        ForgotPasswordViewSet.as_view(
            {
                "get": "send_email",
                "post": "send_reset_code",
                "patch": "change_password",
            }
        ),
        name="reset-password",
    ),
    # User Settings Views
    path(
        "users/settings/",
        UserInfoViewSet.as_view(
            {
                "get": "get_current",
                "patch": "partial_update_current",
                "delete": "delete_current",
            }
        ),
        name="user_settings",
    ),
    # Search Views
    path("all-songs/", SearchAllSongsAPIView.as_view(), name="search_all_songs"),
    path(
        "all-playlists/",
        SearchAllPlayliststAPIView.as_view(),
        name="search_all_playlists",
    ),
    path("my-songs/", SearchMySongsAPIView.as_view(), name="search_my_songs"),
    path(
        "my-playlists/", SearchMyPlaylistsAPIView.as_view(), name="search_my_playlists"
    ),
    # Genre Views
    path(
        "get-available-genres/",
        GetAvailableGenres.as_view(),
        name="get_available_genres",
    ),
    # Song Views
    path(
        "songs/<int:pk>/",
        SongViewSet.as_view(
            {
                "get": "retrieve",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="RUD-song",
    ),
    path("songs/", SongViewSet.as_view({"post": "create"}), name="create-song"),
    # Playlist Views
    path(
        "playlists/<int:pk>/",
        PlaylistViewSet.as_view(
            {
                "get": "retrieve",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="RUD-playlist",
    ),
    path(
        "playlists/",
        PlaylistViewSet.as_view({"post": "create"}),
        name="create-playlist",
    ),
]
