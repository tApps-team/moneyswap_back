from fastapi import APIRouter, Request

from django.db.models import Count, Q, Prefetch
from django.db import connection

from general_models.utils.http_exc import http_exception_json
from general_models.utils.endpoints import (get_exchange_direction_list, get_exchange_direction_list_with_aml,
                                            get_valute_json,
                                            get_valute_json_2, get_valute_json_3,
                                            increase_popular_count_direction, new_get_reviews_count_filters,
                                            positive_review_count_filter,
                                            neutral_review_count_filter,
                                            negative_review_count_filter,
                                            get_reviews_count_filters,
                                            check_valute_on_cash)

from cash.endpoints import cash_exchange_directions_with_location, cash_exchange_directions_with_location2, test_cash_exchange_directions_with_location2

from partners.utils.endpoints import get_no_cash_partner_directions, new_get_no_cash_partner_directions
from partners.models import NonCashDirection, NonCashDirectionRate

from .models import ExchangeDirection


no_cash_router = APIRouter(prefix='/no_cash',
                           tags=['Безналичные'])


# Вспомогательный эндпоинт для получения безналичных валют
def no_cash_valutes(request: Request,
                    params: dict):
    if not params['base']:
        http_exception_json(status_code=400, param='base')

    base = params['base']

    queries = ExchangeDirection.objects\
                                .select_related('exchange',
                                                'direction',
                                                'direction__valute_from',
                                                'direction__valute_to')\
                                .filter(is_active=True,
                                        exchange__is_active=True)

    if base == 'ALL':
        # queries = queries.values_list('direction__valute_from').all()
        queries = queries.order_by('direction__valute_from_id')\
                            .distinct('direction__valute_from_id')\
                            .values_list('direction__valute_from_id', flat=True)
    else:
        # queries = queries.filter(direction__valute_from=base)\
        #                     .values_list('direction__valute_to').all()
        queries = queries.filter(direction__valute_from_id=base)\
                            .order_by('direction__valute_to_id')\
                            .distinct('direction__valute_to_id')\
                            .values_list('direction__valute_to_id', flat=True)

        
    if not queries:
        http_exception_json(status_code=404, param=request.url)

    return get_valute_json(queries)


#
# Вспомогательный эндпоинт для получения безналичных валют
def no_cash_valutes_2(request: Request,
                    params: dict):
    if not params['base']:
        http_exception_json(status_code=400, param='base')

    base = params['base']

    queries = ExchangeDirection.objects\
                                .select_related('exchange',
                                                'direction',
                                                'direction__valute_from',
                                                'direction__valute_to')\
                                .filter(is_active=True,
                                        exchange__is_active=True)

    if base == 'ALL':
        # queries = queries.values_list('direction__valute_from').all()
        queries = queries.order_by('direction__valute_from_id')\
                            .distinct('direction__valute_from_id')\
                            .values_list('direction__valute_from_id', flat=True)
    else:
        # queries = queries.filter(direction__valute_from=base)\
        #                     .values_list('direction__valute_to').all()
        queries = queries.filter(direction__valute_from_id=base)\
                            .order_by('direction__valute_to_id')\
                            .distinct('direction__valute_to_id')\
                            .values_list('direction__valute_to_id', flat=True)

        
    if not queries:
        http_exception_json(status_code=404, param=request.url)

    return get_valute_json_2(queries)
#


def no_cash_valutes_3(request: Request,
                    params: dict):
    if not params['base']:
        http_exception_json(status_code=400, param='base')

    base = params['base']

    queries = ExchangeDirection.objects\
                                .select_related('exchange',
                                                'direction',
                                                'direction__valute_from',
                                                'direction__valute_to')\
                                .filter(is_active=True,
                                        exchange__is_active=True)

    partner_queries = NonCashDirection.objects\
                                        .select_related('direction',
                                                        'direction__valute_from',
                                                        'direction__valute_to',
                                                        'exchange')\
                                        .filter(is_active=True,
                                                exchange__is_active=True,
                                                exchange__isnull=False)

    if base == 'ALL':
        queries = queries.values_list('direction__valute_from').all()
        partner_queries = partner_queries\
                                .values_list('direction__valute_from__code_name').all()
    else:
        queries = queries.filter(direction__valute_from=base)\
                                    .values_list('direction__valute_to').all()
        partner_queries = partner_queries.filter(direction__valute_from__code_name=base)\
                                        .values_list('direction__valute_to__code_name').all()

    queries = queries.union(partner_queries)

    # if base == 'ALL':
    #     # queries = queries.values_list('direction__valute_from').all()
    #     queries = queries.order_by('direction__valute_from_id')\
    #                         .distinct('direction__valute_from_id')\
    #                         .values_list('direction__valute_from_id', flat=True)
    # else:
    #     # queries = queries.filter(direction__valute_from=base)\
    #     #                     .values_list('direction__valute_to').all()
    #     queries = queries.filter(direction__valute_from_id=base)\
    #                         .order_by('direction__valute_to_id')\
    #                         .distinct('direction__valute_to_id')\
    #                         .values_list('direction__valute_to_id', flat=True)

        
    if not queries:
        http_exception_json(status_code=404, param=request.url)

    return get_valute_json_3(queries)


# Вспомогательный эндпоинт для получения безналичных готовых направлений
def no_cash_exchange_directions(request: Request,
                                params: dict):
    # print(len(connection.queries))
    params.pop('city')
    for param in params:
        if not params[param]:
            http_exception_json(status_code=400, param=param)

    valute_from, valute_to = (params[key] for key in params)

    review_counts = get_reviews_count_filters('exchange_direction')

    queries = ExchangeDirection.objects\
                                .select_related('exchange',
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
                                .order_by('-exchange__is_vip',
                                          '-out_count',
                                          'in_count').all()
    
    if not queries:
        return cash_exchange_directions_with_location(request,
                                                      params)

    increase_popular_count_direction(valute_from=valute_from,
                                     valute_to=valute_to)
    
    return get_exchange_direction_list(queries,
                                       valute_from,
                                       valute_to)


# Вспомогательный эндпоинт для получения безналичных готовых направлений
def no_cash_exchange_directions2(request: Request,
                                params: dict):
    # print(len(connection.queries))
    params.pop('city')
    for param in params:
        if not params[param]:
            http_exception_json(status_code=400, param=param)

    valute_from, valute_to = (params[key] for key in params)

    if check_valute_on_cash(valute_from,
                            valute_to):
        return cash_exchange_directions_with_location2(request,
                                                      params)

    review_counts = get_reviews_count_filters('exchange_direction')

    queries = ExchangeDirection.objects\
                                .select_related('exchange',
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
                                .order_by('-exchange__is_vip',
                                          '-out_count',
                                          'in_count').all()
    
    if not queries:
        http_exception_json(status_code=404, param=request.url)
        # return cash_exchange_directions_with_location2(request,
        #                                               params)

    increase_popular_count_direction(valute_from=valute_from,
                                     valute_to=valute_to)
    
    return get_exchange_direction_list(queries,
                                       valute_from,
                                       valute_to)


def test_no_cash_exchange_directions2(request: Request,
                                params: dict):
    # print(len(connection.queries))
    params.pop('city')
    for param in params:
        if not params[param]:
            http_exception_json(status_code=400, param=param)

    valute_from, valute_to = (params[key] for key in params)

    if check_valute_on_cash(valute_from,
                            valute_to):
        return test_cash_exchange_directions_with_location2(request,
                                                            params)

    review_counts = get_reviews_count_filters('exchange_direction')

    queries = ExchangeDirection.objects\
                                .select_related('exchange',
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
                                .order_by('-exchange__is_vip',
                                          '-out_count',
                                          'in_count').all()
    
    if not queries:
        http_exception_json(status_code=404, param=request.url)
        # return cash_exchange_directions_with_location2(request,
        #                                               params)

    increase_popular_count_direction(valute_from=valute_from,
                                     valute_to=valute_to)
    
    return get_exchange_direction_list(queries,
                                       valute_from,
                                       valute_to)


def test_no_cash_exchange_directions3(request: Request,
                                      params: dict):
    # print(len(connection.queries))
    params.pop('city')
    for param in params:
        if not params[param]:
            http_exception_json(status_code=400, param=param)

    valute_from, valute_to = (params[key] for key in params)

    if check_valute_on_cash(valute_from,
                            valute_to):
        return test_cash_exchange_directions_with_location2(request,
                                                            params)

    review_counts = get_reviews_count_filters('exchange_direction')

    queries = ExchangeDirection.objects\
                                .select_related('exchange',
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
                                .order_by('-exchange__is_vip',
                                          '-out_count',
                                          'in_count').all()
    
    if not queries:
        http_exception_json(status_code=404, param=request.url)
        # return cash_exchange_directions_with_location2(request,
        #                                               params)

    increase_popular_count_direction(valute_from=valute_from,
                                     valute_to=valute_to)
    
    return get_exchange_direction_list_with_aml(queries,
                                                valute_from,
                                                valute_to)


def test_no_cash_exchange_directions4(request: Request,
                                      params: dict):
    # print(len(connection.queries))
    params.pop('city')
    for param in params:
        if not params[param]:
            http_exception_json(status_code=400, param=param)

    valute_from, valute_to = (params[key] for key in params)

    if check_valute_on_cash(valute_from,
                            valute_to):
        return test_cash_exchange_directions_with_location2(request,
                                                            params)

    review_counts = new_get_reviews_count_filters('exchange_direction')

    queries = ExchangeDirection.objects\
                                .select_related('exchange',
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
                                .order_by('-exchange__is_vip',
                                          '-out_count',
                                          'in_count').all()
    
    # partner_prefetch = Prefetch('direction_rates',
    #                             queryset=NonCashDirectionRate.objects.order_by('min_rate_limit'))
    
    # partner_directions = NonCashDirection.objects.select_related('exchange',
    #                                                              'direction',
    #                                                              'direction__valute_from',
    #                                                              'direction__valute_to')\
    #                                                 .prefetch_related(partner_prefetch)\
    #                                                 .filter(direction__valute_from=valute_from,
    #                                                         direction__valute_to=valute_to,
    #                                                         is_active=True,
    #                                                         exchange__is_active=True)

    partner_directions = new_get_no_cash_partner_directions(valute_from,
                                                        valute_to)
    
    # print(partner_directions)
    
    # queries = sorted(list(queries) + list(partner_directions),
    #                  key=lambda query: (-query.exchange.is_vip,
    #                                     -query.out_count,
    #                                     query.in_count))
    
    queries = sorted(list(queries) + list(partner_directions),
                     key=lambda query: (-query.exchange.is_vip,))

    
    if not queries:
        http_exception_json(status_code=404, param=request.url)
        # return cash_exchange_directions_with_location2(request,
        #                                               params)

    increase_popular_count_direction(valute_from=valute_from,
                                     valute_to=valute_to)
    
    return get_exchange_direction_list_with_aml(queries,
                                                valute_from,
                                                valute_to,
                                                is_no_cash=True)