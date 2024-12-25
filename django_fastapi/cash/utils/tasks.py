from cash.models import Exchange

from django.db import connection


def check_direction_count(direction_count: int,
                          exchange_direction_count: int,
                          exchange_black_list_count: int):
    # print(exchange_direction_count + exchange_black_list_count)
    return bool(direction_count - exchange_direction_count - exchange_black_list_count)


def get_cash_direction_set_for_creating(directions: set[tuple[str,str,str]],
                                        exchange: Exchange):
    '''
    Получить перечень направлений для создания
    '''

    direction_count, _directions = directions

    # print('direction_count', direction_count)

    exchange_directions = exchange\
                            .directions\
                            .select_related('city',
                                            'direction',
                                            'direction__valute_from',
                                            'direction__valute_to')
                            # .values_list('city__pk',
                            #              'city__code_name',
                            #              'direction__pk',
                            #              'direction__valute_from',
                            #              'direction__valute_to').all()
    exchange_black_list_directions = exchange\
                                .direction_black_list\
                                .select_related('city',
                                                'direction',
                                                'direction__valute_from',
                                                'direction__valute_to')
    if direction_count:                               
        if check_direction_count(direction_count,
                                exchange_directions.count(),
                                exchange_black_list_directions.count()):
            # print('not empty', exchange.name)
            exchange_directions = exchange_directions\
                                        .values_list('city__pk',
                                                    'city__code_name',
                                                    'direction__pk',
                                                    'direction__valute_from__code_name',
                                                    'direction__valute_to__code_name').all()
            exchange_black_list_directions = exchange_black_list_directions\
                                        .values_list('city__pk',
                                                    'city__code_name',
                                                    'direction__pk',
                                                    'direction__valute_from__code_name',
                                                    'direction__valute_to__code_name').all()
            
            checked_directions_by_exchange = exchange_black_list_directions.union(exchange_directions)

            _directions -= set(checked_directions_by_exchange)
            # print(_directions)
            return _directions
        else:
            # print('empty')
            return set()
    else:
        # print('empty')
        return set()
    # print('DIRECTIONS FOR CREATING', directions)


# def get_cash_direction_set_for_creating(directions: set[tuple[str,str,str]],
#                                         exchange: Exchange):
#     '''
#     Получить перечень направлений для создания
#     '''

#     exchange_directions = exchange\
#                             .directions\
#                             .select_related('city',
#                                             'direction',
#                                             'direction__valute_from',
#                                             'direction__valute_to')\
#                             .values_list('city__pk',
#                                          'city__code_name',
#                                          'direction__pk',
#                                          'direction__valute_from',
#                                          'direction__valute_to').all()
#     exchange_black_list_directions = exchange\
#                                 .direction_black_list\
#                                 .select_related('city',
#                                                 'direction',
#                                                 'direction__valute_from',
#                                                 'direction__valute_to')\
#                                 .values_list('city__pk',
#                                              'city__code_name',
#                                              'direction__pk',
#                                              'direction__valute_from',
#                                              'direction__valute_to').all()
#     checked_directions_by_exchange = exchange_black_list_directions.union(exchange_directions)

#     directions -= set(checked_directions_by_exchange)
#     # print('DIRECTIONS FOR CREATING', directions)

#     return directions


def generate_direction_dict(directions: set[str,str,str,str,str]):
    '''
    Генерирует словарь в формате: ключ - кодовое сокращение города,
    значение - список направлений. Пример направления: ('BTC', 'CASHRUB').
    '''
    direction_dict = {}
    for city_id, city_code_name, directon_id, valute_from, valute_to in directions:
        direction_dict[city_code_name] = direction_dict.get(city_code_name, [])\
                                                 + [(city_id, directon_id, valute_from, valute_to)]

    return direction_dict


def generate_direction_dict_2(directions: set[str,str,str,str,str]):
    '''
    Генерирует словарь в формате: ключ - кодовое сокращение города,
    значение - список направлений. Пример направления: ('BTC', 'CASHRUB').
    '''
    direction_dict = {}
    for city_id, city_code_name, directon_id, valute_from, valute_to in directions:
        if not direction_dict.get(city_code_name):
            direction_dict[city_code_name] = dict()
        
        inner_key = f'{valute_from} {valute_to}'
        if not direction_dict[city_code_name].get(inner_key):
            direction_dict[city_code_name][inner_key] = (city_id, directon_id)
        # direction_dict[city_code_name] = direction_dict.get(city_code_name, dict())\
        #                                         + [(city_id, directon_id, valute_from, valute_to)]

    return direction_dict



def generate_direction_dict_black_list(directions: set[str,str,str,str,str]):
    '''
    Генерирует словарь в формате: ключ - кодовое сокращение города,
    значение - список направлений. Пример направления: ('BTC', 'CASHRUB').
    '''
    direction_dict = {}
    for city_id, city_code_name, directon_id, valute_from, valute_to in directions:
        direction_dict[city_code_name] = direction_dict.get(city_code_name, [])\
                                                 + [(city_id, directon_id, valute_from, valute_to)]

    return direction_dict
