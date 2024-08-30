from typing import List

from django.db.models import Count, Q, Prefetch
from django.db import connection
from django.core.exceptions import ObjectDoesNotExist

from fastapi import APIRouter, Request, HTTPException

from general_models.utils.http_exc import http_exception_json
from general_models.utils.endpoints import (get_exchange_direction_list,
                                            get_valute_json,
                                            get_valute_json_2,
                                            increase_popular_count_direction,
                                            positive_review_count_filter,
                                            neutral_review_count_filter,
                                            negative_review_count_filter,
                                            try_generate_icon_url)

from partners.utils.endpoints import get_partner_directions
from partners.models import Direction as PartnerDirection

from .models import City, ExchangeDirection, Country
from .schemas import (MultipleName,
                      RuEnCountryModel,
                      SpecificCountrySchema,
                      SpecificCitySchema)
from .utils.endpoints import get_available_countries


cash_router = APIRouter(prefix='/cash',
                        tags=['Наличные'])


# Эндпоинт для получения доступных стран
# и связанных с ними городов
@cash_router.get('/countries',
                 response_model=List[RuEnCountryModel],
                 response_model_by_alias=False)
def get_available_coutries(request: Request):
    print(len(connection.queries))
    #
    # cities = City.objects.filter(Q(is_parse=True) | Q(has_partner_cities=True))\
    #                         .select_related('country').all()
    #
    # cities = City.objects.filter(is_parse=True)\
    #                         .select_related('country').all()
    
    # countries = Country.objects.prefetch_related('cities')\
    #                             .annotate(direction_count=Count('cities__cash_directions',
    #                                                             filter=Q(cities__cash_directions__is_active=True)))\
    #                             .filter(direction_count__gt=0)\
    #                             .all()
    prefetch_cities_queryset =  City.objects.order_by('name')\
                                            .prefetch_related('cash_directions')\
                                            .annotate(partner_direction_count=Count('partner_cities',
                                                                                    filter=Q(partner_cities__partner_directions__is_active=True)))\
                                            .annotate(direction_count=Count('cash_directions',
                                                                            filter=Q(cash_directions__is_active=True)))\
                                            .filter(Q(direction_count__gt=0) | Q(partner_direction_count__gt=0))


    # prefetch_cities = Prefetch('cities', City.objects.order_by('name')\
    #                                                     .prefetch_related('cash_directions')\
    #                                                     .annotate(partner_direction_count=Count('partner_cities',
    #                                                                                             filter=Q(partner_cities__partner_directions__is_active=True)))\
    #                                                     .annotate(direction_count=Count('cash_directions'))\
    #                                                     .filter(Q(direction_count__gt=0) | Q(partner_direction_count__gt=0)))
    prefetch_cities = Prefetch('cities', prefetch_cities_queryset)



    countries = Country.objects.prefetch_related(prefetch_cities)\
                                .annotate(direction_count=Count('cities__cash_directions',
                                                                filter=Q(cities__cash_directions__is_active=True)))\
                                .filter(direction_count__gt=0)\
                                .order_by('name')\
                                .all()


    if not countries:
        http_exception_json(status_code=404, param=request.url)

    countries = get_available_countries(countries)

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
                                                city__exchange__isnull=False)

    if base == 'ALL':
        cash_queries = cash_queries\
                                .values_list('direction__valute_from').all()
        partner_queries = partner_queries\
                                .values_list('direction__valute_from__code_name').all()
    else:
        cash_queries = cash_queries.filter(direction__valute_from=base)\
                                    .values_list('direction__valute_to').all()
        partner_queries = partner_queries.filter(direction__valute_from__code_name=base)\
                                        .values_list('direction__valute_to__code_name').all()

    queries = cash_queries.union(partner_queries)

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
                                                city__exchange__isnull=False)

    if base == 'ALL':
        cash_queries = cash_queries\
                                .values_list('direction__valute_from').all()
        partner_queries = partner_queries\
                                .values_list('direction__valute_from__code_name').all()
    else:
        cash_queries = cash_queries.filter(direction__valute_from=base)\
                                    .values_list('direction__valute_to').all()
        partner_queries = partner_queries.filter(direction__valute_from__code_name=base)\
                                        .values_list('direction__valute_to__code_name').all()

    queries = cash_queries.union(partner_queries)

    if not queries:
        http_exception_json(status_code=404, param=request.url)

    return get_valute_json_2(queries)
#


# Вспомогательный эндпоинт для получения наличных готовых направлений
def cash_exchange_directions(request: Request,
                             params: dict):
    for param in params:
        if not params[param]:
            http_exception_json(status_code=400, param=param)

    # print(len(connection.queries))    

    city, valute_from, valute_to = (params[key] for key in params)

    # review_count_filter = Count('exchange__reviews',
    #                             filter=Q(exchange__reviews__moderation=True))
    positive_review_count = Count('exchange__reviews',
                                         filter=positive_review_count_filter)
    neutral_review_count = Count('exchange__reviews',
                                         filter=neutral_review_count_filter)
    negative_review_count = Count('exchange__reviews',
                                         filter=negative_review_count_filter)
    queries = ExchangeDirection.objects\
                                .select_related('exchange',
                                                'city',
                                                'direction',
                                                'direction__valute_from',
                                                'direction__valute_to')\
                                .annotate(positive_review_count=positive_review_count)\
                                .annotate(neutral_review_count=neutral_review_count)\
                                .annotate(negative_review_count=negative_review_count)\
                                .filter(city__code_name=city,
                                        direction__valute_from=valute_from,
                                        direction__valute_to=valute_to,
                                        is_active=True,
                                        exchange__is_active=True)\
                                .all()
    
    partner_directions = get_partner_directions(city,
                                                valute_from,
                                                valute_to)
    
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