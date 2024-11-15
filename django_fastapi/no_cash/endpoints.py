from fastapi import APIRouter, Request

from django.db.models import Count, Q
from django.db import connection

from general_models.utils.http_exc import http_exception_json
from general_models.utils.endpoints import (get_exchange_direction_list,
                                            get_valute_json,
                                            get_valute_json_2,
                                            increase_popular_count_direction,
                                            positive_review_count_filter,
                                            neutral_review_count_filter,
                                            negative_review_count_filter,
                                            get_reviews_count_filters)

from cash.endpoints import cash_exchange_directions_with_location, cash_exchange_directions_with_location2

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
        return cash_exchange_directions_with_location2(request,
                                                      params)

    increase_popular_count_direction(valute_from=valute_from,
                                     valute_to=valute_to)
    
    return get_exchange_direction_list(queries,
                                       valute_from,
                                       valute_to)