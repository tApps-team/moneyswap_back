from django.core.management.base import BaseCommand, CommandError

from django_celery_beat.models import IntervalSchedule, PeriodicTask

from general_models.utils.periodic_tasks import get_or_create_schedule


#Скрипт для создания периодической задачи для парсинга
#актуального курса безналичных направлений
# python manage.py create_periodic_task_for_parse_no_cash_course в docker-compose файле


class Command(BaseCommand):
    print('Creating periodic task for parse actual courses...')

    def handle(self, *args, **kwargs):
        try:
            schedule = get_or_create_schedule(60, IntervalSchedule.SECONDS)
            PeriodicTask.objects.create(
                    interval=schedule,
                    name='parse_actual_course_task',
                    task='parse_actual_courses',
                    )
        except Exception as ex:
            print(ex)
            raise CommandError('Initalization failed.')