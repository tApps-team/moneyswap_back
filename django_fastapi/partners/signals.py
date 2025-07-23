from datetime import datetime

from asgiref.sync import async_to_sync

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone

from django_celery_beat.models import IntervalSchedule, PeriodicTask

from general_models.utils.endpoints import send_review_notifitation_to_exchange_admin
from general_models.utils.base import get_actual_datetime, UNIT_TIME_CHOICES
from general_models.utils.periodic_tasks import get_or_create_schedule
from general_models.models import ExchangeAdmin, PartnerTimeUpdate

from .models import Direction, Exchange, Review, Comment, AdminComment, PartnerCountry, PartnerCity


# Сигнал для создания периодической задачи, которая проверяет
# партнёрские направления на активность, если направление не изменялось
# более 3 дней, направление становится неактивным
@receiver(post_save, sender=PartnerTimeUpdate)
def create_custom_user_for_user(sender, instance, created, **kwargs):
    if instance.name != 'Управление временем жизни направлений':
        if created:
            amount = instance.amount
            unit_time = instance.unit_time

            schedule = get_or_create_schedule(amount,
                                              UNIT_TIME_CHOICES[unit_time])
            match instance.name:
                case 'Управление временем проверки активности направлений':
                    task_name = 'check_update_time_for_directions_task'
                    background_task = 'check_update_time_for_directions'
                case 'Управление временем обнуления популярности направления':
                    task_name = 'update_popular_count_direction_time_task'
                    background_task = 'update_popular_count_direction_time'

            PeriodicTask.objects.create(
                    interval=schedule,
                    name=task_name,
                    task=background_task,
                    )


#Сигнал для добавления поля en_name обменника
#перед созданием в БД
@receiver(pre_save, sender=Exchange)
def add_en_name_for_exchange(sender, instance, **kwargs):
    if not instance.en_name:
        instance.en_name = instance.name


#Сигнал для автоматической установки времени
#по московскому часовому поясу при создании отзыва в БД
@receiver(pre_save, sender=Review)
def change_time_create_for_review(sender, instance, **kwargs):
    if instance.time_create is None:
        instance.time_create = datetime.now()


#Сигнал для автоматической установки времени
#по московскому часовому поясу при создании комментария в БД
@receiver(pre_save, sender=Comment)
def change_time_create_for_comment(sender, instance, **kwargs):
    if instance.time_create is None:
        instance.time_create = datetime.now()


#Сигнал для автоматической установки времени
#по московскому часовому поясу при создании комментария
#администрации в БД
@receiver(pre_save, sender=AdminComment)
def change_time_create_for_comment(sender, instance, **kwargs):
    if instance.time_create is None:
        instance.time_create = datetime.now()


# @receiver(pre_save, sender=Direction)
# def change_time_create_for_direction(sender, instance, **kwargs):
#     if instance.time_update is None:
#         instance.time_update = get_actual_datetime()

@receiver(post_save, sender=Review)
def send_notification_after_add_review(sender, instance, created, **kwargs):
    
    if not created and instance.moderation == True:
        exchange_marker = 'partner'

        exchange_admin = ExchangeAdmin.objects.filter(exchange_id=instance.exchange_id,
                                                      exchange_marker=exchange_marker).first()
        
        if exchange_admin:
            user_id = exchange_admin.user_id

            async_to_sync(send_review_notifitation_to_exchange_admin)(user_id,
                                                                      instance.exchange.id,
                                                                      instance.pk,
                                                                      exchange_marker)
            # send notification to admin user in chat with bot
            pass


@receiver(pre_save, sender=PartnerCountry)
def auto_time_update_for_partner_country(sender, instance, **kwargs):
    instance.time_update = timezone.now()


@receiver(pre_save, sender=PartnerCity)
def auto_time_update_for_partner_country(sender, instance, **kwargs):
    instance.time_update = timezone.now()

# @receiver(post_save, sender=Comment)
# def create_tasks_for_exchange(sender, instance, created, **kwargs):

#     # print(instance)

#     # print(instance.review)

#     # print(instance.review.exchange_id)

#     # print(instance.__dict__)
    
#     if not created and instance.moderation == True:
#         exchange_marker = 'cash'

#         # send notification review owner to new comment
#         # async_to_sync(send_comment_notifitation_to_owner)(user_id,
#         #                                                   instance.pk,
#         #                                                   exchange_marker)

#         exchange_admin = ExchangeAdmin.objects.filter(exchange_id=instance.review.exchange_id,
#                                                       exchange_marker=exchange_marker).first()
        
#         if exchange_admin:
#             user_id = exchange_admin.user_id

#             # send notification to admin user in chat with bot
#             async_to_sync(send_comment_notifitation_to_exchange_admin)(user_id,
#                                                                        instance.pk,
#                                                                        exchange_marker)
            
#             # send notification to review owner in chat with bot
#         async_to_sync(send_comment_notifitation_to_review_owner)(instance.review.guest_id,
#                                                                  instance.pk,
#                                                                  exchange_marker)