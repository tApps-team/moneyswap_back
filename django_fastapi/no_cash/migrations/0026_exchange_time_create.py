# Generated by Django 4.2.7 on 2025-04-14 12:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('no_cash', '0025_comment_review_from_review_review_from'),
    ]

    operations = [
        migrations.AddField(
            model_name='exchange',
            name='time_create',
            field=models.DateTimeField(auto_now_add=True, null=True, verbose_name='Время добавления'),
        ),
    ]
