from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import filters, viewsets
from rest_framework.decorators import (
    action,
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.generics import CreateAPIView, GenericAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from music_player_api.models import Genre, Playlist, Song, SongPlaylist
from music_player_api.permissions import IsSameUserOrReadonly
from music_player_api.serializers import (
    ChangePasswordForgotSerializer,
    ChangePasswordSerializer,
    CodeWithEmailSerializer,
    CreateSongSerializer,
    CreateUpdatePlaylistSerializer,
    EditSongSerializer,
    FindEmailSerializer,
    GetDeepPlaylistSerializer,
    GetFlatPlaylistSerializer,
    GetFlatSongSerializer,
    GetGenreSerializer,
    GetSongSerializer,
    RegisterUserSerializer,
    UserInfoSerializer,
)

User = get_user_model()


# User model views


class RegisterAPIView(CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterUserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        user = serializer.instance
        access_token = str(AccessToken.for_user(user))
        refresh_token = str(RefreshToken.for_user(user))

        return Response(
            {**serializer.data, "access": access_token, "refresh": refresh_token},
            status=201,
            headers=headers,
        )


@api_view(["PATCH"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def change_my_password(request):
    serializer = ChangePasswordSerializer(
        request.user,
        data=request.data,
        partial=True,
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response({"message": "Successfully changed password."}, 200)


class UserInfoViewSet(viewsets.GenericViewSet):
    queryset = User.objects.all()
    serializer_class = UserInfoSerializer
    permission_classes = (IsAuthenticated,)

    @action(detail=False, methods=["get"])
    def get_current(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=["patch"])
    def partial_update_current(self, request):
        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, 200)

    @action(detail=False, methods=["delete"])
    def delete_current(self, request):
        request.user.delete()
        return Response({"success": "User successfully deleted."}, 204)


class ForgotPasswordViewSet(viewsets.GenericViewSet):
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.action == "change_password":
            return ChangePasswordForgotSerializer
        elif self.action == "send_reset_code":
            return CodeWithEmailSerializer
        else:
            return FindEmailSerializer

    @action(detail=False, methods=["get"])
    def send_email(self, request):
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"success": f"Successfully sent a reset code to {user.email}."}, status=200
        )

    @action(detail=False, methods=["post"])
    def send_reset_code(self, request):
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        session_token = serializer.save()
        return Response(
            {"session_token": f"{session_token}"},
            status=200,
        )

    @action(detail=False, methods=["patch"])
    def change_password(self, request):
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"success": f"Successfully changed password for {user.email}."}, status=200
        )


# Search related views
class SearchAllPlayliststAPIView(ListAPIView):
    queryset = Playlist.objects.all()
    serializer_class = GetFlatPlaylistSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "songs__title", "songs__author", "songs__genres__name"]
    ordering_fields = ["id"]
    ordering = ["-id"]


class SearchMyPlaylistsAPIView(ListAPIView):
    serializer_class = GetFlatPlaylistSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "songs__title", "songs__author", "songs__genres__name"]
    ordering_fields = ["id"]
    ordering = ["-id"]

    def get_queryset(self):
        return self.request.user.playlists.all()


class SearchAllSongsAPIView(ListAPIView):
    queryset = Song.objects.all()
    serializer_class = GetFlatSongSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "genres__name", "author"]
    ordering_fields = ["id"]
    ordering = ["-id"]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["user"] = self.request.user
        return context


class SearchMySongsAPIView(ListAPIView):
    serializer_class = GetFlatSongSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    permission_classes = [IsAuthenticated]
    search_fields = ["title", "genres__name", "author"]
    ordering_fields = ["id"]
    ordering = ["-id"]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["user"] = self.request.user
        return context

    def get_queryset(self):
        return self.request.user.songs.all()


# Genres model views


class GetAvailableGenres(ListAPIView):
    pagination_class = None
    queryset = Genre.objects.all()
    serializer_class = GetGenreSerializer


# Song model views


class SongViewSet(viewsets.ModelViewSet):
    queryset = Song.objects.all()

    def get_permissions(self):
        if self.action in ("retrieve", "create"):
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsSameUserOrReadonly]
        return [permission() for permission in permission_classes]

    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

    def get_serializer_class(self):
        if self.action == "partial_update":
            return EditSongSerializer
        elif self.action == "create":
            return CreateSongSerializer
        return GetSongSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["user"] = self.request.user
        return context


# Playlist model views


class PlaylistViewSet(viewsets.GenericViewSet):
    queryset = Playlist.objects.all()

    def get_permissions(self):
        if self.action in ("retrieve", "create"):
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsSameUserOrReadonly]
        return [permission() for permission in permission_classes]

    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

    @action(detail=True, methods=["get"])
    def retrieve(self, request, pk=None):
        playlist = self.get_object()
        serializer = GetDeepPlaylistSerializer(
            instance=playlist, context={"user": request.user}
        )
        return Response(serializer.data, 200)

    @action(detail=False, methods=["post"])
    def create(self, request):
        serializer = CreateUpdatePlaylistSerializer(
            data=request.data, context={"user": request.user}
        )
        serializer.is_valid(raise_exception=True)
        playlist = serializer.save()
        response_serializer = GetDeepPlaylistSerializer(
            instance=playlist, context={"user": request.user}
        )
        return Response(response_serializer.data, 201)

    @action(detail=True, methods=["patch"])
    def partial_update(self, request, pk=None):
        playlist = self.get_object()
        serializer = CreateUpdatePlaylistSerializer(
            data=request.data, context={"playlist": playlist}, partial=True
        )
        serializer.is_valid(raise_exception=True)
        playlist = serializer.save()
        response_serializer = GetDeepPlaylistSerializer(
            instance=playlist, context={"user": request.user}
        )
        return Response(response_serializer.data, 200)

    @action(detail=True, methods=["delete"])
    def destroy(self, request, pk=None):
        playlist = self.get_object()
        playlist.delete()
        return Response({"success": "Playlist deleted successfully."}, 204)
