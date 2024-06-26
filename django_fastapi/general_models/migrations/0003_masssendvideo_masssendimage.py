# Generated by Django 4.2.7 on 2024-06-03 08:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('general_models', '0002_masssendmessage'),
    ]

    operations = [
        migrations.CreateModel(
            name='MassSendVideo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('video', models.FileField(upload_to='mass_send/videos/', verbose_name='Видео')),
                ('messsage', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='videos', to='general_models.masssendmessage', verbose_name='Cообщение')),
            ],
        ),
        migrations.CreateModel(
            name='MassSendImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='mass_send/images/', verbose_name='Изображение')),
                ('messsage', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='general_models.masssendmessage', verbose_name='Cообщение')),
            ],
        ),
    ]
