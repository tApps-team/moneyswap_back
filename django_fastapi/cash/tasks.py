from time import time

from celery import shared_task

from celery_once import QueueOnce

from django.db import connection

from general_models.utils.exc import NoFoundXmlElement
from general_models.utils.periodic_tasks import try_get_xml_file

from .utils.parsers import cash_parse_xml
from .utils.periodic_tasks import new_run_cash_background_tasks, run_cash_background_tasks, run_update_tasks
from .utils.tasks import (get_cash_direction_set_for_creating,
                          generate_direction_dict,
                          generate_direction_dict_2)
from .utils.cache import get_or_set_cash_directions_cache

from .models import Exchange, ExchangeDirection, BlackListElement, Direction, City


# #PERIODIC CREATE
# @shared_task(name='create_cash_directions_for_exchange')
# def create_cash_directions_for_exchange(exchange_name: str):
#     try:
#         exchange = Exchange.objects.get(name=exchange_name)
#         # xml_file = try_get_xml_file(exchange)

#         all_cash_directions = get_or_set_cash_directions_cache()

#         if all_cash_directions:
#             direction_list = get_cash_direction_set_for_creating(all_cash_directions,
#                                                                 exchange)
        
#         # exchange = Exchange.objects.get(name=exchange_name)
#         # xml_file = try_get_xml_file(exchange)
    
#         # if xml_file is not None and exchange.is_active:
#         #     all_cash_directions = get_or_set_cash_directions_cache()
#         #     if all_cash_directions:
#         #         direction_list = get_cash_direction_set_for_creating(all_cash_directions,
#         #                                                             exchange)

#             if direction_list:
#                 xml_file = try_get_xml_file(exchange)
                
#                 if xml_file is not None and exchange.is_active:
#                     direction_dict = generate_direction_dict(direction_list)
#                     run_cash_background_tasks(create_direction,
#                                             exchange,
#                                             direction_dict,
#                                             xml_file)
#     except Exception as ex:
#         print(ex)



#PERIODIC CREATE
# @shared_task(base=QueueOnce,
#              once={'graceful': True},
#              name='create_cash_directions_for_exchange')
# def create_cash_directions_for_exchange(exchange_id: int):
#     try:
#         exchange = Exchange.objects.get(pk=exchange_id)

#         if exchange.active_status in ('disabled', 'scam', ):
#             return
#         # print(exchange)

#         all_cash_directions = get_or_set_cash_directions_cache()

#         # if exchange.name == 'CoinPoint':
#         #     print('direct22',all_cash_directions)

#         if all_cash_directions:
#             direction_list = get_cash_direction_set_for_creating(all_cash_directions,
#                                                                  exchange)

#             # print(len(direction_list))
#             if direction_list:
#                 print(f'request to exchanger {exchange.name}')
#                 xml_file = try_get_xml_file(exchange)
                
#                 if xml_file is not None and exchange.is_active:
#                     direction_dict = generate_direction_dict_2(direction_list)
#                     run_cash_background_tasks(create_direction,
#                                             exchange,
#                                             direction_dict,
#                                             xml_file)
#         #     else:
#         #         print(f'1не зашел в блок try_xml_file {exchange.name}')
#         # else:
#         #     print(f'2не зашел в блок try_xml_file {exchange.name}')

#     except Exception as ex:
#         print(ex)

#new (одна задача на добавление и обновление направлений)
@shared_task(base=QueueOnce,
             once={'graceful': True},
             name='create_cash_directions_for_exchange')
def create_cash_directions_for_exchange(exchange_id: int):
    try:
        exchange = Exchange.objects.get(pk=exchange_id)

        if exchange.active_status in ('disabled', 'scam', 'skip'):
            return
        
        all_cash_directions = get_or_set_cash_directions_cache()

        if all_cash_directions:
            # print(f'request to exchanger {exchange.name}')
            start_time = time()
            xml_file = try_get_xml_file(exchange)
            print(f'наличные время получения xml {time() - start_time} sec')
            # print('get xml file', time() - start_time)
        
            if xml_file is not None and exchange.is_active:
                # start_generate_time = time()
                direction_dict = generate_direction_dict_2(all_cash_directions[-1])
                # print('время генерации словаря направлений', time() - start_generate_time)
                
                new_run_cash_background_tasks(exchange,
                                              direction_dict,
                                              xml_file)

    except Exception as ex:
        print(ex, exchange_id)
        


@shared_task
def create_direction(dict_for_parse: dict,
                     xml_file: str):
    # print('*' * 10)
    # print('inside task')

    try:
        # direction = Direction.objects.get(valute_from=dict_for_parse['valute_from_id'],
        #                                 valute_to=dict_for_parse['valute_to_id'])    
        # city = City.objects.get(code_name=dict_for_parse['city'])
    
        dict_for_create_exchange_direction = cash_parse_xml(dict_for_parse, xml_file)
    except NoFoundXmlElement:
        black_list_element, _ = BlackListElement\
                                .objects\
                                .get_or_create(city_id=dict_for_parse['city_id'],
                                               direction_id=dict_for_parse['direction_id'])
        # print('Нет элемента')
        Exchange.objects.get(name=dict_for_parse['name'])\
                        .direction_black_list.add(black_list_element)
    except Exception as ex:
        print('PARSE FAILED', ex)
        pass
    else:
        # print('Получилось')
        # exchange = Exchange.objects.get(name=dict_for_parse['name'])
        dict_for_create_exchange_direction['exchange_id'] = dict_for_parse['id']
        dict_for_create_exchange_direction['direction_id'] = dict_for_parse['direction_id']
        dict_for_create_exchange_direction['city_id'] = dict_for_parse['city_id']
        try:
            ExchangeDirection.objects.create(**dict_for_create_exchange_direction)
        except Exception:
            pass


#PERIODIC UPDATE
@shared_task(base=QueueOnce,
             once={'graceful': True},
             name='update_cash_directions_for_exchange')
def update_cash_directions_for_exchange(exchange_id: int):
    try:
        exchange = Exchange.objects.get(pk=exchange_id)

        if exchange.active_status in ('disabled', 'scam', ):
            return
        # xml_file = try_get_xml_file(exchange)

        # if xml_file is not None and exchange.is_active:
        # direction_list = exchange.directions\
        #                             .select_related('city',
        #                                             'direction',
        #                                             'direction__valute_from',
        #                                             'direction__valute_to')\
        #                             .values_list('city__code_name',
        #                                             'pk',
        #                                             'direction__valute_from',
        #                                             'direction__valute_to')\
        #                             .all()
        direction_list = exchange.directions\
                                    .select_related('city',
                                                    'direction',
                                                    'direction__valute_from',
                                                    'direction__valute_to')\
                                    .all()

        if direction_list:
            xml_file = try_get_xml_file(exchange)

            if xml_file is not None and exchange.is_active:
                run_update_tasks(try_update_direction,
                                    exchange,
                                    direction_list,
                                    xml_file)
        else:
            print(f'не зашел в блок try_xml_file {exchange.name}')
    except Exception as ex:
        print(ex)


# @shared_task
# def try_update_direction(dict_for_parse: dict,
#                          xml_file: str):
#     print('*' * 10)
#     print('inside task')

#     try:
#         exchange_direction = ExchangeDirection.objects\
#                             .select_related('city',
#                                             'direction',
#                                             'direction__valute_from',
#                                             'direction__valute_to')\
#                             .filter(exchange=dict_for_parse['id'],
#                                     city__code_name=dict_for_parse['city'],
#                                     direction__valute_from=dict_for_parse['valute_from_id'],
#                                     direction__valute_to=dict_for_parse['valute_to_id'],
#                                     )
#         dict_for_update_exchange_direction = cash_parse_xml(dict_for_parse, xml_file)
#     except NoFoundXmlElement as ex:
#         print('CATCH EXCEPTION', ex)
#         exchange_direction.update(is_active=False)
#         pass
#     except Exception as ex:
#         print('PARSE UPDATE FAILED', ex)
#         exchange_direction.update(is_active=False)
#         pass
#     else:
#         print('update')
#         dict_for_update_exchange_direction['is_active'] = True

#         exchange_direction.update(**dict_for_update_exchange_direction)


@shared_task
def try_update_direction(dict_for_parse: dict):
    exchange_direction = ExchangeDirection.objects\
                                            .filter(pk=dict_for_parse.pop('direction_id'))
    dict_for_parse['is_active'] = True
    exchange_direction.update(**dict_for_parse)


# #PERIODIC BLACK LIST
# @shared_task(name='try_create_cash_directions_from_black_list')
# def try_create_cash_directions_from_black_list(exchange_name: str):
#     try:
#         exchange = Exchange.objects.get(name=exchange_name)
#         xml_file = try_get_xml_file(exchange)

#         if xml_file is not None and exchange.is_active:
#             black_list_directions = exchange.direction_black_list\
#                                             .select_related('city',
#                                                             'direction',
#                                                             'direction__valute_from',
#                                                             'direction__valute_to')\
#                                             .values_list('city__pk',
#                                                          'city__code_name',
#                                                          'direction__pk',
#                                                          'direction__valute_from',
#                                                          'direction__valute_to')\
#                                             .all()

#             if black_list_directions:
#                 direction_dict = generate_direction_dict(black_list_directions)
#                 run_cash_background_tasks(try_create_black_list_direction,
#                                         exchange,
#                                         direction_dict,
#                                         xml_file,
#                                         black_list_parse=True)
#     except Exception as ex:
#         print(ex)

#PERIODIC BLACK LIST
@shared_task(base=QueueOnce,
             once={'graceful': True},
             name='try_create_cash_directions_from_black_list')
def try_create_cash_directions_from_black_list(exchange_id: int):
    try:
        exchange = Exchange.objects.get(pk=exchange_id)

        if exchange.active_status in ('disabled', 'scam', ):
            return

        black_list_directions = exchange.direction_black_list\
                                        .select_related('city',
                                                        'direction',
                                                        'direction__valute_from',
                                                        'direction__valute_to')\
                                        .values_list('city__pk',
                                                     'city__code_name',
                                                     'direction__pk',
                                                     'direction__valute_from',
                                                     'direction__valute_to')\
                                        .all()

        if black_list_directions:
            xml_file = try_get_xml_file(exchange)

            if xml_file is not None and exchange.is_active:
                direction_dict = generate_direction_dict_2(black_list_directions)
                run_cash_background_tasks(try_create_black_list_direction,
                                        exchange,
                                        direction_dict,
                                        xml_file,
                                        black_list_parse=True)
    except Exception as ex:
        print(ex)



@shared_task
def try_create_black_list_direction(dict_for_parse: dict,
                                    xml_file: str):
    # print('*' * 10)
    # print('inside task')

    try:
        dict_for_exchange_direction = cash_parse_xml(dict_for_parse, xml_file)
    except Exception as ex:
        print('BLACK LIST PARSE FAILED', ex)
        pass
    else:
        try:
            # direction = Direction.objects.get(valute_from=dict_for_parse['valute_from_id'],
            #                                 valute_to=dict_for_parse['valute_to_id'])
            exchange = Exchange.objects.get(name=dict_for_parse['id'])
            # city = City.objects.get(code_name=dict_for_parse['city'])
            
            dict_for_exchange_direction['exchange'] = exchange
            dict_for_exchange_direction['direction_id'] = dict_for_parse['direction_id']
            dict_for_exchange_direction['city_id'] = dict_for_parse['city_id']
            
            ExchangeDirection.objects.create(**dict_for_exchange_direction)

            black_list_element = BlackListElement.objects\
                                    .get(city_id=dict_for_parse['city_id'],
                                         direction_id=dict_for_parse['direction_id'])

            exchange.direction_black_list.remove(black_list_element)
        except Exception:
            pass