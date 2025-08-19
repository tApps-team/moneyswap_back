from celery.local import Proxy

from django.db import transaction

from cash.models import Exchange as CashExchange, BlackListElement, Direction, City

from .parsers import check_city_in_xml_file, parse_xml_to_dict, parse_xml_to_dict_2


# def run_cash_background_tasks(task: Proxy,
#                               exchange: CashExchange,
#                               direction_dict: dict,
#                               xml_file: str,
#                               black_list_parse=False):
#     '''
#     Запуск фоновых задач для создания
#     наличных готовых направлений
#     '''

#     for city in direction_dict:
#         try:
#             if not check_city_in_xml_file(city, xml_file):
#                 # print(f'Нет города {city} в {exchange.name}')
#                 if not black_list_parse:
#                     for city_id, direction_id, valute_from, valute_to in direction_dict[city]:
#                         # direction = Direction.objects.get(valute_from=valute_from,
#                         #                                 valute_to=valute_to)
#                         # direction = Direction.get(pk=direction_id)
#                         # city_model = City.objects.get(code_name=city)
#                         black_list_element, _ = BlackListElement\
#                                                 .objects\
#                                                 .get_or_create(city_id=city_id,
#                                                                direction_id=direction_id)

#                         exchange.direction_black_list.add(black_list_element)
#             else:
#                 for direction in direction_dict[city]:
#                     city_id, direction_id, valute_from_id, valute_to_id = direction
#                     dict_for_parse = exchange.__dict__.copy()
#                     dict_for_parse['valute_from_id'] = valute_from_id
#                     dict_for_parse['valute_to_id'] = valute_to_id
#                     dict_for_parse['direction_id'] = direction_id
#                     dict_for_parse['city_id'] = city_id
#                     dict_for_parse['city'] = city
                    
#                     if dict_for_parse.get('_state'):
#                         dict_for_parse.pop('_state')
                    
#                     try:
#                         task.delay(dict_for_parse, xml_file)
#                     except Exception as ex:
#                         print(ex)
#                         continue
#         except Exception as ex:
#             print(ex)


def run_cash_background_tasks(task: Proxy,
                              exchange: CashExchange,
                              direction_dict: dict,
                              xml_file: str,
                              black_list_parse=False):
    '''
    Запуск фоновых задач для создания
    наличных готовых направлений
    '''

    # if exchange.name == 'test':
    #     print('direct22',direction_dict)

    for city in direction_dict:
        try:
            if not check_city_in_xml_file(city, xml_file):
                # print(f'Нет города {city} в {exchange.name}')
                if not black_list_parse:
                    black_list = []
                    with transaction.atomic():
                        for key in direction_dict[city]:
                            city_id , direction_id = direction_dict[city][key]
                            black_list_element, _ = BlackListElement\
                                                    .objects\
                                                    .get_or_create(city_id=city_id,
                                                                   direction_id=direction_id)
                            # black_list_element_query = BlackListElement.objects.filter(city_id=city_id,
                            #                                                            direction_id=direction_id)

                            # if black_list_element_query.exists():
                            #     black_list_element = black_list_element_query.first()
                            # else:
                            #     black_list_element = BlackListElement\
                            #                             .objects\
                            #                             .create(city_id=city_id,
                            #                                     direction_id=direction_id)
                            black_list.append(black_list_element)

                        exchange.direction_black_list.add(*black_list)

                direction_dict[city] = None

        except Exception as ex:
            print(ex)
            continue

    # if exchange.name == 'test':
    #     print('direct22',direction_dict)

    parse_xml_to_dict_2(direction_dict,
                        xml_file,
                        exchange,
                        black_list_parse)
    


# def run_cash_background_tasks(task: Proxy,
#                               exchange: CashExchange,
#                               direction_dict: dict,
#                               xml_file: str,
#                               black_list_parse=False):
#     '''
#     Запуск фоновых задач для создания
#     наличных готовых направлений
#     '''

#     # if exchange.name == 'test':
#     #     print('direct22',direction_dict)

#     for city in direction_dict:
#         try:
#             if not check_city_in_xml_file(city, xml_file):
#                 if not black_list_parse:
#                     with transaction.atomic():
#                         # собираем все пары
#                         pairs = [
#                             (city_id, direction_id)
#                             for key in direction_dict[city]
#                             for city_id, direction_id in [direction_dict[city][key]]
#                         ]

#                         # достаём уже существующие blacklistelement
#                         existing = set(
#                             BlackListElement.objects.filter(
#                                 city_id__in=[c for c, _ in pairs],
#                                 direction_id__in=[d for _, d in pairs],
#                             ).values_list("city_id", "direction_id")
#                         )

#                         # создаём недостающие
#                         to_create = [
#                             BlackListElement(city_id=cid, direction_id=did)
#                             for cid, did in pairs
#                             if (cid, did) not in existing
#                         ]
#                         BlackListElement.objects.bulk_create(to_create, ignore_conflicts=True)

#                         # теперь получаем все blacklistelement.id для этих пар
#                         black_ids = list(
#                             BlackListElement.objects.filter(
#                                 city_id__in=[c for c, _ in pairs],
#                                 direction_id__in=[d for _, d in pairs],
#                             ).values_list("id", flat=True)
#                         )

#                         # создаём связи exchange <-> blacklistelement
#                         link_objs = [
#                             ExchangeDirectionBlackList(
#                                 exchange_id=exchange.id,
#                                 blacklistelement_id=bid
#                             )
#                             for bid in black_ids
#                         ]
#                         ExchangeDirectionBlackList.objects.bulk_create(
#                             link_objs, ignore_conflicts=True
#                         )

#                     direction_dict[city] = None

#         except Exception as ex:
#             print(ex)
#             continue

#     # if exchange.name == 'test':
#     #     print('direct22',direction_dict)

#     parse_xml_to_dict_2(direction_dict,
#                         xml_file,
#                         exchange,
#                         black_list_parse)
    

        # except Exception as ex:
        #     print(ex)


# def run_update_tasks(task: Proxy,
#                      exchange: CashExchange,
#                      direction_list: list,
#                      xml_file: str):
#     '''
#     Запуск фоновых задач для обновления
#     наличных готовых направлений
#     '''

#     for direction in direction_list:
#         city, valute_from_id, valute_to_id = direction
#         dict_for_parse = exchange.__dict__.copy()
#         dict_for_parse['valute_from_id'] = valute_from_id
#         dict_for_parse['valute_to_id'] = valute_to_id
#         dict_for_parse['city'] = city

#         if dict_for_parse.get('_state'):
#             dict_for_parse.pop('_state')

#         if dict_for_parse.get('_prefetched_objects_cache'):
#             dict_for_parse.pop('_prefetched_objects_cache')

#         try:
#             task.delay(dict_for_parse, xml_file)
#         except Exception as ex:
#             print(ex)




def run_update_tasks(task: Proxy,
                     exchange: CashExchange,
                     direction_list: list,
                     xml_file: str):
    '''
    Запуск фоновых задач для обновления
    наличных готовых направлений
    '''
    dict_for_parse = dict()

    for direction in direction_list:
        # city, direciton_id, valute_from_id, valute_to_id = direction
        city = direction.city.code_name
        valute_from_id = direction.direction.valute_from_id
        valute_to_id = direction.direction.valute_to_id
        # dict_for_parse[f'{city} {valute_from_id} {valute_to_id}'] = direciton_id
        dict_for_parse[f'{city} {valute_from_id} {valute_to_id}'] = direction

    parse_xml_to_dict(dict_for_parse,
                      xml_file,
                      task)
    

