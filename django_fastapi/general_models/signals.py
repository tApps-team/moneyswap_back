from datetime import datetime

from asgiref.sync import async_to_sync

from django.contrib.auth.models import User, Group
from django.contrib.admin.models import LogEntry
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from partners.models import CustomUser

from .models import (ExchangeAdmin,
                     NewBaseComment,
                     Valute,
                     CustomOrder,
                     NewBaseReview,
                     NewBaseAdminComment)
from .utils.base import get_actual_datetime
from .utils.periodic_tasks import request_to_bot_swift_sepa
from .utils.endpoints import send_comment_notifitation_to_exchange_admin, send_comment_notifitation_to_review_owner, send_review_notifitation_to_exchange_admin


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

@receiver(pre_save, sender=NewBaseReview)
def change_time_create_for_review(sender, instance, **kwargs):
    if instance.time_create is None:
        instance.time_create = datetime.now()


@receiver(pre_save, sender=NewBaseComment)
def change_time_create_for_comment(sender, instance, **kwargs):
    if instance.time_create is None:
        instance.time_create = datetime.now()


@receiver(pre_save, sender=NewBaseAdminComment)
def change_time_create_for_admin_comment(sender, instance, **kwargs):
    if instance.time_create is None:
        instance.time_create = datetime.now()


@receiver(post_save, sender=NewBaseReview)
def send_notification_after_add_review(sender, instance, created, **kwargs):
    
    if not created and instance.moderation == True:
        # exchange_marker = 'cash'

        exchange_admin = ExchangeAdmin.objects.filter(exchange_name=instance.exchange_name)\
                                                .first()
        
        if exchange_admin:
            user_id = exchange_admin.user_id
            exchange_id = exchange_admin.exchange_id
            exchange_marker = exchange_admin.exchange_marker

            async_to_sync(send_review_notifitation_to_exchange_admin)(user_id,
                                                                      exchange_id,
                                                                      exchange_marker,
                                                                      instance.pk)
            # send notification to admin user in chat with bot
            pass


@receiver(post_save, sender=NewBaseComment)
def send_notification_after_add_comment(sender, instance, created, **kwargs):

    # print(instance)

    # print(instance.review)

    # print(instance.review.exchange_id)

    # print(instance.__dict__)
    
    if not created and instance.moderation == True:
        # exchange_marker = 'cash'

        # send notification review owner to new comment
        # async_to_sync(send_comment_notifitation_to_owner)(user_id,
        #                                                   instance.pk,
        #                                                   exchange_marker)

        exchange_admin = ExchangeAdmin.objects.filter(exchange_name=instance.review.exchange_name)\
                                                .first()
        
        if exchange_admin:
            user_id = exchange_admin.user_id
            exchange_id = exchange_admin.exchange_id
            exchange_marker = exchange_admin.exchange_marker

            # send notification to admin user in chat with bot
            async_to_sync(send_comment_notifitation_to_exchange_admin)(user_id,
                                                                       exchange_id,
                                                                       exchange_marker,
                                                                       instance.review_id)
            
            # send notification to review owner in chat with bot
        async_to_sync(send_comment_notifitation_to_review_owner)(instance.review.guest_id,
                                                                 exchange_id,
                                                                 exchange_marker,
                                                                 instance.review_id)

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
