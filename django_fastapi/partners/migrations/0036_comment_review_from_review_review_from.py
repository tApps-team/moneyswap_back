# Generated by Django 4.2.7 on 2025-04-11 09:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0035_exchange_high_aml_alter_countrydirection_direction_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='review_from',
            field=models.CharField(choices=[('bestchange', 'bestchange'), ('moneyswap', 'moneyswap')], default='moneyswap', max_length=50, verbose_name='Откуда отзыв'),
        ),
        migrations.AddField(
            model_name='review',
            name='review_from',
            field=models.CharField(choices=[('bestchange', 'bestchange'), ('moneyswap', 'moneyswap')], default='moneyswap', max_length=50, verbose_name='Откуда отзыв'),
        ),
    ]
