# Generated by Django 4.2.7 on 2024-10-07 10:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('general_models', '0010_feedbackform'),
    ]

    operations = [
        migrations.AlterField(
            model_name='feedbackform',
            name='time_create',
            field=models.DateTimeField(auto_created=True, verbose_name='Время создания'),
        ),
    ]
