# Generated by Django 4.1 on 2022-08-19 11:17

from django.db import migrations, models
import music_player_api.utils


class Migration(migrations.Migration):

    dependencies = [
        ('music_player_api', '0002_playlist_song_songplaylist_playlist_songs_genre'),
    ]

    operations = [
        migrations.AddField(
            model_name='song',
            name='audio_file',
            field=models.FileField(blank=True, null=True, upload_to=music_player_api.utils.upload_audio_to),
        ),
        migrations.AddField(
            model_name='song',
            name='cover_img',
            field=models.ImageField(blank=True, null=True, upload_to=music_player_api.utils.upload_coverimg_to),
        ),
        migrations.AddField(
            model_name='song',
            name='lyrics',
            field=models.TextField(blank=True),
        ),
    ]
