# Generated by Django 4.2.7 on 2024-10-28 14:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0020_direction_max_amount_direction_min_amount'),
    ]

    operations = [
        migrations.AddField(
            model_name='partnercity',
            name='max_amount',
            field=models.FloatField(default=0, verbose_name='Максимальное количество'),
        ),
        migrations.AddField(
            model_name='partnercity',
            name='min_amount',
            field=models.FloatField(default=0, verbose_name='Минимальное количество'),
        ),
    ]