from django.core.cache import cache

from no_cash.models import Direction

from general_models.models import Valute


def get_or_set_no_cash_directions_cache():
    '''
    Получить или установить кэш значение безналичных направлений
    '''
    try:
        if not (all_no_cash_directions := cache.get('all_no_cash_directions', False)):
            print('SET VALUE TO CACHE')
            all_no_cash_directions = Direction.objects\
                                    .select_related('valute_from', 'valute_to')\
                                    .values_list('valute_from', 'valute_to').all()
            cache.set('all_no_cash_directions', all_no_cash_directions, 60)#вывести время в settings
        return set(all_no_cash_directions)
    except Exception as ex:
        print(ex)



def get_or_set_all_no_cash_valutes_cache(queries):
    if not (all_no_cash_valutes := cache.get('all_no_cash_valutes', False)):
        print('set to cache')
        valutes = Valute.objects.filter(code_name__in=(queries)).all()
        all_no_cash_valutes = valutes
        cache.set('all_no_cash_valutes', all_no_cash_valutes, 300)

    return all_no_cash_valutes


def get_or_set_no_cash_valutes_by_valute_cache(base: str,
                                               queries):
    if not (no_cash_valutes := cache.get(f'no_cash_valutes_by_{base}', False)):
        no_cash_valutes = queries
        cache.set(f'no_cash_valutes_by_{base}', no_cash_valutes, 30)

    return no_cash_valutes
