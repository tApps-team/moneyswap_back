from django.core.management.base import BaseCommand, CommandError

from django_celery_beat.models import PeriodicTask, IntervalSchedule

from general_models.utils.periodic_tasks import get_or_create_schedule


# python manage.py create_periodic_task_for_delete_reviews в docker-compose файле
# Команда для создания периодической задачи, которая проверяет и удаляет
# отклонённые отзывы и комментарии


class Command(BaseCommand):
    print('Creating Task for delete unlinked records from DB...')

    def handle(self, *args, **kwargs):
        try:
            schedule = get_or_create_schedule(1, IntervalSchedule.HOURS) # for prod
            # schedule = get_or_create_schedule(90, IntervalSchedule.SECONDS) # for test
            PeriodicTask.objects.create(
                interval=schedule,
                name='task for delete unlinked records from db',
                task='periodic_delete_unlinked_exchange_records',
            )
            pass
        except Exception as ex:
            print(ex)
            raise CommandError('Initalization failed.')