from django.contrib import admin

from music_player_api.models import Genre, Playlist, Song, SongPlaylist, User

admin.site.register(User)
admin.site.register(Song)
admin.site.register(SongPlaylist)
admin.site.register(Playlist)
admin.site.register(Genre)
