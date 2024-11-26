from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element

from io import BytesIO

from lxml import etree

from celery.local import Proxy

from django.db import transaction

from general_models.utils.exc import NoFoundXmlElement
from general_models.utils.tasks import make_valid_values_for_dict

from cash.models import ExchangeDirection, Exchange, BlackListElement


def cash_parse_xml(dict_for_parse: dict,
                   xml_file: str):
        direction_dict = dict_for_parse.copy()
        valute_from = direction_dict.pop('valute_from_id')
        valute_to = direction_dict.pop('valute_to_id')
        city = direction_dict.pop('city')

        xml_url = dict_for_parse.get('xml_url')
        root = ET.fromstring(xml_file)

        element = root.find(f'item[from="{valute_from}"][to="{valute_to}"][city="{city.upper()}"]')

        if element is not None:
              return generate_exchange_direction_dict(element,
                                                      valute_from,
                                                      valute_to,
                                                      city)
        else:
            element = root.find(f'item[from="{valute_from}"][to="{valute_to}"][city="{city.lower()}"]')
            if element is not None:
                return generate_exchange_direction_dict(element,
                                                        valute_from,
                                                        valute_to,
                                                        city)
            raise NoFoundXmlElement(f'Xml элемент не найден, {xml_url}')
        


def parse_xml_to_dict(dict_for_parse: dict,
                      xml_file: str,
                      task: Proxy):
    # root = etree.fromstring(xml_file.encode())
    xml_file = xml_file.encode()

    update_fields = [
        'in_count',
        'out_count',
        'min_amount',
        'max_amount',
        'fromfee',
        'params',
        'is_active',
    ]

    update_list = []

    for event, element in etree.iterparse(BytesIO(xml_file), tag='item'):
        if dict_for_parse:
    #  print(event)
            try:
                city = element.xpath('./city/text()')
                
                if city:
                    city = city[0].upper()
                    valute_from = element.xpath('./from/text()')
                    valute_to = element.xpath('./to/text()')
                    
                    if all(el for el in (valute_from, valute_to)):
                        key = f'{city} {valute_from[0]} {valute_to[0]}'
                        
                        if dict_for_parse.get(key, False):
                            # direction_id = dict_for_parse.pop(key)
                            direction = dict_for_parse.pop(key)

                            fromfee = element.xpath('./fromfee/text()')
                            # print('fromfee', fromfee)
                            param = element.xpath('./param/text()')

                            fromfee = None if not fromfee else fromfee[0]
                            
                            if fromfee:
                                fromfee: str
                                if fromfee.endswith('%'):
                                    fromfee = float(fromfee[:-1].strip())
                                else:
                                    fromfee = None

                            param = None if not param else param[0]

                            # min_amount = element.xpath('./minamount/text()')
                            if not (min_amount := element.xpath('./minamount/text()')):
                                min_amount = element.xpath('./minAmount/text()')

                            # max_amount = element.xpath('./maxamount/text()')
                            if not (max_amount := element.xpath('./maxamount/text()')):
                                max_amount = element.xpath('./maxAmount/text()')

                            try:
                                # if fromfee and not fromfee.isdigit():
                                #     fromfee = None
                                    
                                d = {
                                    'in_count': element.xpath('./in/text()')[0],
                                    'out_count': element.xpath('./out/text()')[0],
                                    'min_amount': min_amount[0],
                                    'max_amount': max_amount[0],
                                    'fromfee': fromfee,
                                    'params': param,
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
                                # ExchangeDirection.objects.filter(pk=direction_id)\
                                #                             .update(**d)
                                for field, value in d.items():
                                    setattr(direction, field, value)
                                update_list.append(direction)
                                
            except Exception as ex:
                print(ex)
                continue
            finally:
                element.clear()
        else:
            break   
    
    with transaction.atomic():
        if dict_for_parse:
            for direction in dict_for_parse.values():
                direction.is_active = False
                update_list.append(direction)
            # direction_ids = [el.pk for el in dict_for_parse.values()]
            # ExchangeDirection.objects.filter(pk__in=direction_ids).update(is_active=False)
        try:
            ExchangeDirection.objects.bulk_update(update_list, update_fields)
        except Exception as ex:
            print('CASH BULK UPDATE ERROR', ex)


def parse_xml_to_dict_2(dict_for_parse: dict,
                      xml_file: str,
                      exchange: Exchange,
                      black_list_parse: bool):
    # root = etree.fromstring(xml_file.encode())
    xml_file = xml_file.encode()

    bulk_create_list = []

    if black_list_parse:
        city_id_list = []
        direction_id_list = []

    for event, element in etree.iterparse(BytesIO(xml_file), tag='item'):
        # if dict_for_parse:
    #  print(event)
            try:
                city = element.xpath('./city/text()')
                
                if city:
                    city = city[0].upper()
                    valute_from = element.xpath('./from/text()')
                    valute_to = element.xpath('./to/text()')
                    
                    if all(el for el in (valute_from, valute_to)):
                        inner_key = f'{valute_from[0]} {valute_to[0]}'
                        
                        if dict_for_parse.get(city, None) is not None:
                            if dict_for_parse[city].get(inner_key):
                                city_id, direction_id = dict_for_parse[city].pop(inner_key)
                            # direction_id = dict_for_parse.pop(key)
                                fromfee = element.xpath('./fromfee/text()')
                                param = element.xpath('./param/text()')

                                fromfee = None if not fromfee else fromfee[0]
                                if fromfee:
                                    fromfee: str
                                    if fromfee.endswith('%'):
                                        fromfee = float(fromfee[:-1].strip())

                                param = None if not param else param[0]

                                # min_amount = element.xpath('./minamount/text()')
                                if not (min_amount := element.xpath('./minamount/text()')):
                                    min_amount = element.xpath('./minAmount/text()')

                                # max_amount = element.xpath('./maxamount/text()')
                                if not (max_amount := element.xpath('./maxamount/text()')):
                                    max_amount = element.xpath('./maxAmount/text()')

                                try:
                                    # if fromfee is not None:
                                    #     fromfee = fromfee if fromfee.isdigit() else None

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
                                        'exchange_id': exchange.id,
                                        # 'direction_id': direction_id,
                                    }
                                
                                    make_valid_values_for_dict(d)
                                except Exception as ex:
                                    print(ex)
                                    continue
                                else:
                                    try:
                                        bulk_create_list.append(ExchangeDirection(**d))

                                        if black_list_parse:
                                            city_id_list.append(city_id)
                                            direction_id_list.append(direction_id)

                                    except Exception as ex:
                                        print(ex)
                                        continue
                                
            except Exception as ex:
                print(ex)
                continue
            finally:
                element.clear()
    
    with transaction.atomic():
        try:
            if black_list_parse:
                    exchange.direction_black_list.remove(
                            *exchange.direction_black_list.filter(city_id__in=city_id_list,
                                                                direction_id__in=direction_id_list)
                        )
                    ExchangeDirection.objects.bulk_create(bulk_create_list)
                    
            else:
                ExchangeDirection.objects.bulk_create(bulk_create_list)

                black_list = []
                for city in dict_for_parse:
                    if inner_dict := dict_for_parse.get(city):
                        for inner_key in inner_dict:
                            if value := inner_dict.get(inner_key):
                                city_id, direction_id = value
                                black_list_direction, _ = BlackListElement\
                                                        .objects\
                                                        .get_or_create(city_id=city_id,
                                                                       direction_id=direction_id)
                                black_list.append(black_list_direction)
                exchange.direction_black_list.add(*black_list)
                # создаем BlackListElement`ы и добавляюм в exchange.direction_black_list.add(*elements)
        except Exception as ex:
            print('CREATE OR BLACK LIST ERROR')
            print(ex)
        

def check_city_in_xml_file(city: str, xml_file: str):
    '''
    Проверка города на наличие в XML файле
    '''
    
    root = ET.fromstring(xml_file)
    element = root.find(f'item[city="{city.upper()}"]')
    if element is None:
          element = root.find(f'item[city="{city.lower()}"]')
    return bool(element)


def generate_exchange_direction_dict(element: Element,
                                     valute_from: str,
                                     valute_to: str,
                                     city: str):
    '''
    Генерирует словарь готового направления
    '''
    
    fromfee = element.find('fromfee')
    if fromfee is not None:
        fromfee = fromfee.text

    params = element.find('param')
    if params is not None:
        params = params.text

    dict_for_exchange_direction = {
        # 'valute_from': valute_from,
        # 'valute_to': valute_to,
        # 'city': city.upper(),
        'in_count': element.find('in').text,
        'out_count': element.find('out').text,
        'min_amount': element.find('minamount').text,
        'max_amount': element.find('maxamount').text,
        'fromfee': fromfee,
        'params': params,
    }
    make_valid_values_for_dict(dict_for_exchange_direction)

    return dict_for_exchange_direction
