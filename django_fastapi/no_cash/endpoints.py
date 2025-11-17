from fastapi import APIRouter, Request

from django.db import connection

from general_models.utils.http_exc import http_exception_json
from general_models.utils.endpoints import (new_get_exchange_direction_list_with_aml,
                                            test_new_get_exchange_direction_list_with_aml,
                                            get_valute_json,
                                            get_valute_json_2, get_valute_json_3,
                                            new_increase_popular_count_direction,
                                            new_check_valute_on_cash)
from general_models.utils.base import annotate_string_field

from cash.endpoints import (cash_exchange_directions_with_location,
                            test_cash_exchange_directions_with_location)

from partners.utils.endpoints import get_no_cash_partner_directions
from partners.models import NonCashDirection, NewNonCashDirection

from .models import ExchangeDirection, NewExchangeDirection


no_cash_router = APIRouter(prefix='/no_cash',
                           tags=['Безналичные'])



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
        
    if not queries:
        http_exception_json(status_code=404, param=request.url)

    return get_valute_json_3(queries)


def no_cash_valutes(request: Request,
                    params: dict):
    if not params['base']:
        http_exception_json(status_code=400, param='base')

    base = params['base']

    queries = NewExchangeDirection.objects\
                                .select_related('exchange',
                                                'direction')\
                                .filter(is_active=True,
                                        exchange__is_active=True)

    partner_queries = NewNonCashDirection.objects\
                                        .select_related('exchange',
                                                        'direction')\
                                        .filter(is_active=True,
                                                exchange__is_active=True,
                                                exchange__isnull=False)

    if base == 'ALL':
        queries = queries.values_list('direction__valute_from_id')
        partner_queries = partner_queries\
                                .values_list('direction__valute_from_id')
    else:
        queries = queries.filter(direction__valute_from=base)\
                                    .values_list('direction__valute_to_id')
        partner_queries = partner_queries.filter(direction__valute_from__code_name=base)\
                                        .values_list('direction__valute_to_id')

    queries = queries.union(partner_queries)
        
    if not queries:
        http_exception_json(status_code=404, param=request.url)

    return get_valute_json(queries)


def no_cash_exchange_directions(request: Request,
                                params: dict):
    # print(len(connection.queries))
    params.pop('city')
    for param in params:
        if not params[param]:
            http_exception_json(status_code=400, param=param)

    valute_from, valute_to = (params[key] for key in params)

    if new_check_valute_on_cash(valute_from,
                                valute_to):
        # осталась проблема с партнерскими направлениями на уровне стран
        return cash_exchange_directions_with_location(request,
                                                      params)

    queries = NewExchangeDirection.objects\
                                .select_related('exchange',
                                                'direction',
                                                'direction__valute_from',
                                                'direction__valute_to')\
                                .annotate(direction_marker=annotate_string_field('auto_noncash'))\
                                .filter(direction__valute_from=valute_from,
                                        direction__valute_to=valute_to,
                                        is_active=True,
                                        exchange__is_active=True)\

    partner_directions = get_no_cash_partner_directions(valute_from,
                                                        valute_to)
    
    queries = sorted(list(queries) + list(partner_directions),
                     key=lambda query: (-query.exchange.is_vip,
                                        -query.out_count,
                                        query.in_count))

    
    if not queries:
        http_exception_json(status_code=404, param=request.url)

    # new_increase_popular_count_direction(valute_from=valute_from,
    #                                      valute_to=valute_to)
    
    return new_get_exchange_direction_list_with_aml(queries,
                                                valute_from,
                                                valute_to,
                                                is_no_cash=True)


def test_no_cash_exchange_directions(request: Request,
                                     params: dict):
    # print(len(connection.queries))
    params.pop('city')
    for param in params:
        if not params[param]:
            http_exception_json(status_code=400, param=param)

    valute_from, valute_to = (params[key] for key in params)

    if new_check_valute_on_cash(valute_from,
                                valute_to):
        # осталась проблема с партнерскими направлениями на уровне стран
        return test_cash_exchange_directions_with_location(request,
                                                      params)

    queries = NewExchangeDirection.objects\
                                .select_related('exchange',
                                                'direction',
                                                'direction__valute_from',
                                                'direction__valute_to')\
                                .annotate(direction_marker=annotate_string_field('auto_noncash'))\
                                .filter(direction__valute_from=valute_from,
                                        direction__valute_to=valute_to,
                                        is_active=True,
                                        exchange__is_active=True)\

    partner_directions = get_no_cash_partner_directions(valute_from,
                                                        valute_to)
    
    queries = sorted(list(queries) + list(partner_directions),
                     key=lambda query: (-query.exchange.is_vip,
                                        -query.out_count,
                                        query.in_count))

    
    if not queries:
        http_exception_json(status_code=404, param=request.url)

    new_increase_popular_count_direction(valute_from=valute_from,
                                         valute_to=valute_to)
    
    return test_new_get_exchange_direction_list_with_aml(queries,
                                                valute_from,
                                                valute_to,
                                                is_no_cash=True,
                                                new_version=True)