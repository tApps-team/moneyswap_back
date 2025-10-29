from django.core.management.base import BaseCommand, CommandError

from django_celery_beat.models import PeriodicTask, IntervalSchedule

from general_models.utils.periodic_tasks import get_or_create_schedule


# python manage.py create_periodic_task_for_delete_reviews в docker-compose файле
# Команда для создания периодической задачи, которая проверяет и удаляет
# отклонённые отзывы и комментарии


class Command(BaseCommand):
    print('Creating Task for get xml files')

    def handle(self, *args, **kwargs):
        try:
            schedule = get_or_create_schedule(90, IntervalSchedule.SECONDS)
            PeriodicTask.objects.create(
                interval=schedule,
                name='task for get xml files',
                task='get_xml_file_for_exchangers',
            )
            pass
        except Exception as ex:
            print(ex)
            raise CommandError('Initalization failed.')