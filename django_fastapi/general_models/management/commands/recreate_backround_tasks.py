from django.core.management.base import BaseCommand, CommandError

from django_celery_beat.models import IntervalSchedule, PeriodicTask

from general_models.utils.periodic_tasks import get_or_create_schedule


#Скрипт для пересоздания периодических задач
#создание, обновление и парсинг черного списка обменников
# python manage.py create_periodic_task_for_parse_no_cash_course в docker-compose файле


class Command(BaseCommand):
    print('Recreate backround tasks...')

    def handle(self, *args, **kwargs):
        try:
            from django_celery_beat.models import PeriodicTask, IntervalSchedule

            PeriodicTask.objects.filter(name__icontains='cash').delete()
            PeriodicTask.objects.filter(name__icontains='no_cash').delete()

            from no_cash import models as no_cash_models, periodic_tasks as no_cash_periodic_tasks
            from cash import models as cash_models, periodic_tasks as cash_periodic_tasks

            import no_cash, cash

            for model in (no_cash, cash):
                model_exchanges = model.models.Exchange.objects.all()

                for exchange in model_exchanges:
                    model.periodic_tasks.manage_periodic_task_for_create(exchange.id,
                                                                        exchange.name,
                                                                        90)
                    model.periodic_tasks.manage_periodic_task_for_update(exchange.id,
                                                                        exchange.name,
                                                                        60)
                    model.periodic_tasks.manage_periodic_task_for_parse_black_list(exchange.id,
                                                                                    exchange.name,
                                                                                    24)

        except Exception as ex:
            print(ex)
            raise CommandError('Initalization failed.')