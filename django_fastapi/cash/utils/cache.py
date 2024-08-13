from django.core.cache import cache

from cash.models import Direction, City


def get_or_set_cash_directions_cache():
    '''
    Получить или установить кэш значение наличных направлений с городами
    '''
    # try:
    if not (all_cash_directions := cache.get('all_cash_directions', False)):
        cash_directions = Direction.objects\
                                .select_related('valute_from',
                                                'valute_to')\
                                .values_list('pk',
                                            'valute_from',
                                            'valute_to')\
                                .all()
        cities_for_parse = City.objects.filter(is_parse=True)\
                                        .values_list('pk',
                                                    'code_name')\
                                        .all()
        all_cash_directions = set()

        for city_id, city_code_name in cities_for_parse:
            for direction_id, valute_from, valute_to in cash_directions:
                all_cash_directions.add((city_id, city_code_name, direction_id, valute_from, valute_to))
                
        cache.set('all_cash_directions', all_cash_directions, 60)
    # print('SET VALUE TO CACHE')
# else:
    # print('VALUE GETTING FROM CACHE')
    return all_cash_directions
    # except Exception as ex:
    #     print(ex)