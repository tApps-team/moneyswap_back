from django.core.management.base import BaseCommand, CommandError
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.models import LogEntry, ADDITION
from django.contrib.auth.models import Group, Permission

from no_cash.models import Exchange as NoCashExchange
from cash.models import Exchange as CashExchange
from partners.models import Exchange as PartnerExchange

# python manage.py create_moderator_group в docker-compose файле
# Команда для создания группы "Партнёры" с ограниченными правами доступа


class Command(BaseCommand):
    print('Add time create for Exchanges...')

    def handle(self, *args, **kwargs):
        update_fields = [
            'time_create',
        ]

        try:
            # for model, model_id in ((NoCashExchange, 18), (CashExchange, 24), (PartnerExchange, 33)):
            for model, model_id in ((NoCashExchange, 18), (CashExchange, 24), (PartnerExchange, 33)):
                entry_log = LogEntry.objects.filter(content_type_id=model_id,
                                                    action_flag=ADDITION).values_list('object_repr',
                                                                                      'action_time')
                entry_log_dict = {el[0]: el[-1] for el in entry_log}
                exchage_list = model.objects.all()

                update_list = []
                for exchange in exchage_list:
                    if exchange.name in entry_log_dict:
                        exchange.time_create = entry_log_dict[exchange.name]
                        update_list.append(exchange)

                model.objects.bulk_update(update_list, update_fields)

        except Exception as ex:
            print(ex)
            raise CommandError('Initalization failed.')