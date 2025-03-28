# Generated by Django 4.2.7 on 2024-09-20 10:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0011_alter_exchange_icon_url'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exchange',
            name='icon_url',
            field=models.FileField(blank=True, default='icons/country/russia.svg', null=True, upload_to='icons/exchange/', verbose_name='Иконка обменника'),
        ),
    ]
