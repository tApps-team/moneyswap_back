import re
from time import time
from urllib.parse import urlparse
from typing import Any, List, Literal
from collections import defaultdict
from datetime import timedelta, datetime

import aiohttp
from django.conf import settings
from django.db import connection, models
from django.db.models import Count, Q, QuerySet, Prefetch, Sum, OuterRef, Subquery, Value, F, IntegerField
from django.db.models.functions import Coalesce
from django.utils import timezone

from fastapi import HTTPException

import no_cash.models as no_cash_models
import cash.models as cash_models
import partners.models as partner_models

from cash.models import ExchangeDirection as CashExDir, City, Country, Direction as CashDirection
from cash.schemas import (SpecialCashDirectionMultiPrtnerExchangeRatesWithLocationModel,
                          NewSpecialCashDirectionMultiPrtnerExchangeRatesWithLocationModel,
                          SpecialCashDirectionMultiPrtnerWithExchangeRatesWithAmlModel,
                          NewSpecialCashDirectionMultiPrtnerWithExchangeRatesWithAmlModel,
                          SpecialCashDirectionMultiWithAmlModel,
                          NewSpecialCashDirectionMultiWithAmlModel,
                          SpecificCitySchema,
                          SpecificCountrySchema,
                          RuEnCityModel,
                          SpecialCashDirectionMultiPrtnerModel,
                          SpecialCashDirectionMultiWithLocationModel,
                          NewSpecialCashDirectionMultiWithLocationModel,
                          SpecialCashDirectionMultiModel,
                          SpecialCashDirectionMultiPrtnerWithLocationModel,
                          SpecialCashDirectionMultiPrtnerWithExchangeRatesModel)
from no_cash.models import ExchangeDirection as NoCashExDir, Direction as NoCashDirection

from general_models.models import (Comment,
                                   ExchangeAdmin,
                                   Review,
                                   Guest,
                                   NewBaseComment,
                                   Valute,
                                   en_type_valute_dict,
                                   BaseExchange,
                                   NewBaseReview,
                                   NewValute,
                                   Exchanger,
                                   NewExchangeAdmin)
from general_models.schemas import (SpecialDirectionMultiWithAmlModel,
                                    NewSpecialDirectionMultiWithAmlModel,
                                    SpecialPartnerNoCashDirectionSchema,
                                    NewSpecialPartnerNoCashDirectionSchema,
                                    ValuteListSchema1,
                                    ValuteListSchema2,
                                    NewValuteListSchema,
                                    ValuteModel,
                                    EnValuteModel,
                                    MultipleName,
                                    ReviewCountSchema,
                                    ValuteTypeListSchema,
                                    ValuteListSchema,
                                    ValuteTypeNameSchema,
                                    TopCoinSchema,
                                    SpecialDirectionMultiModel,
                                    InfoSchema)
from general_models.utils.base import annotate_string_field
from general_models.utils.http_exc import comment_exception_json, review_exception_json

availabale_active_status_list = [
    'active',
    'inactive',
    'disabled',
]


round_valute_dict = {
    'BTC': 5,
    # 'ETH': 3,
    'Криптовалюта': 3,
    'Наличные': 3,
}

DEFAUT_ROUND = 3


EXCHANGE_MARKER_DICT = {
    'no_cash': no_cash_models.Exchange,
    'cash': cash_models.Exchange,
    'partner': partner_models.Exchange,
}   



def get_base_url(url: str | None) -> str:
    if url is None:
        return url
    
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"

# def get_reviews_count_filters(marker: str = None):
#     match marker:
#         case 'exchange':
#             positive_review_count_filter = Q(reviews__moderation=True) \
#                                         & Q(reviews__grade='1')
#             neutral_review_count_filter = Q(reviews__moderation=True) \
#                                                     & Q(reviews__grade='0')
#             negative_review_count_filter = Q(reviews__moderation=True) \
#                                                     & Q(reviews__grade='-1')
#         case _:
#             positive_review_count_filter = Q(exchange__reviews__moderation=True) \
#                                                     & Q(exchange__reviews__grade='1')
#             neutral_review_count_filter = Q(exchange__reviews__moderation=True) \
#                                                     & Q(exchange__reviews__grade='0')
#             negative_review_count_filter = Q(exchange__reviews__moderation=True) \
#                                                     & Q(exchange__reviews__grade='-1')   
#     return {
#         'positive': positive_review_count_filter,
#         'neutral': neutral_review_count_filter,
#         'negative': negative_review_count_filter,
#     }

def get_review_count_dict():
    # '''
    # Возвращает словарь вида {'exchange_id': {'positive_count': int,'neutral_count': int,'negative_count': int,},}
    # '''
    """
    Возвращает кол-во отзывов обменников разделенных по grade

    Returns:
        dict: Словарь вида:
            {
                "exchange_id": {
                    "positive_count": int,
                    "neutral_count": int,
                    "negative_count": int,
                },
                ...
            }
    """
    review_counts = (
        Review.objects
        .filter(moderation=True)
        .values('exchange_id')
        .annotate(
            positive_count=Count('id', filter=Q(grade='1') & Q(review_from__in=('moneyswap', 'ai'))),
            neutral_count=Count('id', filter=Q(grade='0') & Q(review_from__in=('moneyswap', 'ai'))),
            negative_count=Count('id', filter=Q(grade='-1') & Q(review_from__in=('moneyswap', 'ai'))),
        )
    )

    review_map = {r['exchange_id']: r for r in review_counts}

    return review_map


def get_reviews_count_filters(marker: Literal['exchange',
                                              'exchange_direction',
                                              'partner_direction']):
    related_field_name = 'reviews'

    match marker:
        case 'exchange':
            positive_review_count_filter = Q(reviews__moderation=True) \
                                        & Q(reviews__grade='1')
            neutral_review_count_filter = Q(reviews__moderation=True) \
                                                    & Q(reviews__grade='0')
            negative_review_count_filter = Q(reviews__moderation=True) \
                                                    & Q(reviews__grade='-1')
        case 'partner_direction':
            related_field_name = 'city__exchange__' + related_field_name
            
            positive_review_count_filter = Q(city__exchange__reviews__moderation=True) \
                                                    & Q(city__exchange__reviews__grade='1')
            neutral_review_count_filter = Q(city__exchange__reviews__moderation=True) \
                                                    & Q(city__exchange__reviews__grade='0')
            negative_review_count_filter = Q(city__exchange__reviews__moderation=True) \
                                                    & Q(city__exchange__reviews__grade='-1')
        case 'partner_country_direction':
            related_field_name = 'country__exchange__' + related_field_name
            
            positive_review_count_filter = Q(country__exchange__reviews__moderation=True) \
                                                    & Q(country__exchange__reviews__grade='1')
            neutral_review_count_filter = Q(country__exchange__reviews__moderation=True) \
                                                    & Q(country__exchange__reviews__grade='0')
            negative_review_count_filter = Q(country__exchange__reviews__moderation=True) \
                                                    & Q(country__exchange__reviews__grade='-1')
        case 'exchange_direction':
        # case _:
            related_field_name = 'exchange__' + related_field_name

            positive_review_count_filter = Q(exchange__reviews__moderation=True) \
                                                    & Q(exchange__reviews__grade='1')
            neutral_review_count_filter = Q(exchange__reviews__moderation=True) \
                                                    & Q(exchange__reviews__grade='0')
            negative_review_count_filter = Q(exchange__reviews__moderation=True) \
                                                    & Q(exchange__reviews__grade='-1')
            
    positive_review_count = Count(related_field_name,
                                  filter=positive_review_count_filter,
                                  distinct=True)
    neutral_review_count = Count(related_field_name,
                                 filter=neutral_review_count_filter,
                                 distinct=True)
    negative_review_count = Count(related_field_name,
                                  filter=negative_review_count_filter,
                                  distinct=True)

    return {
        'positive': positive_review_count,
        'neutral': neutral_review_count,
        'negative': negative_review_count,
    }


def new_get_reviews_count_filters(marker: Literal['exchange',
                                              'exchange_direction',
                                              'partner_direction']):
    # related_field_name = 'reviews'
    # Coalesce(Sum('count'), Value(0))
    match marker:
        case 'exchange':
            outref_name = 'name'
            # positive_reviews_count_subquery = NewBaseReview.objects.filter(
            #     exchange_name=OuterRef('name'),
            #     moderation=True,
            #     grade='1',
            # ).order_by().values('exchange_name').annotate(
            #     count=Coalesce(Count('id'), Value(0))
            # ).values('count')
            # neutral_reviews_count_subquery = NewBaseReview.objects.filter(
            #     exchange_name=OuterRef('name'),
            #     moderation=True,
            #     grade='0',
            # ).order_by().values('exchange_name').annotate(
            #     count=Coalesce(Count('id'), Value(0))
            # ).values('count')
            # negative_reviews_count_subquery = NewBaseReview.objects.filter(
            #     exchange_name=OuterRef('name'),
            #     moderation=True,
            #     grade='-1',
            # ).order_by().values('exchange_name').annotate(
            #     count=Coalesce(Count('id'), Value(0))
            # ).values('count')
            # positive_review_count_filter = Q(reviews__moderation=True) \
            #                             & Q(reviews__grade='1')
            # neutral_review_count_filter = Q(reviews__moderation=True) \
            #                                         & Q(reviews__grade='0')
            # negative_review_count_filter = Q(reviews__moderation=True) \
            #                                         & Q(reviews__grade='-1')
        case 'partner_direction':
            outref_name = 'city__exchange__name'
            # related_field_name = 'city__exchange__' + related_field_name
            
            # positive_review_count_filter = Q(city__exchange__reviews__moderation=True) \
            #                                         & Q(city__exchange__reviews__grade='1')
            # neutral_review_count_filter = Q(city__exchange__reviews__moderation=True) \
            #                                         & Q(city__exchange__reviews__grade='0')
            # negative_review_count_filter = Q(city__exchange__reviews__moderation=True) \
            #                                         & Q(city__exchange__reviews__grade='-1')
            # positive_reviews_count_subquery = NewBaseReview.objects.filter(
            #     exchange_name=OuterRef('city__exchange__name'),
            #     moderation=True,
            #     grade='1',
            # ).order_by().values('exchange_name').annotate(
            #     count=Coalesce(Count('id'), Value(0))
            # ).values('count')
            # neutral_reviews_count_subquery = NewBaseReview.objects.filter(
            #     exchange_name=OuterRef('city__exchange__name'),
            #     moderation=True,
            #     grade='0',
            # ).order_by().values('exchange_name').annotate(
            #     count=Coalesce(Count('id'), Value(0))
            # ).values('count')
            # negative_reviews_count_subquery = NewBaseReview.objects.filter(
            #     exchange_name=OuterRef('city__exchange__name'),
            #     moderation=True,
            #     grade='-1',
            # ).order_by().values('exchange_name').annotate(
            #     count=Coalesce(Count('id'), Value(0))
            # ).values('count')
        case 'partner_country_direction':
            outref_name = 'country__exchange__name'

            # related_field_name = 'country__exchange__' + related_field_name
            
            # positive_review_count_filter = Q(country__exchange__reviews__moderation=True) \
            #                                         & Q(country__exchange__reviews__grade='1')
            # neutral_review_count_filter = Q(country__exchange__reviews__moderation=True) \
            #                                         & Q(country__exchange__reviews__grade='0')
            # negative_review_count_filter = Q(country__exchange__reviews__moderation=True) \
            #                                         & Q(country__exchange__reviews__grade='-1')
            # positive_reviews_count_subquery = NewBaseReview.objects.filter(
            #     exchange_name=OuterRef('country__exchange__name'),
            #     moderation=True,
            #     grade='1',
            # ).order_by().values('exchange_name').annotate(
            #     count=Coalesce(Count('id'), Value(0))
            # ).values('count')
            # neutral_reviews_count_subquery = NewBaseReview.objects.filter(
            #     exchange_name=OuterRef('country__exchange__name'),
            #     moderation=True,
            #     grade='0',
            # ).order_by().values('exchange_name').annotate(
            #     count=Coalesce(Count('id'), Value(0))
            # ).values('count')
            # negative_reviews_count_subquery = NewBaseReview.objects.filter(
            #     exchange_name=OuterRef('country__exchange__name'),
            #     moderation=True,
            #     grade='-1',
            # ).order_by().values('exchange_name').annotate(
            #     count=Coalesce(Count('id'), Value(0))
            # ).values('count')
        case 'exchange_direction':
            outref_name = 'exchange__name'
        # case _:
            # related_field_name = 'exchange__' + related_field_name

            # positive_review_count_filter = Q(exchange__reviews__moderation=True) \
            #                                         & Q(exchange__reviews__grade='1')
            # neutral_review_count_filter = Q(exchange__reviews__moderation=True) \
            #                                         & Q(exchange__reviews__grade='0')
            # negative_review_count_filter = Q(exchange__reviews__moderation=True) \
            #                                         & Q(exchange__reviews__grade='-1')
    positive_reviews_count_subquery = NewBaseReview.objects.filter(
        exchange_name=OuterRef(outref_name),
        moderation=True,
        grade='1',
        review_from__in=('moneyswap', 'ai'),
    ).values('exchange_name').annotate(
        count=Count('id')
    ).values('count')[:1]
    neutral_reviews_count_subquery = NewBaseReview.objects.filter(
        exchange_name=OuterRef(outref_name),
        moderation=True,
        grade='0',
        review_from__in=('moneyswap', 'ai'),
    ).values('exchange_name').annotate(
        count=Count('id')
    ).values('count')[:1]
    negative_reviews_count_subquery = NewBaseReview.objects.filter(
        exchange_name=OuterRef(outref_name),
        moderation=True,
        grade='-1',
        review_from__in=('moneyswap', 'ai'),
    ).values('exchange_name').annotate(
        count=Count('id')
    ).values('count')[:1]
            
    # positive_review_count = Count(related_field_name,
    #                               filter=positive_review_count_filter,
    #                               distinct=True)
    # neutral_review_count = Count(related_field_name,
    #                              filter=neutral_review_count_filter,
    #                              distinct=True)
    # negative_review_count = Count(related_field_name,
    #                               filter=negative_review_count_filter,
    #                               distinct=True)
    positive_review_count = Subquery(positive_reviews_count_subquery, output_field=models.IntegerField())
    neutral_review_count = Subquery(neutral_reviews_count_subquery, output_field=models.IntegerField())
    negative_review_count = Subquery(negative_reviews_count_subquery, output_field=models.IntegerField())



    return {
        'positive': Coalesce(positive_review_count, Value(0)),
        'neutral': Coalesce(neutral_review_count, Value(0)),
        'negative': Coalesce(negative_review_count, Value(0)),
    }


def new_get_reviews_count_filters_2(marker: Literal['exchange',
                                                    'exchange_direction',
                                                    'partner_direction']):
    match marker:
        case 'exchange':
            outref_name = 'pk'
        case 'partner_direction':
            outref_name = 'city__exchange_id'
        case 'partner_country_direction':
            outref_name = 'country__exchange_id'
        case 'exchange_direction':
            outref_name = 'exchange_id'

    positive_reviews_count_subquery = Review.objects.filter(
        exchange_id=OuterRef(outref_name),
        moderation=True,
        grade='1',
        review_from__in=('moneyswap', 'ai'),
    ).values('exchange_id').annotate(
        count=Count('id')
    ).values('count')[:1]
    neutral_reviews_count_subquery = Review.objects.filter(
        exchange_id=OuterRef(outref_name),
        moderation=True,
        grade='0',
        review_from__in=('moneyswap', 'ai'),
    ).values('exchange_id').annotate(
        count=Count('id')
    ).values('count')[:1]
    negative_reviews_count_subquery = Review.objects.filter(
        exchange_id=OuterRef(outref_name),
        moderation=True,
        grade='-1',
        review_from__in=('moneyswap', 'ai'),
    ).values('exchange_id').annotate(
        count=Count('id')
    ).values('count')[:1]
            
    positive_review_count = Subquery(positive_reviews_count_subquery, output_field=models.IntegerField())
    neutral_review_count = Subquery(neutral_reviews_count_subquery, output_field=models.IntegerField())
    negative_review_count = Subquery(negative_reviews_count_subquery, output_field=models.IntegerField())

    return {
        'positive': Coalesce(positive_review_count, Value(0)),
        'neutral': Coalesce(neutral_review_count, Value(0)),
        'negative': Coalesce(negative_review_count, Value(0)),
    }


        # no_cash_link_count_subquery = no_cash_models.ExchangeLinkCount.objects.filter(
        #     user_id=OuterRef('tg_id')
        # ).values('user_id').annotate(
        #     total_count=Coalesce(Sum('count'), Value(0))
        # ).values('total_count')

        # cash_link_count_subquery = cash_models.ExchangeLinkCount.objects.filter(
        #     user_id=OuterRef('tg_id')
        # ).values('user_id').annotate(
        #     total_count=Coalesce(Sum('count'), Value(0))
        # ).values('total_count')

        # partner_link_count_subquery = partner_models.ExchangeLinkCount.objects.filter(
        #     user_id=OuterRef('tg_id')
        # ).values('user_id').annotate(
        #     total_count=Coalesce(Sum('count'), Value(0))
        # ).values('total_count')

        # partner_country_link_count_subquery = partner_models.CountryExchangeLinkCount.objects.filter(
        #     user_id=OuterRef('tg_id')
        # ).values('user_id').annotate(
        #     total_count=Coalesce(Sum('count'), Value(0))
        # ).values('total_count')



def get_exchange_query_with_reviews_counts(exchange_marker: str,
                                           review_counts: dict[str, Count]):
    exchange_model: BaseExchange = EXCHANGE_MARKER_DICT.get(exchange_marker)

    exchanges = exchange_model.objects.annotate(positive_review_count=review_counts['positive'],
                                                neutral_review_count=review_counts['neutral'],
                                                negative_review_count=review_counts['negative'])\
                                        # .annotate(neutral_review_count=review_counts['neutral'])\
                                        # .annotate(negative_review_count=review_counts['negative'])
        
    return exchanges


def generate_top_exchanges_query_by_model(exchange_marker: str,
                                          review_counts: dict[str, Count] = None):
    top_exchanges = get_exchange_query_with_reviews_counts(exchange_marker,
                                                           review_counts=review_counts)
    
    top_exchanges = top_exchanges\
                        .annotate(link_count=Sum('exchange_counts__count'))\
                        .annotate(exchange_marker=annotate_string_field(exchange_marker))\
                        .filter(is_active=True,
                                link_count__isnull=False)\
                        .values('pk',
                                'icon_url',
                                'name',
                                'positive_review_count',
                                'neutral_review_count',
                                'negative_review_count',
                                'link_count',
                                'exchange_marker')
    # print(top_exchanges)
    # print('*' * 8)
    return top_exchanges


def new_generate_top_exchanges_query_by_model(exchange_marker: str,
                                          review_counts: dict[str, Count] = None):
    # top_exchanges = get_exchange_query_with_reviews_counts(exchange_marker,
    #                                                        review_counts=review_counts)

    exchange_model: BaseExchange = EXCHANGE_MARKER_DICT.get(exchange_marker)

    top_exchanges = exchange_model.objects
    
    top_exchanges = top_exchanges\
                        .annotate(link_count=Sum('exchange_counts__count'))\
                        .annotate(exchange_marker=annotate_string_field(exchange_marker))\
                        .filter(is_active=True,
                                link_count__isnull=False)\
                        .values('pk',
                                'icon_url',
                                'name',
                                # 'positive_review_count',
                                # 'neutral_review_count',
                                # 'negative_review_count',
                                'link_count',
                                'exchange_marker')
    # print(top_exchanges)
    # print('*' * 8)
    return top_exchanges



positive_review_count_filter = Q(exchange__reviews__moderation=True) \
                                        & Q(exchange__reviews__grade='1')
neutral_review_count_filter = Q(exchange__reviews__moderation=True) \
                                        & Q(exchange__reviews__grade='0')
negative_review_count_filter = Q(exchange__reviews__moderation=True) \
                                        & Q(exchange__reviews__grade='-1')

# positive_review_count_filter = Q(reviews__moderation=True) \
#                                         & Q(reviews__grade='1')
# neutral_review_count_filter = Q(reviews__moderation=True) \
#                                         & Q(reviews__grade='0')
# negative_review_count_filter = Q(reviews__moderation=True) \
#                                         & Q(reviews__grade='-1')
# neutral_review_count_filter = Count('exchange__reviews',
#                                         filter=Q(exchange__reviews__moderation=True) & Q(exchange__reviews__grade='0'))
# negative_review_count_filter = Count('exchange__reviews',
#                                         filter=Q(exchange__reviews__moderation=True) & Q(exchange__reviews__grade='-1'))


# def round_valute_values(exchange_direction_dict: dict):

#     '''
#     Округляет значения "min_amount" и "max_amount"
#     '''

#     try:
#         # print('1',exchange_direction_dict)
#         valute_from = exchange_direction_dict['valute_from']
#         type_valute_from = exchange_direction_dict['type_valute_from']

#         valute_to = exchange_direction_dict['valute_to']
#         type_valute_to = exchange_direction_dict['type_valute_to']
        
#         min_amount = float(exchange_direction_dict['min_amount'].split()[0])
#         max_amount = float(exchange_direction_dict['max_amount'].split()[0])
#         in_count = exchange_direction_dict.get('in_count')
#         out_count = exchange_direction_dict.get('out_count')

#         if valute_from in round_valute_dict:
#             min_amount = round(min_amount, round_valute_dict[valute_from])
#             max_amount = round(max_amount, round_valute_dict[valute_from])
#             out_count = round(out_count, round_valute_dict[valute_from])
#         elif type_valute_from in round_valute_dict:
#             min_amount = round(min_amount, round_valute_dict[type_valute_from])
#             max_amount = round(max_amount, round_valute_dict[type_valute_from])
#             out_count = round(out_count, round_valute_dict[type_valute_from])
#         else:
#             min_amount = int(min_amount)
#             max_amount = int(max_amount)
#             out_count = round(out_count, DEFAUT_ROUND)

#         if valute_to in round_valute_dict:
#             in_count = round(in_count, round_valute_dict[valute_to])
#         elif type_valute_to in round_valute_dict:
#             in_count = round(in_count, round_valute_dict[type_valute_to])
#         else:
#             in_count = round(in_count, DEFAUT_ROUND)
        
#         exchange_direction_dict['min_amount'] = f'{min_amount}'
#         exchange_direction_dict['max_amount'] = f'{max_amount}'
#         exchange_direction_dict['in_count'] = in_count
#         exchange_direction_dict['out_count'] = out_count

#         # print('2', exchange_direction_dict)

#     except Exception:
#         pass


def round_valute_values(exchange_direction_dict: dict):

    '''
    Округляет значения "min_amount" и "max_amount"
    '''

    try:
        valute_from = exchange_direction_dict['valute_from']
        type_valute_from = exchange_direction_dict['type_valute_from']

        valute_to = exchange_direction_dict['valute_to']
        type_valute_to = exchange_direction_dict['type_valute_to']
        
        min_amount = exchange_direction_dict['min_amount']

        if min_amount:
            min_amount = float(min_amount.split()[0])

        max_amount = exchange_direction_dict['max_amount']

        if max_amount:
            max_amount = float(max_amount.split()[0])

        in_count = exchange_direction_dict.get('in_count')
        out_count = exchange_direction_dict.get('out_count')

        if valute_from in round_valute_dict:
            if min_amount:
                min_amount = round(min_amount, round_valute_dict[valute_from])
            if max_amount:
                max_amount = round(max_amount, round_valute_dict[valute_from])

        elif type_valute_from in round_valute_dict:
            if min_amount:
                min_amount = round(min_amount, round_valute_dict[type_valute_from])
            if max_amount:
                max_amount = round(max_amount, round_valute_dict[type_valute_from])

        else:
            if min_amount:
                min_amount = int(min_amount)
            if max_amount:
                max_amount = int(max_amount)

        valute_type_set = set((type_valute_from,type_valute_to))
        check_valutes = valute_type_set.intersection(set(('Наличные',
                                                         'Банкинг',
                                                         'Денежные переводы',
                                                         'ATM QR')))

        tether_set = set(('USDTTRC20', 'USDTERC20', 'USDTBEP20', 'USDCERC20', 'USDCTRC20'))
        if check_valutes:
            if set((valute_from, valute_to)).intersection(tether_set):
                # 3 знака
                _sign_number = 3

                in_count = round(in_count, _sign_number)
                out_count = round(out_count, _sign_number)
                pass
            # else:
            # поменял по просьбе Андрея модера
            elif len(check_valutes) == 2:
                # 1 знак
                _sign_number = 3
                
                in_count = round(in_count, _sign_number)
                out_count = round(out_count, _sign_number)
            else:
                # 1 знак
                _sign_number = 1

                in_count = round(in_count, _sign_number)
                out_count = round(out_count, _sign_number)
        elif type_valute_from == 'Криптовалюта' and type_valute_to == 'Криптовалюта':
            # 5 знаков
            _sign_number = 5

            in_count = round(in_count, _sign_number)
            out_count = round(out_count, _sign_number)
        else:
            _sign_number = DEFAUT_ROUND

            in_count = round(in_count, _sign_number)
            out_count = round(out_count, _sign_number)
        
        exchange_direction_dict['min_amount'] = f'{min_amount}' if min_amount else None
        exchange_direction_dict['max_amount'] = f'{max_amount}' if max_amount else None
        exchange_direction_dict['in_count'] = in_count
        exchange_direction_dict['out_count'] = out_count

    except Exception as ex:
        # print(ex)
        pass


def try_generate_icon_url(obj: Country | Valute) -> str | None:
    '''
    Генерирует путь до иконки переданного объекта.
    '''
    
    icon_url = None

    if obj.icon_url.name:
        icon_url = settings.PROTOCOL + settings.SITE_DOMAIN\
                                            + obj.icon_url.url
    if not icon_url:
        icon_url = settings.PROTOCOL + settings.SITE_DOMAIN\
                                            + '/media/icons/valute/BTC.svg'

    return icon_url


def generate_image_icon(icon_url: str):
    return settings.PROTOCOL + settings.SITE_DOMAIN\
                                + icon_url.url


def generate_image_icon2(icon_url: str | None):
    # print(settings.PROTOCOL)
    # print(settings.SITE_DOMAIN)
    # print(icon_url)
    icon = settings.PROTOCOL +\
                            settings.SITE_DOMAIN\
                                + '/media/'
    
    if icon_url is not None:
        icon += icon_url

    return icon


def generate_coin_for_schema(direction: CashDirection,
                             coin: Valute):
    icon = try_generate_icon_url(coin)
    coin.icon = icon
    coin.actual_course = direction.actual_course

    if direction.previous_course is not None:

        defferent = direction.actual_course - direction.previous_course

        if defferent != 0:
            is_increase = True if defferent > 0 else False

            one_percent = direction.previous_course / 100

            percent = abs(defferent) / one_percent
            
            coin.percent = percent
            coin.is_increase = is_increase
        else:
            coin.percent = None
            coin.is_increase = None  
    else:
        coin.percent = None
        coin.is_increase = None     

    return TopCoinSchema.model_construct(**coin.__dict__)  


def get_exchange(exchange_id: int,
                 exchange_marker: str,
                 review_counts: dict[str, Count] = None,
                 black_list_exchange: bool = False):
    # print(len(connection.queries))
    if exchange_marker == 'both':     # !
        exchange_marker = 'no_cash'

    exchange_model: BaseExchange = EXCHANGE_MARKER_DICT.get(exchange_marker)

    if not exchange_model:
        raise HTTPException(status_code=400)
    

    # exchange = exchange_model.objects.filter(pk=exchange_id,
    #                                          is_active=True)
    exchange = exchange_model.objects.filter(pk=exchange_id)

    if not black_list_exchange:
        # exchange = exchange.filter(is_active=True)
        exchange = exchange.filter(active_status__in=availabale_active_status_list)
    else:
        exchange = exchange.filter(active_status='scam')


    if not exchange.exists():
        raise HTTPException(status_code=400)
    
    if review_counts:
        exchange = exchange.annotate(positive_review_count=review_counts['positive'])\
                            .annotate(neutral_review_count=review_counts['neutral'])\
                            .annotate(negative_review_count=review_counts['negative'])
    
    return exchange


def get_exchange_with_direction_count(exchange: models.Manager[BaseExchange],
                                      exchange_id: int,
                                      exchange_marker: str):
    # print(len(connection.queries))
    match exchange_marker:
        case 'no_cash':
            direction_count_subquery = no_cash_models.ExchangeDirection.objects.filter(
                exchange_id=exchange_id,
                is_active=True,
            ).values('exchange_id').annotate(
                direction_count=Coalesce(Count('id'), Value(0))
            ).values('direction_count')
            return exchange.annotate(direction_count=direction_count_subquery)
        case 'cash':
            direction_count_subquery = cash_models.ExchangeDirection.objects.filter(
                exchange_id=exchange_id,
                is_active=True,
            ).values('exchange_id').annotate(
                direction_count=Coalesce(Count('id'), Value(0))
            ).values('direction_count')
            return exchange.annotate(direction_count=direction_count_subquery)
        case 'both':
            no_cash_direction_count_subquery = no_cash_models.ExchangeDirection.objects.filter(
                exchange_id=exchange_id,
                is_active=True,
            ).values('exchange_id').annotate(
                direction_count=Coalesce(Count('id'), Value(0))
            ).values('direction_count')

            no_cash_exchange_name_subquery = no_cash_models.Exchange.objects.filter(pk=exchange_id).values('name')[:1]
            
            try:
                cash_exchange_id = cash_models.Exchange.objects.get(name=Subquery(no_cash_exchange_name_subquery))
            except Exception as ex:
                print(ex)
                raise HTTPException(status_code=400,
                                    detail='invalid id for "both" marker')
            
            cash_direction_count_subquery = cash_models.ExchangeDirection.objects.filter(
                exchange_id=cash_exchange_id,
                is_active=True,
            ).values('exchange_id').annotate(
                direction_count=Coalesce(Count('id'), Value(0))
            ).values('direction_count')
            return exchange.annotate(no_cash_diretion_count=no_cash_direction_count_subquery,
                                     cash_diretion_count=cash_direction_count_subquery,
                                     direction_count=Coalesce(F('no_cash_diretion_count'), Value(0))+Coalesce(F('cash_diretion_count'), Value(0)))
        case 'partner':
            city_direction_count_subquery = partner_models.Direction.objects.select_related(
                'city',
                'city__exchange',
            ).filter(
                city__exchange__pk=exchange_id,
                is_active=True,
            ).values('city__exchange__pk').annotate(
                direction_count=Coalesce(Count('id'), Value(0))
            ).values('direction_count')

            country_direction_count_subquery = partner_models.CountryDirection.objects.select_related(
                'country',
                'country__exchange',
            ).filter(
                country__exchange__pk=exchange_id,
                is_active=True,
            ).values('country__exchange__pk').annotate(
                direction_count=Coalesce(Count('id'), Value(0))
            ).values('direction_count')

            return exchange.annotate(city_direction_count=city_direction_count_subquery,
                                     country_direction_count=country_direction_count_subquery,
                                     direction_count=Coalesce(F('city_direction_count'), Value(0))+Coalesce(F('country_direction_count'), Value(0)))


def get_exchange_with_direction_count_for_exchange_list(exchange_list: models.Manager[BaseExchange],
                                                        exchange_marker: str):
    # print(len(connection.queries))
    match exchange_marker:
        case 'no_cash':
            direction_count_subquery = no_cash_models.ExchangeDirection.objects.filter(
                exchange_id=OuterRef('id'),
                is_active=True,
            ).values('exchange_id').annotate(
                direction_count=Coalesce(Count('id'), Value(0))
            ).values('direction_count')
            return exchange_list.annotate(direction_count=Coalesce(direction_count_subquery, Value(0)))
            pass
        case 'cash':
            direction_count_subquery = cash_models.ExchangeDirection.objects.filter(
                exchange_id=OuterRef('id'),
                is_active=True,
            ).values('exchange_id').annotate(
                direction_count=Coalesce(Count('id'), Value(0))
            ).values('direction_count')
            return exchange_list.annotate(direction_count=Coalesce(direction_count_subquery, Value(0)))
            pass
        # case 'both':
        #     no_cash_direction_count_subquery = no_cash_models.ExchangeDirection.objects.filter(
        #         exchange_id=exchange_id,
        #         is_active=True,
        #     ).values('exchange_id').annotate(
        #         direction_count=Coalesce(Count('id'), Value(0))
        #     ).values('direction_count')

            # no_cash_exchange_name = no_cash_models.Exchange.objects.get(pk=exchange_id).name
            # no_cash_exchange_name_subquery = no_cash_models.Exchange.objects.filter(pk=exchange_id).values('name')[:1]
            # cash_exchange_id = cash_models.Exchange.objects.get(name=Subquery(no_cash_exchange_name_subquery))

            # cash_direction_count_subquery = cash_models.ExchangeDirection.objects.filter(
            #     exchange_id=cash_exchange_id,
            #     is_active=True,
            # ).values('exchange_id').annotate(
            #     direction_count=Coalesce(Count('id'), Value(0))
            # ).values('direction_count')
            # return exchange.annotate(no_cash_diretion_count=no_cash_direction_count_subquery,
            #                          cash_diretion_count=cash_direction_count_subquery,
            #                          direction_count=Coalesce(F('no_cash_diretion_count'), Value(0))+Coalesce(F('cash_diretion_count'), Value(0)))
            # pass
        case 'partner':
            city_direction_count_subquery = partner_models.Direction.objects.select_related(
                'city',
                'city__exchange',
            ).filter(
                city__exchange__pk=OuterRef('id'),
                is_active=True,
            ).values('city__exchange__pk').annotate(
                direction_count=Coalesce(Count('id'), Value(0))
            ).values('direction_count')

            country_direction_count_subquery = partner_models.CountryDirection.objects.select_related(
                'country',
                'country__exchange',
            ).filter(
                country__exchange__pk=OuterRef('id'),
                is_active=True,
            ).values('country__exchange__pk').annotate(
                direction_count=Coalesce(Count('id'), Value(0))
            ).values('direction_count')

            return exchange_list.annotate(city_direction_count=city_direction_count_subquery,
                                     country_direction_count=country_direction_count_subquery,
                                     direction_count=Coalesce(F('city_direction_count'), Value(0))+Coalesce(F('country_direction_count'), Value(0)))


def get_exchange_dircetions_dict_tuple():
    # print(len(connection.queries))
    result_dict = {
        'no_cash': {},
        'cash': {},
        'partner': {},
    }

    # review_counts = (
    #     NewBaseReview.objects
    #     .filter(moderation=True)
    #     .values('exchange_name')
    #     .annotate(
    #         positive_count=Count('id', filter=Q(grade='1')),
    #         neutral_count=Count('id', filter=Q(grade='0')),
    #         negative_count=Count('id', filter=Q(grade='-1')),
    #     )
    # )

    # review_map = {r['exchange_name']: r for r in review_counts}

    no_cash_exchange_directions = no_cash_models.ExchangeDirection.objects.select_related('exchange')\
                                                                            .filter(is_active=True,
                                                                                    exchange__is_active=True)\
                                                                            .values('exchange_id')\
                                                                            .annotate(total=Count('id'))\

    cash_exchange_directions = cash_models.ExchangeDirection.objects.select_related('exchange')\
                                                                            .filter(is_active=True,
                                                                                    exchange__is_active=True)\
                                                                            .values('exchange_id')\
                                                                            .annotate(total=Count('id'))\

    partner_exchange_directions = partner_models.Direction.objects.select_related('city__exchange')\
                                                                            .filter(is_active=True,
                                                                                    city__exchange__is_active=True)\
                                                                            .values('city__exchange_id')\
                                                                            .annotate(total=Count('id'))\

    country_exchange_directions = partner_models.CountryDirection.objects.select_related('country__exchange')\
                                                                            .filter(is_active=True,
                                                                                    country__exchange__is_active=True)\
                                                                            .values('country__exchange_id')\
                                                                            .annotate(total=Count('id'))\
    
    # print(no_cash_exchange_directions.all())
    # print(cash_exchange_directions.all())
    # print(partner_exchange_directions.all())
    # print(country_exchange_directions.all())
    result_dict['no_cash'] = {el['exchange_id']: el['total'] for el in no_cash_exchange_directions}
    result_dict['cash'] = {el['exchange_id']: el['total'] for el in cash_exchange_directions}
    # result_dict['partner_directions'] = {el['city__exchange_id']: el['total'] for el in partner_exchange_directions}
    # result_dict['country_directions'] = {el['country__exchange_id']: el['total'] for el in country_exchange_directions}
    _partner_directions = {el['city__exchange_id']: el['total'] for el in partner_exchange_directions}
    _country_directions = {el['country__exchange_id']: el['total'] for el in country_exchange_directions}

    for exchange_id in _country_directions:
        _partner_directions[exchange_id] = _partner_directions.get(exchange_id, 0) + _country_directions[exchange_id]

    result_dict['partner'] = _partner_directions

    # print(len(result_dict['no_cash']))
    # print(len(result_dict['cash']))
    # print(len(result_dict['partner']))

    return result_dict


def new_get_exchange_directions_count_dict(exchange_list: list[Exchanger],
                                           _pk: int = None):

    exchange_direction_count_dict = {exchanger['pk']: 0 \
                                     for exchanger in exchange_list}

    no_cash_exchange_directions =  no_cash_models.NewExchangeDirection.objects\
        .select_related('exchange')\
        .filter(is_active=True, exchange__is_active=True)\
        .values("exchange_id")\
        .annotate(total=Count("id"))\
        .values_list("exchange_id", "total")

    cash_exchange_directions = cash_models.NewExchangeDirection.objects\
        .select_related('exchange')\
        .filter(is_active=True, exchange__is_active=True)\
        .values("exchange_id")\
        .annotate(total=Count("id"))\
        .values_list("exchange_id", "total")\

    partner_city_exchange_directions = partner_models.NewDirection.objects\
        .select_related('city__exchange')\
        .filter(is_active=True,
                city__exchange__is_active=True)\
        .values("city__exchange_id")\
        .annotate(total=Count("id"))\
        .values_list("city__exchange_id", "total")\

    partner_country_exchange_directions = partner_models.NewCountryDirection.objects\
        .select_related('country__exchange')\
        .filter(is_active=True,
                country__exchange__is_active=True)\
        .values("country__exchange_id")\
        .annotate(total=Count("id"))\
        .values_list("country__exchange_id", "total")\

    partner_noncash_exchange_directions = partner_models.NewNonCashDirection.objects\
        .select_related('exchange')\
        .filter(is_active=True, exchange__is_active=True)\
        .values("exchange_id")\
        .annotate(total=Count("id"))\
        .values_list("exchange_id", "total")\

    if _pk:
        no_cash_exchange_directions = no_cash_exchange_directions.filter(exchange_id=_pk)
        cash_exchange_directions = cash_exchange_directions.filter(exchange_id=_pk)
        partner_city_exchange_directions = partner_city_exchange_directions.filter(city__exchange_id=_pk)
        partner_country_exchange_directions = partner_country_exchange_directions.filter(country__exchange_id=_pk)
        partner_noncash_exchange_directions = partner_noncash_exchange_directions.filter(exchange_id=_pk)

    no_cash_exchange_directions = dict(no_cash_exchange_directions)
    cash_exchange_directions = dict(cash_exchange_directions)
    partner_city_exchange_directions = dict(partner_city_exchange_directions)
    partner_country_exchange_directions = dict(partner_country_exchange_directions)
    partner_noncash_exchange_directions = dict(partner_noncash_exchange_directions)


    for exchange_id in exchange_direction_count_dict.keys():
        exchange_direction_count_dict[exchange_id] += no_cash_exchange_directions.get(exchange_id, 0)
        exchange_direction_count_dict[exchange_id] += cash_exchange_directions.get(exchange_id, 0)
        exchange_direction_count_dict[exchange_id] += partner_city_exchange_directions.get(exchange_id, 0)
        exchange_direction_count_dict[exchange_id] += partner_country_exchange_directions.get(exchange_id, 0)
        exchange_direction_count_dict[exchange_id] += partner_noncash_exchange_directions.get(exchange_id, 0)

    if not _pk:
        return exchange_direction_count_dict
    
    else:
        no_cash_sigment = bool(no_cash_exchange_directions or partner_noncash_exchange_directions)
        
        cash_sigment = bool(cash_exchange_directions or partner_city_exchange_directions or partner_country_exchange_directions)
        
        if no_cash_sigment and cash_sigment:
            segment_marker = 'both'
        elif no_cash_sigment:
            segment_marker = 'no_cash'
        elif cash_sigment:
            segment_marker = 'cash'
        else:
            segment_marker = None

        return exchange_direction_count_dict, segment_marker


def add_location_to_exchange_direction(exchange_direction: dict[str, Any],
                                       query):
    
    if exchange_direction['exchange_marker'] == 'partner':
        try:
            country_model = query.city.city.country
            city_model = query.city.city
        except AttributeError:
            country_model = query.country.country
            city_model = query.city.city

    else:
        country_model = query.city.country
        city_model = query.city

    country_multiple_name = MultipleName.model_construct(**country_model.__dict__)
    country_flag = try_generate_icon_url(country_model)
    country_info = SpecificCountrySchema(name=country_multiple_name,
                                         icon_url=country_flag)
    city_multiple_name = MultipleName.model_construct(**city_model.__dict__)
    city_model.name = city_multiple_name
    city_model.pk = city_model.id
    city_model.__dict__['country_info'] = country_info

    location = SpecificCitySchema.model_construct(**city_model.__dict__)
    exchange_direction['location'] = location


def new_add_location_to_exchange_direction(exchange_direction: dict[str, Any]):
    
    if exchange_direction['direction_marker'] in ('city', 'country'):

        country_model = exchange_direction['country_model']
        city_model = exchange_direction['city_model']

    else:
        country_model = exchange_direction['city'].country
        city_model = exchange_direction['city']

    # country_multiple_name = MultipleName.model_construct(**country_model.__dict__)
    country_multiple_name = MultipleName(name=country_model.name,
                                         en_name=country_model.en_name)

    country_flag = try_generate_icon_url(country_model)
    country_info = SpecificCountrySchema(name=country_multiple_name,
                                         icon_url=country_flag)
    # city_multiple_name = MultipleName.model_construct(**city_model.__dict__)
    city_multiple_name = MultipleName(name=city_model.name,
                                         en_name=city_model.en_name)

    city_dict = {
        'pk': city_model.pk,
        'name': city_multiple_name,
        'en_name': city_model.en_name,
        'code_name': city_model.code_name,
        'country_info': country_info,
    }

    location = SpecificCitySchema.model_construct(**city_dict)
    exchange_direction['location'] = location


# def get_exchange_direction_list(queries: List[NoCashExDir | CashExDir],
#                                 valute_from: str,
#                                 valute_to: str,
#                                 city: str = None):
#     '''
#     Возвращает список готовых направлений с необходимыми данными
#     '''
    
#     valute_from_obj = valute_to_obj = None

#     direction_list = []

#     exchange_marker = 'no_cash'

#     partner_link_pattern = f'&cur_from={valute_from}&cur_to={valute_to}'
    
#     if city:
#         partner_link_pattern += f'&city={city}'
#         exchange_marker = 'cash'

#     for _id, query in enumerate(queries, start=1):
#         if query.exchange.__dict__.get('partner_link') and query.exchange.__dict__.get('period_for_create'):
#             query.exchange.__dict__['partner_link'] += partner_link_pattern

#         if valute_from_obj is None:
#             valute_from_obj = query.direction.valute_from

#         icon_url_valute_from = try_generate_icon_url(valute_from_obj)
#         type_valute_from = valute_from_obj.type_valute

#         if valute_to_obj is None:
#             valute_to_obj = query.direction.valute_to

#         icon_url_valute_to = try_generate_icon_url(valute_to_obj)
#         type_valute_to = valute_to_obj.type_valute

#         exchange_direction = query.__dict__ | query.exchange.__dict__
#         exchange_direction['id'] = _id
#         exchange_direction['exchange_id'] = query.exchange.id
#         exchange_direction['review_count'] = ReviewCountSchema(
#             positive=query.positive_review_count,
#             neutral=query.neutral_review_count,
#             negative=query.negative_review_count,
#             )
        
#         if not hasattr(query,'exchange_marker'):
#             exchange_direction['exchange_marker'] = exchange_marker

#         exchange_direction['name'] = MultipleName(name=exchange_direction['name'],
#                                                   en_name=exchange_direction['en_name'])
#         exchange_direction['valute_from'] = valute_from
#         exchange_direction['icon_valute_from'] = icon_url_valute_from
#         exchange_direction['type_valute_from'] = type_valute_from

#         exchange_direction['valute_to'] = valute_to
#         exchange_direction['icon_valute_to'] = icon_url_valute_to
#         exchange_direction['type_valute_to'] = type_valute_to

#         # if add_location:
#         #     add_location_to_exchange_direction(exchange_direction,
#         #                                     query)
            
#         round_valute_values(exchange_direction)
#         direction_list.append(exchange_direction)

#     # print(len(connection.queries))
#     # print(connection.queries)
#     # for query in connection.queries:
#     #     print(query)
#     return direction_list


def get_valid_partner_link(partner_link: str | None):
    if partner_link is None:
        pass
    else:
        if partner_link.find('/ref/') != -1:
            link_tail = partner_link[-2:]

            if link_tail == '/?':
                pass
            elif re.match(r'.\/', link_tail): 
                partner_link += '?'
            else:
                partner_link += '/?'
    
    if partner_link.find('?') == -1:
        partner_link += '?'
                    
    return partner_link


def try_convert_course_with_frofee(exchange_direction: dict):
    if fromfee := exchange_direction.get('fromfee'):
        in_count = float(exchange_direction.get('in_count'))
        out_count = float(exchange_direction.get('out_count'))

        if in_count == 1:
            different = (out_count / 100) * fromfee
            out_count = out_count - different
            exchange_direction['out_count'] = round(out_count, 2)
        else:
            different = (in_count / 100) * fromfee
            in_count = in_count - different
            exchange_direction['in_count'] = round(in_count, 2)


def get_schema_model_by_exchange_marker(exchange_marker: Literal['no_cash',
                                                                 'cash',
                                                                 'partner'],
                                        with_location: bool):
    match exchange_marker:
        case 'no_cash':
            schema_model = SpecialDirectionMultiModel
        case 'cash':
            schema_model = SpecialCashDirectionMultiModel if not with_location\
                                                             else SpecialCashDirectionMultiWithLocationModel
        case 'partner':
            schema_model = SpecialCashDirectionMultiPrtnerModel if not with_location\
                                                             else SpecialCashDirectionMultiPrtnerWithLocationModel
            print(schema_model)
    
    return schema_model


def test_get_schema_model_by_exchange_marker(exchange_marker: Literal['no_cash',
                                                                 'cash',
                                                                 'partner'],
                                        with_location: bool):
    match exchange_marker:
        case 'no_cash':
            schema_model = SpecialDirectionMultiModel
        case 'cash':
            schema_model = SpecialCashDirectionMultiModel if not with_location\
                                                             else SpecialCashDirectionMultiWithLocationModel
        case 'partner':
            # schema_model = SpecialCashDirectionMultiPrtnerWithExchangeRatesModel if not with_location\
            #                                                  else SpecialCashDirectionMultiPrtnerWithLocationModel
            schema_model = SpecialCashDirectionMultiPrtnerWithExchangeRatesModel if not with_location\
                                                             else SpecialCashDirectionMultiPrtnerExchangeRatesWithLocationModel

            # print(schema_model)
            # SpecialCashDirectionMultiPrtnerExchangeRatesWithLocationModel
    
    return schema_model


def test_get_schema_model_by_exchange_marker_with_aml(exchange_marker: Literal['no_cash',
                                                                               'cash',
                                                                               'partner'],
                                                    with_location: bool,
                                                    is_no_cash: bool = False):
    match exchange_marker:
        case 'no_cash':
            schema_model = SpecialDirectionMultiWithAmlModel
        case 'cash':
            schema_model = SpecialCashDirectionMultiWithAmlModel if not with_location\
                                                             else SpecialCashDirectionMultiWithLocationModel
        case 'partner':
            if is_no_cash:
                schema_model = SpecialPartnerNoCashDirectionSchema
            else:
                schema_model = SpecialCashDirectionMultiPrtnerWithExchangeRatesWithAmlModel if not with_location\
                                                                else SpecialCashDirectionMultiPrtnerExchangeRatesWithLocationModel
    
    return schema_model


def get_schema_model_by_exchange_marker_with_aml(direction_marker: Literal['auto_cash',
                                                                           'auto_noncash',
                                                                           'city',
                                                                           'country',
                                                                           'no_cash'],
                                                                           with_location: bool,
                                                                           is_no_cash: bool = False):
    match direction_marker:
        case 'auto_noncash':
            schema_model = NewSpecialDirectionMultiWithAmlModel
        case 'auto_cash':
            schema_model = NewSpecialCashDirectionMultiWithAmlModel if not with_location\
                                                             else NewSpecialCashDirectionMultiWithLocationModel
        case 'city' | 'country' | 'no_cash':
            if is_no_cash:
                schema_model = NewSpecialPartnerNoCashDirectionSchema
            else:
                schema_model = NewSpecialCashDirectionMultiPrtnerWithExchangeRatesWithAmlModel if not with_location\
                                                                else NewSpecialCashDirectionMultiPrtnerExchangeRatesWithLocationModel
    
    return schema_model


def get_exchange_direction_list(queries: List[NoCashExDir | CashExDir],
                                valute_from: str,
                                valute_to: str,
                                city: str = None,
                                with_location: bool = False):
    '''
    Возвращает список готовых направлений с необходимыми данными
    '''

    if city and with_location:
        raise AttributeError('сity and with_location args can`t use together')
    
    valute_from_obj = valute_to_obj = None

    direction_list = []

    exchange_marker = 'no_cash'

    partner_link_pattern = f'&cur_from={valute_from}&cur_to={valute_to}'
    
    if city:
        partner_link_pattern += f'&city={city}'
        exchange_marker = 'cash'

    if with_location:
        exchange_marker = 'cash'

    for _id, query in enumerate(queries, start=1):
        if query.exchange.__dict__.get('partner_link') and query.exchange.__dict__.get('period_for_create'):
            # query.exchange.__dict__['partner_link'] += partner_link_pattern
#           
            if query.exchange.__dict__.get('partner_link').startswith('https://t.me'):
                pass
            else:
                partner_link = get_valid_partner_link(query.exchange.__dict__.get('partner_link'))
                query.exchange.__dict__['partner_link'] = partner_link + partner_link_pattern
#
                if with_location:
                    query.exchange.__dict__['partner_link'] += f'&city={query.city.code_name}'

        if valute_from_obj is None:
            valute_from_obj = query.direction.valute_from

        icon_url_valute_from = try_generate_icon_url(valute_from_obj)
        type_valute_from = valute_from_obj.type_valute

        if valute_to_obj is None:
            valute_to_obj = query.direction.valute_to

        icon_url_valute_to = try_generate_icon_url(valute_to_obj)
        type_valute_to = valute_to_obj.type_valute

        exchange_direction = query.__dict__ | query.exchange.__dict__
        exchange_direction['id'] = _id
        exchange_direction['exchange_direction_id'] = query.id
        exchange_direction['exchange_id'] = query.exchange.id
        exchange_direction['review_count'] = ReviewCountSchema(
            positive=query.positive_review_count,
            neutral=query.neutral_review_count,
            negative=query.negative_review_count,
            )
        
        if not hasattr(query,'exchange_marker'):
            exchange_direction['exchange_marker'] = exchange_marker

        exchange_direction['name'] = MultipleName(name=exchange_direction['name'],
                                                  en_name=exchange_direction['en_name'])
        exchange_direction['valute_from'] = valute_from
        exchange_direction['icon_valute_from'] = icon_url_valute_from
        exchange_direction['type_valute_from'] = type_valute_from

        exchange_direction['valute_to'] = valute_to
        exchange_direction['icon_valute_to'] = icon_url_valute_to
        exchange_direction['type_valute_to'] = type_valute_to

        if with_location:
            add_location_to_exchange_direction(exchange_direction,
                                               query)
            
        # try_convert_course_with_frofee(exchange_direction)
        round_valute_values(exchange_direction)

        schema_model = get_schema_model_by_exchange_marker(exchange_direction['exchange_marker'],
                                                           with_location)

        # if exchange_direction['exchange_marker'] == 'partner':
        exchange_direction = schema_model(**exchange_direction)

        direction_list.append(exchange_direction)

    # print(len(connection.queries))
    # print(connection.queries)
    # for query in connection.queries:
    #     print(query)
    return direction_list


def get_exchange_direction_list_with_aml(queries: List[NoCashExDir | CashExDir],
                                        valute_from: str,
                                        valute_to: str,
                                        city: str = None,
                                        with_location: bool = False,
                                        is_no_cash: bool = False):
    '''
    Возвращает список готовых направлений с необходимыми данными
    '''

    if city and with_location:
        raise AttributeError('сity and with_location args can`t use together')
    
    valute_from_obj = valute_to_obj = None

    direction_list = []

    exchange_marker = 'no_cash'

    partner_link_pattern = f'&cur_from={valute_from}&cur_to={valute_to}'
    
    if city:
        partner_link_pattern += f'&city={city}'
        exchange_marker = 'cash'

    if with_location:
        exchange_marker = 'cash'

    for _id, query in enumerate(queries, start=1):
        if query.exchange.__dict__.get('partner_link') and query.exchange.__dict__.get('period_for_create'):
            # query.exchange.__dict__['partner_link'] += partner_link_pattern
#           
            if query.exchange.__dict__.get('partner_link').startswith('https://t.me'):
                pass
            else:
                partner_link = get_valid_partner_link(query.exchange.__dict__.get('partner_link'))
                query.exchange.__dict__['partner_link'] = partner_link + partner_link_pattern
#
                if with_location:
                    query.exchange.__dict__['partner_link'] += f'&city={query.city.code_name}'

        if valute_from_obj is None:
            valute_from_obj = query.direction.valute_from

        icon_url_valute_from = try_generate_icon_url(valute_from_obj)
        type_valute_from = valute_from_obj.type_valute

        if valute_to_obj is None:
            valute_to_obj = query.direction.valute_to

        icon_url_valute_to = try_generate_icon_url(valute_to_obj)
        type_valute_to = valute_to_obj.type_valute

        exchange_direction = query.__dict__ | query.exchange.__dict__
        exchange_direction['id'] = _id
        exchange_direction['exchange_direction_id'] = query.id
        exchange_direction['exchange_id'] = query.exchange.id
        exchange_direction['review_count'] = ReviewCountSchema(
            positive=query.positive_review_count,
            neutral=query.neutral_review_count,
            negative=query.negative_review_count,
            )
        
        if not hasattr(query,'exchange_marker'):
            exchange_direction['exchange_marker'] = exchange_marker

        exchange_direction['name'] = MultipleName(name=exchange_direction['name'],
                                                  en_name=exchange_direction['en_name'])
        exchange_direction['valute_from'] = valute_from
        exchange_direction['icon_valute_from'] = icon_url_valute_from
        exchange_direction['type_valute_from'] = type_valute_from

        exchange_direction['valute_to'] = valute_to
        exchange_direction['icon_valute_to'] = icon_url_valute_to
        exchange_direction['type_valute_to'] = type_valute_to

        if not exchange_direction.get('info'):
            exchange_direction['info'] = InfoSchema(high_aml=exchange_direction['high_aml'])

        if with_location:
            add_location_to_exchange_direction(exchange_direction,
                                               query)
            
        # try_convert_course_with_frofee(exchange_direction)
        round_valute_values(exchange_direction)

        schema_model = test_get_schema_model_by_exchange_marker_with_aml(exchange_direction['exchange_marker'],
                                                                         with_location,
                                                                         is_no_cash=is_no_cash)

        # if exchange_direction['exchange_marker'] == 'partner':
        exchange_direction = schema_model(**exchange_direction)

        direction_list.append(exchange_direction)

    # print(len(connection.queries))
    # print(connection.queries)
    # for query in connection.queries:
    #     print(query)
    # return direction_list
    return sorted(direction_list,
                     key=lambda el: (-el.is_vip,
                                        -el.out_count,
                                        el.in_count))
    # queries = sorted(list(queries) + list(partner_directions),
    #                  key=lambda query: (-query.exchange.is_vip,
    #                                     -query.out_count,
    #                                     query.in_count))


def new_get_exchange_direction_list_with_aml(queries: List[NoCashExDir | CashExDir],
                                        valute_from: str,
                                        valute_to: str,
                                        city: str = None,
                                        with_location: bool = False,
                                        is_no_cash: bool = False):
    '''
    Возвращает список готовых направлений с необходимыми данными
    '''

    if city and with_location:
        raise AttributeError('сity and with_location args can`t use together')
    
    reviews_dict = get_review_count_dict()

    direction_list = []

    partner_link_pattern = f'&cur_from={valute_from}&cur_to={valute_to}'
    
    if city:
        partner_link_pattern += f'&city={city}'

    # start_time = time()

    for _id, query in enumerate(queries, start=1):
        _partner_link: str = query.exchange.partner_link
       
        if query.exchange.xml_url:
            if _partner_link.startswith('https://t.me'):
                pass
            else:
                partner_link = get_valid_partner_link(_partner_link)
                query.exchange.__dict__['partner_link'] = partner_link + partner_link_pattern

                if with_location:
                    query.exchange.__dict__['partner_link'] += f'&city={query.city.code_name}'

        valute_from_obj = query.direction.valute_from
        icon_url_valute_from = try_generate_icon_url(valute_from_obj)
        type_valute_from = valute_from_obj.type_valute

        valute_to_obj = query.direction.valute_to
        icon_url_valute_to = try_generate_icon_url(valute_to_obj)
        type_valute_to = valute_to_obj.type_valute

        exchange_direction = query.__dict__ | query.exchange.__dict__
        exchange_direction['id'] = _id
        exchange_direction['exchange_direction_id'] = query.pk
        exchange_direction['exchange_id'] = query.exchange.pk
        # print('CHECK!!!', exchange_direction)

        if count_dict := reviews_dict.get(query.exchange.pk):
            positive_count = count_dict['positive_count']
            neutral_count = count_dict['neutral_count']
            negative_count = count_dict['negative_count']
        else:
            positive_count = neutral_count = negative_count = 0

        exchange_direction['review_count'] = ReviewCountSchema(
            positive=positive_count,
            neutral=neutral_count,
            negative=negative_count,
            )

        exchange_direction['name'] = MultipleName(name=exchange_direction['name'],
                                                  en_name=exchange_direction['en_name'])
        exchange_direction['valute_from'] = valute_from
        exchange_direction['icon_valute_from'] = icon_url_valute_from
        exchange_direction['type_valute_from'] = type_valute_from

        exchange_direction['valute_to'] = valute_to
        exchange_direction['icon_valute_to'] = icon_url_valute_to
        exchange_direction['type_valute_to'] = type_valute_to

        if not exchange_direction.get('info'):
            exchange_direction['info'] = InfoSchema(high_aml=exchange_direction['high_aml'])

        if with_location:
            new_add_location_to_exchange_direction(exchange_direction,
                                                   query)
            
        round_valute_values(exchange_direction)

        schema_model = get_schema_model_by_exchange_marker_with_aml(exchange_direction['direction_marker'],
                                                                    with_location,
                                                                    is_no_cash=is_no_cash)

        exchange_direction = schema_model(**exchange_direction)

        direction_list.append(exchange_direction)

    # print(f'time generating direction list {time() - start_time} sec | {len(direction_list)} el')

    return sorted(direction_list,
                     key=lambda el: (-el.is_vip,
                                     -el.out_count,
                                     el.in_count))


def new_get_exchange_direction_list_with_aml_and_location(directions: List[dict],
                                        valute_from: str,
                                        valute_to: str,
                                        city: str = None,
                                        with_location: bool = False,
                                        is_no_cash: bool = False):
    '''
    Возвращает список готовых направлений с необходимыми данными
    '''

    if city and with_location:
        raise AttributeError('сity and with_location args can`t use together')
    
    reviews_dict = get_review_count_dict()

    direction_list = []

    partner_link_pattern = f'&cur_from={valute_from}&cur_to={valute_to}'
    
    if city:
        partner_link_pattern += f'&city={city}'

    start_time = time()

    for _id, exchange_direction in enumerate(directions, start=1):
        _partner_link: str = exchange_direction['exchange'].partner_link
       
        if exchange_direction['exchange'].xml_url:
            if _partner_link.startswith('https://t.me'):
                exchange_direction['partner_link'] = _partner_link
            else:
                partner_link = get_valid_partner_link(_partner_link)
                exchange_direction['partner_link'] = partner_link + partner_link_pattern

                if with_location:
                    exchange_direction['partner_link'] += f'&city={exchange_direction["city"].code_name}'
        else:
            exchange_direction['partner_link'] = _partner_link

        valute_from_obj = exchange_direction['direction'].valute_from
        icon_url_valute_from = try_generate_icon_url(valute_from_obj)
        type_valute_from = valute_from_obj.type_valute

        valute_to_obj = exchange_direction['direction'].valute_to
        icon_url_valute_to = try_generate_icon_url(valute_to_obj)
        type_valute_to = valute_to_obj.type_valute

        # exchange_direction = query.__dict__ | query.exchange.__dict__
        exchange_direction['id'] = _id
        # exchange_direction['exchange_direction_id'] = query.pk
        exchange_direction['exchange_id'] = exchange_direction['exchange'].pk

        if count_dict := reviews_dict.get(exchange_direction['exchange'].pk):
            positive_count = count_dict['positive_count']
            neutral_count = count_dict['neutral_count']
            negative_count = count_dict['negative_count']
        else:
            positive_count = neutral_count = negative_count = 0

        exchange_direction['review_count'] = ReviewCountSchema(
            positive=positive_count,
            neutral=neutral_count,
            negative=negative_count,
            )

        exchange_direction['name'] = MultipleName(name=exchange_direction['exchange'].name,
                                                  en_name=exchange_direction['exchange'].en_name)
        exchange_direction['valute_from'] = valute_from
        exchange_direction['icon_valute_from'] = icon_url_valute_from
        exchange_direction['type_valute_from'] = type_valute_from

        exchange_direction['valute_to'] = valute_to
        exchange_direction['icon_valute_to'] = icon_url_valute_to
        exchange_direction['type_valute_to'] = type_valute_to

        if not exchange_direction.get('info'):
            exchange_direction['info'] = InfoSchema(high_aml=exchange_direction['exchange'].high_aml)

        if with_location:
            new_add_location_to_exchange_direction(exchange_direction)
            
        round_valute_values(exchange_direction)

        schema_model = get_schema_model_by_exchange_marker_with_aml(exchange_direction['direction_marker'],
                                                                    with_location,
                                                                    is_no_cash=is_no_cash)

        exchange_direction = schema_model(**exchange_direction)

        direction_list.append(exchange_direction)

    # print(f'time generating direction list {time() - start_time} sec | {len(direction_list)} el')

    return sorted(direction_list,
                     key=lambda el: (-el.is_vip,
                                     -el.out_count,
                                     el.in_count))



def test_get_exchange_direction_list(queries: List[NoCashExDir | CashExDir],
                                valute_from: str,
                                valute_to: str,
                                city: str = None,
                                with_location: bool = False):
    '''
    Возвращает список готовых направлений с необходимыми данными
    '''

    if city and with_location:
        raise AttributeError('сity and with_location args can`t use together')
    
    valute_from_obj = valute_to_obj = None

    direction_list = []

    exchange_marker = 'no_cash'

    partner_link_pattern = f'&cur_from={valute_from}&cur_to={valute_to}'
    
    if city:
        partner_link_pattern += f'&city={city}'
        exchange_marker = 'cash'

    if with_location:
        exchange_marker = 'cash'

    for _id, query in enumerate(queries, start=1):
        if query.exchange.__dict__.get('partner_link') and query.exchange.__dict__.get('period_for_create'):
            # query.exchange.__dict__['partner_link'] += partner_link_pattern
#           
            if query.exchange.__dict__.get('partner_link').startswith('https://t.me'):
                pass
            else:
                partner_link = get_valid_partner_link(query.exchange.__dict__.get('partner_link'))
                query.exchange.__dict__['partner_link'] = partner_link + partner_link_pattern
#
                if with_location:
                    query.exchange.__dict__['partner_link'] += f'&city={query.city.code_name}'

        if valute_from_obj is None:
            valute_from_obj = query.direction.valute_from

        icon_url_valute_from = try_generate_icon_url(valute_from_obj)
        type_valute_from = valute_from_obj.type_valute

        if valute_to_obj is None:
            valute_to_obj = query.direction.valute_to

        icon_url_valute_to = try_generate_icon_url(valute_to_obj)
        type_valute_to = valute_to_obj.type_valute

        exchange_direction = query.__dict__ | query.exchange.__dict__
        exchange_direction['id'] = _id
        exchange_direction['exchange_direction_id'] = query.id
        exchange_direction['exchange_id'] = query.exchange.id
        exchange_direction['review_count'] = ReviewCountSchema(
            positive=query.positive_review_count,
            neutral=query.neutral_review_count,
            negative=query.negative_review_count,
            )
        
        if not hasattr(query,'exchange_marker'):
            exchange_direction['exchange_marker'] = exchange_marker

        exchange_direction['name'] = MultipleName(name=exchange_direction['name'],
                                                  en_name=exchange_direction['en_name'])
        exchange_direction['valute_from'] = valute_from
        exchange_direction['icon_valute_from'] = icon_url_valute_from
        exchange_direction['type_valute_from'] = type_valute_from

        exchange_direction['valute_to'] = valute_to
        exchange_direction['icon_valute_to'] = icon_url_valute_to
        exchange_direction['type_valute_to'] = type_valute_to

        if with_location:
            add_location_to_exchange_direction(exchange_direction,
                                               query)
            
        # try_convert_course_with_frofee(exchange_direction)
        round_valute_values(exchange_direction)

        schema_model = test_get_schema_model_by_exchange_marker(exchange_direction['exchange_marker'],
                                                           with_location)

        # if exchange_direction['exchange_marker'] == 'partner':
        exchange_direction = schema_model(**exchange_direction)

        direction_list.append(exchange_direction)

    # print(connection.queries)
    # for query in connection.queries:
    #     print(query)
    #     print('*' * 8)
    # print(len(connection.queries))
    return direction_list



def test_get_exchange_direction_list_with_aml(queries: List[NoCashExDir | CashExDir],
                                valute_from: str,
                                valute_to: str,
                                city: str = None,
                                with_location: bool = False):
    '''
    Возвращает список готовых направлений с необходимыми данными
    '''

    if city and with_location:
        raise AttributeError('сity and with_location args can`t use together')
    
    valute_from_obj = valute_to_obj = None

    direction_list = []

    exchange_marker = 'no_cash'

    partner_link_pattern = f'&cur_from={valute_from}&cur_to={valute_to}'
    
    if city:
        partner_link_pattern += f'&city={city}'
        exchange_marker = 'cash'

    if with_location:
        exchange_marker = 'cash'

    for _id, query in enumerate(queries, start=1):
        if query.exchange.__dict__.get('partner_link') and query.exchange.__dict__.get('period_for_create'):
            # query.exchange.__dict__['partner_link'] += partner_link_pattern
#           
            if query.exchange.__dict__.get('partner_link').startswith('https://t.me'):
                pass
            else:
                partner_link = get_valid_partner_link(query.exchange.__dict__.get('partner_link'))
                query.exchange.__dict__['partner_link'] = partner_link + partner_link_pattern
#
                if with_location:
                    query.exchange.__dict__['partner_link'] += f'&city={query.city.code_name}'

        if valute_from_obj is None:
            valute_from_obj = query.direction.valute_from

        icon_url_valute_from = try_generate_icon_url(valute_from_obj)
        type_valute_from = valute_from_obj.type_valute

        if valute_to_obj is None:
            valute_to_obj = query.direction.valute_to

        icon_url_valute_to = try_generate_icon_url(valute_to_obj)
        type_valute_to = valute_to_obj.type_valute

        exchange_direction = query.__dict__ | query.exchange.__dict__
        exchange_direction['id'] = _id
        exchange_direction['exchange_direction_id'] = query.id
        exchange_direction['exchange_id'] = query.exchange.id
        exchange_direction['review_count'] = ReviewCountSchema(
            positive=query.positive_review_count,
            neutral=query.neutral_review_count,
            negative=query.negative_review_count,
            )
        
        if not hasattr(query,'exchange_marker'):
            exchange_direction['exchange_marker'] = exchange_marker

        exchange_direction['name'] = MultipleName(name=exchange_direction['name'],
                                                  en_name=exchange_direction['en_name'])
        exchange_direction['valute_from'] = valute_from
        exchange_direction['icon_valute_from'] = icon_url_valute_from
        exchange_direction['type_valute_from'] = type_valute_from

        exchange_direction['valute_to'] = valute_to
        exchange_direction['icon_valute_to'] = icon_url_valute_to
        exchange_direction['type_valute_to'] = type_valute_to

        if not exchange_direction.get('info'):
            exchange_direction['info'] = InfoSchema(high_aml=exchange_direction['high_aml'])

        if with_location:
            add_location_to_exchange_direction(exchange_direction,
                                               query)
            
        # try_convert_course_with_frofee(exchange_direction)
        round_valute_values(exchange_direction)

        schema_model = test_get_schema_model_by_exchange_marker_with_aml(exchange_direction['exchange_marker'],
                                                                         with_location)

        # if exchange_direction['exchange_marker'] == 'partner':
        exchange_direction = schema_model(**exchange_direction)

        direction_list.append(exchange_direction)

    # print(connection.queries)
    # for query in connection.queries:
    #     print(query)
    #     print('*' * 8)
    # print(len(connection.queries))
    # return direction_list
    return sorted(direction_list,
                     key=lambda el: (-el.is_vip,
                                        -el.out_count,
                                        el.in_count))



def get_exchange_direction_list_with_location(queries: List[NoCashExDir | CashExDir],
                                              valute_from: str,
                                              valute_to: str):
    '''
    Возвращает список готовых направлений с необходимыми данными
    '''
    
    valute_from_obj = valute_to_obj = None

    direction_list = []

    exchange_marker = 'cash'

    partner_link_pattern = f'&cur_from={valute_from}&cur_to={valute_to}'
    
    # if city:
    #     partner_link_pattern += f'&city={city}'
    #     exchange_marker = 'cash'

    for _id, query in enumerate(queries, start=1):
        
        if query.exchange.__dict__.get('partner_link') and query.exchange.__dict__.get('period_for_create'):
            query.exchange.__dict__['partner_link'] += partner_link_pattern
            
            # if not hasattr(query,'exchange_marker'):
            query.exchange.__dict__['partner_link'] += f'&city={query.city.code_name}'

        if valute_from_obj is None:
            valute_from_obj = query.direction.valute_from

        icon_url_valute_from = try_generate_icon_url(valute_from_obj)
        type_valute_from = valute_from_obj.type_valute

        if valute_to_obj is None:
            valute_to_obj = query.direction.valute_to

        icon_url_valute_to = try_generate_icon_url(valute_to_obj)
        type_valute_to = valute_to_obj.type_valute

        exchange_direction = query.__dict__ | query.exchange.__dict__
        exchange_direction['id'] = _id
        exchange_direction['exchange_id'] = query.exchange.id
        exchange_direction['review_count'] = ReviewCountSchema(
            positive=query.positive_review_count,
            neutral=query.neutral_review_count,
            negative=query.negative_review_count,
            )
        
        if not hasattr(query,'exchange_marker'):
            exchange_direction['exchange_marker'] = exchange_marker

        exchange_direction['name'] = MultipleName(name=exchange_direction['name'],
                                                  en_name=exchange_direction['en_name'])
        exchange_direction['valute_from'] = valute_from
        exchange_direction['icon_valute_from'] = icon_url_valute_from
        exchange_direction['type_valute_from'] = type_valute_from

        exchange_direction['valute_to'] = valute_to
        exchange_direction['icon_valute_to'] = icon_url_valute_to
        exchange_direction['type_valute_to'] = type_valute_to

        # if add_location:
        add_location_to_exchange_direction(exchange_direction,
                                           query)
            
        round_valute_values(exchange_direction)
        direction_list.append(exchange_direction)

    # print(len(connection.queries))
    # print(connection.queries)
    # for query in connection.queries:
    #     print(query)
    print(len(connection.queries))
    return direction_list



def get_exchange_directions(exchange: QuerySet[BaseExchange],
                            exchange_marker: str):
    if exchange_marker == 'both':
        exchange_marker = 'no_cash'
    # print(exchange)
    match exchange_marker:
        case 'partner':
            exchange_directions = partner_models.Direction.objects.select_related('city',
                                                                                  'city__exchange',
                                                                                  'direction')\
                                                                .filter(city__exchange__in=exchange,
                                                                        is_active=True)
        # case 'both':
        #     exchange = exchange.first()
        #     cash_exchange_directions = cash_models.ExchangeDirection.objects\
        #                                                         .select_related('exchange')\
        #                                                         .filter(exchange__name__icontains=f'{exchange.name}',
        #                                                                 is_active=True)
        #     no_cash_exchange_directions = exchange.directions

        #     exchange_directions = (no_cash_exchange_directions, cash_exchange_directions)
        case _:
            exchange_directions = exchange.first().directions
        
    return exchange_directions


# def get_valute_json(queries: List[NoCashExDir | CashExDir]):
    
#     '''
#     Возвращает словарь валют с необходимыми данными 
#     '''

#     # valute_name_list = set(map(lambda query: query[0], queries))
#     valutes = Valute.objects.filter(code_name__in=queries).all()
    
#     json_dict = {'ru': dict(), 'en': dict()}
#     # json_dict = defaultdict(dict)

#     # json_dict.fromkeys(default_dict_keys)

#     for id, valute in enumerate(valutes, start=1):
#         icon_url = try_generate_icon_url(valute)
#         valute.icon_url = icon_url
#         valute.id = id

#         json_dict['ru'][valute.type_valute] = json_dict['ru'].get(valute.type_valute, [])\
#                                                  + [ValuteModel(**valute.__dict__)]
        
#         en_type_valute = en_type_valute_dict[valute.type_valute]
#         json_dict['en'][en_type_valute] = json_dict['en'].get(en_type_valute, [])\
#                                                  + [EnValuteModel(**valute.__dict__)]

#     return json_dict


def get_valute_json_2(queries: List[NoCashExDir | CashExDir]):
    
    '''
    Возвращает словарь валют с необходимыми данными 
    '''

    # valute_name_list = set(map(lambda query: query[0], queries))
    valutes = Valute.objects.filter(code_name__in=queries).all()
    
    json_dict = {}
    json_dict = defaultdict(list)

    # json_dict.fromkeys(default_dict_keys)

    for valute in valutes:
        icon_url = try_generate_icon_url(valute)

        dict_key = (valute.type_valute, en_type_valute_dict[valute.type_valute])
        json_dict[dict_key].append({
            'id': valute.pk,
            'name': ValuteTypeNameSchema(ru=valute.name,
                                         en=valute.en_name),
            'code_name': valute.code_name,
            'icon_url': icon_url,
            }
        )
    
    res = []
    for idx, obj in enumerate(json_dict, start=1):
        res.append(ValuteListSchema(id=idx,
                                    name=ValuteTypeNameSchema(ru=obj[0],
                                                              en=obj[-1]),
                                    currencies=json_dict[obj]))
        
    # print(connection.queries)

    return res


def get_valute_json_3(queries: List[NoCashExDir | CashExDir]):
    
    '''
    Возвращает словарь валют с необходимыми данными 
    '''

    # valute_name_list = set(map(lambda query: query[0], queries))
    valutes = Valute.objects.filter(code_name__in=queries)\
                            .order_by('-is_popular', '-name')\
                            .all()
    
    json_dict = {}
    json_dict = defaultdict(list)

    # json_dict.fromkeys(default_dict_keys)

    for valute in valutes:
        icon_url = try_generate_icon_url(valute)

        dict_key = (valute.type_valute, en_type_valute_dict[valute.type_valute])
        json_dict[dict_key].append({
            'id': valute.pk,
            'name': ValuteTypeNameSchema(ru=valute.name,
                                         en=valute.en_name),
            'code_name': valute.code_name,
            'icon_url': icon_url,
            'is_popular': valute.is_popular,
            }
        )
    
    res = []
    for idx, obj in enumerate(json_dict, start=1):
        res.append(ValuteListSchema(id=idx,
                                    name=ValuteTypeNameSchema(ru=obj[0],
                                                              en=obj[-1]),
                                    currencies=json_dict[obj]))

    return res


def get_valute_json_3(queries: List[NoCashExDir | CashExDir]):
    
    '''
    Возвращает словарь валют с необходимыми данными 
    '''

    # valute_name_list = set(map(lambda query: query[0], queries))
    valutes = Valute.objects.filter(code_name__in=queries)\
                            .order_by('-is_popular', 'name')\
                            .all()
    
    json_dict = {}
    json_dict = defaultdict(list)

    # json_dict.fromkeys(default_dict_keys)

    for valute in valutes:
        icon_url = try_generate_icon_url(valute)

        dict_key = (valute.type_valute, en_type_valute_dict[valute.type_valute])
        json_dict[dict_key].append({
            'id': valute.pk,
            'name': ValuteTypeNameSchema(ru=valute.name,
                                         en=valute.en_name),
            'code_name': valute.code_name,
            'icon_url': icon_url,
            'is_popular': valute.is_popular,
            }
        )
    
    res = []
    for idx, obj in enumerate(json_dict, start=1):
        res.append(ValuteListSchema1(id=idx,
                                    name=ValuteTypeNameSchema(ru=obj[0],
                                                              en=obj[-1]),
                                    currencies=json_dict[obj]))

    return res


def get_valute_json_4(queries: List[NoCashExDir | CashExDir]):
    
    '''
    Возвращает словарь валют с необходимыми данными 
    '''

    # valute_name_list = set(map(lambda query: query[0], queries))
    valutes = Valute.objects.filter(code_name__in=queries)\
                            .order_by('-is_popular', 'name')\
                            .all()
    
    json_dict = {}
    json_dict = defaultdict(list)

    # json_dict.fromkeys(default_dict_keys)

    for valute in valutes:
        icon_url = try_generate_icon_url(valute)

        dict_key = (valute.type_valute, en_type_valute_dict[valute.type_valute])
        json_dict[dict_key].append({
            'id': valute.pk,
            'name': ValuteTypeNameSchema(ru=valute.name,
                                         en=valute.en_name),
            'code_name': valute.code_name,
            'type_valute': valute.type_valute,
            'icon_url': icon_url,
            'is_popular': valute.is_popular,
            }
        )
    
    res = []
    for idx, obj in enumerate(json_dict, start=1):
        res.append(ValuteListSchema2(id=idx,
                                    name=ValuteTypeNameSchema(ru=obj[0],
                                                              en=obj[-1]),
                                    currencies=json_dict[obj]))

    return res


def get_valute_json(queries: List[NoCashExDir | CashExDir]):
    
    '''
    Возвращает словарь валют с необходимыми данными 
    '''

    valutes = NewValute.objects.filter(code_name__in=queries)\
                            .order_by('-is_popular', 'name')\
                            .all()
    
    json_dict = {}
    json_dict = defaultdict(list)

    for valute in valutes:
        icon_url = try_generate_icon_url(valute)

        dict_key = (valute.type_valute, en_type_valute_dict[valute.type_valute])
        json_dict[dict_key].append({
            'id': valute.pk,
            'name': ValuteTypeNameSchema(ru=valute.name,
                                         en=valute.en_name),
            'code_name': valute.code_name,
            'type_valute': valute.type_valute,
            'icon_url': icon_url,
            'is_popular': valute.is_popular,
            }
        )
    
    res = []
    for idx, obj in enumerate(json_dict, start=1):
        res.append(NewValuteListSchema(id=idx,
                                    name=ValuteTypeNameSchema(ru=obj[0],
                                                              en=obj[-1]),
                                    currencies=json_dict[obj]))

    return res


def increase_popular_count_direction(**kwargs):
    direction = CashDirection if kwargs.get('city') else NoCashDirection
    valute_from, valute_to = kwargs['valute_from'], kwargs['valute_to']
    direction = direction.objects.select_related('valute_from',
                                                 'valute_to')\
                                    .get(valute_from=valute_from,
                                        valute_to=valute_to)
    direction.popular_count += 1
    direction.save()


def new_increase_popular_count_direction(**kwargs):
    city_code_name = kwargs.get('city')
    direction = cash_models.NewDirection if city_code_name else no_cash_models.NewDirection
    valute_from, valute_to = kwargs['valute_from'], kwargs['valute_to']
    try:
        direction = direction.objects.filter(valute_from_id=valute_from,
                                             valute_to_id=valute_to).update(popular_count=F('popular_count') + 1)
        
        if city_code_name:
            City.objects.filter(code_name=city_code_name).update(popular_count=F('popular_count') + 1)

    except Exception as ex:
        print(ex)


def check_exchage_marker(exchange_marker: str):
    if exchange_marker not in {'no_cash', 'cash', 'partner', 'both'}:
        raise HTTPException(status_code=400,
                            detail='Параметр "exchange_marker" должен быть одним из следующих: no_cash, cash, partner, both')


def check_exchage_by_name(exchange_name: str):
        for exchange_model in (no_cash_models.Exchange,
                               cash_models.Exchange,
                               partner_models.Exchange):
            if exchange_model.objects.filter(name=exchange_name).exists():
                return True
        else:
            raise HTTPException(status_code=400,
                                detail='Обменник с таким названием не найден')


def check_perms_for_adding_review(exchange_id: int,
                                  tg_id: int):
    time_delta = timedelta(days=1)

    check_time = timezone.now() - time_delta

    review = Review.objects.filter(exchange_id=exchange_id,
                                   guest_id=tg_id,
                                   time_create__gt=check_time)\
                            .first()

    if review:
        next_time_review = review.time_create.astimezone() + time_delta
        review_exception_json(status_code=423,
                              param=next_time_review.strftime('%d.%m.%Y %H:%M'))

    return {'status': 'success'}



def new_check_perms_for_adding_review(exchange_name: str,
                                      tg_id: int):
    time_delta = timedelta(days=1)

    check_exchage_by_name(exchange_name)

    # match exchange_marker:
    #     case 'no_cash':
    #         review_model = no_cash_models.Review
    #     case 'cash':
    #         review_model = cash_models.Review
    #     case 'partner':
    #         review_model = partner_models.Review
    #     case 'both':
    #         review_model = no_cash_models.Review

    check_time = datetime.now() - time_delta

    review = NewBaseReview.objects.select_related('guest')\
                                    .filter(exchange_name=exchange_name,
                                            guest_id=tg_id,
                                            time_create__gt=check_time)\
                                    .first()

    if review:
        next_time_review = review.time_create.astimezone() + time_delta
        review_exception_json(status_code=423,
                              param=next_time_review.strftime('%d.%m.%Y %H:%M'))

    
    return {'status': 'success'}


def check_perms_for_adding_comment(review_id: int,
                                   user_id: int):
    time_delta = timedelta(minutes=5)

    if not Guest.objects.filter(tg_id=user_id).exists():
        raise HTTPException(status_code=404,
                             detail='User don`t exists in DB')

    review = Review.objects.select_related('exchange')\
                                    .filter(pk=review_id)
    
    if not review.exists():
        raise HTTPException(status_code=404,
                        detail='Review not found')
    
    if review.filter(guest_id=user_id).exists() or NewExchangeAdmin.objects.filter(user_id=user_id,
                                                                                exchange_id=review.first().exchange.pk):
        check_time = timezone.now() - time_delta

        comment = Comment.objects.select_related('guest',
                                                 'review')\
                                        .filter(review_id=review_id,
                                                guest_id=user_id,
                                                time_create__gt=check_time)\
                                        .first()

        if comment:
            next_time_comment = comment.time_create.astimezone() + time_delta
            review_exception_json(status_code=423,
                                param=next_time_comment.strftime('%d.%m.%Y %H:%M'))

        return {'status': 'success'}

    else:
        raise HTTPException(status_code=404,
                             detail='User not review owner or exchange admin')


def new_check_perms_for_adding_comment(review_id: int,
                                       user_id: int):
    time_delta = timedelta(minutes=5)

    if not Guest.objects.filter(tg_id=user_id).exists():
        raise HTTPException(status_code=404,
                             detail='User don`t exists in DB')
    
    # check_exchage_marker(exchange_marker)

    # match exchange_marker:
    #     case 'no_cash':
    #         comment_model = no_cash_models.Comment
    #         review_model = no_cash_models.Review
    #     case 'cash':
    #         comment_model = cash_models.Comment
    #         review_model = cash_models.Review
    #     case 'partner':
    #         comment_model = partner_models.Comment
    #         review_model = partner_models.Review
    #     case 'both':
    #         comment_model = no_cash_models.Comment
    #         review_model = no_cash_models.Review


    review_query = NewBaseReview.objects.select_related('guest')\
                                    .filter(pk=review_id)
    review = review_query.first()
    
    if not review_query.exists():
        raise HTTPException(status_code=400,
                        detail='Review not found')
    
    if review_query.filter(guest_id=user_id).exists() or \
        ExchangeAdmin.objects.filter(user_id=user_id,
                                     exchange_name=review.exchange_name):
        check_time = datetime.now() - time_delta

        comment = NewBaseComment.objects.select_related('guest',
                                                    'review')\
                                        .filter(review_id=review_id,
                                                guest_id=user_id,
                                                time_create__gt=check_time)\
                                        .order_by('-time_create')\
                                        .first()

        if comment:
            next_time_comment = comment.time_create.astimezone() + time_delta
            comment_exception_json(status_code=423,
                                   param=next_time_comment.strftime('%d.%m.%Y %H:%M'))

        return {'status': 'success'}

    else:
        raise HTTPException(status_code=404,
                             detail='User not review owner or exchange admin')


def generate_valute_for_schema(valute: Valute):
    valute.icon = try_generate_icon_url(valute)
    
    valute.multiple_name = MultipleName(
                            name=valute.name,
                            en_name=valute.en_name
                                    )
    valute.multiple_type = MultipleName(
                            name=valute.type_valute,
                            en_name=en_type_valute_dict[valute.type_valute]
                                    )
    return valute


def check_valute_on_cash(valute_from: str,
                         valute_to: str):
    return Valute.objects.filter(code_name__in=(valute_from,valute_to),
                                 type_valute__in=('Наличные', 'ATM QR'))\
                            .exists()


def new_check_valute_on_cash(valute_from: str,
                             valute_to: str):
    return NewValute.objects.filter(code_name__in=(valute_from,valute_to),
                                 type_valute__in=('Наличные', 'ATM QR'))\
                            .exists()


async def pust_to_send_bot(user_id: int,
                           order_id: int,
                           marker: str):
    try:
        _url = f'https://api.moneyswap.online/send_to_tg_group?user_id={user_id}&order_id={order_id}&marker={marker}'
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession() as session:
            async with session.get(_url,
                                timeout=timeout) as response:
                pass
    except Exception as ex:
        print(ex)
        pass


async def send_review_notifitation(review_id: int):
    _url = f'https://api.moneyswap.online/send_to_tg_group_review?review_id={review_id}'
    timeout = aiohttp.ClientTimeout(total=5)
    async with aiohttp.ClientSession() as session:
        async with session.get(_url,
                            timeout=timeout) as response:
            pass


async def new_send_review_notifitation(review_id: int):
    _url = f'https://api.moneyswap.online/new_send_to_tg_group_review?review_id={review_id}'
    timeout = aiohttp.ClientTimeout(total=5)
    async with aiohttp.ClientSession() as session:
        async with session.get(_url,
                            timeout=timeout) as response:
            pass


async def send_comment_notifitation(comment_id: int):
    _url = f'https://api.moneyswap.online/send_to_tg_group_comment?comment_id={comment_id}'
    timeout = aiohttp.ClientTimeout(total=5)
    async with aiohttp.ClientSession() as session:
        async with session.get(_url,
                            timeout=timeout) as response:
            pass


async def new_send_comment_notifitation(comment_id: int):
    _url = f'https://api.moneyswap.online/new_send_to_tg_group_comment?comment_id={comment_id}'
    timeout = aiohttp.ClientTimeout(total=5)
    async with aiohttp.ClientSession() as session:
        async with session.get(_url,
                            timeout=timeout) as response:
            pass


async def send_review_notifitation_to_exchange_admin(user_id: int,
                                                     exchange_id: int,
                                                     exchange_marker: str,
                                                     review_id: int):
    _url = f'https://api.moneyswap.online/send_notification_to_exchange_admin?user_id={user_id}&exchange_id={exchange_id}&exchange_marker={exchange_marker}&review_id={review_id}'
    timeout = aiohttp.ClientTimeout(total=5)
    async with aiohttp.ClientSession() as session:
        async with session.get(_url,
                            timeout=timeout) as response:
            pass


async def new_send_review_notifitation_to_exchange_admin(user_id: int,
                                                         exchange_id: int,
                                                         review_id: int):
    _url = f'https://api.moneyswap.online/new_send_notification_to_exchange_admin?user_id={user_id}&exchange_id={exchange_id}&review_id={review_id}'
    timeout = aiohttp.ClientTimeout(total=5)
    async with aiohttp.ClientSession() as session:
        async with session.get(_url,
                            timeout=timeout) as response:
            pass


async def send_comment_notifitation_to_exchange_admin(user_id: int,
                                                      exchange_id: int,
                                                      exchange_marker: str,
                                                      review_id: int):
    _url = f'https://api.moneyswap.online/send_comment_notification_to_exchange_admin?user_id={user_id}&exchange_id={exchange_id}&exchange_marker={exchange_marker}&review_id={review_id}'
    timeout = aiohttp.ClientTimeout(total=5)
    async with aiohttp.ClientSession() as session:
        async with session.get(_url,
                            timeout=timeout) as response:
            pass


async def new_send_comment_notifitation_to_exchange_admin(user_id: int,
                                                          exchange_id: int,
                                                          review_id: int):
    _url = f'https://api.moneyswap.online/new_send_comment_notification_to_exchange_admin?user_id={user_id}&exchange_id={exchange_id}&review_id={review_id}'
    timeout = aiohttp.ClientTimeout(total=5)
    async with aiohttp.ClientSession() as session:
        async with session.get(_url,
                            timeout=timeout) as response:
            pass



async def send_comment_notifitation_to_review_owner(user_id: int,
                                                    exchange_id: int,
                                                    exchange_marker: str,
                                                    review_id: int):
    _url = f'https://api.moneyswap.online/send_comment_notification_to_review_owner?user_id={user_id}&exchange_id={exchange_id}&exchange_marker={exchange_marker}&review_id={review_id}'
    timeout = aiohttp.ClientTimeout(total=5)
    async with aiohttp.ClientSession() as session:
        async with session.get(_url,
                            timeout=timeout) as response:
            pass


async def new_send_comment_notifitation_to_review_owner(user_id: int,
                                                        exchange_id: int,
                                                        review_id: int):
    _url = f'https://api.moneyswap.online/new_send_comment_notification_to_review_owner?user_id={user_id}&exchange_id={exchange_id}&review_id={review_id}'
    timeout = aiohttp.ClientTimeout(total=5)
    async with aiohttp.ClientSession() as session:
        async with session.get(_url,
                            timeout=timeout) as response:
            pass