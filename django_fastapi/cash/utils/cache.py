from django.core.cache import cache

from fastapi import Request

from .endpoints import get_available_countries
from general_models.utils.http_exc import http_exception_json

from cash.models import Direction, City


def get_or_set_cash_directions_cache():
    '''
    Получить или установить кэш значение наличных направлений с городами
    '''
    try:
        if not (all_cash_directions := cache.get('all_cash_directions', False)):
            cash_directions = Direction.objects\
                                    .select_related('valute_from', 'valute_to')\
                                    .values_list('valute_from', 'valute_to').all()
            cities_for_parse = City.objects.filter(is_parse=True).all()
            all_cash_directions = set()

            for city in cities_for_parse:
                for valute_from, valute_to in cash_directions:
                    all_cash_directions.add((city.code_name, valute_from, valute_to))
                    
            cache.set('all_cash_directions', all_cash_directions, 60)
            print('SET VALUE TO CACHE')
        else:
            print('VALUE GETTING FROM CACHE')
        return all_cash_directions
    except Exception as ex:
        print(ex)



def get_or_set_counries_from_cache(request: Request):
    try:
        if not (countries := cache.get('countries', False)):
            cities = City.objects.filter(is_parse=True)\
                                    .select_related('country').all()
            if not cities:
                http_exception_json(status_code=404, param=request.url)

            countries = get_available_countries(cities)
            cache.set('countries', countries, 30)
            print('set to cache')
        else:
            print('get from cache')
        return countries
    except Exception as ex:
        print(ex)