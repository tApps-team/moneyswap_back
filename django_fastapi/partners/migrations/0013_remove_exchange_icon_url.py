# Generated by Django 4.2.7 on 2024-09-20 10:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0012_alter_exchange_icon_url'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='exchange',
            name='icon_url',
        ),
    ]
