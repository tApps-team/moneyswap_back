import requests

from time import sleep
from datetime import datetime

from celery import shared_task

from django.db.models import Q
from django.db import transaction

from general_models.utils.base import get_timedelta

from cash.models import Direction

from .models import Direction as PartnerDirection, CountryDirection, NonCashDirection


@shared_task(name='parse_cash_courses',
             soft_time_limit=120,
             time_limit=150)
def parse_cash_courses():
    limit_direction = Q(valute_from__type_valute='Криптовалюта',
                        valute_to__type_valute='Наличные') | \
                        Q(valute_from__type_valute='Наличные',
                            valute_to__type_valute='Криптовалюта')
    directions = Direction.objects\
                            .select_related('valute_from', 'valute_to')\
                            .filter(limit_direction).all()
    if directions:
        for direction in directions:
            valid_direction_name = direction.display_name.replace('CASH','')

            valute_list = valid_direction_name.split(' -> ')

            valute_from, valute_to = ['USDT' if valute.startswith('USDT') else valute\
                                        for valute in valute_list]

            try:
                resp = requests.get(
                    f'https://api.coinbase.com/v2/prices/{valute_from}-{valute_to}/spot',
                    timeout=5,
                    )
            except Exception:
                continue
            else:
                try:
                    json_resp = resp.json()
                    actual_course = json_resp['data']['amount']
                    # print(valid_direction_name, actual_course)
                    direction.actual_course = actual_course
                    direction.save()
                except Exception:
                    pass
            sleep(0.4)


@shared_task(name='check_update_time_for_directions')
def check_update_time_for_directions():
    time_delta = get_timedelta()
    check_time = datetime.now() - time_delta
    
    with transaction.atomic():
        PartnerDirection.objects\
                        .filter(time_update__lt=check_time)\
                        .update(is_active=False)
        
        CountryDirection.objects\
                        .filter(time_update__lt=check_time)\
                        .update(is_active=False)
        
        NonCashDirection.objects\
                        .filter(time_update__lt=check_time)\
                        .update(is_active=False)