# Generated by Django 4.2.7 on 2024-06-03 08:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('general_models', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MassSendMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Название')),
                ('content', models.TextField(verbose_name='Контент')),
            ],
        ),
    ]