from fastapi import APIRouter, Request

from django.core.cache import cache

from django.db.models import Count, Q, F, Subquery
from django.db import connection

from general_models.models import Valute
from general_models.utils.http_exc import http_exception_json
from general_models.utils.endpoints import (get_exchange_direction_list,
                                            get_valute_json,
                                            new_get_valute_json,
                                            increase_popular_count_direction,
                                            positive_review_count_filter,
                                            neutral_review_count_filter,
                                            negative_review_count_filter)
from .utils.cache import (get_or_set_all_no_cash_valutes_cache,
                          get_or_set_no_cash_valutes_by_valute_cache)

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
                                .select_related('exchange'
                                                'valute_from',
                                                'valute_to')\
                                .filter(is_active=True,
                                        exchange__is_active=True)

    if base == 'ALL':
        # queries = queries.values(code_name=F('direction__valute_from'),
        #                          name=F('direction__valute_from__name'),
        #                          en_name=F('direction__valute_from__en_name'),
        #                          type_valute=F('direction__valute_from__type_valute'),
        #                          icon_url=F('direction__valute_from__icon_url'))\
        #                     .order_by('direction__valute_from')\
        #                     .distinct().all()
        queries = queries.order_by('valute_from_id')\
                            .distinct('valute_from_id')\
                            .values_list('valute_from_id', flat=True)
        # print(queries)
        # queries = get_or_set_all_no_cash_valutes_cache(queries)
    else:
        # queries = queries.filter(direction__valute_from=base)\
        #                     .values_list('direction__valute_to').all()
        queries = queries.filter(valute_from_id=base)\
                            .order_by('valute_to_id')\
                            .distinct('valute_to_id')\
                            .values_list('valute_to_id', flat=True)
        # queries = queries.filter(direction__valute_from=base)\
        #                     .values(code_name=F('direction__valute_to'),
        #                             name=F('direction__valute_to__name'),
        #                             en_name=F('direction__valute_to__en_name'),
        #                             type_valute=F('direction__valute_to__type_valute'),
        #                             icon_url=F('direction__valute_to__icon_url'))\
        #                     .order_by('direction__valute_to')\
        #                     .distinct().all()
        # queries = queries.filter(direction__valute_from=base)\
        #                     .values_list('direction__valute_to').all()

        # queries = get_or_set_no_cash_valutes_by_valute_cache(base,
        #                                                      queries)

    # print(queries)
    # for q in queries:
    #     print(q)
        # print(type(q.direction.valute_from))
        # print(q[0].name)
    
    # print(connection.queries)
    # print(len(connection.queries))
    
    if not queries:
        http_exception_json(status_code=404, param=request.url)

    return get_valute_json(queries)


# Вспомогательный эндпоинт для получения безналичных готовых направлений
def no_cash_exchange_directions(request: Request,
                                params: dict):
    # print(len(connection.queries))
    params.pop('city')
    for param in params:
        if not params[param]:
            http_exception_json(status_code=400, param=param)

    valute_from, valute_to = (params[key] for key in params)
    #
    # review_count_filter = Count('exchange__reviews',
    #                             filter=Q(exchange__reviews__moderation=True))
    # positive_review_count_filter = Count('exchange__reviews',
    #                                      filter=Q(exchange__reviews__moderation=True) & Q(exchange__reviews__grade='1'))
    # neutral_review_count_filter = Count('exchange__reviews',
    #                                      filter=Q(exchange__reviews__moderation=True) & Q(exchange__reviews__grade='0'))
    # negative_review_count_filter = Count('exchange__reviews',
    #                                      filter=Q(exchange__reviews__moderation=True) & Q(exchange__reviews__grade='-1'))
    positive_review_count = Count('exchange__reviews',
                                         filter=positive_review_count_filter)
    neutral_review_count = Count('exchange__reviews',
                                         filter=neutral_review_count_filter)
    negative_review_count = Count('exchange__reviews',
                                         filter=negative_review_count_filter)

    # print(1)
    #
    # queries = ExchangeDirection.objects\
    #                             .select_related('exchange',
    #                                             'direction',
    #                                             'direction__valute_from',
    #                                             'direction__valute_to')\
    #                             .annotate(positive_review_count=positive_review_count)\
    #                             .annotate(neutral_review_count=neutral_review_count)\
    #                             .annotate(negative_review_count=negative_review_count)\
    #                             .filter(direction__valute_from=valute_from,
    #                                     direction__valute_to=valute_to,
    #                                     is_active=True,
    #                                     exchange__is_active=True)\
    #                             .order_by('-exchange__is_vip',
    #                                       '-out_count',
    #                                       'in_count').all()
    # queries = ExchangeDirection.objects\
    #                             .select_related('exchange',
    #                                             'valute_from',
    #                                             'valute_to')\
    #                             .annotate(positive_review_count=positive_review_count)\
    #                             .annotate(neutral_review_count=neutral_review_count)\
    #                             .annotate(negative_review_count=negative_review_count)\
    #                             .filter(valute_from=valute_from,
    #                                     valute_to=valute_to,
    #                                     is_active=True,
    #                                     exchange__is_active=True)\
    #                             .order_by('-exchange__is_vip',
    #                                       '-out_count',
    #                                       'in_count').all()
    queries = ExchangeDirection.objects\
                                .select_related('exchange',
                                                'valute_from',
                                                'valute_to')\
                                .annotate(positive_review_count=positive_review_count)\
                                .annotate(neutral_review_count=neutral_review_count)\
                                .annotate(negative_review_count=negative_review_count)\
                                .filter(valute_from=valute_from,
                                        valute_to=valute_to)\
                                .filter(is_active=True,
                                        exchange__is_active=True)\
                                .order_by('-exchange__is_vip',
                                          '-out_count',
                                          'in_count').all()
    
    # queries = ExchangeDirection.objects.raw(
    #     '''
    #     SELECT "no_cash_exchangedirection"."id", "no_cash_exchangedirection"."in_count", "no_cash_exchangedirection"."out_count", "no_cash_exchangedirection"."min_amount", "no_cash_exchangedirection"."max_amount", "no_cash_exchangedirection"."is_active", "no_cash_exchangedirection"."exchange_id", "no_cash_exchangedirection"."valute_from_id", "no_cash_exchangedirection"."valute_to_id", COUNT("no_cash_review"."id") FILTER (WHERE ("no_cash_review"."moderation" AND "no_cash_review"."grade" = \'1\')) AS "positive_review_count", COUNT("no_cash_review"."id") FILTER (WHERE ("no_cash_review"."moderation" AND "no_cash_review"."grade" = \'0\')) AS "neutral_review_count", COUNT("no_cash_review"."id") FILTER (WHERE ("no_cash_review"."moderation" AND "no_cash_review"."grade" = \'-1\')) AS "negative_review_count", "no_cash_exchange"."id", "no_cash_exchange"."name", "no_cash_exchange"."en_name", "no_cash_exchange"."partner_link", "no_cash_exchange"."is_active", "no_cash_exchange"."is_vip", "no_cash_exchange"."xml_url", "no_cash_exchange"."period_for_create", "no_cash_exchange"."period_for_update", "no_cash_exchange"."period_for_parse_black_list", "general_models_valute"."name", "general_models_valute"."en_name", "general_models_valute"."code_name", "general_models_valute"."type_valute", "general_models_valute"."icon_url", "general_models_valute"."available_for_partners", T5."name", T5."en_name", T5."code_name", T5."type_valute", T5."icon_url", T5."available_for_partners" FROM "no_cash_exchangedirection" INNER JOIN "no_cash_exchange" ON ("no_cash_exchangedirection"."exchange_id" = "no_cash_exchange"."id") LEFT OUTER JOIN "no_cash_review" ON ("no_cash_exchange"."id" = "no_cash_review"."exchange_id") INNER JOIN "general_models_valute" ON ("no_cash_exchangedirection"."valute_from_id" = "general_models_valute"."code_name") INNER JOIN "general_models_valute" T5 ON ("no_cash_exchangedirection"."valute_to_id" = T5."code_name") WHERE ("no_cash_exchangedirection"."valute_from_id" = \'BTC\' AND "no_cash_exchangedirection"."valute_to_id" = \'SBERRUB\' AND "no_cash_exchange"."is_active" AND "no_cash_exchangedirection"."is_active") GROUP BY "no_cash_exchangedirection"."id", "no_cash_exchange"."id", "general_models_valute"."name", T5."name" ORDER BY "no_cash_exchange"."is_vip" DESC, "no_cash_exchangedirection"."out_count" DESC, "no_cash_exchangedirection"."in_count" ASC
    #     '''
    # )
    # queries = ExchangeDirection.objects.raw(
    #     '''
    #     SELECT "no_cash_exchangedirection"."in_count", "no_cash_exchangedirection"."out_count", "no_cash_exchangedirection"."min_amount", "no_cash_exchangedirection"."max_amount", "no_cash_exchangedirection"."is_active", "no_cash_exchangedirection"."exchange_id", "no_cash_exchangedirection"."valute_from_id", "no_cash_exchangedirection"."valute_to_id", COUNT("no_cash_review"."id") FILTER (WHERE ("no_cash_review"."moderation" AND "no_cash_review"."grade" = \'1\')) AS "positive_review_count", COUNT("no_cash_review"."id") FILTER (WHERE ("no_cash_review"."moderation" AND "no_cash_review"."grade" = \'0\')) AS "neutral_review_count", COUNT("no_cash_review"."id") FILTER (WHERE ("no_cash_review"."moderation" AND "no_cash_review"."grade" = \'-1\')) AS "negative_review_count", "no_cash_exchange"."id", "no_cash_exchange"."name", "no_cash_exchange"."en_name", "no_cash_exchange"."partner_link", "no_cash_exchange"."is_active", "no_cash_exchange"."is_vip", "general_models_valute"."name", "general_models_valute"."en_name", "general_models_valute"."code_name", "general_models_valute"."type_valute", "general_models_valute"."icon_url", T5."name", T5."en_name", T5."code_name", T5."type_valute", T5."icon_url" FROM "no_cash_exchangedirection" INNER JOIN "no_cash_exchange" ON ("no_cash_exchangedirection"."exchange_id" = "no_cash_exchange"."id") LEFT OUTER JOIN "no_cash_review" ON ("no_cash_exchange"."id" = "no_cash_review"."exchange_id") INNER JOIN "general_models_valute" ON ("no_cash_exchangedirection"."valute_from_id" = "general_models_valute"."code_name") INNER JOIN "general_models_valute" T5 ON ("no_cash_exchangedirection"."valute_to_id" = T5."code_name") WHERE ("no_cash_exchangedirection"."valute_from_id" = \'BTC\' AND "no_cash_exchangedirection"."valute_to_id" = \'SBERRUB\' AND "no_cash_exchange"."is_active" AND "no_cash_exchangedirection"."is_active") GROUP BY "no_cash_exchangedirection"."id", "no_cash_exchange"."id", "general_models_valute"."name", T5."name" ORDER BY "no_cash_exchange"."is_vip" DESC, "no_cash_exchangedirection"."out_count" DESC, "no_cash_exchangedirection"."in_count" ASC
    #     '''
    # )

    # print(queries)
    
    # print(2)
    if not queries:
        http_exception_json(status_code=404, param=request.url)

    # increase_popular_count_direction(valute_from=valute_from,
    #                                  valute_to=valute_to)
    
    return get_exchange_direction_list(queries,
                                       valute_from,
                                       valute_to)