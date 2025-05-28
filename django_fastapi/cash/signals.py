from datetime import datetime

from asgiref.sync import async_to_sync

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver

from django_celery_beat.models import PeriodicTask

from general_models.utils.endpoints import send_review_notifitation_to_exchange_admin
from general_models.utils.base import get_actual_datetime

from general_models.models import ExchangeAdmin

from .models import Exchange, Direction, ExchangeDirection, Review, Comment, AdminComment
from .periodic_tasks import (manage_periodic_task_for_create,
                             manage_periodic_task_for_update,
                             manage_periodic_task_for_parse_black_list)


#Сигнал для добавления поля "display_name" в экземпляр Direction
#перед созданием записи в БД
@receiver(pre_save, sender=Direction)
def add_display_name_for_direction(sender, instance, **kwargs):
    instance.display_name = instance.valute_from.code_name + ' -> ' + instance.valute_to.code_name


#Сигнал для попытке создания обратного направления
#при создании направления в БД
@receiver(post_save, sender=Direction)
def try_create_reverse_direction(sender, instance, **kwargs):
    valute_from_id = instance.valute_from_id
    valute_to_id = instance.valute_to_id

    if not Direction.objects.filter(valute_from_id=valute_to_id,
                                    valute_to_id=valute_from_id)\
                            .exists() and instance.valute_to.type_valute != 'ATM QR':
        
        try:
            Direction.objects.create(valute_from_id=valute_to_id,
                                    valute_to_id=valute_from_id)
        except Exception:
            pass

#Сигнал для удаления всех связанных готовых направлений
#при удалении направления из БД
# @receiver(post_delete, sender=Direction)
# def delete_directions_from_exchanges(sender, instance, **kwargs):
#     direction_list = ExchangeDirection.objects.filter(valute_from=instance.valute_from,
#                                                       valute_to=instance.valute_to).all()
#     direction_list.delete()


#Сигнал для добавления поля en_name обменника
#перед созданием в БД
@receiver(pre_save, sender=Exchange)
def add_en_name_for_exchange(sender, instance, **kwargs):
    if instance.en_name is None:
        instance.en_name = instance.name


#Сигнал для создания периодических задач
#при создании обменника в БД
@receiver(post_save, sender=Exchange)
def create_tasks_for_exchange(sender, instance, created, **kwargs):
    if created:
        print('CASH PERIODIC TASKS CREATING...')
        manage_periodic_task_for_create(instance.pk,
                                        instance.name,
                                        instance.period_for_create)
        manage_periodic_task_for_update(instance.pk,
                                        instance.name,
                                        instance.period_for_update)
        manage_periodic_task_for_parse_black_list(instance.pk,
                                                  instance.name,
                                                  instance.period_for_parse_black_list)


#Сигнал для удаления периодических задач
#при удалении обменника из БД
@receiver(post_delete, sender=Exchange)
def delete_task_for_exchange(sender, instance, **kwargs):
    PeriodicTask.objects.filter(name__startswith=f'{instance.pk} cash').delete()


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


@receiver(post_save, sender=Review)
def create_tasks_for_exchange(sender, instance, created, **kwargs):
    
    if not created and instance.moderation == True:
        exchange_marker = 'cash'

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


@receiver(post_save, sender=Comment)
def create_tasks_for_exchange(sender, instance, created, **kwargs):

    print(instance)

    print(instance.review)

    print(instance.review.exchange_id)

    print(instance.__dict__)
    
    if not created and instance.moderation == True:
        exchange_marker = 'cash'

        # send notification review owner to new comment
        # async_to_sync(send_comment_notifitation_to_owner)(user_id,
        #                                                   instance.pk,
        #                                                   exchange_marker)

        exchange_admin = ExchangeAdmin.objects.filter(exchange_id=instance.exchange_id,
                                                      exchange_marker=exchange_marker).first()
        
        if exchange_admin:
            user_id = exchange_admin.user_id

            # send notification to admin user in chat with bot
            async_to_sync(send_review_notifitation_to_exchange_admin)(user_id,
                                                                      instance.pk,
                                                                      exchange_marker)