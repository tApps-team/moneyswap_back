from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element

from io import BytesIO

from lxml import etree

from celery.local import Proxy

from general_models.utils.exc import NoFoundXmlElement
from general_models.utils.tasks import make_valid_values_for_dict

from cash.models import ExchangeDirection


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
                                ExchangeDirection.objects.filter(pk=direction_id)\
                                                            .update(**d)
                                
            except Exception as ex:
                print(ex)
                continue
        

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
