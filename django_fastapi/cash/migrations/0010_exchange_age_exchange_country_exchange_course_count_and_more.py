# Generated by Django 4.2.7 on 2024-09-12 11:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cash', '0009_alter_populardirection_directions'),
    ]

    operations = [
        migrations.AddField(
            model_name='exchange',
            name='age',
            field=models.CharField(blank=True, default=None, max_length=255, null=True, verbose_name='Возраст'),
        ),
        migrations.AddField(
            model_name='exchange',
            name='country',
            field=models.CharField(blank=True, default=None, max_length=255, null=True, verbose_name='Страна'),
        ),
        migrations.AddField(
            model_name='exchange',
            name='course_count',
            field=models.IntegerField(blank=True, default=None, null=True, verbose_name='Количество курсовдля обмена'),
        ),
        migrations.AddField(
            model_name='exchange',
            name='reserve_amount',
            field=models.CharField(blank=True, default=None, max_length=255, null=True, verbose_name='Сумма резерва'),
        ),
    ]
