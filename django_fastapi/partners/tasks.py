import requests

from time import sleep
from datetime import datetime, timedelta

from celery import shared_task

from django.db.models import Q, Prefetch
from django.db import transaction

from django.utils import timezone

from asgiref.sync import async_to_sync

from general_models.utils.base import get_timedelta, get_valid_active_direction_str

from general_models.models import ExchangeAdmin, NewExchangeAdmin, Exchanger

from cash.models import Direction

import partners.models as partner_models

from .models import Direction as PartnerDirection, CountryDirection, NonCashDirection, Exchange

from .utils.endpoints import (request_to_bot_exchange_admin_direction_notification,
                              new_request_to_bot_exchange_admin_direction_notification)


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
    # check_time = datetime.now() - time_delta
    
    # with transaction.atomic():
    #     PartnerDirection.objects\
    #                     .filter(time_update__lt=check_time)\
    #                     .update(is_active=False)
        
    #     CountryDirection.objects\
    #                     .filter(time_update__lt=check_time)\
    #                     .update(is_active=False)
        
    #     NonCashDirection.objects\
    #                     .filter(time_update__lt=check_time)\
    #                     .update(is_active=False)
    
    # new
    check_time = timezone.now() - time_delta
    
    with transaction.atomic():
        partner_models.NewDirection.objects\
                        .filter(time_update__lt=check_time)\
                        .update(is_active=False)
        
        partner_models.NewCountryDirection.objects\
                        .filter(time_update__lt=check_time)\
                        .update(is_active=False)
        
        partner_models.NewNonCashDirection.objects\
                        .filter(time_update__lt=check_time)\
                        .update(is_active=False)


# @shared_task(name='exchange_admin_notifications')
# def exchange_admin_notifications():
#     partner_exchange_admins = ExchangeAdmin.objects.filter(exchange_marker='partner',
#                                                            notification=True)\
#                                                     .values_list('exchange_id', 'user_id')
    
#     # print('sql' ,partner_exchange_admins)
    
#     partner_exchange_admin_dict = {el[0]: el[-1] for el in partner_exchange_admins}

#     # print('dict',partner_exchange_admin_dict)
#     prefetch_timedetla = timezone.now() - timedelta(days=2,
#                                                     hours=12)
    
#     prefetch_city_direction_query = Prefetch('city_directions',
#                                              queryset=PartnerDirection.objects.select_related('direction__valute_from',
#                                                                                        'direction__valute_to',
#                                                                                        'city__city',
#                                                                                        'city__exchange')\
#                                                                         .filter(Q(is_active=False) | \
#                                                                                 Q(is_active=True,
#                                                                                   time_update__lte=prefetch_timedetla)))

#     prefetch_country_direction_query = Prefetch('country_directions',
#                                              queryset=CountryDirection.objects.select_related('direction__valute_from',
#                                                                                               'direction__valute_to',
#                                                                                               'country__country',
#                                                                                               'country__exchange')\
#                                                                         .filter(Q(is_active=False) | \
#                                                                                 Q(is_active=True,
#                                                                                   time_update__lte=prefetch_timedetla)))

#     prefetch_noncash_direction_query = Prefetch('no_cash_directions',
#                                              queryset=NonCashDirection.objects.select_related('direction__valute_from',
#                                                                                               'direction__valute_to',
#                                                                                               'exchange')\
#                                                                         .filter(Q(is_active=False) | \
#                                                                                 Q(is_active=True,
#                                                                                   time_update__lte=prefetch_timedetla)))

#     exchange_list = Exchange.objects.filter(pk__in=list(partner_exchange_admin_dict.keys())).prefetch_related(prefetch_city_direction_query,
#                                                                                                               prefetch_country_direction_query,
#                                                                                                               prefetch_noncash_direction_query)
#     # exchange_list = Exchange.objects.prefetch_related(prefetch_city_direction_query,
#     #                                                   prefetch_country_direction_query,
#     #                                                   prefetch_noncash_direction_query).all()

#     # exchange_list = Exchange.objects.prefetch_related(prefetch_noncash_direction_query).all()


#     for exchange in exchange_list:
#         print(exchange)

#         # if exchange.name != 'test_ex':
#         #     continue

#         # без доп SQL запросов
#         city_direction_count = len(exchange.city_directions.all())
#         country_direction_count = len(exchange.country_directions.all())
#         no_cash_direction_count = len(exchange.no_cash_directions.all())

#         total_count = city_direction_count + country_direction_count \
#                         + no_cash_direction_count
        
#         _text = f'🔔 <b>Уведомление об актуализации курсов направлений обменника <u>{exchange.name}</u></b> \n\n'
#         _text += f'Кол-во направлений, требующих внимания: {total_count}\n\nИз них: \n- направлений на уровне городов - {city_direction_count}\n- направлений на уровне стран - {country_direction_count}\n- безналичных направлений - {no_cash_direction_count}'
#         # print(f'Кол-во направлений, требующих наблюдений или обновлений: {total_count}')
#         # print('активные направления города', active_city_direction_count)
#         # print(f'Из них {city_direction_count} направлений на уровне городов, {country_direction_count} на уровне стран, {no_cash_direction_count} безналичных направлений')

#         if total_count == 0:
#             continue

#         default_slice = 5

#         city_active_list = []
#         city_unactive_list = []

#         for c in exchange.city_directions.all():
#             if c.is_active:
#                 city_active_list.append(c)
#             else:
#                 city_unactive_list.append(c)

#         # city_active_directions_text = '\n\n'.join(f'{direction} (активно✅, отключится через {direction.time_update - (timezone.now() - timedelta(days=3))}🕚)' for direction in city_active_list[:default_slice])
#         city_active_directions_text = '\n\n'.join(f'{get_valid_active_direction_str(direction)}' for direction in city_active_list[:default_slice])

#         if len(city_active_list[default_slice:]):
#             city_active_directions_text += f'\n <i>** <u>и еще {len(city_active_list[default_slice:])} активных направлений</u></i>'

#         city_unactive_directions_text = '\n\n'.join(f'{direction} (выключено❗️)' for direction in city_unactive_list[:default_slice])

#         if len(city_unactive_list[default_slice:]):
#             city_unactive_directions_text += f'\n <i>** <u>и еще {len(city_unactive_list[default_slice:])} неактивных направлений</u></i>'

#         country_active_list = []
#         country_unactive_list = []

#         for c in exchange.country_directions.all():
#             if c.is_active:
#                 country_active_list.append(c)
#             else:
#                 country_unactive_list.append(c)

#         # country_active_directions_text = '\n\n'.join(f'{direction} (активно✅, отключится через {direction.time_update - (timezone.now() - timedelta(days=3))}🕚)' for direction in country_active_list[:default_slice])
#         country_active_directions_text = '\n\n'.join(f'{get_valid_active_direction_str(direction)}' for direction in country_active_list[:default_slice])

#         if len(country_active_list[default_slice:]):
#             country_active_directions_text += f'\n <i>** <u>и еще {len(country_active_list[default_slice:])} активных направлений</u></i>'

#         country_unactive_directions_text = '\n\n'.join(f'{direction} (выключено❗️)' for direction in country_unactive_list[:default_slice])

#         if len(country_unactive_list[default_slice:]):
#             country_unactive_directions_text += f'\n <i>** <u>и еще {len(country_unactive_list[default_slice:])} неактивных направлений</u></i>'

#         no_cash_active_list = []
#         no_cash_unactive_list = []

#         for c in exchange.no_cash_directions.all():
#             if c.is_active:
#                 no_cash_active_list.append(c)
#             else:
#                 no_cash_unactive_list.append(c)

#         # no_cash_active_directions_text = '\n\n'.join(f'{str(direction).strip()} (активно✅, отключится через {direction.time_update - (timezone.now() - timedelta(days=3))}🕚)' for direction in no_cash_active_list[:default_slice])
#         no_cash_active_directions_text = '\n\n'.join(f'{get_valid_active_direction_str(direction)}' for direction in no_cash_active_list[:default_slice])

#         if len(country_active_list[default_slice:]):
#             no_cash_active_directions_text += f'\n <i>** <u>и еще {len(no_cash_active_list[default_slice:])} активных направлений</u></i>'

#         no_cash_unactive_directions_text = ' \n\n'.join(f'{str(direction).strip()} (выключено❗️)' for direction in no_cash_unactive_list[:default_slice])

#         if len(no_cash_unactive_list[default_slice:]):
#             no_cash_unactive_directions_text += f'\n <i>** <u>и еще {len(no_cash_unactive_list[default_slice:])} неактивных направлений</u></i>'

#         # print(_text)
#         # print('<u>Направления городов, требующие внимания:</u>')
#         # if city_active_directions_text:
#         #     print(city_active_directions_text, '\n')
#         # if city_unactive_directions_text:
#         #     print(city_unactive_directions_text, '\n')
#         # print('<u>Направления стран, требующие внимания:</u>')
#         # if country_active_directions_text:
#         #     print(country_active_directions_text, '\n')
#         # if country_unactive_directions_text:
#         #     print(country_unactive_directions_text, '\n')
#         # print('<u>Безналичные направления, требующие внимания:</u>')
#         # if no_cash_active_directions_text:
#         #     print( no_cash_active_directions_text, '\n')
#         # if no_cash_unactive_directions_text:
#         #     print(no_cash_unactive_directions_text, '\n')

#         # print('*' * 8)
#         _text += '\n\n<u>Направления городов, требующие внимания:</u>\n'
#         if city_active_directions_text:
#             _text += f'{city_active_directions_text}\n'
#         if city_unactive_directions_text:
#             _text += f'{city_unactive_directions_text}\n'

#         _text += '\n\n<u>Направления стран, требующие внимания:</u>\n'
        
#         if country_active_directions_text:
#             _text += f'{country_active_directions_text}\n'
#         if country_unactive_directions_text:
#             _text += f'{country_unactive_directions_text}\n'

#         _text += '\n\n<u>Безналичные направления, требующие внимания:</u>\n'

#         if no_cash_active_directions_text:
#             _text += f'{no_cash_active_directions_text}\n'
#         if no_cash_unactive_directions_text:
#             _text += f'{no_cash_unactive_directions_text}\n'

#         # print('<u>Направления городов, требующие внимания:</u>')
#         # if city_active_directions_text:
#             # print(city_active_directions_text, '\n')
#         # if city_unactive_directions_text:
#         #     print(city_unactive_directions_text, '\n')
#         # print('<u>Направления стран, требующие внимания:</u>')
#         # if country_active_directions_text:
#         #     print(country_active_directions_text, '\n')
#         # if country_unactive_directions_text:
#             # print(country_unactive_directions_text, '\n')
#         # print('<u>Безналичные направления, требующие внимания:</u>')
#         # if no_cash_active_directions_text:
#         #     print( no_cash_active_directions_text, '\n')
#         # if no_cash_unactive_directions_text:
#         #     print(no_cash_unactive_directions_text, '\n')


#         user_id = partner_exchange_admin_dict.get(exchange.pk)

#         # t = bool(user_id and user_id == 686339126)

#         # print(t)

#         if user_id:
#             # print('make request...')
#             # запрос на API бота для отправки уведомления админу обменника ( user_id )
#             async_to_sync(request_to_bot_exchange_admin_direction_notification)(user_id,
#                                                                                 _text)
#             sleep(0.3)

#     pass  

# new
@shared_task(name='exchange_admin_notifications')
def exchange_admin_notifications():
    partner_exchange_admins = NewExchangeAdmin.objects.filter(notification=True)\
                                                    .values_list('exchange_id', 'user_id')
        
    partner_exchange_admin_dict = {el[0]: el[-1] for el in partner_exchange_admins}

    prefetch_timedetla = timezone.now() - timedelta(days=2,
                                                    hours=12)
    
    prefetch_city_direction_query = Prefetch('city_directions',
                                             queryset=partner_models.NewDirection.objects.select_related('direction__valute_from',
                                                                                       'direction__valute_to',
                                                                                       'city__city',
                                                                                       'city__exchange')\
                                                                        .filter(Q(is_active=False) | \
                                                                                Q(is_active=True,
                                                                                  time_update__lte=prefetch_timedetla)))

    prefetch_country_direction_query = Prefetch('country_directions',
                                             queryset=partner_models.NewCountryDirection.objects.select_related('direction__valute_from',
                                                                                              'direction__valute_to',
                                                                                              'country__country',
                                                                                              'country__exchange')\
                                                                        .filter(Q(is_active=False) | \
                                                                                Q(is_active=True,
                                                                                  time_update__lte=prefetch_timedetla)))

    prefetch_noncash_direction_query = Prefetch('no_cash_directions',
                                             queryset=partner_models.NewNonCashDirection.objects.select_related('direction__valute_from',
                                                                                              'direction__valute_to',
                                                                                              'exchange')\
                                                                        .filter(Q(is_active=False) | \
                                                                                Q(is_active=True,
                                                                                  time_update__lte=prefetch_timedetla)))

    exchange_list = Exchanger.objects.filter(pk__in=list(partner_exchange_admin_dict.keys())).prefetch_related(prefetch_city_direction_query,
                                                                                                              prefetch_country_direction_query,
                                                                                                              prefetch_noncash_direction_query)


    for exchange in exchange_list:
        print(exchange)

        # без доп SQL запросов
        city_direction_count = len(exchange.city_directions.all())
        country_direction_count = len(exchange.country_directions.all())
        no_cash_direction_count = len(exchange.no_cash_directions.all())

        total_count = city_direction_count + country_direction_count \
                        + no_cash_direction_count
        
        _text = f'🔔 <b>Уведомление об актуализации курсов направлений обменника <u>{exchange.name}</u></b> \n\n'
        _text += f'Кол-во направлений, требующих внимания: {total_count}\n\nИз них: \n- направлений на уровне городов - {city_direction_count}\n- направлений на уровне стран - {country_direction_count}\n- безналичных направлений - {no_cash_direction_count}'

        if total_count == 0:
            continue

        default_slice = 5

        city_active_list = []
        city_unactive_list = []

        for c in exchange.city_directions.all():
            if c.is_active:
                city_active_list.append(c)
            else:
                city_unactive_list.append(c)

        city_active_directions_text = '\n\n'.join(f'{get_valid_active_direction_str(direction)}' for direction in city_active_list[:default_slice])

        if len(city_active_list[default_slice:]):
            city_active_directions_text += f'\n <i>** <u>и еще {len(city_active_list[default_slice:])} активных направлений</u></i>'

        city_unactive_directions_text = '\n\n'.join(f'{direction} (выключено❗️)' for direction in city_unactive_list[:default_slice])

        if len(city_unactive_list[default_slice:]):
            city_unactive_directions_text += f'\n <i>** <u>и еще {len(city_unactive_list[default_slice:])} неактивных направлений</u></i>'

        country_active_list = []
        country_unactive_list = []

        for c in exchange.country_directions.all():
            if c.is_active:
                country_active_list.append(c)
            else:
                country_unactive_list.append(c)

        country_active_directions_text = '\n\n'.join(f'{get_valid_active_direction_str(direction)}' for direction in country_active_list[:default_slice])

        if len(country_active_list[default_slice:]):
            country_active_directions_text += f'\n <i>** <u>и еще {len(country_active_list[default_slice:])} активных направлений</u></i>'

        country_unactive_directions_text = '\n\n'.join(f'{direction} (выключено❗️)' for direction in country_unactive_list[:default_slice])

        if len(country_unactive_list[default_slice:]):
            country_unactive_directions_text += f'\n <i>** <u>и еще {len(country_unactive_list[default_slice:])} неактивных направлений</u></i>'

        no_cash_active_list = []
        no_cash_unactive_list = []

        for c in exchange.no_cash_directions.all():
            if c.is_active:
                no_cash_active_list.append(c)
            else:
                no_cash_unactive_list.append(c)

        no_cash_active_directions_text = '\n\n'.join(f'{get_valid_active_direction_str(direction)}' for direction in no_cash_active_list[:default_slice])

        if len(country_active_list[default_slice:]):
            no_cash_active_directions_text += f'\n <i>** <u>и еще {len(no_cash_active_list[default_slice:])} активных направлений</u></i>'

        no_cash_unactive_directions_text = ' \n\n'.join(f'{str(direction).strip()} (выключено❗️)' for direction in no_cash_unactive_list[:default_slice])

        if len(no_cash_unactive_list[default_slice:]):
            no_cash_unactive_directions_text += f'\n <i>** <u>и еще {len(no_cash_unactive_list[default_slice:])} неактивных направлений</u></i>'

        _text += '\n\n<u>Направления городов, требующие внимания:</u>\n'
        if city_active_directions_text:
            _text += f'{city_active_directions_text}\n'
        if city_unactive_directions_text:
            _text += f'{city_unactive_directions_text}\n'

        _text += '\n\n<u>Направления стран, требующие внимания:</u>\n'
        
        if country_active_directions_text:
            _text += f'{country_active_directions_text}\n'
        if country_unactive_directions_text:
            _text += f'{country_unactive_directions_text}\n'

        _text += '\n\n<u>Безналичные направления, требующие внимания:</u>\n'

        if no_cash_active_directions_text:
            _text += f'{no_cash_active_directions_text}\n'
        if no_cash_unactive_directions_text:
            _text += f'{no_cash_unactive_directions_text}\n'

        user_id = partner_exchange_admin_dict.get(exchange.pk)

        if user_id:
            # print('make request...')
            # запрос на API бота для отправки уведомления админу обменника ( user_id )
            async_to_sync(new_request_to_bot_exchange_admin_direction_notification)(user_id,
                                                                                    _text)
            sleep(0.3)
