# Generated by Django 4.2.7 on 2024-08-05 15:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0007_alter_review_transaction_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='partnercity',
            name='working_days',
            field=models.ManyToManyField(related_name='working_days_cities', to='partners.workingday', verbose_name='Рабочие дни'),
        ),
    ]