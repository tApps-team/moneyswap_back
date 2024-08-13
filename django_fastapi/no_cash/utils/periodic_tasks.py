from no_cash.models import Exchange as NoCashExchange

from celery.local import Proxy

from .parsers import parse_xml_to_dict


def run_no_cash_background_tasks(task: Proxy,
                                exchange: NoCashExchange,
                                direction_list: set,
                                xml_file: str):
    for direction in direction_list:
        direction_id, valute_from_id, valute_to_id = direction
        dict_for_parse = exchange.__dict__.copy()
        dict_for_parse['valute_from_id'] = valute_from_id
        dict_for_parse['valute_to_id'] = valute_to_id
        dict_for_parse['direction_id'] = direction_id

        if dict_for_parse.get('_state'):
            dict_for_parse.pop('_state')

        try:    
            task.delay(dict_for_parse, xml_file)
        except Exception as ex:
            print(ex)
            continue



def run_update_tasks(task: Proxy,
                     exchange: NoCashExchange,
                     direction_list: list,
                     xml_file: str):
    '''
    Запуск фоновых задач для обновления
    наличных готовых направлений
    '''
    dict_for_parse = dict()
    for direciton in direction_list:
        direciton_id, valute_from_id, valute_to_id = direciton
        dict_for_parse[f'{valute_from_id} {valute_to_id}'] = direciton_id
    parse_xml_to_dict(dict_for_parse,
                      xml_file,
                      task)