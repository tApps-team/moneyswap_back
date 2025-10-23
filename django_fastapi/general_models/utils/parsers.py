from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element

from io import BytesIO
from time import time

from lxml import etree

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from general_models.models import Exchanger

import cash.models as cash_models
import no_cash.models as no_cash_models

# from cash.utils.parsers import new_parse_create_direction_by_city

from .exc import NoFoundXmlElement
from .tasks import make_valid_values_for_dict



def parse_cash_direction_by_city(dict_for_parse: dict,
                                 element: Element,
                                 city: str,
                                 exchange: Exchanger,
                                 cash_bulk_create_list: list,
                                 time_action: timezone):
    valute_from = element.xpath('./from/text()')
    valute_to = element.xpath('./to/text()')
    
    if all(el for el in (valute_from, valute_to)):
        # inner_key = f'{valute_from[0]} {valute_to[0]}'
        inner_key = (valute_from[0], valute_to[0])

        if dict_for_parse.get(city, None) is not None:
            if dict_for_parse[city].get(inner_key):
                city_id, direction_id = dict_for_parse[city].get(inner_key)

                fromfee = element.xpath('./fromfee/text()')
                param = element.xpath('./param/text()')

                fromfee = None if not fromfee else fromfee[0]
                if fromfee:
                    fromfee: str
                    if fromfee.endswith('%'):
                        fromfee = float(fromfee[:-1].strip())

                param = None if not param else param[0]

                if not (min_amount := element.xpath('./minamount/text()')):
                    min_amount = element.xpath('./minAmount/text()')

                if not (max_amount := element.xpath('./maxamount/text()')):
                    max_amount = element.xpath('./maxAmount/text()')

                try:
                    d = {
                        'in_count': element.xpath('./in/text()')[0],
                        'out_count': element.xpath('./out/text()')[0],
                        'min_amount': min_amount[0],
                        'max_amount': max_amount[0],
                        'fromfee': fromfee,
                        'params': param,
                        'is_active': True,
                        'city_id': city_id,
                        'direction_id': direction_id,
                        'exchange_id': exchange.pk,
                        'time_action': time_action,
                    }
                
                    make_valid_values_for_dict(d)
                except Exception as ex:
                    print(f'{ex} | {exchange.name} direction_id {direction_id}')
                    pass
                else:
                    try:
                        cash_bulk_create_list.append(cash_models.NewExchangeDirection(**d))
                        
                        # dict_for_parse[city].pop(inner_key)

                    except Exception as ex:
                        # print('тут ошибка 2')
                        print(ex)


def parse_no_cash_direction(dict_for_parse: dict,
                            element: Element,
                            exchange: Exchanger,
                            no_cash_bulk_create_list: list,
                            time_action: timezone):
    no_cash_dict_key = 'NOCASH'

    valute_from = element.xpath('./from/text()')
    valute_to = element.xpath('./to/text()')
    
    if all(el for el in (valute_from, valute_to)):
        # key = f'{valute_from[0]} {valute_to[0]}'
        key = (valute_from[0], valute_to[0])

        if dict_for_parse[no_cash_dict_key].get(key):
            direction_id = dict_for_parse[no_cash_dict_key].pop(key)

            if not (min_amount := element.xpath('./minamount/text()')):
                min_amount = element.xpath('./minAmount/text()')

            if not (max_amount := element.xpath('./maxamount/text()')):
                max_amount = element.xpath('./maxAmount/text()')

            try:
                d = {
                    'in_count': element.xpath('./in/text()')[0],
                    'out_count': element.xpath('./out/text()')[0],
                    'min_amount': min_amount[0],
                    'max_amount': max_amount[0],
                    'is_active': True,
                    'direction_id': direction_id,
                    'exchange_id': exchange.pk,
                    'time_action': time_action,
                }
            
                make_valid_values_for_dict(d)
            except Exception as ex:
                print(f'{ex} || {exchange.name}')
                # continue

            else:
                try:
                    no_cash_bulk_create_list.append(no_cash_models.NewExchangeDirection(**d))

                except Exception as ex:
                    print(ex)
                    # continue
    


def parse_xml_and_create_or_update_directions(exchange: Exchanger,
                                              xml_file: str,
                                              dict_for_parse: dict):
    xml_file = xml_file.encode()

    cash_bulk_create_list = []
    no_cash_bulk_create_list = []

    time_action = timezone.now()

    start_parse_time = time()

    for event, element in etree.iterparse(BytesIO(xml_file), events=('end',), tag='item'):
        # if any(v for v in dict_for_parse.values()):
            try:
                city = element.xpath('./city/text()')
                
                if city:
                    city = city[0].upper()

                    if city.find(',') == -1:
                        parse_cash_direction_by_city(dict_for_parse,
                                                     element,
                                                     city,
                                                     exchange,
                                                     cash_bulk_create_list,
                                                     time_action)
                    else:
                        cities = [c.strip() for c in city.split(',')]
                        
                        for city in cities:
                            parse_cash_direction_by_city(dict_for_parse,
                                                         element,
                                                         city,
                                                         exchange,
                                                         cash_bulk_create_list,
                                                         time_action)
                else:
                    parse_no_cash_direction(dict_for_parse,
                                            element,
                                            exchange,
                                            no_cash_bulk_create_list,
                                            time_action)

            except Exception as ex:
                print('ошибка парсинга направления', ex)
                continue
            finally:
                element.clear()
    
    print(f'время парсинга xml {exchange.name} - {time() - start_parse_time} sec')
    
    update_fields = [
        'in_count',
        'out_count',
        'min_amount',
        'max_amount',
        'is_active',
        'time_action',
    ]
    unique_fields = [
        'exchange_id',
        'direction_id',
    ]
    additional_cash_update_fields = [
        'fromfee',
        'params',
    ]
    additional_cash_unique_fields = [
        'city_id',
    ]

    start_db_time = time()

    # NO CASH CREATE/UPDATE
    with transaction.atomic():
        try:
            no_cash_models.NewExchangeDirection.objects.bulk_create(no_cash_bulk_create_list,
                                                                    update_conflicts=True,
                                                                    update_fields=update_fields,
                                                                    unique_fields=unique_fields)
            
            no_cash_models.NewExchangeDirection.objects.filter(Q(exchange_id=exchange.pk) \
                                                                & ~Q(time_action=time_action))\
                                                        .update(is_active=False)
        except Exception as ex:
            print('CREATE/UPDATE NO CASH ERROR')
            print(ex)

    # CASH CREATE/UPDATE
    with transaction.atomic():
        try:
            cash_models.NewExchangeDirection.objects.bulk_create(cash_bulk_create_list,
                                                                 update_conflicts=True,
                                                                 update_fields=update_fields + additional_cash_update_fields,
                                                                 unique_fields=unique_fields + additional_cash_unique_fields)
            
            cash_models.NewExchangeDirection.objects.filter(Q(exchange_id=exchange.pk) \
                                                            & ~Q(time_action=time_action))\
                                                    .update(is_active=False)

        except Exception as ex:
            print('CREATE/UPDATE CASH ERROR')
            print(ex)

    print(f'время обновления в бд {exchange.name} - {time() - start_db_time} sec')
