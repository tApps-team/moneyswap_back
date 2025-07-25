from typing import List

from django.db.models import Count, Q, Prefetch
from django.db import connection
from django.core.exceptions import ObjectDoesNotExist

from fastapi import APIRouter, Request, HTTPException

from general_models.utils.http_exc import http_exception_json
from general_models.utils.endpoints import (get_exchange_direction_list,
                                            get_exchange_direction_list_with_location,
                                            get_valute_json,
                                            get_valute_json_2, get_valute_json_3,
                                            increase_popular_count_direction, new_get_reviews_count_filters,
                                            positive_review_count_filter,
                                            neutral_review_count_filter,
                                            negative_review_count_filter, test_get_exchange_direction_list, test_get_exchange_direction_list_with_aml,
                                            try_generate_icon_url,
                                            get_reviews_count_filters)

from partners.utils.endpoints import (get_partner_directions,
                                      get_partner_directions3,
                                      get_partner_directions_with_location,
                                      get_partner_directions2, new_test_get_partner_directions2_with_aml, new_test_get_partner_directions2_with_aml2, test_get_partner_directions2, test_get_partner_directions2_with_aml, test_get_partner_directions3)
from partners.models import CountryDirection, Direction as PartnerDirection, PartnerCountry

from .models import City, ExchangeDirection, Country
from .schemas import (MultipleName,
                      RuEnCountryModel, RuEnCountryModel1,
                      SpecificCountrySchema,
                      SpecificCitySchema)
from .utils.endpoints import (get_available_countries,
                              get_available_countries2,
                              get_available_countries3)
from .utils.cache import get_or_set_cache_available_countries, get_or_set_cache_available_countries2, get_or_set_cache_available_countries3, get_or_set_cache_available_countries4

cash_router = APIRouter(prefix='/cash',
                        tags=['Наличные'])


# Эндпоинт для получения доступных стран
# и связанных с ними городов
# @cash_router.get('/countries',
#                  response_model=List[RuEnCountryModel],
#                  response_model_by_alias=False)
# def get_available_coutries(request: Request):
#     print(len(connection.queries))
#     #
#     # cities = City.objects.filter(Q(is_parse=True) | Q(has_partner_cities=True))\
#     #                         .select_related('country').all()
#     #
#     # cities = City.objects.filter(is_parse=True)\
#     #                         .select_related('country').all()
    
#     # countries = Country.objects.prefetch_related('cities')\
#     #                             .annotate(direction_count=Count('cities__cash_directions',
#     #                                                             filter=Q(cities__cash_directions__is_active=True)))\
#     #                             .filter(direction_count__gt=0)\
#     #                             .all()
#     prefetch_cities_queryset =  City.objects.order_by('name')\
#                                             .prefetch_related('cash_directions')\
#                                             .annotate(partner_direction_count=Count('partner_cities',
#                                                                                     filter=Q(partner_cities__partner_directions__is_active=True)))\
#                                             .annotate(direction_count=Count('cash_directions',
#                                                                             filter=Q(cash_directions__is_active=True)))\
#                                             .filter(Q(direction_count__gt=0) | Q(partner_direction_count__gt=0))


#     # prefetch_cities = Prefetch('cities', City.objects.order_by('name')\
#     #                                                     .prefetch_related('cash_directions')\
#     #                                                     .annotate(partner_direction_count=Count('partner_cities',
#     #                                                                                             filter=Q(partner_cities__partner_directions__is_active=True)))\
#     #                                                     .annotate(direction_count=Count('cash_directions'))\
#     #                                                     .filter(Q(direction_count__gt=0) | Q(partner_direction_count__gt=0)))
#     prefetch_cities = Prefetch('cities', prefetch_cities_queryset)



#     countries = Country.objects.prefetch_related(prefetch_cities)\
#                                 .annotate(direction_count=Count('cities__cash_directions',
#                                                                 filter=Q(cities__cash_directions__is_active=True)))\
#                                 .filter(direction_count__gt=0)\
#                                 .order_by('name')\
#                                 .all()


#     if not countries:
#         http_exception_json(status_code=404, param=request.url)

#     countries = get_available_countries(countries)

#     return countries


# Эндпоинт для получения доступных стран
# и связанных с ними городов
# @cash_router.get('/countries',
#                  response_model=List[RuEnCountryModel],
#                  response_model_by_alias=False)
# def get_available_coutries2(request: Request):
#     # print(len(connection.queries))

#     countries = get_or_set_cache_available_countries2(request)
#     #
#     # cities = City.objects.filter(Q(is_parse=True) | Q(has_partner_cities=True))\
#     #                         .select_related('country').all()
#     #
#     # cities = City.objects.filter(is_parse=True)\
#     #                         .select_related('country').all()
    
#     # countries = Country.objects.prefetch_related('cities')\
#     #                             .annotate(direction_count=Count('cities__cash_directions',
#     #                                                             filter=Q(cities__cash_directions__is_active=True)))\
#     #                             .filter(direction_count__gt=0)\
#     #                             .all()
#     # prefetch_cities_queryset =  City.objects.order_by('name')\
#     #                                         .select_related('country')\
#     #                                         .prefetch_related('cash_directions',
#     #                                                           'partner_cities')\
#     #                                         .annotate(partner_direction_count=Count('partner_cities',
#     #                                                                                 filter=Q(partner_cities__partner_directions__is_active=True)))\
#     #                                         .annotate(direction_count=Count('cash_directions',
#     #                                                                         filter=Q(cash_directions__is_active=True)))\
#     #                                         .filter(Q(direction_count__gt=0) \
#     #                                                 | Q(partner_direction_count__gt=0) \
#     #                                                     | Q(country__partner_countries__partner_directions__isnull=False))\
#     #                                         .distinct()


#     # prefetch_counries_queryset =  PartnerCountry.objects.prefetch_related('partner_directions')\
#     #                                         .annotate(partner_direction_count=Count('partner_directions',
#     #                                                                                 filter=Q(partner_directions__is_active=True)))\
#     #                                         .filter(Q(partner_direction_count__gt=0))
#     # # prefetch_cities = Prefetch('cities', City.objects.order_by('name')\
#     # #                                                     .prefetch_related('cash_directions')\
#     # #                                                     .annotate(partner_direction_count=Count('partner_cities',
#     # #                                                                                             filter=Q(partner_cities__partner_directions__is_active=True)))\
#     # #                                                     .annotate(direction_count=Count('cash_directions'))\
#     # #                                                     .filter(Q(direction_count__gt=0) | Q(partner_direction_count__gt=0)))
#     # prefetch_cities = Prefetch('cities', prefetch_cities_queryset)
#     # prefetch_countries = Prefetch('partner_countries', prefetch_counries_queryset)

#     # countries = Country.objects.prefetch_related(prefetch_cities,
#     #                                              prefetch_countries)\
#     #                             .annotate(direction_count=Count('cities__cash_directions',
#     #                                                             filter=Q(cities__cash_directions__is_active=True)))\
#     #                             .annotate(country_direction_count=Count('partner_countries__partner_directions',
#     #                                                                     filter=Q(partner_countries__partner_directions__is_active=True)))\
#     #                             .filter(Q(direction_count__gt=0) | Q(country_direction_count__gt=0))\
#     #                             .order_by('name')\
#     #                             .all()


#     # if not countries:
#     #     http_exception_json(status_code=404, param=request.url)

#     # countries = get_available_countries3(countries)

#     return countries


@cash_router.get('/countries',
                 response_model=List[RuEnCountryModel],
                 response_model_by_alias=False)
def get_available_coutries2(request: Request):

    countries = get_or_set_cache_available_countries3(request)

    return countries



@cash_router.get('/countries2',
                 response_model=List[RuEnCountryModel1],
                 response_model_by_alias=False)
def get_available_coutries2(request: Request):

    countries = get_or_set_cache_available_countries4(request)

    return countries


#
@cash_router.get('/specific_city',
                 response_model=SpecificCitySchema,
                 response_model_by_alias=False)
def get_specific_city(code_name: str):
    code_name = code_name.upper()
    try:
        city = City.objects.select_related('country').get(code_name=code_name)
    except ObjectDoesNotExist:
        raise HTTPException(status_code=400)
    else:
        icon_url = try_generate_icon_url(city.country)
        city.country_info = SpecificCountrySchema(name=MultipleName(name=city.country.name,
                                                                    en_name=city.country.en_name),
                                            icon_url=icon_url)
        city.name = MultipleName(name=city.name,
                                en_name=city.en_name)
        
        return city
#

# Вспомогательный эндпоинт для получения наличных валют
def cash_valutes(request: Request,
                 params: dict):
    for param in params:
        if not params[param]:
            http_exception_json(status_code=400, param=param)
    
    city, base = (params[key] for key in params)

    cash_queries = ExchangeDirection.objects\
                                    .select_related('exchange',
                                                    'city',
                                                    'direction',
                                                    'direction__valute_from',
                                                    'direction__valute_to')\
                                    .filter(city__code_name=city,
                                            is_active=True,
                                            exchange__is_active=True)
    partner_queries = PartnerDirection.objects\
                                        .select_related('direction',
                                                        'city',
                                                        'direction__valute_from',
                                                        'direction__valute_to',
                                                        'city__exchange')\
                                        .filter(city__city__code_name=city,
                                                is_active=True,
                                                city__exchange__isnull=False,
                                                city__exchange__is_active=True)
    
    country_directions_query = CountryDirection.objects\
                                .select_related('direction',
                                                'direction__valute_from',
                                                'direction__valute_to',
                                                'country',
                                                'country__country',
                                                'country__exchange')\
                                .filter(is_active=True,
                                        country__exchange__is_active=True,
                                        country__exchange__isnull=False,
                                        country__country__cities__code_name=city)

    if base == 'ALL':
        cash_queries = cash_queries\
                                .values_list('direction__valute_from').all()
        partner_queries = partner_queries\
                                .values_list('direction__valute_from__code_name').all()
        country_directions_query = country_directions_query\
                                .values_list('direction__valute_from__code_name').all()
    else:
        cash_queries = cash_queries.filter(direction__valute_from=base)\
                                    .values_list('direction__valute_to').all()
        partner_queries = partner_queries.filter(direction__valute_from__code_name=base)\
                                        .values_list('direction__valute_to__code_name').all()
        country_directions_query = country_directions_query\
                                        .filter(direction__valute_from__code_name=base)\
                                        .values_list('direction__valute_to__code_name').all()

    queries = cash_queries.union(partner_queries, country_directions_query)

    if not queries:
        http_exception_json(status_code=404, param=request.url)

    return get_valute_json(queries)


#
# Вспомогательный эндпоинт для получения наличных валют
def cash_valutes_2(request: Request,
                 params: dict):
    for param in params:
        if not params[param]:
            http_exception_json(status_code=400, param=param)
    
    city, base = (params[key] for key in params)

    cash_queries = ExchangeDirection.objects\
                                    .select_related('exchange',
                                                    'city',
                                                    'direction',
                                                    'direction__valute_from',
                                                    'direction__valute_to')\
                                    .filter(city__code_name=city,
                                            is_active=True,
                                            exchange__is_active=True)
    partner_queries = PartnerDirection.objects\
                                        .select_related('direction',
                                                        'city',
                                                        'direction__valute_from',
                                                        'direction__valute_to',
                                                        'city__exchange')\
                                        .filter(city__city__code_name=city,
                                                is_active=True,
                                                city__exchange__is_active=True,
                                                city__exchange__isnull=False)
    
    country_directions_query = CountryDirection.objects\
                                .select_related('direction',
                                                'direction__valute_from',
                                                'direction__valute_to',
                                                'country',
                                                'country__country',
                                                'country__exchange')\
                                .filter(is_active=True,
                                        country__exchange__is_active=True,
                                        country__exchange__isnull=False,
                                        country__country__cities__code_name=city)

    if base == 'ALL':
        cash_queries = cash_queries\
                                .values_list('direction__valute_from').all()
        partner_queries = partner_queries\
                                .values_list('direction__valute_from__code_name').all()
        country_directions_query = country_directions_query\
                                .values_list('direction__valute_from__code_name').all()
    else:
        cash_queries = cash_queries.filter(direction__valute_from=base)\
                                    .values_list('direction__valute_to').all()
        partner_queries = partner_queries.filter(direction__valute_from__code_name=base)\
                                        .values_list('direction__valute_to__code_name').all()
        country_directions_query = country_directions_query\
                                        .filter(direction__valute_from__code_name=base)\
                                        .values_list('direction__valute_to__code_name').all()

    queries = cash_queries.union(partner_queries, country_directions_query)

    if not queries:
        http_exception_json(status_code=404, param=request.url)

    return get_valute_json_2(queries)
#


def cash_valutes_3(request: Request,
                 params: dict):
    for param in params:
        if not params[param]:
            http_exception_json(status_code=400, param=param)
    
    city, base = (params[key] for key in params)

    cash_queries = ExchangeDirection.objects\
                                    .select_related('exchange',
                                                    'city',
                                                    'direction',
                                                    'direction__valute_from',
                                                    'direction__valute_to')\
                                    .filter(city__code_name=city,
                                            is_active=True,
                                            exchange__is_active=True)
    partner_queries = PartnerDirection.objects\
                                        .select_related('direction',
                                                        'city',
                                                        'direction__valute_from',
                                                        'direction__valute_to',
                                                        'city__exchange')\
                                        .filter(city__city__code_name=city,
                                                is_active=True,
                                                city__exchange__is_active=True,
                                                city__exchange__isnull=False)
    
    country_directions_query = CountryDirection.objects\
                                .select_related('direction',
                                                'direction__valute_from',
                                                'direction__valute_to',
                                                'country',
                                                'country__country',
                                                'country__exchange')\
                                .filter(is_active=True,
                                        country__exchange__is_active=True,
                                        country__exchange__isnull=False,
                                        country__country__cities__code_name=city)

    if base == 'ALL':
        cash_queries = cash_queries\
                                .values_list('direction__valute_from').all()
        partner_queries = partner_queries\
                                .values_list('direction__valute_from__code_name').all()
        country_directions_query = country_directions_query\
                                .values_list('direction__valute_from__code_name').all()
    else:
        cash_queries = cash_queries.filter(direction__valute_from=base)\
                                    .values_list('direction__valute_to').all()
        partner_queries = partner_queries.filter(direction__valute_from__code_name=base)\
                                        .values_list('direction__valute_to__code_name').all()
        country_directions_query = country_directions_query\
                                        .filter(direction__valute_from__code_name=base)\
                                        .values_list('direction__valute_to__code_name').all()

    queries = cash_queries.union(partner_queries, country_directions_query)

    if not queries:
        http_exception_json(status_code=404, param=request.url)

    return get_valute_json_3(queries)


# Вспомогательный эндпоинт для получения наличных готовых направлений
def cash_exchange_directions(request: Request,
                             params: dict):
    for param in params:
        if not params[param]:
            http_exception_json(status_code=400, param=param) 

    city, valute_from, valute_to = (params[key] for key in params)

    review_counts = get_reviews_count_filters('exchange_direction')

    queries = ExchangeDirection.objects\
                                .select_related('exchange',
                                                'city',
                                                'city__country',
                                                'direction',
                                                'direction__valute_from',
                                                'direction__valute_to')\
                                .annotate(positive_review_count=review_counts['positive'])\
                                .annotate(neutral_review_count=review_counts['neutral'])\
                                .annotate(negative_review_count=review_counts['negative'])\
                                .filter(city__code_name=city,
                                        direction__valute_from=valute_from,
                                        direction__valute_to=valute_to,
                                        is_active=True,
                                        exchange__is_active=True)\
                                .all()
    
    partner_directions = get_partner_directions(valute_from,
                                                valute_to,
                                                city)
    
    queries = sorted(list(queries) + list(partner_directions),
                     key=lambda query: (-query.exchange.is_vip,
                                        -query.out_count,
                                        query.in_count))
    
    if not queries:
        http_exception_json(status_code=404, param=request.url)

    increase_popular_count_direction(valute_from=valute_from,
                                     valute_to=valute_to,
                                     city=city)

    return get_exchange_direction_list(queries,
                                       valute_from,
                                       valute_to,
                                       city=city)

# Вспомогательный эндпоинт для получения наличных готовых направлений
def cash_exchange_directions2(request: Request,
                             params: dict):
    for param in params:
        if not params[param]:
            http_exception_json(status_code=400, param=param) 

    city, valute_from, valute_to = (params[key] for key in params)

    review_counts = get_reviews_count_filters('exchange_direction')

    queries = ExchangeDirection.objects\
                                .select_related('exchange',
                                                'city',
                                                'city__country',
                                                'direction',
                                                'direction__valute_from',
                                                'direction__valute_to')\
                                .annotate(positive_review_count=review_counts['positive'])\
                                .annotate(neutral_review_count=review_counts['neutral'])\
                                .annotate(negative_review_count=review_counts['negative'])\
                                .filter(city__code_name=city,
                                        direction__valute_from=valute_from,
                                        direction__valute_to=valute_to,
                                        is_active=True,
                                        exchange__is_active=True)\
                                .all()
    
    partner_directions = get_partner_directions2(valute_from,
                                                valute_to,
                                                city)
    
    queries = sorted(list(queries) + list(partner_directions),
                     key=lambda query: (-query.exchange.is_vip,
                                        -query.out_count,
                                        query.in_count))
    
    if not queries:
        http_exception_json(status_code=404, param=request.url)

    increase_popular_count_direction(valute_from=valute_from,
                                     valute_to=valute_to,
                                     city=city)

    return get_exchange_direction_list(queries,
                                       valute_from,
                                       valute_to,
                                       city=city)


def test_cash_exchange_directions2(request: Request,
                                   params: dict):
    for param in params:
        if not params[param]:
            http_exception_json(status_code=400, param=param) 

    city, valute_from, valute_to = (params[key] for key in params)

    review_counts = get_reviews_count_filters('exchange_direction')

    queries = ExchangeDirection.objects\
                                .select_related('exchange',
                                                'city',
                                                'city__country',
                                                'direction',
                                                'direction__valute_from',
                                                'direction__valute_to')\
                                .annotate(positive_review_count=review_counts['positive'])\
                                .annotate(neutral_review_count=review_counts['neutral'])\
                                .annotate(negative_review_count=review_counts['negative'])\
                                .filter(city__code_name=city,
                                        direction__valute_from=valute_from,
                                        direction__valute_to=valute_to,
                                        is_active=True,
                                        exchange__is_active=True)\
                                .all()
    
    partner_directions = test_get_partner_directions2(valute_from,
                                                valute_to,
                                                city)
    
    queries = sorted(list(queries) + list(partner_directions),
                     key=lambda query: (-query.exchange.is_vip,
                                        -query.out_count,
                                        query.in_count))
    
    if not queries:
        http_exception_json(status_code=404, param=request.url)

    increase_popular_count_direction(valute_from=valute_from,
                                     valute_to=valute_to,
                                     city=city)

    return test_get_exchange_direction_list(queries,
                                       valute_from,
                                       valute_to,
                                       city=city)


def test_cash_exchange_directions3(request: Request,
                                   params: dict):
    for param in params:
        if not params[param]:
            http_exception_json(status_code=400, param=param) 

    city, valute_from, valute_to = (params[key] for key in params)

    # review_counts = get_reviews_count_filters('exchange_direction')
    review_counts = new_get_reviews_count_filters('exchange_direction')

    queries = ExchangeDirection.objects\
                                .select_related('exchange',
                                                'city',
                                                'city__country',
                                                'direction',
                                                'direction__valute_from',
                                                'direction__valute_to')\
                                .annotate(positive_review_count=review_counts['positive'])\
                                .annotate(neutral_review_count=review_counts['neutral'])\
                                .annotate(negative_review_count=review_counts['negative'])\
                                .filter(city__code_name=city,
                                        direction__valute_from=valute_from,
                                        direction__valute_to=valute_to,
                                        is_active=True,
                                        exchange__is_active=True)\
                                .all()
    
    partner_directions = new_test_get_partner_directions2_with_aml(valute_from,
                                                valute_to,
                                                city)
    
    # queries = sorted(list(queries) + list(partner_directions),
    #                  key=lambda query: (-query.exchange.is_vip,
    #                                     -query.out_count,
    #                                     query.in_count))
    queries = sorted(list(queries) + list(partner_directions),
                     key=lambda query: (-query.exchange.is_vip,))
    
    if not queries:
        http_exception_json(status_code=404, param=request.url)

    increase_popular_count_direction(valute_from=valute_from,
                                     valute_to=valute_to,
                                     city=city)

    return test_get_exchange_direction_list_with_aml(queries,
                                       valute_from,
                                       valute_to,
                                       city=city)


def test_cash_exchange_directions22(request: Request,
                                   params: dict):
    for param in params:
        if not params[param]:
            http_exception_json(status_code=400, param=param) 

    city, valute_from, valute_to = (params[key] for key in params)

    # review_counts = get_reviews_count_filters('exchange_direction')
    review_counts = new_get_reviews_count_filters('exchange_direction')

    queries = ExchangeDirection.objects\
                                .select_related('exchange',
                                                'city',
                                                'city__country',
                                                'direction',
                                                'direction__valute_from',
                                                'direction__valute_to')\
                                .annotate(positive_review_count=review_counts['positive'])\
                                .annotate(neutral_review_count=review_counts['neutral'])\
                                .annotate(negative_review_count=review_counts['negative'])\
                                .filter(city__code_name=city,
                                        direction__valute_from=valute_from,
                                        direction__valute_to=valute_to,
                                        is_active=True,
                                        exchange__is_active=True)\
                                .all()
    
    partner_directions = new_test_get_partner_directions2_with_aml2(valute_from,
                                                valute_to,
                                                city)
    
    # queries = sorted(list(queries) + list(partner_directions),
    #                  key=lambda query: (-query.exchange.is_vip,
    #                                     -query.out_count,
    #                                     query.in_count))
    queries = sorted(list(queries) + list(partner_directions),
                     key=lambda query: (-query.exchange.is_vip,))
    
    if not queries:
        http_exception_json(status_code=404, param=request.url)

    increase_popular_count_direction(valute_from=valute_from,
                                     valute_to=valute_to,
                                     city=city)

    return test_get_exchange_direction_list_with_aml(queries,
                                       valute_from,
                                       valute_to,
                                       city=city)



# Вспомогательный эндпоинт для получения наличных готовых направлений
def cash_exchange_directions_with_location(request: Request,
                                           params: dict): 
    valute_from, valute_to = (params[key] for key in params)

    review_counts = get_reviews_count_filters('exchange_direction')

    queries = ExchangeDirection.objects\
                                .select_related('exchange',
                                                'city',
                                                'city__country',
                                                'direction',
                                                'direction__valute_from',
                                                'direction__valute_to')\
                                .annotate(positive_review_count=review_counts['positive'])\
                                .annotate(neutral_review_count=review_counts['neutral'])\
                                .annotate(negative_review_count=review_counts['negative'])\
                                .filter(
                                        direction__valute_from=valute_from,
                                        direction__valute_to=valute_to,
                                        is_active=True,
                                        exchange__is_active=True)\
                                .all()
    
    partner_directions = get_partner_directions(valute_from,
                                                valute_to)
    
    queries = sorted(list(queries) + list(partner_directions),
                     key=lambda query: (-query.exchange.is_vip,
                                        -query.out_count,
                                        query.in_count))
    
    if not queries:
        http_exception_json(status_code=404, param=request.url)

    return get_exchange_direction_list(queries,
                                       valute_from,
                                       valute_to,
                                       with_location=True)


# Вспомогательный эндпоинт для получения наличных готовых направлений
def cash_exchange_directions_with_location2(request: Request,
                                           params: dict): 
    valute_from, valute_to = (params[key] for key in params)

    review_counts = get_reviews_count_filters('exchange_direction')

    queries = ExchangeDirection.objects\
                                .select_related('exchange',
                                                'city',
                                                'city__country',
                                                'direction',
                                                'direction__valute_from',
                                                'direction__valute_to')\
                                .annotate(positive_review_count=review_counts['positive'])\
                                .annotate(neutral_review_count=review_counts['neutral'])\
                                .annotate(negative_review_count=review_counts['negative'])\
                                .filter(
                                        direction__valute_from=valute_from,
                                        direction__valute_to=valute_to,
                                        is_active=True,
                                        exchange__is_active=True)\
                                .all()
    
    partner_directions = get_partner_directions3(valute_from,
                                                valute_to)
    
    # print(partner_directions)
    
    queries = sorted(list(queries) + list(partner_directions),
                     key=lambda query: (-query.exchange.is_vip,
                                        -query.out_count,
                                        query.in_count))
    
    if not queries:
        http_exception_json(status_code=404, param=request.url)

    return get_exchange_direction_list(queries,
                                       valute_from,
                                       valute_to,
                                       with_location=True)


def test_cash_exchange_directions_with_location2(request: Request,
                                           params: dict): 
    valute_from, valute_to = (params[key] for key in params)

    review_counts = new_get_reviews_count_filters('exchange_direction')

    queries = ExchangeDirection.objects\
                                .select_related('exchange',
                                                'city',
                                                'city__country',
                                                'direction',
                                                'direction__valute_from',
                                                'direction__valute_to')\
                                .annotate(positive_review_count=review_counts['positive'])\
                                .annotate(neutral_review_count=review_counts['neutral'])\
                                .annotate(negative_review_count=review_counts['negative'])\
                                .filter(direction__valute_from=valute_from,
                                        direction__valute_to=valute_to,
                                        is_active=True,
                                        exchange__is_active=True)\
                                .all()
    
    partner_directions = test_get_partner_directions3(valute_from,
                                                valute_to)
    
    # print(partner_directions)
    
    queries = sorted(list(queries) + list(partner_directions),
                     key=lambda query: (-query.exchange.is_vip,
                                        -query.out_count,
                                        query.in_count))
    
    if not queries:
        http_exception_json(status_code=404, param=request.url)

    return test_get_exchange_direction_list(queries,
                                       valute_from,
                                       valute_to,
                                       with_location=True)