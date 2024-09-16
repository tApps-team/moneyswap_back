from django.core.management.base import BaseCommand, CommandError

from django_celery_beat.models import IntervalSchedule, PeriodicTask

from general_models.utils.periodic_tasks import get_or_create_schedule


#Скрипт для создания периодической задачи для парсинга
#актуальной информации об обменниках
# python manage.py create_periodic_task_for_update_exchange_info в docker-compose файле


class Command(BaseCommand):
    print('Creating periodic task for parse actual info to exchanges...')

    def handle(self, *args, **kwargs):
        try:
            schedule = get_or_create_schedule(30, IntervalSchedule.SECONDS)
            PeriodicTask.objects.create(
                    interval=schedule,
                    name='parse_actual_exchanges_info_task',
                    task='parse_actual_exchanges_info',
                    )
        except Exception as ex:
            print(ex)
            raise CommandError('Initalization failed.')