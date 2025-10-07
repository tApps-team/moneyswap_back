import json

from django_celery_beat.models import PeriodicTask, IntervalSchedule

from django.utils import timezone

from .utils.periodic_tasks import get_or_create_schedule

from .models import Exchanger


# def manage_popular_count_direction_task(fields_to_update: dict):
#     try:
#         task = PeriodicTask.objects.get(name='update_popular_count_direction_time_task')
#     except PeriodicTask.DoesNotExist:
#         pass
#     else:
#         amount = fields_to_update['amount']
#         unit_time = fields_to_update['unit_time']
#         schedule = get_or_create_schedule(amount,
#                                           UNIT_TIME_CHOICES[unit_time])
#         task.interval = schedule
#         task.save()


def manage_periodic_task_for_parse_directions(exchange_id: int,
                                              interval: int):
    '''
    Создание, изменение, остановка периодической задачи
    для парсинга направлений из XML файла обменника
    '''
    
    try:
        task = PeriodicTask.objects.get(name=f'{exchange_id} parse directions task')
    except PeriodicTask.DoesNotExist:
        if interval == 0:
            print('PASS')
            pass
        else:
            schedule = get_or_create_schedule(interval, IntervalSchedule.SECONDS)
            PeriodicTask.objects.create(
                    interval=schedule,
                    name=f'{exchange_id} parse directions task',
                    task='create_update_directions_for_exchanger',
                    args=json.dumps([exchange_id,]),
                    )
    else:
        if interval == 0:
            #остановить задачу периодических созданий готовых направлений
            task.enabled = False
            Exchanger.objects.filter(pk=exchange_id).update(is_active=False,
                                                            active_status='disabled',
                                                            time_disable=timezone.now())
        else:
            Exchanger.objects.filter(pk=exchange_id).update(active_status='active')

            task.enabled = True
            schedule = get_or_create_schedule(interval, IntervalSchedule.SECONDS)
            task.interval = schedule
        
        task.save()