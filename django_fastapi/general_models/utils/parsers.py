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

from .base import check_valid_min_max_amount
from .exc import NoFoundXmlElement
from .tasks import make_valid_values_for_dict



def parse_cash_direction_by_city(dict_for_parse: dict,
                                 element: Element,
                                 city: str,
                                 exchange: Exchanger,
                                 cash_bulk_create_list: list,
                                 cash_set: set,
                                 cash_duble_list: list,
                                 time_action: timezone):
    # min_amount = element.findtext('minamount') or element.findtext('minAmount')
    # valute_from = element.xpath('./from/text()')element.findtext('from')
    # valute_to = element.xpath('./to/text()')element.findtext('to')
    valute_from = element.findtext('from')
    valute_to = element.findtext('to')

    
    if all(el for el in (valute_from, valute_to)):
        # inner_key = f'{valute_from[0]} {valute_to[0]}'
        # inner_key = (valute_from[0], valute_to[0])
        inner_key = (valute_from, valute_to)


        if dict_for_parse.get(city, None) is not None:
            if dict_for_parse[city].get(inner_key):
                city_id, direction_id = dict_for_parse[city].get(inner_key)

                # fromfee = element.xpath('./fromfee/text()')
                # param = element.xpath('./param/text()')
                fromfee = element.findtext('fromfee')
                param = element.findtext('param')


                # fromfee = None if not fromfee else fromfee[0]
                if fromfee:
                    # fromfee: str
                    if fromfee.endswith('%'):
                        fromfee = float(fromfee[:-1].strip())

                # param = None if not param else param[0]

                # if not (min_amount := element.xpath('./minamount/text()')):
                #     min_amount = element.xpath('./minAmount/text()')


                # if not (max_amount := element.xpath('./maxamount/text()')):
                #     max_amount = element.xpath('./maxAmount/text()')

                min_amount = element.findtext('minamount') or element.findtext('minAmount')
                max_amount = element.findtext('maxamount') or element.findtext('maxAmount')

                in_count = element.findtext('in')
                out_count = element.findtext('out')

                try:
                    if not (min_amount and max_amount) or\
                        not check_valid_min_max_amount(min_amount,
                                                    max_amount):
                        return
                    
                    d = {
                        # 'in_count': element.xpath('./in/text()')[0],
                        # 'out_count': element.xpath('./out/text()')[0],
                        'in_count': in_count,
                        'out_count': out_count,
                        'min_amount': min_amount,
                        'max_amount': max_amount,
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
                    # print(f'{ex} | {exchange.name} direction_id {direction_id}')
                    pass
                else:
                    unique_key = (exchange.pk, direction_id, city_id)

                    if unique_key not in cash_set:
                        cash_set.add(unique_key)
                        try:
                            cash_bulk_create_list.append(cash_models.NewExchangeDirection(**d))
                            
                            # dict_for_parse[city].pop(inner_key)

                        except Exception as ex:
                            # print('тут ошибка 2')
                            print(ex)
                    else:
                        cash_duble_list.append(unique_key)



def parse_no_cash_direction(dict_for_parse: dict,
                            element: Element,
                            exchange: Exchanger,
                            no_cash_bulk_create_list: list,
                            no_cash_set: set,
                            no_cash_duble_list: list,
                            time_action: timezone):
    no_cash_dict_key = 'NOCASH'

    # valute_from = element.xpath('./from/text()')
    # valute_to = element.xpath('./to/text()')
    valute_from = element.findtext('from')
    valute_to = element.findtext('to')
    
    if all(el for el in (valute_from, valute_to)):
        # key = f'{valute_from[0]} {valute_to[0]}'
        # key = (valute_from[0], valute_to[0])
        key = (valute_from, valute_to)

        if dict_for_parse[no_cash_dict_key].get(key):
            direction_id = dict_for_parse[no_cash_dict_key].pop(key)

            # if not (min_amount := element.xpath('./minamount/text()')):
            #     min_amount = element.xpath('./minAmount/text()')

            # if not (max_amount := element.xpath('./maxamount/text()')):
            #     max_amount = element.xpath('./maxAmount/text()')
            min_amount = element.findtext('minamount') or element.findtext('minAmount')
            max_amount = element.findtext('maxamount') or element.findtext('maxAmount')
            in_count = element.findtext('in')
            out_count = element.findtext('out')

            d = {
                'min_amount': min_amount,
                'max_amount':max_amount,
                'in_count': in_count,
                'out_count': out_count,
            }

            has_required_fields = bool(in_count and out_count and max_amount and min_amount)

            try:
                if not has_required_fields or\
                    not check_valid_min_max_amount(min_amount,
                                                   max_amount):
                    # print('ERROR WITH REQURED FILEDS', has_required_fields, d)
                    return
                
                d = {
                    'in_count': in_count,
                    'out_count': out_count,
                    'min_amount': min_amount,
                    'max_amount': max_amount,
                    # 'in_count': element.xpath('./in/text()')[0],
                    # 'out_count': element.xpath('./out/text()')[0],
                    # 'min_amount': min_amount[0],
                    # 'max_amount': max_amount[0],
                    'is_active': True,
                    'direction_id': direction_id,
                    'exchange_id': exchange.pk,
                    'time_action': time_action,
                }
            
                make_valid_values_for_dict(d)
            except Exception as ex:
                pass
                # print(f'{ex} || {exchange.name}')
                # continue

            else:
                unique_key = (exchange.pk, direction_id)
                if unique_key not in no_cash_set:
                    no_cash_set.add(unique_key)
                    try:
                        no_cash_bulk_create_list.append(no_cash_models.NewExchangeDirection(**d))

                    except Exception as ex:
                        print(ex)
                        # continue
                else:
                    no_cash_duble_list.append(unique_key)    


def parse_xml_and_create_or_update_directions(exchange: Exchanger,
                                              xml_file: str,
                                              dict_for_parse: dict):
    xml_file = xml_file.encode()

    cash_bulk_create_list = []
    cash_set = set()
    cash_duble_list = []

    no_cash_bulk_create_list = []
    no_cash_set = set()
    no_cash_duble_list = []

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
                                                     cash_set=cash_set,
                                                     cash_duble_list=cash_duble_list,
                                                     time_action=time_action)
                    else:
                        cities = [c.strip() for c in city.split(',')]
                        
                        for city in cities:
                            parse_cash_direction_by_city(dict_for_parse,
                                                        element,
                                                        city,
                                                        exchange,
                                                        cash_bulk_create_list,
                                                        cash_set=cash_set,
                                                        cash_duble_list=cash_duble_list,
                                                        time_action=time_action)
                else:
                    parse_no_cash_direction(dict_for_parse,
                                            element,
                                            exchange,
                                            no_cash_bulk_create_list,
                                            no_cash_set=no_cash_set,
                                            no_cash_duble_list=no_cash_duble_list,
                                            time_action=time_action)

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

    batch_size = 400

    # NO CASH CREATE/UPDATE
    with transaction.atomic():
        try:
            no_cash_models.NewExchangeDirection.objects.bulk_create(no_cash_bulk_create_list,
                                                                    update_conflicts=True,
                                                                    update_fields=update_fields,
                                                                    unique_fields=unique_fields,
                                                                    batch_size=batch_size)
            
            no_cash_models.NewExchangeDirection.objects.filter(Q(exchange_id=exchange.pk,
                                                                 is_active=True) \
                                                                & ~Q(time_action=time_action))\
                                                        .update(is_active=False)
        except Exception as ex:
            print('CREATE/UPDATE NO CASH ERROR')
            print(ex)
            print('DUBLES', no_cash_duble_list)

    # CASH CREATE/UPDATE
    with transaction.atomic():
        try:
            cash_models.NewExchangeDirection.objects.bulk_create(cash_bulk_create_list,
                                                                 update_conflicts=True,
                                                                 update_fields=update_fields + additional_cash_update_fields,
                                                                 unique_fields=unique_fields + additional_cash_unique_fields,
                                                                 batch_size=batch_size)
            
            cash_models.NewExchangeDirection.objects.filter(Q(exchange_id=exchange.pk,
                                                              is_active=True) \
                                                            & ~Q(time_action=time_action))\
                                                    .update(is_active=False)

        except Exception as ex:
            print('CREATE/UPDATE CASH ERROR')
            print(ex)
            print('DUBLES', cash_duble_list)

    print(f'время обновления в бд {exchange.name} - {time() - start_db_time} sec')
