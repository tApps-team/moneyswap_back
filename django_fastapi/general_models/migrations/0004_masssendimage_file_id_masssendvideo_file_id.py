# Generated by Django 4.2.7 on 2024-06-05 09:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('general_models', '0003_masssendvideo_masssendimage'),
    ]

    operations = [
        migrations.AddField(
            model_name='masssendimage',
            name='file_id',
            field=models.CharField(blank=True, default=None, max_length=255, null=True, verbose_name='ID файла'),
        ),
        migrations.AddField(
            model_name='masssendvideo',
            name='file_id',
            field=models.CharField(blank=True, default=None, max_length=255, null=True, verbose_name='ID файла'),
        ),
    ]
