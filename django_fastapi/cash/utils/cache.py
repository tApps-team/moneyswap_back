from django.core.cache import cache

from django.db.models import Count, Q, Prefetch

from fastapi import Request

from .endpoints import get_available_countries3
from general_models.utils.http_exc import http_exception_json

from cash.models import Direction, City, Country

from partners.models import PartnerCountry


def generate_all_cash_directions(cash_directions,
                                 cities_for_parse):
    cash_directions = cash_directions\
                            .values_list('pk',
                                        'valute_from__code_name',
                                        'valute_to__code_name')\
                            .all()
    cities_for_parse = cities_for_parse.values_list('pk',
                                                    'code_name')\
                                        .all()
    all_cash_directions = set()

    for city_id, city_code_name in cities_for_parse:
        for direction_id, valute_from, valute_to in cash_directions:
            all_cash_directions.add((city_id, city_code_name, direction_id, valute_from, valute_to))
            
    cache.set('all_cash_directions', all_cash_directions, 3600)

    return all_cash_directions


def get_or_set_cash_directions_cache():
    '''
    Получить или установить кэш значение наличных направлений с городами
    '''
    
    cash_directions = Direction.objects\
                            .select_related('valute_from',
                                            'valute_to')

    cities_for_parse = City.objects.filter(is_parse=True)
    
    city_direction_count = cash_directions.count() * cities_for_parse.count()

    # print('city_direction_count', city_direction_count)
    _r = False

    if not (cache_city_directon_count := cache.get('cache_city_directon_count', None)):
        cache.set('cache_city_directon_count', city_direction_count, 3600)
        _r = True
    else:
        different = city_direction_count - cache_city_directon_count

        # print('different', different)
        if different > 0:
            _r = True
            cache.set('cache_city_directon_count', city_direction_count, 3600)

    if not (all_cash_directions := cache.get('all_cash_directions', False)):
        all_cash_directions = generate_all_cash_directions(cash_directions,
                                                           cities_for_parse)

    else:
        if _r:
            all_cash_directions = generate_all_cash_directions(cash_directions,
                                                               cities_for_parse)


    return (
        len(all_cash_directions),
        all_cash_directions,
        )


# def get_or_set_cash_directions_cache():
#     '''
#     Получить или установить кэш значение наличных направлений с городами
#     '''
#     # try:
#     if not (all_cash_directions := cache.get('all_cash_directions', False)):
#         cash_directions = Direction.objects\
#                                 .select_related('valute_from',
#                                                 'valute_to')\
#                                 .values_list('pk',
#                                             'valute_from',
#                                             'valute_to')\
#                                 .all()
#         cities_for_parse = City.objects.filter(is_parse=True)\
#                                         .values_list('pk',
#                                                     'code_name')\
#                                         .all()
#         all_cash_directions = set()

#         for city_id, city_code_name in cities_for_parse:
#             for direction_id, valute_from, valute_to in cash_directions:
#                 all_cash_directions.add((city_id, city_code_name, direction_id, valute_from, valute_to))
                
#         cache.set('all_cash_directions', all_cash_directions, 60)
#     # print('SET VALUE TO CACHE')
# # else:
#     # print('VALUE GETTING FROM CACHE')
#     return all_cash_directions
#     # except Exception as ex:
#     #     print(ex)



def get_or_set_cache_available_countries(request: Request):
    if not (available_countries := cache.get('available_countries', False)):
        prefetch_cities_queryset =  City.objects.order_by('name')\
                                                .select_related('country')\
                                                .prefetch_related('cash_directions',
                                                                'partner_cities')\
                                                .annotate(partner_direction_count=Count('partner_cities',
                                                                                        filter=Q(partner_cities__partner_directions__is_active=True)))\
                                                .annotate(direction_count=Count('cash_directions',
                                                                                filter=Q(cash_directions__is_active=True)))\
                                                .filter(Q(direction_count__gt=0) \
                                                        | Q(partner_direction_count__gt=0) \
                                                            | Q(country__partner_countries__partner_directions__isnull=False))\
                                                .distinct()


        prefetch_counries_queryset =  PartnerCountry.objects.prefetch_related('partner_directions')\
                                                .annotate(partner_direction_count=Count('partner_directions',
                                                                                        filter=Q(partner_directions__is_active=True)))\
                                                .filter(Q(partner_direction_count__gt=0))
        # prefetch_cities = Prefetch('cities', City.objects.order_by('name')\
        #                                                     .prefetch_related('cash_directions')\
        #                                                     .annotate(partner_direction_count=Count('partner_cities',
        #                                                                                             filter=Q(partner_cities__partner_directions__is_active=True)))\
        #                                                     .annotate(direction_count=Count('cash_directions'))\
        #                                                     .filter(Q(direction_count__gt=0) | Q(partner_direction_count__gt=0)))
        prefetch_cities = Prefetch('cities', prefetch_cities_queryset)
        prefetch_countries = Prefetch('partner_countries', prefetch_counries_queryset)

        countries = Country.objects.prefetch_related(prefetch_cities,
                                                    prefetch_countries)\
                                    .annotate(direction_count=Count('cities__cash_directions',
                                                                    filter=Q(cities__cash_directions__is_active=True)))\
                                    .annotate(country_direction_count=Count('partner_countries__partner_directions',
                                                                            filter=Q(partner_countries__partner_directions__is_active=True)))\
                                    .filter(Q(direction_count__gt=0) | Q(country_direction_count__gt=0))\
                                    .order_by('name')\
                                    .all()
        
        # countries = Country.objects.prefetch_related(prefetch_cities,
        #                                             prefetch_countries)\
        #                             .annotate(direction_count=Count('cities__cash_directions',
        #                                                             filter=Q(cities__cash_directions__is_active=True)))\
        #                             .annotate(partner_direction_count=Count('cities__partner_directions',
        #                                                             filter=Q(cities__partner_directions__is_active=True)))\
        #                             .annotate(country_direction_count=Count('partner_countries__partner_directions',
        #                                                                     filter=Q(partner_countries__partner_directions__is_active=True)))\
        #                             .filter(Q(direction_count__gt=0) | Q(country_direction_count__gt=0) | Q(partner_direction_count__gt=0))\
        #                             .order_by('name')\
        #                             .all()


        if not countries:
            http_exception_json(status_code=404, param=request.url)

        available_countries = get_available_countries3(countries)
        cache.set('available_countries', available_countries, 180)
    
    return available_countries



def get_or_set_cache_available_countries2(request: Request):
    if not (available_countries := cache.get('available_countries2', False)):
        prefetch_cities_queryset =  City.objects.order_by('name')\
                                                .select_related('country')\
                                                .prefetch_related('cash_directions',
                                                                'partner_cities')\
                                                .annotate(partner_direction_count=Count('partner_cities',
                                                                                        filter=Q(partner_cities__partner_directions__is_active=True)))\
                                                .annotate(direction_count=Count('cash_directions',
                                                                                filter=Q(cash_directions__is_active=True)))\
                                                .filter(Q(direction_count__gt=0) \
                                                        | Q(partner_direction_count__gt=0) \
                                                            | Q(country__partner_countries__partner_directions__isnull=False))\
                                                .distinct()


        prefetch_counries_queryset =  PartnerCountry.objects.prefetch_related('partner_directions')\
                                                .annotate(partner_direction_count=Count('partner_directions',
                                                                                        filter=Q(partner_directions__is_active=True)))\
                                                .filter(Q(partner_direction_count__gt=0))
        # prefetch_cities = Prefetch('cities', City.objects.order_by('name')\
        #                                                     .prefetch_related('cash_directions')\
        #                                                     .annotate(partner_direction_count=Count('partner_cities',
        #                                                                                             filter=Q(partner_cities__partner_directions__is_active=True)))\
        #                                                     .annotate(direction_count=Count('cash_directions'))\
        #                                                     .filter(Q(direction_count__gt=0) | Q(partner_direction_count__gt=0)))
        prefetch_cities = Prefetch('cities', prefetch_cities_queryset)
        prefetch_countries = Prefetch('partner_countries', prefetch_counries_queryset)

        # countries = Country.objects.prefetch_related(prefetch_cities,
        #                                             prefetch_countries)\
        #                             .annotate(direction_count=Count('cities__cash_directions',
        #                                                             filter=Q(cities__cash_directions__is_active=True)))\
        #                             .annotate(country_direction_count=Count('partner_countries__partner_directions',
        #                                                                     filter=Q(partner_countries__partner_directions__is_active=True)))\
        #                             .filter(Q(direction_count__gt=0) | Q(country_direction_count__gt=0))\
        #                             .order_by('name')\
        #                             .all()
        
        countries = Country.objects.prefetch_related(prefetch_cities,
                                                    prefetch_countries)\
                                    .annotate(direction_count=Count('cities__cash_directions',
                                                                    filter=Q(cities__cash_directions__is_active=True)))\
                                    .annotate(partner_direction_count=Count('cities__partner_cities__partner_directions',
                                                                    filter=Q(cities__partner_cities__partner_directions__is_active=True)))\
                                    .annotate(country_direction_count=Count('partner_countries__partner_directions',
                                                                            filter=Q(partner_countries__partner_directions__is_active=True)))\
                                    .filter(Q(direction_count__gt=0) | Q(country_direction_count__gt=0) | Q(partner_direction_count__gt=0))\
                                    .order_by('name')\
                                    .all()


        if not countries:
            http_exception_json(status_code=404, param=request.url)

        available_countries = get_available_countries3(countries)
        cache.set('available_countries2', available_countries, 180)
    
    return available_countries


def get_or_set_cache_available_countries3(request: Request):
    if not (available_countries := cache.get('available_countries', False)):
        prefetch_cities_queryset =  City.objects.order_by('name')\
                                                .select_related('country')\
                                                .prefetch_related('cash_directions',
                                                                'partner_cities')\
                                                .annotate(partner_direction_count=Count('partner_cities__partner_directions',
                                                                                        filter=Q(partner_cities__partner_directions__is_active=True)))\
                                                .annotate(direction_count=Count('cash_directions',
                                                                                filter=Q(cash_directions__is_active=True)))\
                                                .filter(Q(direction_count__gt=0) \
                                                        | Q(partner_direction_count__gt=0) \
                                                            | Q(country__partner_countries__partner_directions__is_active=True))\
                                                .distinct()


        prefetch_counries_queryset =  PartnerCountry.objects.prefetch_related('partner_directions')\
                                                .annotate(partner_direction_count=Count('partner_directions',
                                                                                        filter=Q(partner_directions__is_active=True)))\
                                                .filter(Q(partner_direction_count__gt=0))
        # prefetch_cities = Prefetch('cities', City.objects.order_by('name')\
        #                                                     .prefetch_related('cash_directions')\
        #                                                     .annotate(partner_direction_count=Count('partner_cities',
        #                                                                                             filter=Q(partner_cities__partner_directions__is_active=True)))\
        #                                                     .annotate(direction_count=Count('cash_directions'))\
        #                                                     .filter(Q(direction_count__gt=0) | Q(partner_direction_count__gt=0)))
        prefetch_cities = Prefetch('cities', prefetch_cities_queryset)
        prefetch_countries = Prefetch('partner_countries', prefetch_counries_queryset)

        # countries = Country.objects.prefetch_related(prefetch_cities,
        #                                             prefetch_countries)\
        #                             .annotate(direction_count=Count('cities__cash_directions',
        #                                                             filter=Q(cities__cash_directions__is_active=True)))\
        #                             .annotate(country_direction_count=Count('partner_countries__partner_directions',
        #                                                                     filter=Q(partner_countries__partner_directions__is_active=True)))\
        #                             .filter(Q(direction_count__gt=0) | Q(country_direction_count__gt=0))\
        #                             .order_by('name')\
        #                             .all()
        
        countries = Country.objects.prefetch_related(prefetch_cities,
                                                    prefetch_countries)\
                                    .annotate(direction_count=Count('cities__cash_directions',
                                                                    filter=Q(cities__cash_directions__is_active=True)))\
                                    .annotate(partner_direction_count=Count('cities__partner_cities__partner_directions',
                                                                    filter=Q(cities__partner_cities__partner_directions__is_active=True)))\
                                    .annotate(country_direction_count=Count('partner_countries__partner_directions',
                                                                filter=Q(partner_countries__partner_directions__is_active=True)))\
                                    .filter(Q(direction_count__gt=0) | Q(country_direction_count__gt=0) | Q(partner_direction_count__gt=0))\
                                    .order_by('name')\
                                    .all()
        # country_direction_count =  Country.objects.prefetch_related(prefetch_cities,
        #                                             prefetch_countries)\
        #                                         .annotate(country_direction_count=Count('partner_countries__partner_directions',
        #                                                                     filter=Q(partner_countries__partner_directions__is_active=True)))\
        #                             .filter(Q(country_direction_count=0))\
        #                             .order_by('name')\
        #                             .values('name', 'country_direction_count')\
        #                             .all()
        
        # print(country_direction_count)

        # _country_direction_count_dict = {el['name']: el['country_direction_count'] for el in country_direction_count}
        
        # for country in countries:
        #     if country.name in _country_direction_count_dict:
        #         country.country_direction_count = _country_direction_count_dict[country.name]

        # countries = [el for el in countries if (el.direction_count > 0 or el.partner_direction_count > 0 or el.country_direction_count > 0)]

        if not countries:
            http_exception_json(status_code=404, param=request.url)

        available_countries = get_available_countries3(countries)
        cache.set('available_countries', available_countries, 180)
    
    return available_countries