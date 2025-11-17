from typing import List

from django.db.models import Count, Q, Prefetch
from django.db import connection
from django.core.exceptions import ObjectDoesNotExist

from fastapi import APIRouter, Request, HTTPException

from general_models.utils.http_exc import http_exception_json
from general_models.utils.endpoints import (get_valute_json,
                                            get_valute_json_3,
                                            new_increase_popular_count_direction,
                                            test_new_get_exchange_direction_list_with_aml,
                                            try_generate_icon_url)
from general_models.utils.base import annotate_string_field

from partners.utils.endpoints import (get_partner_directions_with_location,
                                      test_get_partner_directions_with_aml,
                                      get_bankomats_and_partner_valute_dict)
from partners.models import (CountryDirection,
                             Direction as PartnerDirection,
                             PartnerCountry,
                             NewCountryDirection,
                             NewDirection as NewPartnerDirection,
                             NewCountryDirectionRate)

from .models import City, ExchangeDirection, NewExchangeDirection
from .schemas import (MultipleName,
                      RuEnCountryModel1,
                      SpecificCountrySchema,
                      SpecificCitySchema)
from .utils.endpoints import (get_available_countries,
                              test_get_available_countries,)
# from .utils.cache import (get_or_set_cache_available_countries3,
#                           get_or_set_cache_available_countries5)

cash_router = APIRouter(prefix='/cash',
                        tags=['Наличные'])

new_cash_router = APIRouter(prefix='/cash',
                            tags=['Наличные(НОВЫЕ)'])



# @new_cash_router.get('/countries',
#                  response_model=List[RuEnCountryModel1],
#                  response_model_by_alias=False)
# def get_available_coutries(request: Request):

#     countries = get_available_countries(request)

#     return countries


# def get_available_coutries3(request: Request):

#     countries = get_or_set_cache_available_countries5(request)

#     return countries


@new_cash_router.get('/countries',
                 response_model=List[RuEnCountryModel1],
                 response_model_by_alias=False)
def get_available_coutries(request: Request):

    countries = test_get_available_countries(request)

    return countries


#
@cash_router.get('/specific_city',
                 response_model=SpecificCitySchema,
                 response_model_by_alias=False)
def get_specific_city(code_name: str):
    code_name = code_name.upper()
    if len(code_name) > 10:
        raise HTTPException(status_code=400,
                            detail='Invalid "code_name"')
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


# Вспомогательный эндпоинт для получения наличных валют
# def cash_valutes_2(request: Request,
#                  params: dict):
#     for param in params:
#         if not params[param]:
#             http_exception_json(status_code=400, param=param)
    
#     city, base = (params[key] for key in params)

#     cash_queries = ExchangeDirection.objects\
#                                     .select_related('exchange',
#                                                     'city',
#                                                     'direction',
#                                                     'direction__valute_from',
#                                                     'direction__valute_to')\
#                                     .filter(city__code_name=city,
#                                             is_active=True,
#                                             exchange__is_active=True)
#     partner_queries = PartnerDirection.objects\
#                                         .select_related('direction',
#                                                         'city',
#                                                         'direction__valute_from',
#                                                         'direction__valute_to',
#                                                         'city__exchange')\
#                                         .filter(city__city__code_name=city,
#                                                 is_active=True,
#                                                 city__exchange__is_active=True,
#                                                 city__exchange__isnull=False)
    
#     country_directions_query = CountryDirection.objects\
#                                 .select_related('direction',
#                                                 'direction__valute_from',
#                                                 'direction__valute_to',
#                                                 'country',
#                                                 'country__country',
#                                                 'country__exchange')\
#                                 .filter(is_active=True,
#                                         country__exchange__is_active=True,
#                                         country__exchange__isnull=False,
#                                         country__country__cities__code_name=city)

#     if base == 'ALL':
#         cash_queries = cash_queries\
#                                 .values_list('direction__valute_from').all()
#         partner_queries = partner_queries\
#                                 .values_list('direction__valute_from__code_name').all()
#         country_directions_query = country_directions_query\
#                                 .values_list('direction__valute_from__code_name').all()
#     else:
#         cash_queries = cash_queries.filter(direction__valute_from=base)\
#                                     .values_list('direction__valute_to').all()
#         partner_queries = partner_queries.filter(direction__valute_from__code_name=base)\
#                                         .values_list('direction__valute_to__code_name').all()
#         country_directions_query = country_directions_query\
#                                         .filter(direction__valute_from__code_name=base)\
#                                         .values_list('direction__valute_to__code_name').all()

#     queries = cash_queries.union(partner_queries, country_directions_query)

#     if not queries:
#         http_exception_json(status_code=404, param=request.url)

#     return get_valute_json_2(queries)
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
                                .values_list('direction__valute_from',
                                             flat=True).all()
        partner_queries = partner_queries\
                                .values_list('direction__valute_from__code_name',
                                             flat=True).all()
        country_directions_query = country_directions_query\
                                .values_list('direction__valute_from__code_name',
                                             flat=True).all()
    else:
        cash_queries = cash_queries.filter(direction__valute_from=base)\
                                    .values_list('direction__valute_to',
                                                 flat=True).all()
        partner_queries = partner_queries.filter(direction__valute_from__code_name=base)\
                                        .values_list('direction__valute_to__code_name',
                                                     flat=True).all()
        country_directions_query = country_directions_query\
                                        .filter(direction__valute_from__code_name=base)\
                                        .values_list('direction__valute_to__code_name',
                                                     flat=True).all()

    queries = cash_queries.union(partner_queries, country_directions_query)

    if not queries:
        http_exception_json(status_code=404, param=request.url)

    return get_valute_json_3(queries)


def cash_valutes(request: Request,
                 params: dict):
    for param in params:
        if not params[param]:
            http_exception_json(status_code=400, param=param)
    
    city, base = (params[key] for key in params)

    cash_queries = NewExchangeDirection.objects\
                                    .select_related('exchange',
                                                    'city',
                                                    'direction',
                                                    'direction__valute_from',
                                                    'direction__valute_to')\
                                    .filter(city__code_name=city,
                                            is_active=True,
                                            exchange__is_active=True)
    partner_queries = NewPartnerDirection.objects\
                                        .select_related('direction',
                                                        'direction__valute_from',
                                                        'direction__valute_to',
                                                        'city',
                                                        'city__city',
                                                        'city__exchange')\
                                        .filter(city__city__code_name=city,
                                                is_active=True,
                                                city__exchange__is_active=True,
                                                city__exchange__isnull=False)
    
    country_directions_query = NewCountryDirection.objects\
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
                                .values_list('direction__valute_from_id')
        partner_queries = partner_queries\
                                .values_list('direction__valute_from_id')
        country_directions_query = country_directions_query\
                                .values_list('direction__valute_from_id')
    else:
        cash_queries = cash_queries.filter(direction__valute_from=base)\
                                    .values_list('direction__valute_to_id')
        partner_queries = partner_queries.filter(direction__valute_from__code_name=base)\
                                        .values_list('direction__valute_to_id')
        country_directions_query = country_directions_query\
                                        .filter(direction__valute_from__code_name=base)\
                                        .values_list('direction__valute_to_id')

    queries = cash_queries.union(partner_queries, country_directions_query)

    if not queries:
        http_exception_json(status_code=404, param=request.url)

    return get_valute_json(queries)


def cash_exchange_directions(request: Request,
                             params: dict):
    for param in params:
        if not params[param]:
            http_exception_json(status_code=400, param=param) 

    city, valute_from, valute_to = (params[key] for key in params)


    country_direction_rate_prefetch = Prefetch('country_direction__direction_rates',
                                       NewCountryDirectionRate.objects.order_by('min_rate_limit'))
    
    _bankomats, partner_valute_dict = get_bankomats_and_partner_valute_dict(valute_to)

    queries = NewExchangeDirection.objects\
                                .select_related('exchange',
                                                'exchange__account',
                                                'city',
                                                'city__country',
                                                'direction',
                                                'country_direction',
                                                'country_direction__country',
                                                'direction__valute_from',
                                                'direction__valute_to')\
                                .prefetch_related(country_direction_rate_prefetch,
                                                #   unavailable_cities_by_partner_country_prefetch,
                                                #   country_cities_prefetch,
                                                  'country_direction__country__working_days')\
                                .annotate(direction_marker=annotate_string_field('auto_cash'))\
                                .filter(city__code_name=city,
                                        direction__valute_from=valute_from,
                                        direction__valute_to=valute_to,
                                        is_active=True,
                                        exchange__is_active=True)\

    
    # доп параметры bankomats, partner_valute_dict
    partner_directions = test_get_partner_directions_with_aml(valute_from,
                                                         valute_to,
                                                         city,
                                                         _bankomats=_bankomats,
                                                         partner_valute_dict=partner_valute_dict)
    
    queries = sorted(list(queries) + list(partner_directions),
                     key=lambda query: (-query.exchange.is_vip,
                                        -query.out_count,
                                        query.in_count))
    
    if not queries:
        http_exception_json(status_code=404, param=request.url)

    # new_increase_popular_count_direction(valute_from=valute_from,
    #                                      valute_to=valute_to,
    #                                      city=city)

    # доп параметры bankomats, partner_valute_dict
    return test_new_get_exchange_direction_list_with_aml(queries,
                                                    valute_from,
                                                    valute_to,
                                                    city=city,
                                                    _bankomats=_bankomats,
                                                    partner_valute_dict=partner_valute_dict)


def test_cash_exchange_directions(request: Request,
                                  params: dict):
    for param in params:
        if not params[param]:
            http_exception_json(status_code=400, param=param) 

    city, valute_from, valute_to = (params[key] for key in params)


    country_direction_rate_prefetch = Prefetch('country_direction__direction_rates',
                                       NewCountryDirectionRate.objects.order_by('min_rate_limit'))
    
    _bankomats, partner_valute_dict = get_bankomats_and_partner_valute_dict(valute_to)

    queries = NewExchangeDirection.objects\
                                .select_related('exchange',
                                                'exchange__account',
                                                'city',
                                                'city__country',
                                                'direction',
                                                'country_direction',
                                                'country_direction__country',
                                                'direction__valute_from',
                                                'direction__valute_to')\
                                .prefetch_related(country_direction_rate_prefetch,
                                                #   unavailable_cities_by_partner_country_prefetch,
                                                #   country_cities_prefetch,
                                                  'country_direction__country__working_days')\
                                .annotate(direction_marker=annotate_string_field('auto_cash'))\
                                .filter(city__code_name=city,
                                        direction__valute_from=valute_from,
                                        direction__valute_to=valute_to,
                                        is_active=True,
                                        exchange__is_active=True)\

    
    # доп параметры bankomats, partner_valute_dict
    partner_directions = test_get_partner_directions_with_aml(valute_from,
                                                         valute_to,
                                                         city,
                                                         _bankomats=_bankomats,
                                                         partner_valute_dict=partner_valute_dict)
    
    queries = sorted(list(queries) + list(partner_directions),
                     key=lambda query: (-query.exchange.is_vip,
                                        -query.out_count,
                                        query.in_count))
    
    if not queries:
        http_exception_json(status_code=404, param=request.url)

    new_increase_popular_count_direction(valute_from=valute_from,
                                         valute_to=valute_to,
                                         city=city)

    # доп параметры bankomats, partner_valute_dict
    return test_new_get_exchange_direction_list_with_aml(queries,
                                                    valute_from,
                                                    valute_to,
                                                    city=city,
                                                    _bankomats=_bankomats,
                                                    partner_valute_dict=partner_valute_dict,
                                                    new_version=True)


def cash_exchange_directions_with_location(request: Request,
                                           params: dict):
    valute_from, valute_to = (params[key] for key in params)

    # review_counts = new_get_reviews_count_filters('exchange_direction')

    country_direction_rate_prefetch = Prefetch('country_direction__direction_rates',
                                       NewCountryDirectionRate.objects.order_by('min_rate_limit'))
    
    _bankomats, partner_valute_dict = get_bankomats_and_partner_valute_dict(valute_to)

    queries = NewExchangeDirection.objects\
                                .select_related('exchange',
                                                'exchange__account',
                                                'city',
                                                'city__country',
                                                'direction',
                                                'direction__valute_from',
                                                'direction__valute_to',
                                                'country_direction',
                                                'country_direction__country')\
                                .prefetch_related(country_direction_rate_prefetch,
                                                  'country_direction__country__working_days')\
                                .annotate(direction_marker=annotate_string_field('auto_cash'))\
                                .filter(direction__valute_from=valute_from,
                                        direction__valute_to=valute_to,
                                        is_active=True,
                                        exchange__is_active=True)\

    # auto_cash_direction_dict_list = []
    # for direction in queries:
    #     direction_dict = {
    #         'exchange': direction.exchange,
    #         # for sort
    #         'is_vip': direction.exchange.is_vip,
    #         'exchange_direction_id': direction.pk,
    #         'direction': direction.direction,
    #         'direction_marker': direction.direction_marker,
    #         'valute_from': direction.direction.valute_from_id,
    #         'valute_to': direction.direction.valute_to_id,
    #         'params': direction.params,
    #         'fromfee': None,
    #         'city': direction.city,
    #         'min_amount': direction.min_amount,
    #         'max_amount': direction.max_amount,
    #         'in_count': direction.in_count,
    #         'out_count': direction.out_count,

    #     }
    #     auto_cash_direction_dict_list.append(direction_dict)

    # нужна новая функция get_partner_directions_with_aml_with_location
    # с доп for циклом по разрешенным городам страны направления для NewCountryDirection ?
    partner_directions: list[dict] = get_partner_directions_with_location(valute_from,
                                                                          valute_to,
                                                                          _bankomats,
                                                                          partner_valute_dict)
    
    # print(partner_directions)
    
    directions = sorted(list(queries) + list(partner_directions),
                     key=lambda el: (-el.exchange.is_vip,
                                        -el.out_count,
                                        el.in_count))
    
    if not directions:
        http_exception_json(status_code=404, param=request.url)

    # return new_get_exchange_direction_list_with_aml_and_location(directions,
    #                                                 valute_from,
    #                                                 valute_to,
    #                                                 with_location=True)
    return test_new_get_exchange_direction_list_with_aml(directions,
                                                         valute_from,
                                                         valute_to,
                                                         with_location=True,
                                                         _bankomats=_bankomats,
                                                         partner_valute_dict=partner_valute_dict)


def test_cash_exchange_directions_with_location(request: Request,
                                           params: dict):
    valute_from, valute_to = (params[key] for key in params)

    # review_counts = new_get_reviews_count_filters('exchange_direction')

    country_direction_rate_prefetch = Prefetch('country_direction__direction_rates',
                                       NewCountryDirectionRate.objects.order_by('min_rate_limit'))
    
    _bankomats, partner_valute_dict = get_bankomats_and_partner_valute_dict(valute_to)

    queries = NewExchangeDirection.objects\
                                .select_related('exchange',
                                                'exchange__account',
                                                'city',
                                                'city__country',
                                                'direction',
                                                'direction__valute_from',
                                                'direction__valute_to',
                                                'country_direction',
                                                'country_direction__country')\
                                .prefetch_related(country_direction_rate_prefetch,
                                                  'country_direction__country__working_days')\
                                .annotate(direction_marker=annotate_string_field('auto_cash'))\
                                .filter(direction__valute_from=valute_from,
                                        direction__valute_to=valute_to,
                                        is_active=True,
                                        exchange__is_active=True)\

    # auto_cash_direction_dict_list = []
    # for direction in queries:
    #     direction_dict = {
    #         'exchange': direction.exchange,
    #         # for sort
    #         'is_vip': direction.exchange.is_vip,
    #         'exchange_direction_id': direction.pk,
    #         'direction': direction.direction,
    #         'direction_marker': direction.direction_marker,
    #         'valute_from': direction.direction.valute_from_id,
    #         'valute_to': direction.direction.valute_to_id,
    #         'params': direction.params,
    #         'fromfee': None,
    #         'city': direction.city,
    #         'min_amount': direction.min_amount,
    #         'max_amount': direction.max_amount,
    #         'in_count': direction.in_count,
    #         'out_count': direction.out_count,

    #     }
    #     auto_cash_direction_dict_list.append(direction_dict)

    # нужна новая функция get_partner_directions_with_aml_with_location
    # с доп for циклом по разрешенным городам страны направления для NewCountryDirection ?
    partner_directions: list[dict] = get_partner_directions_with_location(valute_from,
                                                                          valute_to,
                                                                          _bankomats,
                                                                          partner_valute_dict)
    
    # print(partner_directions)
    
    directions = sorted(list(queries) + list(partner_directions),
                     key=lambda el: (-el.exchange.is_vip,
                                        -el.out_count,
                                        el.in_count))
    
    if not directions:
        http_exception_json(status_code=404, param=request.url)

    # return new_get_exchange_direction_list_with_aml_and_location(directions,
    #                                                 valute_from,
    #                                                 valute_to,
    #                                                 with_location=True)
    return test_new_get_exchange_direction_list_with_aml(directions,
                                                         valute_from,
                                                         valute_to,
                                                         with_location=True,
                                                         _bankomats=_bankomats,
                                                         partner_valute_dict=partner_valute_dict,
                                                         new_version=True)