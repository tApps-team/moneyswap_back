from xml.etree import ElementTree as ET

from io import BytesIO

from lxml import etree

from celery.local import Proxy

from django.db import transaction

from general_models.utils.exc import NoFoundXmlElement
from general_models.utils.tasks import make_valid_values_for_dict

from no_cash.models import ExchangeDirection, Exchange


def no_cash_parse_xml(dict_for_parser: dict,
                      xml_file: str):
        direction_dict = dict_for_parser.copy()
        valute_from = direction_dict.pop('valute_from_id')
        valute_to = direction_dict.pop('valute_to_id')

        xml_url = dict_for_parser.get('xml_url')
        root = ET.fromstring(xml_file)

        element = root.find(f'item[from="{valute_from}"][to="{valute_to}"]')

        if element is not None:
            try:
                dict_for_exchange_direction = {
                    # 'valute_from': valute_from,
                    # 'valute_to': valute_to,
                    'in_count': element.find('in').text,
                    'out_count': element.find('out').text,
                    'min_amount': element.find('minamount').text,
                    'max_amount': element.find('maxamount').text
                    }
                make_valid_values_for_dict(dict_for_exchange_direction)
            except Exception as ex:
                dict_for_exchange_direction = {
                    'in_count': 0,
                    'out_count': 0,
                    'min_amount': '0',
                    'max_amount': '0',
                    'is_active': False,
                }
            finally:
                return dict_for_exchange_direction
        else:
            raise NoFoundXmlElement(f'Xml элемент не найден, {xml_url}')
        

def parse_xml_to_dict(dict_for_parse: dict,
                      xml_file: str,
                      task: Proxy):
    # root = etree.fromstring(xml_file.encode())
    xml_file = xml_file.encode()

    for event, element in etree.iterparse(BytesIO(xml_file), tag='item'):
        if dict_for_parse:
    #  print(event)
            try:
                valute_from = element.xpath('./from/text()')
                valute_to = element.xpath('./to/text()')
                
                if all(el for el in (valute_from, valute_to)):
                    key = f'{valute_from[0]} {valute_to[0]}'
                    
                    if dict_for_parse.get(key, False):
                        direction_id = dict_for_parse.pop(key)
                        try:
                            d = {
                                'in_count': element.xpath('./in/text()')[0],
                                'out_count': element.xpath('./out/text()')[0],
                                'min_amount': element.xpath('./minamount/text()')[0],
                                'max_amount': element.xpath('./maxamount/text()')[0],
                                'is_active': True,
                                # 'direction_id': direction_id,
                            }
                            
                            make_valid_values_for_dict(d)
                        except Exception as ex:
                            print(ex)
                            d = {
                                # 'direction_id': direction_id,
                                'is_active': False,
                            }
                        finally:
                            # task.delay(d)
                            ExchangeDirection.objects.filter(pk=direction_id)\
                                                        .update(**d)
            except Exception as ex:
                print(ex)
                continue
        else:
            break
    else:
        if dict_for_parse:
            direction_ids = list(dict_for_parse.values())
            ExchangeDirection.objects.filter(pk__in=direction_ids).update(is_active=False)


def parse_xml_to_dict_2(dict_for_parse: dict,
                      xml_file: str,
                      exchange: Exchange,
                      black_list_parse: bool):
    # root = etree.fromstring(xml_file.encode())
    xml_file = xml_file.encode()

    bulk_create_list = []

    if black_list_parse:
        direction_id_list = []

    for event, element in etree.iterparse(BytesIO(xml_file), tag='item'):
        try:
            valute_from = element.xpath('./from/text()')
            valute_to = element.xpath('./to/text()')
            
            if all(el for el in (valute_from, valute_to)):
                key = f'{valute_from[0]} {valute_to[0]}'
                
                if dict_for_parse.get(key):
                    direction_id = dict_for_parse.pop(key)

                    fromfee = element.xpath('./fromfee/text()')
                    param = element.xpath('./param/text()')

                    fromfee = None if not fromfee else fromfee[0]
                    param = None if not param else param[0]

                    try:
                        d = {
                            'in_count': element.xpath('./in/text()')[0],
                            'out_count': element.xpath('./out/text()')[0],
                            'min_amount': element.xpath('./minamount/text()')[0],
                            'max_amount': element.xpath('./maxamount/text()')[0],
                            # 'fromfee': fromfee,
                            # 'params': param,
                            'is_active': True,
                            'direction_id': direction_id,
                            'exchange_id': exchange.id,
                        }
                    
                        make_valid_values_for_dict(d)
                    except Exception as ex:
                        print(ex)
                        continue

                    else:
                        try:
                            bulk_create_list.append(ExchangeDirection(**d))

                            if black_list_parse:
                                direction_id_list.append(direction_id)

                        except Exception as ex:
                            print(ex)
                            continue

        except Exception as ex:
            print(ex)
            continue

    try:
        print(22)
        if black_list_parse:
            with transaction.atomic():
                exchange.direction_black_list.remove(
                        *exchange.direction_black_list.filter(pk__in=direction_id_list)
                    )
                ExchangeDirection.objects.bulk_create(bulk_create_list)
        else:
            ExchangeDirection.objects.bulk_create(bulk_create_list)
    except Exception as ex:
        print(ex)


# def parse_xml_to_dict_2(dict_for_parse: dict,
#                       xml_file: str,
#                       exchange: Exchange,
#                       black_list_parse: bool = False):
#     # root = etree.fromstring(xml_file.encode())
#     xml_file = xml_file.encode()

#     bulk_create_list = []

#     if black_list_parse:
#         city_id_list = []
#         direction_id_list = []

#     for event, element in etree.iterparse(BytesIO(xml_file), tag='item'):
#         # if dict_for_parse:
#     #  print(event)
#             try:
#                 city = element.xpath('./city/text()')
                
#                 if city:
#                     city = city[0].upper()
#                     valute_from = element.xpath('./from/text()')
#                     valute_to = element.xpath('./to/text()')
                    
#                     if all(el for el in (valute_from, valute_to)):
#                         inner_key = f'{valute_from[0]} {valute_to[0]}'
                        
#                         if dict_for_parse.get(city, None) is not None:
#                             if dict_for_parse[city].get(inner_key):
#                                 city_id, direction_id = dict_for_parse[city].pop(inner_key)
#                             # direction_id = dict_for_parse.pop(key)
#                                 fromfee = element.xpath('./fromfee/text()')
#                                 param = element.xpath('./param/text()')

#                                 fromfee = None if not fromfee else fromfee[0]
#                                 param = None if not param else param[0]

#                                 try:
#                                     d = {
#                                         'in_count': element.xpath('./in/text()')[0],
#                                         'out_count': element.xpath('./out/text()')[0],
#                                         'min_amount': element.xpath('./minamount/text()')[0],
#                                         'max_amount': element.xpath('./maxamount/text()')[0],
#                                         'fromfee': fromfee,
#                                         'params': param,
#                                         'is_active': True,
#                                         'city_id': city_id,
#                                         'direction_id': direction_id,
#                                         'exchange_id': exchange.id,
#                                         # 'direction_id': direction_id,
#                                     }
                                
#                                     make_valid_values_for_dict(d)
#                                 except Exception as ex:
#                                     print(ex)
#                                     continue
#                                 else:
#                                     try:
#                                         bulk_create_list.append(ExchangeDirection(**d))

#                                         if black_list_parse:
#                                             city_id_list.append(city_id)
#                                             direction_id_list.append(direction_id)

#                                     except Exception as ex:
#                                         print(ex)
#                                         continue
                                
#             except Exception as ex:
#                 print(ex)
#                 continue
    
#     try:
#         with transaction.atomic():
#             exchange.direction_black_list.remove(
#                     *exchange.direction_black_list.filter(city_id__in=city_id_list,
#                                                           direction_id__in=direction_id_list)
#                 )
#             ExchangeDirection.objects.bulk_create(bulk_create_list)
#     except Exception as ex:
#         print(ex)