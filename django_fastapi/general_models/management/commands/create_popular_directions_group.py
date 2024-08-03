from django.core.management.base import BaseCommand, CommandError

from cash.models import PopularDirection as CashPopularDirection
from no_cash.models import PopularDirection as NoCashPopularDirection



class Command(BaseCommand):
    print('Creating Popular Directions Groups...')

    def handle(self, *args, **kwargs):
        try:
            CashPopularDirection.objects.create(name='Наличные полулярные направления')
            NoCashPopularDirection.objects.create(name='Безналичные полулярные направления')            

        except Exception as ex:
            print(ex)
            raise CommandError('Initalization failed.')