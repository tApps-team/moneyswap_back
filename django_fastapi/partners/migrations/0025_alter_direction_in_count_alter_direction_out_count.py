# Generated by Django 4.2.7 on 2024-11-12 08:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0024_alter_exchange_partner_link_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='direction',
            name='in_count',
            field=models.DecimalField(decimal_places=5, default=None, max_digits=20, null=True, verbose_name='Сколько отдаём'),
        ),
        migrations.AlterField(
            model_name='direction',
            name='out_count',
            field=models.DecimalField(decimal_places=5, default=None, max_digits=20, null=True, verbose_name='Сколько получаем'),
        ),
    ]
