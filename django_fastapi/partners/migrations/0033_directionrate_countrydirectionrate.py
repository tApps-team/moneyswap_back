# Generated by Django 4.2.7 on 2025-03-06 13:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0032_countryexchangelinkcount'),
    ]

    operations = [
        migrations.CreateModel(
            name='DirectionRate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('in_count', models.DecimalField(decimal_places=5, default=None, max_digits=20, null=True, verbose_name='Сколько отдаём')),
                ('out_count', models.DecimalField(decimal_places=5, default=None, max_digits=20, null=True, verbose_name='Сколько получаем')),
                ('min_rate_limit', models.FloatField(verbose_name='Минимальный лимит')),
                ('max_rate_limit', models.FloatField(blank=True, default=None, null=True, verbose_name='Максимальный лимит')),
                ('exchange', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exchange_rates', to='partners.exchange', verbose_name='Обменник')),
                ('exchange_direction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='direction_rates', to='partners.direction', verbose_name='Готовое направление')),
            ],
            options={
                'verbose_name': 'Объём направления',
                'verbose_name_plural': 'Объёмы направлений',
                'unique_together': {('exchange', 'exchange_direction', 'min_rate_limit')},
            },
        ),
        migrations.CreateModel(
            name='CountryDirectionRate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('in_count', models.DecimalField(decimal_places=5, default=None, max_digits=20, null=True, verbose_name='Сколько отдаём')),
                ('out_count', models.DecimalField(decimal_places=5, default=None, max_digits=20, null=True, verbose_name='Сколько получаем')),
                ('min_rate_limit', models.FloatField(verbose_name='Минимальный лимит')),
                ('max_rate_limit', models.FloatField(blank=True, default=None, null=True, verbose_name='Максимальный лимит')),
                ('exchange', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exchange_country_rates', to='partners.exchange', verbose_name='Обменник')),
                ('exchange_direction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='direction_rates', to='partners.countrydirection', verbose_name='Готовое направление')),
            ],
            options={
                'verbose_name': 'Объём направления (страны)',
                'verbose_name_plural': 'Объёмы направлений (страны)',
                'unique_together': {('exchange', 'exchange_direction', 'min_rate_limit')},
            },
        ),
    ]
