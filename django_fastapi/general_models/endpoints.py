from typing import List, Union
from datetime import datetime, timedelta
from math import ceil
from random import choice, shuffle

from asgiref.sync import async_to_sync

from django.contrib.admin.models import LogEntry
from django.db.models import Count, Q, OuterRef, Subquery, F, Prefetch, Sum
from django.db import connection
from django.db.utils import IntegrityError
from django.core.exceptions import ObjectDoesNotExist

from fastapi import APIRouter, Request, Depends, HTTPException

from .utils.periodic_tasks import get_or_create_schedule
from general_models.models import (Valute,
                                   BaseAdminComment, 
                                   Guest,
                                   FeedbackForm,
                                   en_type_valute_dict)
from general_models.utils.endpoints import (positive_review_count_filter,
                                            neutral_review_count_filter,
                                            negative_review_count_filter,
                                            get_reviews_count_filters,
                                            get_exchange,
                                            generate_image_icon,
                                            # add_reviews_counts,
                                            generate_top_exchanges_query_by_model)
from general_models.utils.base import annotate_string_field

import no_cash.models as no_cash_models
from no_cash.endpoints import no_cash_exchange_directions2, no_cash_valutes, no_cash_exchange_directions, no_cash_valutes_2, no_cash_valutes_3, test_no_cash_exchange_directions2, test_no_cash_exchange_directions3

import cash.models as cash_models
from cash.endpoints import  cash_valutes, cash_exchange_directions, cash_valutes_2, cash_exchange_directions2, cash_valutes_3, test_cash_exchange_directions2, test_cash_exchange_directions3
from cash.schemas import (SpecialCashDirectionMultiModel,
                          CityModel, SpecialCashDirectionMultiPrtnerWithExchangeRatesWithAmlModel, SpecialCashDirectionMultiWithAmlModel,
                          SpecialCashDirectionMultiWithLocationModel,
                          SpecialCashDirectionMultiPrtnerWithLocationModel,
                          SpecialCashDirectionMultiPrtnerModel,
                          SpecialCashDirectionMultiPrtnerWithExchangeRatesModel,
                          SpecialCashDirectionMultiPrtnerExchangeRatesWithLocationModel)
from cash.models import Direction, Country, Exchange, Review

import partners.models as partner_models

from partners.utils.endpoints import generate_actual_course

# from partners.utils.endpoints import get_partner_directions_for_test

from .utils.query_models import AvailableValutesQuery, SpecificDirectionsQuery
from .utils.http_exc import http_exception_json, review_exception_json
from .utils.endpoints import (check_exchage_marker,
                              check_perms_for_adding_review, pust_to_send_bot,
                              try_generate_icon_url,
                              generate_valute_for_schema,
                              get_exchange_directions,
                              generate_image_icon2,
                              generate_coin_for_schema)

from .schemas import (PopularDirectionSchema, SpecialDirectionMultiWithAmlModel,
                      ValuteModel,
                      EnValuteModel,
                      SpecialDirectionMultiModel,
                      ReviewViewSchema,
                      ReviewsByExchangeSchema,
                      AddReviewSchema,
                      CommentSchema,
                      CommentRoleEnum,
                      ValuteListSchema,
                      SpecificValuteSchema,
                      MultipleName,
                      CommonExchangeSchema,
                      ReviewCountSchema,
                      DetailExchangeSchema,
                      DirectionSideBarSchema,
                      ExchangeLinkCountSchema,
                      TopExchangeSchema,
                      TopCoinSchema,
                      FeedbackFormSchema,
                      SiteMapDirectonSchema)


common_router = APIRouter(tags=['Общее'])

test_router = APIRouter(prefix='/test',
                          tags=['Общее(Changed)'])

#
review_router = APIRouter(prefix='/reviews',
                          tags=['Отзывы'])
#


# Эндпоинт для получения доступных валют
# @common_router.get('/available_valutes',
#                    response_model=dict[str, dict[str, list[ValuteModel | EnValuteModel]]],
#                    response_model_by_alias=False)
# def get_available_valutes(request: Request,
#                           query: AvailableValutesQuery = Depends()):
#     params = query.params()
#     if not params['city']:
#         json_dict = no_cash_valutes(request, params)
#     else:
#         json_dict = cash_valutes(request, params)
    
#     return json_dict

#
# @common_router.get('/available_valutes_2')
# def get_available_valutes(request: Request,
#                           query: AvailableValutesQuery = Depends()):
#     params = query.params()
#     if not params['city']:
#         json_dict = no_cash_valutes_2(request, params)
#     else:
#         json_dict = cash_valutes_2(request, params)
    
#     return json_dict
#

@common_router.get('/available_valutes_2')
def get_available_valutes2(request: Request,
                          query: AvailableValutesQuery = Depends()):
    params = query.params()
    if not params['city']:
        json_dict = no_cash_valutes_3(request, params)
    else:
        json_dict = cash_valutes_3(request, params)
    
    return json_dict


# @test_router.get('/available_valutes_2')
# def get_available_valutes2(request: Request,
#                           query: AvailableValutesQuery = Depends()):
#     params = query.params()
#     if not params['city']:
#         json_dict = no_cash_valutes_3(request, params)
#     else:
#         json_dict = cash_valutes_3(request, params)
    
#     return json_dict


#
@common_router.get('/specific_valute',
                   response_model=SpecificValuteSchema,
                   response_model_by_alias=False)
def get_specific_valute(code_name: str):
    code_name = code_name.upper()
    try:
        valute = Valute.objects.get(code_name=code_name)
    except ObjectDoesNotExist:
        raise HTTPException(status_code=400)
    else:
        # print(valute.icon_url)
        valute.icon = try_generate_icon_url(valute)
        # print(valute.icon)
        valute.multiple_name = MultipleName(name=valute.name,
                                            en_name=valute.en_name)
        valute.multiple_type = MultipleName(name=valute.type_valute,
                                            en_name=en_type_valute_dict[valute.type_valute])
        
        return valute
#

# Эндпоинт для получения доступных готовых направлений
# @common_router.get('/directions',
#                  response_model=list[SpecialCashDirectionMultiWithLocationModel | SpecialCashDirectionMultiModel | SpecialDirectionMultiModel],
#                  response_model_by_alias=False)
# def get_current_exchange_directions(request: Request,
#                                     query: SpecificDirectionsQuery = Depends()):
#     params = query.params()
#     if not params['city']:
#         exchange_direction_list = no_cash_exchange_directions(request, params)
#     else:
#         exchange_direction_list = cash_exchange_directions(request, params)
    
#     return exchange_direction_list
# @test_router.get('/directions')
# def get_current_exchange_directions(valute_from: str,
#                                     valute_to: str):
#     get_partner_directions_for_test(valute_from=valute_from,
#                                     valute_to=valute_to)
#     pass
union_directions_response_models = Union[SpecialCashDirectionMultiPrtnerExchangeRatesWithLocationModel,
                                         SpecialCashDirectionMultiPrtnerWithLocationModel,
                                         SpecialCashDirectionMultiWithLocationModel,
                                         SpecialCashDirectionMultiPrtnerWithExchangeRatesModel,
                                         SpecialCashDirectionMultiPrtnerModel,
                                         SpecialCashDirectionMultiModel,
                                         SpecialDirectionMultiModel]

# @common_router.get('/directions',
#                    response_model=list[union_directions_response_models],
#                    response_model_by_alias=False)
#                 #  response_model=list[SpecialCashDirectionMultiPrtnerWithLocationModel | SpecialCashDirectionMultiWithLocationModel | SpecialCashDirectionMultiPrtnerModel | SpecialCashDirectionMultiModel | SpecialDirectionMultiModel],
# def get_current_exchange_directions(request: Request,
#                                     query: SpecificDirectionsQuery = Depends()):
#     params = query.params()
#     if not params['city']:
#         exchange_direction_list = no_cash_exchange_directions2(request, params)
#     else:
#         exchange_direction_list = cash_exchange_directions2(request, params)
    
#     return exchange_direction_list


@common_router.get('/directions',
                   response_model=list[union_directions_response_models],
                   response_model_by_alias=False)
def get_current_exchange_directions(request: Request,
                                    query: SpecificDirectionsQuery = Depends()):
    params = query.params()
    if not params['city']:
        exchange_direction_list = test_no_cash_exchange_directions2(request, params)
    else:
        exchange_direction_list = test_cash_exchange_directions2(request, params)
    
    return exchange_direction_list


test_union_directions_response_models = Union[SpecialCashDirectionMultiPrtnerExchangeRatesWithLocationModel,
                                         SpecialCashDirectionMultiPrtnerWithLocationModel,
                                         SpecialCashDirectionMultiWithLocationModel,
                                         SpecialCashDirectionMultiPrtnerWithExchangeRatesWithAmlModel,
                                         SpecialCashDirectionMultiPrtnerModel,
                                         SpecialCashDirectionMultiWithAmlModel,
                                         SpecialDirectionMultiWithAmlModel]

# SpecialDirectionMultiWithAmlModel
@test_router.get('/directions',
                   response_model=list[test_union_directions_response_models],
                   response_model_by_alias=False)
def get_current_exchange_directions(request: Request,
                                    query: SpecificDirectionsQuery = Depends()):
    params = query.params()
    if not params['city']:
        exchange_direction_list = test_no_cash_exchange_directions3(request, params)
    else:
        exchange_direction_list = test_cash_exchange_directions3(request, params)
    
    return exchange_direction_list


@common_router.get('/popular_directions',
                   response_model=list[PopularDirectionSchema],
                   response_model_by_alias=False)
def get_popular_directions(exchange_marker: str,
                           limit: int = None):
    limit = 9 if limit is None else limit
    # print(len(connection.queries))
    if exchange_marker not in ('cash', 'no_cash'):
        raise HTTPException(status_code=400)

    if exchange_marker == 'no_cash':
        popular_direction = no_cash_models.PopularDirection
        additional_direction = no_cash_models.Direction
        popular_direction_name = 'Безналичные популярные направления'
    else:
        popular_direction = cash_models.PopularDirection
        additional_direction = cash_models.Direction
        popular_direction_name = 'Наличные популярные направления'

    directions = popular_direction.objects\
                                    .get(name=popular_direction_name)\
                                    .directions\
                                    .select_related('valute_from',
                                                    'valute_to')\
                                    .order_by('-popular_count')\
                                    .all()[:limit]
    
    res = []

    pk_set = set()

    for direction in directions:
        pk_set.add(direction.pk)

        valute_from = generate_valute_for_schema(direction.valute_from)
        valute_to = generate_valute_for_schema(direction.valute_to)
        res.append(PopularDirectionSchema(valute_from=valute_from.__dict__,
                                          valute_to=valute_to.__dict__))
        
    if (len(directions) - limit) < 0:
        more_directions = additional_direction.objects.select_related('valute_from',
                                                                     'valute_to')\
                                                        .filter(~Q(pk__in=pk_set))\
                                                        .order_by('-popular_count')\
                                                        .all()[:limit - len(directions)]
        for direction in more_directions:
            valute_from = generate_valute_for_schema(direction.valute_from)
            valute_to = generate_valute_for_schema(direction.valute_to)
            res.append(PopularDirectionSchema(valute_from=valute_from.__dict__,
                                              valute_to=valute_to.__dict__))

        # print(more_directions)
    # print(connection.queries)
    # print(len(connection.queries))

    return res



@common_router.get('/random_directions',
                   response_model=list[PopularDirectionSchema],
                   response_model_by_alias=False)
def get_random_directions(exchange_marker: str,
                          limit: int = None):
    print(len(connection.queries))
    limit = 9 if limit is None else limit

    if exchange_marker not in ('cash', 'no_cash'):
        raise HTTPException(status_code=400)

    if exchange_marker == 'no_cash':
        direction_model = no_cash_models.Direction
        exchange_direction_model = no_cash_models.ExchangeDirection
    else:
        direction_model = cash_models.Direction
        exchange_direction_model = cash_models.ExchangeDirection

    # direction_pks = list(direction_model.objects.values_list('pk',
    #                                                          flat=True))
    random_directions = exchange_direction_model.objects\
                                                .select_related('direction',
                                                                'exchange')\
                                                .filter(exchange__is_active=True,
                                                        is_active=True)\
                                                .order_by('direction_id')\
                                                .distinct('direction_id')\
                                                .values_list('direction_id',
                                                             flat=True)
    direction_pks = list(random_directions)
    shuffle(direction_pks)

    directions = direction_model.objects.select_related('valute_from',
                                                        'valute_to')\
                                        .filter(pk__in=direction_pks[:limit])

    for direction in directions:
        valute_from = generate_valute_for_schema(direction.valute_from)
        valute_to = generate_valute_for_schema(direction.valute_to)
        direction = PopularDirectionSchema(valute_from=valute_from.__dict__,
                                           valute_to=valute_to.__dict__)

    # print(connection.queries)
    print(len(connection.queries))
    return directions


@common_router.get('/similar_directions',
                   response_model=list[PopularDirectionSchema],
                   response_model_by_alias=False)
def get_similar_directions(exchange_marker: str,
                           valute_from: str,
                           valute_to: str,
                           city: str = None,
                           limit: int = None):
    # print(len(connection.queries))
    limit = 9 if limit is None else limit
    city = None if city is None else city.upper()
    valute_from, valute_to = [el.upper() for el in (valute_from, valute_to)]

    if exchange_marker not in ('cash', 'no_cash'):
        raise HTTPException(status_code=400)

    if exchange_marker == 'no_cash':
        direction_model = no_cash_models.ExchangeDirection
        similar_direction_filter = Q(direction__valute_from_id=valute_from,
                                     exchange__is_active=True,
                                     is_active=True) \
                                    | Q(direction__valute_to_id=valute_to,
                                        exchange__is_active=True,
                                        is_active=True)

        similar_direction_pks = direction_model.objects.select_related('direction',
                                                                    'exchange')\
                                                    .exclude(direction__valute_from_id=valute_from,
                                                             direction__valute_to_id=valute_to)\
                                                    .filter(similar_direction_filter)\
                                                    .values_list('direction__pk',
                                                                 flat=True)\
                                                    .all()[:limit]
        similar_directions = no_cash_models.Direction.objects\
                                                        .select_related('valute_from',
                                                                        'valute_to')\
                                                        .filter(pk__in=similar_direction_pks)

    else:
        if not city:
            raise HTTPException(status_code=400)
        # direction_model = cash_models.Direction
        direction_model = cash_models.ExchangeDirection
        partner_direction_model = partner_models.Direction

        similar_direction_filter = Q(direction__valute_from=valute_from,
                                     city__code_name=city,
                                     exchange__is_active=True,
                                     is_active=True)\
                                | Q(direction__valute_to=valute_to,
                                    city__code_name=city,
                                    exchange__is_active=True,
                                    is_active=True)
        similar_partner_direction_filter = Q(direction__valute_from=valute_from,
                                             city__city__code_name=city,
                                             city__exchange__is_active=True,
                                             is_active=True)\
                                         | Q(direction__valute_to=valute_to,
                                             city__city__code_name=city,
                                             city__exchange__is_active=True,
                                             is_active=True)
        similar_cash_direction_pks = direction_model.objects.select_related('direction',
                                                                            'exchange,'
                                                                            'city')\
                                                    .exclude(city__code_name=city,
                                                             direction__valute_from=valute_from,
                                                             direction__valute_to=valute_to)\
                                                    .filter(similar_direction_filter)\
                                                    .values_list('direction__pk',
                                                                 flat=True)\
                                                    .all()
        similar_partner_direction_pks = partner_direction_model.objects.select_related('direction',
                                                                                       'city',
                                                                                       'city__city',
                                                                                       'city__exchange')\
                                                    .exclude(city__city__code_name=city,
                                                             direction__valute_from=valute_from,
                                                             direction__valute_to=valute_to)\
                                                    .filter(similar_partner_direction_filter)\
                                                    .values_list('direction__pk',
                                                                 flat=True)\
                                                    .all()
        similar_direction_pks = similar_cash_direction_pks.union(similar_partner_direction_pks)
        similar_directions = cash_models.Direction.objects.select_related('valute_from',
                                                                          'valute_to')\
                                                            .filter(pk__in=similar_direction_pks)

    for direction in similar_directions:
        valute_from = generate_valute_for_schema(direction.valute_from)
        valute_to = generate_valute_for_schema(direction.valute_to)
        direction = PopularDirectionSchema(valute_from=valute_from.__dict__,
                                           valute_to=valute_to.__dict__)
    # print(len(connection.queries))
    return similar_directions



@common_router.get('/similar_cities_by_direction',
                   response_model=list[CityModel])
def get_similar_cities_by_direction(valute_from: str,
                                    valute_to: str,
                                    city: str):
    # print(len(connection.queries))
    valute_from, valute_to, city = [el.upper() for el in (valute_from, valute_to, city)]

    direction_model = cash_models.ExchangeDirection
    partner_direction_model = partner_models.Direction
    try:
        city_model = cash_models.City.objects.select_related('country')\
                                            .get(code_name=city)
    except ObjectDoesNotExist:
        raise HTTPException(status_code=400)
    else:
        similar_cities = direction_model.objects.select_related('direction',
                                                                'exchange',
                                                                'city')\
                                                    .exclude(city__code_name=city)\
                                                    .filter(direction__valute_from_id=valute_from,
                                                            direction__valute_to_id=valute_to,
                                                            is_active=True,
                                                            exchange__is_active=True)\
                                                    .values_list('city__pk',
                                                                 flat=True)\
                                                    .all()
        
        similar_partner_cities = partner_direction_model.objects.select_related('direction',
                                                                                'city',
                                                                                'city__city',
                                                                                'city__exchange')\
                                                                .exclude(city__city__code_name=city)\
                                                                .filter(direction__valute_from_id=valute_from,
                                                                        direction__valute_to_id=valute_to,
                                                                        is_active=True,
                                                                        city__exchange__is_active=True)\
                                                                .values_list('city__city__pk',
                                                                            flat=True)\
                                                                .all()
        
        similar_city_pks = similar_cities.union(similar_partner_cities)
        # print(similar_city_pks)

        exchange_count_filter = Q(cash_directions__direction__valute_from_id=valute_from,
                                cash_directions__direction__valute_to_id=valute_to,
                                cash_directions__exchange__is_active=True,
                                cash_directions__is_active=True)
        partner_exchange_count_filter = Q(partner_cities__partner_directions__direction__valute_from_id=valute_from,
                                        partner_cities__partner_directions__direction__valute_to_id=valute_to,
                                        partner_cities__partner_directions__is_active=True)

        #
        # cities = city_model.country.cities.annotate(
        #                             exchange_count=Count('cash_directions',
        #                                                  filter=exchange_count_filter))
        
        # partner_cities = city_model.partner_cities\
        #                             .annotate(partner_exchange_count=Count('partner_directions',
        #                                                            filter=partner_exchange_count_filter))\
        #                             .values('partner_exchange_count')
        # cities = cities.annotate(partner_exchange_count=Subquery(partner_cities,
        #                                                          output_field='partner_exchange_count'))\
        #                 .filter(pk__in=similar_city_pks)

        # partner_count_subquery = city_model.partner_cities.filter(
        #     city=OuterRef('pk')
        # ).annotate(
        #     partner_exchange_count=Count('partner_cities__partner_directions', filter=partner_exchange_count_filter)
        # ).values('partner_exchange_count')

        # cities = cities.annotate(partner_exchange_count=Subquery(partner_count_subquery))\
        #                 .filter(pk__in=similar_city_pks)
        #

        # cities = city_model.country.cities\
        #                             .annotate(partner_exchange_count=Count('partner_cities__partner_directions',
        #                                                            filter=partner_exchange_count_filter))\
        #                             .annotate(exchange_count=Count('cash_directions',
        #                                                            filter=exchange_count_filter))\
        #                             .filter(pk__in=similar_city_pks)\
        #                             .all()

        cities = city_model.country.cities\
                                    .annotate(exchange_count=Count('cash_directions',
                                                        filter=exchange_count_filter))\
                                    .filter(pk__in=similar_city_pks)\
                                    .all()
        
        partner_cities = list(city_model.country.cities\
                                    .annotate(partner_exchange_count=Count('partner_cities__partner_directions',
                                                                filter=partner_exchange_count_filter))\
                                    .filter(pk__in=similar_city_pks)\
                                    .values_list('partner_exchange_count',
                                                flat=True)\
                                    .all())
        
        for idx in range(len(cities)):
            cities[idx].exchange_count += partner_cities[idx]

        # q = partner_models.PartnerCity.objects.select_related('city')\
        #                                         .annotate(partner_directions_count=Count('partner_directions',
        #                                                         filter=partner_exchange_count_filter))\
        #                                         .get(city__code_name='SPB')

        # for city in cities:
        # print(q.__dict__)
        
            
            # print(city.code_name)
            # print(city.exchange_count)
            # print(city.partner_exchange_count)
            # print(city.exchange_count)
            # print(city.exq)
            # city.exchange_count = city.exchange_count + city.partner_exchange_count
            # print(city.partner_exchange_count)
        # print(cities)
        # print(len(connection.queries))
        # print(connection.queries)
        # 4 queries
        return cities
    


# @common_router.get('/exchange_list',
#                    response_model=list[CommonExchangeSchema],
#                    response_model_by_alias=False)
# def get_exchange_list():

#     review_counts = get_reviews_count_filters(marker='exchange')
    
#     exchanges = []

#     for exchange_marker, exchange_model in (('no_cash', no_cash_models.Exchange),
#                                             ('cash', cash_models.Exchange),
#                                             ('partner', partner_models.Exchange)):
#         exchange_query = exchange_model.objects\
#                                     .annotate(positive_review_count=review_counts['positive'])\
#                                     .annotate(neutral_review_count=review_counts['neutral'])\
#                                     .annotate(negative_review_count=review_counts['negative'])\
#                                     .annotate(exchange_marker=annotate_string_field(exchange_marker))\
#                                     .values('pk',
#                                             'name',
#                                             'reserve_amount',
#                                             'course_count',
#                                             'positive_review_count',
#                                             'neutral_review_count',
#                                             'negative_review_count',
#                                             'is_active',
#                                             'exchange_marker',
#                                             'partner_link')\
#                                     .all()
#         exchanges.append(exchange_query)

#     exchange_list = exchanges[0].union(exchanges[1])\
#                                 .union(exchanges[2])

#     for exchange in exchange_list:
#         exchange['reviews'] = ReviewCountSchema(positive=exchange['positive_review_count'],
#                                                 neutral=exchange['neutral_review_count'],
#                                                 negative=exchange['neutral_review_count'])

#     # print(len(connection.queries))
#     return sorted(exchange_list,
#                   key=lambda el: el.get('name'))


# новый exchange_marker 'both'
@common_router.get('/exchange_list',
                   response_model=list[CommonExchangeSchema],
                   response_model_by_alias=False)
def get_exchange_list():

    review_counts = get_reviews_count_filters(marker='exchange')
    
    queries = []

    for exchange_marker, exchange_model in (('no_cash', no_cash_models.Exchange),
                                            ('cash', cash_models.Exchange),
                                            ('partner', partner_models.Exchange)):
        exchange_query = exchange_model.objects\
                                    .annotate(positive_review_count=review_counts['positive'])\
                                    .annotate(neutral_review_count=review_counts['neutral'])\
                                    .annotate(negative_review_count=review_counts['negative'])\
                                    .annotate(exchange_marker=annotate_string_field(exchange_marker))\
                                    .values('pk',
                                            'name',
                                            'reserve_amount',
                                            'course_count',
                                            'positive_review_count',
                                            'neutral_review_count',
                                            'negative_review_count',
                                            'is_active',
                                            'exchange_marker',
                                            'partner_link')\
                                    .filter(is_active=True)\
                                    .all()
        queries.append(exchange_query)

    exchange_list = queries[0].union(queries[1])\
                                .union(queries[2])
    
    exchange_dict = {}
    exchange_name_set = set()

    for exchange in exchange_list:
        exchange_name = exchange.get('name').lower()   # lower() для name !

        if exchange_name in exchange_name_set:
            exchange_marker = exchange['exchange_marker']
            exchange_dict[exchange_name]['exchange_marker'] = 'both'

            if exchange_marker == 'no_cash':
                exchange_dict[exchange_name]['pk'] = exchange['pk'] # id no_cash обменников
        else:
            exchange_name_set.add(exchange_name)

            exchange['reviews'] = ReviewCountSchema(positive=exchange['positive_review_count'],
                                                    neutral=exchange['neutral_review_count'],
                                                    negative=exchange['neutral_review_count'])
            
            exchange_dict[exchange_name] = exchange

    # print(len(connection.queries))
    # return sorted(exchange_list,
                #   key=lambda el: el.get('name'))
    return sorted(exchange_dict.values(),
                  key=lambda el: el.get('name'))



# @common_router.get('/exchange_detail',
#                    response_model=DetailExchangeSchema,
#                    response_model_by_alias=False)
# def get_exchange_detail_info(exchange_id: int,
#                              exchange_marker: str):
#     review_counts = get_reviews_count_filters(marker='exchange')

#     exchange = get_exchange(exchange_id,
#                             exchange_marker,
#                             review_counts=review_counts)
#     exchange = exchange.first()

#     exchange.review_set = ReviewCountSchema(positive=exchange.positive_review_count,
#                                             neutral=exchange.neutral_review_count,
#                                             negative=exchange.negative_review_count)
#     exchange.icon = try_generate_icon_url(exchange)
    
#     if exchange.course_count is None or not exchange.course_count.isdigit():
#         exchange.course_count = None
#     else:
#         exchange.course_count = int(exchange.course_count)
    
#     return exchange


@common_router.get('/exchange_detail',
                   response_model=DetailExchangeSchema,
                   response_model_by_alias=False)
def get_exchange_detail_info(exchange_id: int,
                             exchange_marker: str):
    # is_both = None
    # if exchange_marker == 'both':
    #     exchange_marker = 'no_cash'
    #     is_both = True

    review_counts = get_reviews_count_filters(marker='exchange')

    exchange = get_exchange(exchange_id,
                            exchange_marker,
                            review_counts=review_counts)
    exchange = exchange.first()

    exchange.review_set = ReviewCountSchema(positive=exchange.positive_review_count,
                                            neutral=exchange.neutral_review_count,
                                            negative=exchange.negative_review_count)
    exchange.icon = try_generate_icon_url(exchange)
    
    if exchange.course_count is None or not exchange.course_count.isdigit():
        exchange.course_count = None
    else:
        exchange.course_count = int(exchange.course_count)
    
    return exchange


@common_router.get('/direction_pair_by_exchange',
                   response_model=list[DirectionSideBarSchema],
                   response_model_by_alias=False)
def get_all_directions_by_exchange(exchange_id: int,
                                   exchange_marker: str):
    # print(len(connection.queries))
    exchange = get_exchange(exchange_id,
                            exchange_marker)
    
    exchange_directions_queryset = get_exchange_directions(exchange,
                                                           exchange_marker)

    exchange_directions = exchange_directions_queryset\
                                    .select_related('direction',
                                                    'direction__valute_from',
                                                    'direction__valute_to')\
                                    .annotate(pair_count=Count('direction__exchange_directions',
                                                               filter=Q(direction__exchange_directions__direction_id=F('direction_id'),
                                                                        direction__exchange_directions__is_active=True,
                                                                        direction__exchange_directions__exchange__is_active=True)))\

    if exchange_marker == 'both':
        exchange_marker = 'no_cash'

    if exchange_marker != 'no_cash':
        prefetch_queryset = Prefetch('direction__partner_directions',
                                     partner_models.Direction.objects.filter(is_active=True,
                                                                             pk=F('pk')))
        exchange_directions = exchange_directions.prefetch_related(prefetch_queryset)

    check_direction_id_set = set()
    exchange_direction_list = []

    for exchange_direction in exchange_directions:
        if exchange_direction.direction_id not in check_direction_id_set:
            # exchange_direction_list.append(exchange_direction)
            check_direction_id_set.add(exchange_direction.direction_id)
        
            valute_from_icon = try_generate_icon_url(exchange_direction.direction.valute_from)
            exchange_direction.direction.valute_from.icon_url = valute_from_icon

            valute_to_icon = try_generate_icon_url(exchange_direction.direction.valute_to)
            exchange_direction.direction.valute_to.icon_url = valute_to_icon

            exchange_direction.valuteFrom = ValuteModel.model_construct(**exchange_direction.direction.valute_from.__dict__)
            exchange_direction.valuteTo = ValuteModel.model_construct(**exchange_direction.direction.valute_to.__dict__)
            exchange_direction.direction_type = 'no_cash'
            
            if exchange_marker != 'no_cash':
                exchange_direction.direction_type = 'cash'
                similar_partner_direction_count = len(exchange_direction.direction.partner_directions.all())
                exchange_direction.pair_count += similar_partner_direction_count

            if exchange_direction.pair_count > 0:
                exchange_direction_list.append(exchange_direction)

    # print(connection.queries)
    # print(len(connection.queries))
    return exchange_direction_list


# @test_router.get('/direction_pair_by_exchange',
#                    response_model=list[DirectionSideBarSchema],
#                    response_model_by_alias=False)
# def get_all_directions_by_exchange2(exchange_id: int,
#                                    exchange_marker: str):
#     # print(len(connection.queries))
#     exchange = get_exchange(exchange_id,
#                             exchange_marker)
    
#     exchange_directions_queryset = get_exchange_directions(exchange,
#                                                            exchange_marker)
    
#     if isinstance(exchange_directions_queryset, tuple):
#         for exchange_directions in exchange_directions_queryset:
#             exchange_directions = exchange_directions_queryset\
#                                             .select_related('direction',
#                                                             'direction__valute_from',
#                                                             'direction__valute_to')\
#                                             .annotate(pair_count=Count('direction__exchange_directions',
#                                                                     filter=Q(direction__exchange_directions__direction_id=F('direction_id'),
#                                                                                 direction__exchange_directions__is_active=True,
#                                                                                 direction__exchange_directions__exchange__is_active=True)))\
                                                                        


#     exchange_directions = exchange_directions_queryset\
#                                     .select_related('direction',
#                                                     'direction__valute_from',
#                                                     'direction__valute_to')\
#                                     .annotate(pair_count=Count('direction__exchange_directions',
#                                                                filter=Q(direction__exchange_directions__direction_id=F('direction_id'),
#                                                                         direction__exchange_directions__is_active=True,
#                                                                         direction__exchange_directions__exchange__is_active=True)))\
                                                                        
#     if exchange_marker != 'no_cash':
#         prefetch_queryset = Prefetch('direction__partner_directions',
#                                      partner_models.Direction.objects.filter(is_active=True,
#                                                                              pk=F('pk')))
#         exchange_directions = exchange_directions.prefetch_related(prefetch_queryset)

#     check_direction_id_set = set()
#     exchange_direction_list = []

#     for exchange_direction in exchange_directions:
#         if exchange_direction.direction_id not in check_direction_id_set:
#             # exchange_direction_list.append(exchange_direction)
#             check_direction_id_set.add(exchange_direction.direction_id)
        
#             valute_from_icon = try_generate_icon_url(exchange_direction.direction.valute_from)
#             exchange_direction.direction.valute_from.icon_url = valute_from_icon

#             valute_to_icon = try_generate_icon_url(exchange_direction.direction.valute_to)
#             exchange_direction.direction.valute_to.icon_url = valute_to_icon

#             exchange_direction.valuteFrom = ValuteModel.model_construct(**exchange_direction.direction.valute_from.__dict__)
#             exchange_direction.valuteTo = ValuteModel.model_construct(**exchange_direction.direction.valute_to.__dict__)
#             exchange_direction.direction_type = 'no_cash'
            
#             if exchange_marker != 'no_cash':
#                 exchange_direction.direction_type = 'cash'
#                 similar_partner_direction_count = len(exchange_direction.direction.partner_directions.all())
#                 exchange_direction.pair_count += similar_partner_direction_count

#             if exchange_direction.pair_count > 0:
#                 exchange_direction_list.append(exchange_direction)

#     # print(connection.queries)
#     # print(len(connection.queries))
#     return exchange_direction_list
    

@common_router.post('/feedback_form')
def add_feedback_form(feedback: FeedbackFormSchema):
    try:
        feedback_form = FeedbackForm.objects.create(**feedback.model_dump())
    except Exception as ex:
        print(ex)
        raise HTTPException(status_code=400)
    else:
        async_to_sync(pust_to_send_bot)(user_id=1,
                                        order_id=feedback_form.pk,
                                        marker='feedback_form')
        return {'status': 'success',
                'details': 'feedback added'}


# Эндпоинт для получения актуального курса обмена
# для выбранного направления
@common_router.get('/actual_course')
def get_actual_course_for_direction(valute_from: str, valute_to: str):
    valute_from, valute_to = valute_from.upper(), valute_to.upper()
    
    direction = cash_models.Direction.objects\
                            .filter(display_name=f'{valute_from} -> {valute_to}')\
                            .first()
    
    if not direction:
        direction = no_cash_models.Direction.objects\
                                    .filter(valute_from_id=valute_from,
                                            valute_to_id=valute_to).first()
        
    if direction and direction.actual_course is not None:
        return direction.actual_course
    else:
        raise HTTPException(status_code=404)
    

@test_router.get('/actual_course')
def get_actual_course_for_direction(valute_from: str, valute_to: str):
    valute_from, valute_to = valute_from.upper(), valute_to.upper()
    
    direction = cash_models.Direction.objects\
                            .filter(display_name=f'{valute_from} -> {valute_to}')\
                            .first()
    
    if not direction:
        direction = no_cash_models.Direction.objects\
                                    .filter(valute_from_id=valute_from,
                                            valute_to_id=valute_to).first()
        
    # if direction and direction.actual_course is not None:
    #     return direction.actual_course
    # else:
    if not direction:
        raise HTTPException(status_code=404)
    
    return generate_actual_course(direction) 


@common_router.get('/top_exchanges',
                   response_model=list[TopExchangeSchema],
                   response_model_by_alias=False)
def get_top_exchanges():
    limit = 10
    # print(len(connection.queries))
    review_counts = get_reviews_count_filters(marker='exchange')

    no_cash_exchanges = generate_top_exchanges_query_by_model('no_cash',
                                           review_counts=review_counts)

    cash_exchanges = generate_top_exchanges_query_by_model('cash',
                                        review_counts=review_counts)

    partner_exchanges = generate_top_exchanges_query_by_model('partner',
                                           review_counts=review_counts)
    
    top_exchanges = no_cash_exchanges.union(cash_exchanges,
                                            partner_exchanges)
                                                
    for top_exchange in top_exchanges:
        top_exchange['reviews'] = ReviewCountSchema(positive=top_exchange['positive_review_count'],
                                                    neutral=top_exchange['neutral_review_count'],
                                                    negative=top_exchange['negative_review_count'])
        top_exchange['icon'] = generate_image_icon2(top_exchange['icon_url'])


    return sorted(top_exchanges,
                  key=lambda el: el.get('link_count'),
                  reverse=True)[:limit]


@common_router.get('/top_coins',
                   response_model=list[TopCoinSchema],
                   response_model_by_alias=False)
def get_top_coins():
    usd = 'CASHUSD'
    limit = 10
    top_coins = cash_models.Direction.objects.select_related('valute_from',
                                                             'valute_to')\
                                            .filter(valute_to_id=usd,
                                                    actual_course__isnull=False)\
                                            .order_by('-popular_count')[:limit]
    coin_list = []

    for direction in top_coins:
        coin = direction.valute_from
        coin = generate_coin_for_schema(direction,
                                        coin)
        coin_list.append(coin)

    return coin_list


# Эндпоинт для получения списка отзывов
# для определённого обменника
@review_router.get('/reviews_by_exchange',
                   response_model=ReviewsByExchangeSchema)
def get_reviews_by_exchange(exchange_id: int,
                            exchange_marker: str,
                            page: int,
                            element_on_page: int = None,
                            grade_filter: int = None):
    if exchange_marker == 'both':     # !
        exchange_marker = 'no_cash'

    check_exchage_marker(exchange_marker)

    if page < 1:
        raise HTTPException(status_code=400,
                            detail='Параметр "page" должен быть положительным числом')
    
    if element_on_page is not None:
        if element_on_page < 1:
            raise HTTPException(status_code=400,
                                detail='Параметр "element_on_page" должен быть положительным числом')
    
    match exchange_marker:
        case 'no_cash':
            review_model = no_cash_models.Review
        case 'cash':
            review_model = cash_models.Review
        case 'partner':
            review_model = partner_models.Review

    reviews = review_model.objects.select_related('guest')\
                                    .annotate(comment_count=Count('admin_comments'))\
                                    .filter(exchange_id=exchange_id,
                                            moderation=True)
                                    # .order_by('-time_create')
    if grade_filter is not None:
        reviews = reviews.filter(grade=str(grade_filter))

    reviews = reviews.order_by('-time_create').all()
    
    pages = 1 if element_on_page is None else ceil(len(reviews) / element_on_page)

    # if element_on_page:
    #     pages = ceil(len(reviews) / element_on_page)


    # if element_on_page:
    #     pages = len(reviews) // element_on_page

    #     if len(reviews) % element_on_page != 0:
    #         pages += 1
    

    # reviews = reviews.all() if grade_filter is None\
    #              else reviews.filter(grade=str(grade_filter)).all()

    # reviews = reviews.all()


    if element_on_page:
        offset = (page - 1) * element_on_page
        limit = offset + element_on_page
        reviews = reviews[offset:limit]

    review_list = []
    for review in reviews:
        date, time = review.time_create.astimezone().strftime('%d.%m.%Y %H:%M').split()
        review.username = review.username if review.guest is None else review.guest.username
        review.review_date = date
        review.review_time = time
        review_list.append(ReviewViewSchema(**review.__dict__))

    return ReviewsByExchangeSchema(page=page,
                                   pages=pages,
                                   exchange_id=exchange_id,
                                   exchange_marker=exchange_marker,
                                   element_on_page=len(review_list),
                                   content=review_list)


# Эндпоинт для добавления нового отзыва
# для определённого обменника
@review_router.post('/add_review_by_exchange')
def add_review_by_exchange(review: AddReviewSchema):
    check_exchage_marker(review.exchange_marker)
    
    check_perms_for_adding_review(exchange_id=review.exchange_id,
                                  exchange_marker=review.exchange_marker,
                                  tg_id=review.tg_id)

    if review.grade != -1 and review.transaction_id is not None:
        raise HTTPException(status_code=423,
                            detail='Неотрицательный отзыв не требует номера транзакции')
    
    
    match review.exchange_marker:
        case 'no_cash':
            review_model = no_cash_models.Review
        case 'cash':
            review_model = cash_models.Review
        case 'partner':
            review_model = partner_models.Review

    new_review = {
        'exchange_id': review.exchange_id,
        'guest_id': review.tg_id,
        'grade': review.grade,
        'text': review.text,
    }

    if review.transaction_id:
        new_review.update({'transaction_id': review.transaction_id})

    try:
        # review_model.objects.create(
        #     exchange_id=review.exchange_id,
        #     guest_id=review.tg_id,
        #     grade=review.grade,
        #     text=review.text
        #     )
        review_model.objects.create(**new_review)
    except Exception:
        raise HTTPException(status_code=400,
                            detail='Переданы некорректные данные')
    else:
        return {'status': 'success'}


# Эндпоинт для проверки пользователя,
# может ли он добавить новый отзыв
# для опеределённого обменника (один в день)
@review_router.get('/check_user_review_permission')
def check_user_review_permission(exchange_id: int,
                                 exchange_marker: str,
                                 tg_id: int):
    return check_perms_for_adding_review(exchange_id,
                                         exchange_marker,
                                         tg_id)
    # time_delta = timedelta(days=1)

    # check_exchage_marker(exchange_marker)

    # match exchange_marker:
    #     case 'no_cash':
    #         review_model = no_cash_models.Review
    #     case 'cash':
    #         review_model = cash_models.Review
    #     case 'partner':
    #         review_model = partner_models.Review

    # check_time = datetime.now() - time_delta

    # review = review_model.objects.select_related('guest')\
    #                                 .filter(exchange_id=exchange_id,
    #                                         guest_id=tg_id,
    #                                         time_create__gt=check_time)\
    #                                 .first()

    # if review:
    #     next_time_review = review.time_create.astimezone() + time_delta
    #     review_exception_json(status_code=423,
    #                           param=next_time_review.strftime('%d.%m.%Y %H:%M'))

    
    # return {'status': 'success'}


@review_router.get('/get_comments_by_review',
                   response_model=list[CommentSchema],
                   response_model_exclude_none=True)
def get_comments_by_review(exchange_id: int,
                           exchange_marker: str,
                           review_id: int):
    check_exchage_marker(exchange_marker)
    # print(len(connection.queries))
    match exchange_marker:
        case 'no_cash':
            # review_model = no_cash_models.Review
            comment_model = no_cash_models.AdminComment
        case 'cash':
            # review_model = cash_models.Review
            comment_model = cash_models.AdminComment
        case 'partner':
            # review_model = partner_models.Review
            comment_model = partner_models.AdminComment

    # review = review_model.objects.filter(exchange_id=exchange_id,
    #                                      pk=review_id)
    comments = comment_model.objects.select_related('review',
                                                    'review__exchange')\
                                    .filter(review_id=review_id,
                                            review__exchange_id=exchange_id)\
                                    .order_by('time_create').all()

    if not comments:
        raise HTTPException(status_code=404)
    
    #
    # comments = review.first().admin_comments\
    #                             .order_by('time_create').all()

    for comment in comments:
        if isinstance(comment, BaseAdminComment):
            comment.role = CommentRoleEnum.admin
        date, time = comment.time_create.astimezone().strftime('%d.%m.%Y %H:%M').split()
        comment.comment_date = date
        comment.comment_time = time
    #
    # print(len(connection.queries))
    return comments


# @common_router.get('/change_interval')
# def change_interval_info_exchange_task(interval: int,
#                                        period: str):
#     from django_celery_beat.models import IntervalSchedule, PeriodicTask

#     period_dict = {
#         'second': IntervalSchedule.SECONDS,
#         'minute': IntervalSchedule.MINUTES,
#         'day': IntervalSchedule.DAYS,
#     }

#     period = period_dict[period.lower()]

#     task = PeriodicTask.objects.get(name='parse_actual_exchanges_info_task')

#     interval = get_or_create_schedule(interval, period)

#     task.interval = interval

#     task.save()
    
###
exchange_link_count_dict = {
    'cash': cash_models.ExchangeLinkCount,
    'no_cash': no_cash_models.ExchangeLinkCount,
    'partner': partner_models.ExchangeLinkCount,
}
###

@common_router.post('/increase_link_count')
def increase_link_count(data: ExchangeLinkCountSchema):
    exchange_link_count: Union[cash_models.ExchangeLinkCount,
                               no_cash_models.ExchangeLinkCount,
                               partner_models.ExchangeLinkCount] = exchange_link_count_dict.get(data.exchange_marker)

    if not exchange_link_count:
        raise HTTPException(status_code=400,
                            detail='invalid marker')

    check_user = Guest.objects.filter(tg_id=data.user_id)

    if not check_user.exists():
        raise HTTPException(status_code=400)

    exchange_link_count_queryset = exchange_link_count.objects\
                                                .filter(exchange_id=data.exchange_id,
                                                        exchange_marker=data.exchange_marker,
                                                        exchange_direction_id=data.exchange_direction_id,
                                                        user_id=data.user_id)
    if not exchange_link_count_queryset.exists():
        try:
            exchange_link_count_queryset = exchange_link_count.objects.create(user_id=data.user_id,
                                                                            exchange_id=data.exchange_id,
                                                                            exchange_marker=data.exchange_marker,
                                                                            exchange_direction_id=data.exchange_direction_id,
                                                                            count=1)
        except IntegrityError:
            raise HTTPException(status_code=400,
                                detail='Constraint error. This row already exists')
            # return {'status': 'error',
            #         'details': 'Constraint error. This row already exists'}
    else:
        exchange_link_count_queryset.update(count=F('count') + 1)

    return {'status': 'success'}



@common_router.get('/sitemap_directions',
                   response_model=list[SiteMapDirectonSchema])
def get_directions_for_sitemap():
    # print(len(connection.queries))
    #valute_from
    #valute_to
    #city | None
    #exchange_marker
    no_cash_directions = no_cash_models.ExchangeDirection.objects\
                                .select_related('exchange',
                                                'direction')\
                                .annotate(exchange_marker=annotate_string_field('no_cash'))\
                                .values_list('direction__valute_from',
                                             'direction__valute_to',
                                             'exchange_marker',
                                             'exchange__name')\
                                .order_by('direction_id')\
                                .distinct('direction_id')
    
    # print(no_cash_directions)

    cash_directions = cash_models.ExchangeDirection.objects\
                                .select_related('exchange',
                                                'direction',
                                                'city')\
                                .annotate(exchange_marker=annotate_string_field('cash'))\
                                .values_list('direction__valute_from',
                                             'direction__valute_to',
                                             'exchange_marker',
                                             'city__code_name')\
                                .order_by('direction_id')\
                                .distinct('direction_id',
                                          'city_id')
    # print(cash_directions)

    partner_directions = partner_models.Direction.objects\
                                .select_related('direction',
                                                'city',
                                                'city__city',
                                                'city__exchange')\
                                .annotate(exchange_marker=annotate_string_field('cash'))\
                                .values_list('direction__valute_from',
                                             'direction__valute_to',
                                             'exchange_marker',
                                             'city__city__code_name')\
                                .order_by('direction_id')\
                                .distinct('direction_id',
                                          'city__city_id')
    
    # print(partner_directions)

    directions = no_cash_directions.union(cash_directions,
                                          partner_directions)
    
    # print(len(list(directions)) == len(set(directions)))

    result = []

    for direction in directions:
        valute_from, valute_to, exchange_marker, city = direction

        #
        if exchange_marker == 'no_cash':
            city = None
        #

        result.append(
            {
                'valute_from': valute_from,
                'valute_to': valute_to,
                'exchange_marker': exchange_marker,
                'city': city,
            }
        )

    # print(connection.queries)
    return result



# @common_router.get('/test_logentry')
# def test_log_entry():
#     w = LogEntry.objects.all()[:5]
#     for q in w:
#         print(q)
#         print(q.__dict__)
#         print(q.action_time)
    # print(w.content_type.get_object_for_this_type(pk=w.object_id))
    # print(w.objects)