from celery import shared_task

from celery_once import QueueOnce

from general_models.utils.exc import NoFoundXmlElement
from general_models.utils.periodic_tasks import try_get_xml_file

from .utils.periodic_tasks import new_run_no_cash_background_tasks, run_no_cash_background_tasks, run_update_tasks
from .utils.parsers import no_cash_parse_xml
from .utils.tasks import get_no_cash_direction_set_for_creating, generate_direction_dict
from .utils.cache import get_or_set_no_cash_directions_cache

from .models import Exchange, ExchangeDirection, Direction

from time import time


# #PERIODIC CREATE
# @shared_task(name='create_no_cash_directions_for_exchange',
#              soft_time_limit=10,
#              time_limit=15)
# def create_no_cash_directions_for_exchange(exchange_name: str):
#     try:
#         exchange = Exchange.objects.get(name=exchange_name)
        
#         all_no_cash_directions = get_or_set_no_cash_directions_cache()
        
#         if all_no_cash_directions:
#             direction_list = get_no_cash_direction_set_for_creating(all_no_cash_directions,
#                                                                     exchange)

                                    
#         # xml_file = try_get_xml_file(exchange)
        
#         # if xml_file is not None and exchange.is_active:
#         #         all_no_cash_directions = get_or_set_no_cash_directions_cache()
#         #         if all_no_cash_directions:
#         #             direction_list = get_no_cash_direction_set_for_creating(all_no_cash_directions,
#         #                                                                     exchange)
                    
#             if direction_list:
#                 xml_file = try_get_xml_file(exchange)

#                 if xml_file is not None and exchange.is_active:
#                     run_no_cash_background_tasks(create_direction,
#                                                 exchange,
#                                                 direction_list,
#                                                 xml_file)
#     except Exception as ex:
#         print(ex)

#PERIODIC CREATE
# @shared_task(base=QueueOnce,
#              once={'graceful': True},
#              name='create_no_cash_directions_for_exchange')
# def create_no_cash_directions_for_exchange(exchange_id: int):
#     try:
#         exchange = Exchange.objects.get(pk=exchange_id)

#         if exchange.active_status in ('disabled', 'scam', ):
#             return
        
#         all_no_cash_directions = get_or_set_no_cash_directions_cache()
        
#         if all_no_cash_directions:
#             direction_list = get_no_cash_direction_set_for_creating(all_no_cash_directions,
#                                                                     exchange)
                    
#             if direction_list:
#                 xml_file = try_get_xml_file(exchange)

#                 if xml_file is not None and exchange.is_active:
#                     #
#                     # if exchange.name == 'Bixter':
#                     #     print('Bixter', xml_file)
#                     #
#                     direction_dict = generate_direction_dict(direction_list)
#                     run_no_cash_background_tasks(create_direction,
#                                                 exchange,
#                                                 direction_dict,
#                                                 xml_file)
#         #     else:
#         #         print(f'1не зашел в блок try_xml_file {exchange.name}')
#         # else:
#         #     print(f'2не зашел в блок try_xml_file {exchange.name}')
#     except Exception as ex:
#         print(ex)


# new
#PERIODIC CREATE
@shared_task(base=QueueOnce,
             once={'graceful': True},
             name='create_no_cash_directions_for_exchange')
def create_no_cash_directions_for_exchange(exchange_id: int):
    try:
        exchange = Exchange.objects.get(pk=exchange_id)

        if exchange.active_status in ('disabled', 'scam', 'skip'):
            return
        
        all_no_cash_directions = get_or_set_no_cash_directions_cache()
        
        if all_no_cash_directions:
            # direction_list = get_no_cash_direction_set_for_creating(all_no_cash_directions,
            #                                                         exchange)
                    
            # if direction_list:
                print(f'no cash {exchange.name}')
                start_time = time()
                xml_file = try_get_xml_file(exchange)
                print(f'безнал время на получения xml файла {time() - start_time} sec')

                if xml_file is not None and exchange.is_active:
                    #
                    # if exchange.name == 'Bixter':
                    #     print('Bixter', xml_file)
                    #
                    direction_dict = generate_direction_dict(all_no_cash_directions)
                    new_run_no_cash_background_tasks(exchange,
                                                     direction_dict,
                                                     xml_file)
        #     else:
        #         print(f'1не зашел в блок try_xml_file {exchange.name}')
        # else:
        #     print(f'2не зашел в блок try_xml_file {exchange.name}')
    except Exception as ex:
        print(ex)



@shared_task
def create_direction(dict_for_parse: dict,
                     xml_file: str):
    # print('*' * 10)
    # print('inside task')

    try:
        # direction = Direction.objects.get(valute_from=dict_for_parse['valute_from_id'],
        #                                   valute_to=dict_for_parse['valute_to_id'])
        
        dict_for_create_exchange_direction = no_cash_parse_xml(dict_for_parse, xml_file)
    except NoFoundXmlElement:
        not_found_direction = Direction.objects.get(pk=dict_for_parse['direction_id'])
        exchange = Exchange.objects.get(pk=dict_for_parse['id'])
        # not_found_direction = direction
        print('NOT FOUND DIRECTION', not_found_direction)
        exchange.direction_black_list.add(not_found_direction)
    except Exception as ex:
        print('PARSE FAILED', ex)
        pass
    else:
        dict_for_create_exchange_direction['exchange_id'] = dict_for_parse['id']
        dict_for_create_exchange_direction['direction_id'] = dict_for_parse['direction_id']
        try:
            ExchangeDirection.objects.create(**dict_for_create_exchange_direction)
        except Exception as ex:
            print(ex)
            pass


#PERIODIC UPDATE
@shared_task(base=QueueOnce,
             once={'graceful': True},
             name='update_no_cash_diretions_for_exchange')
def update_no_cash_diretions_for_exchange(exchange_id: int):
    try:
        exchange = Exchange.objects.get(pk=exchange_id)

        if exchange.active_status in ('disabled', 'scam', ):
            return

        # xml_file = try_get_xml_file(exchange)

        # if xml_file is not None and exchange.is_active:
        # direction_list = exchange.directions\
        #                         .select_related('direction',
        #                                         'direction__valute_from',
        #                                         'direction__valute_to')\
        #                         .values_list('pk',
        #                                         'direction__valute_from',
        #                                         'direction__valute_to').all()
        direction_list = exchange.directions\
                                .select_related('direction',
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

#     exchange_direction = ExchangeDirection.objects\
#                         .select_related('direction',
#                                         'direction__valute_from',
#                                         'direction__valute_to')\
#                         .filter(exchange=dict_for_parse['id'],
#                                 direction__valute_from=dict_for_parse['valute_from_id'],
#                                 direction__valute_to=dict_for_parse['valute_to_id'])

#     try:
#         dict_for_update_exchange_direction = no_cash_parse_xml(dict_for_parse, xml_file)
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
    if len(dict_for_parse) > 1:
        dict_for_parse['is_active'] = True

    exchange_direction.update(**dict_for_parse)



#PERIODIC BLACK LIST
@shared_task(base=QueueOnce,
             once={'graceful': True},
             name='try_create_no_cash_directions_from_black_list')
def try_create_no_cash_directions_from_black_list(exchange_id: int):
    try:
        exchange = Exchange.objects.get(pk=exchange_id)

        if exchange.active_status in ('disabled', 'scam', ):
            return
        
        black_list_directions = exchange.direction_black_list\
                                        .select_related('valute_from',
                                                        'valute_to')\
                                        .values_list('pk',
                                                        'valute_from',
                                                        'valute_to')\
                                        .all()

        if black_list_directions:
            xml_file = try_get_xml_file(exchange)
            
            if xml_file is not None and exchange.is_active:
                black_list_direction_dict = generate_direction_dict(black_list_directions)
                run_no_cash_background_tasks(try_create_black_list_direction,
                                            exchange,
                                            black_list_direction_dict,
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
        dict_for_exchange_direction = no_cash_parse_xml(dict_for_parse, xml_file)
    except NoFoundXmlElement as ex:
        print('CATCH EXCEPTION', ex)
        pass
    except Exception as ex:
        print('BLACK LIST PARSE FAILED', ex)
        pass
    else:
        try:
            exchange = Exchange.objects.get(pk=dict_for_parse['id'])
            direction = Direction.objects.get(pk=dict_for_parse['direction_id'])

            dict_for_exchange_direction['exchange'] = exchange
            dict_for_exchange_direction['direction'] = direction

            ExchangeDirection.objects.create(**dict_for_exchange_direction)

            exchange.direction_black_list.remove(direction)
        except Exception:
            pass