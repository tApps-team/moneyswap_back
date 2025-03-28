from datetime import datetime

from django.contrib.auth.models import User, Group
from django.contrib.admin.models import LogEntry
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from partners.models import CustomUser

from .models import Valute, CustomOrder
from .utils.base import get_actual_datetime
from .utils.periodic_tasks import request_to_bot_swift_sepa


#Сигнал для автоматической установки английского названия
#валюты(если оно не указано) при создании валюты в БД
@receiver(pre_save, sender=Valute)
def add_en_name_to_valute_obj(sender, instance, **kwargs):
    if instance.en_name is None:
        instance.en_name = instance.name


#Сигнал для создания корректного пользователя админ панели
@receiver(pre_save, sender=User)
def add_fields_for_user(sender, instance, **kwargs):
    if not instance.is_superuser:
        instance.is_active = True
        instance.is_staff = True


@receiver(pre_save, sender=CustomOrder)
def premoderation_custom_order(sender, instance, **kwargs):
    if instance.moderation and instance.status == 'Модерация':
        # print('True')
        instance.status = 'В обработке'

        user_id = instance.guest_id

        data = {
            'user_id': instance.guest_id,
            'order_id': instance.pk,
        }
        try:
            request_to_bot_swift_sepa(data)
        except Exception as ex:
            print(ex)
            pass
        else:
            instance.status = 'Завершен'
        # print(user_id)


#Сигнал для создания связующей модели (пользователь + наличный обменник)
#при создании модели пользователя админ панели
#и ограничения прав доступа созданного пользователя
# @receiver(post_save, sender=User)
# def create_custom_user_for_user(sender, instance, created, **kwargs):
#     if created:
#         if not instance.is_superuser:
#             moderator_group = Group.objects.get(name='Партнёры')
#             instance.groups.add(moderator_group)
#             CustomUser.objects.create(user=instance)
