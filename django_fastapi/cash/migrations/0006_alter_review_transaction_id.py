# Generated by Django 4.2.7 on 2024-06-03 08:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cash', '0005_admincomment'),
    ]

    operations = [
        migrations.AlterField(
            model_name='review',
            name='transaction_id',
            field=models.CharField(blank=True, default=None, null=True, verbose_name='Номер транзакции'),
        ),
    ]
