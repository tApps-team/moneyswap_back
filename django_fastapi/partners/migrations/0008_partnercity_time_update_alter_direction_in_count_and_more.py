# Generated by Django 4.2.7 on 2024-04-10 09:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0007_remove_direction_fix_amount_remove_direction_percent_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='partnercity',
            name='time_update',
            field=models.DateTimeField(default=None, null=True, verbose_name='Время последнего обновления'),
        ),
        migrations.AlterField(
            model_name='direction',
            name='in_count',
            field=models.DecimalField(decimal_places=10, default=None, max_digits=20, null=True, verbose_name='Сколько отдаём'),
        ),
        migrations.AlterField(
            model_name='direction',
            name='out_count',
            field=models.DecimalField(decimal_places=10, default=None, max_digits=20, null=True, verbose_name='Сколько получаем'),
        ),
    ]