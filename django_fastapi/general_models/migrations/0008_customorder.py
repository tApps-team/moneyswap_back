# Generated by Django 4.2.7 on 2024-06-20 13:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('general_models', '0007_guest_first_name_guest_is_active_guest_is_premium_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_type', models.CharField(max_length=255, verbose_name='Тип заявки')),
                ('country', models.CharField(max_length=255, verbose_name='Страна')),
                ('amount', models.CharField(max_length=255, verbose_name='Сумма')),
                ('comment', models.TextField(verbose_name='Комментарий')),
                ('time_create', models.DateTimeField(auto_now_add=True, verbose_name='Время создания')),
                ('guest', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='custom_orders', to='general_models.guest')),
            ],
            options={
                'verbose_name': 'Завка пользователя',
                'verbose_name_plural': 'Заявки пользователей',
                'ordering': ('-time_create',),
            },
        ),
    ]