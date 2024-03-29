# Generated by Django 4.2.7 on 2024-03-11 05:00

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='SimplePage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Название')),
                ('identificator', models.CharField(max_length=100, unique=True, verbose_name='Идентификатор')),
                ('title', models.TextField(verbose_name='title')),
                ('description', models.TextField(verbose_name='description')),
                ('keywords', models.TextField(verbose_name='keywords')),
                ('upper_content', models.TextField(verbose_name='upper')),
                ('lower_content', models.TextField(verbose_name='lower')),
            ],
            options={
                'verbose_name': 'Seo страница',
                'verbose_name_plural': 'Seo страницы',
            },
        ),
    ]
