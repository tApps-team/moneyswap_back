from django.core.cache import cache

from no_cash.models import Direction, NewDirection


def get_or_set_no_cash_directions_cache():
    '''
    Получить или установить кэш значение безналичных направлений
    '''
    # try:
    if not (all_no_cash_directions := cache.get('all_no_cash_directions', False)):
    # print('SET VALUE TO CACHE')
        all_no_cash_directions = Direction.objects\
                                .select_related('valute_from',
                                                'valute_to')\
                                .values_list('pk',
                                             'valute_from',
                                             'valute_to')\
                                .all()
        cache.set('all_no_cash_directions', all_no_cash_directions, 60)#вывести время в settings
    return set(all_no_cash_directions)
    # except Exception as ex:
    #     print(ex)


def new_get_or_set_no_cash_directions_cache():
    '''
    Получить или установить кэш значение безналичных направлений
    '''
    # try:
    if not (all_no_cash_directions := cache.get('new_all_no_cash_directions', False)):
    # print('SET VALUE TO CACHE')
        all_no_cash_directions = NewDirection.objects\
                                .select_related('valute_from',
                                                'valute_to')\
                                .values_list('pk',
                                             'valute_from',
                                             'valute_to')\
                                .all()
        cache.set('new_all_no_cash_directions', all_no_cash_directions, 60)#вывести время в settings
    return list(all_no_cash_directions)