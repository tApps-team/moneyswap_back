import functools
from typing import Union

from django.core.cache import cache
from django.db.models import Prefetch, Subquery, OuterRef
from django.db import connection

from bs4 import BeautifulSoup

from cash import models as cash_models
from no_cash import models as no_cash_models


def get_exchange_list(marker: str = None):
    match marker:
        case 'no_cash':
            exchange_list = cash_models.Exchange.objects.values('name').all()
        case 'cash':
            exchange_list = no_cash_models.Exchange.objects.values('name').all()
        case _:
            cash_exchange_list = cash_models.Exchange.objects.values('name').all()
            no_cash_exchange_list = no_cash_models.Exchange.objects.values('name').all()
            exchange_list = cash_exchange_list.union(no_cash_exchange_list)

    return exchange_list


def make_valid_values_for_dict(dict_for_exchange_direction: dict):
    in_count = abs(float(dict_for_exchange_direction['in_count']))
    out_count = abs(float(dict_for_exchange_direction['out_count']))
    
    if in_count != 1:
        out_count = out_count / in_count
        in_count = 1

    if out_count < 1:
        in_count = 1 / out_count
        out_count = 1

    if fromfee := dict_for_exchange_direction.get('fromfee'):
        if in_count == 1:
            defferent = out_count / 100 * fromfee
            out_count = out_count - defferent
        else:
            defferent = in_count / 100 * fromfee
            in_count = in_count - defferent  
    
    dict_for_exchange_direction['in_count'] = in_count
    dict_for_exchange_direction['out_count'] = out_count


def make_valid_partner_values_for_dict(dict_for_exchange_direction: dict):
    in_count = abs(float(dict_for_exchange_direction['in_count']))
    out_count = abs(float(dict_for_exchange_direction['out_count']))
    
    if in_count != 1:
        out_count = out_count / in_count
        in_count = 1

    if out_count < 1:
        in_count = 1 / out_count
        out_count = 1

    if fromfee := dict_for_exchange_direction.get('fromfee'):
        if in_count == 1:
            defferent = out_count / 100 * fromfee
            out_count = out_count - defferent
        else:
            defferent = in_count / 100 * fromfee
            in_count = in_count - defferent  
    
    dict_for_exchange_direction['in_count'] = in_count
    dict_for_exchange_direction['out_count'] = out_count


#Type hinting for 'try_update_courses' function
direction_union = Union[no_cash_models.Direction,
                        cash_models.Direction]
exchange_direction_union = Union[no_cash_models.ExchangeDirection,
                                 cash_models.ExchangeDirection]


# def try_update_courses(direction_model: direction_union,
#                        exchange_direction_model: exchange_direction_union):
#     bulk_update_fields = ['actual_course']
    
#     if direction_model == cash_models.Direction:
#         bulk_update_fields.append('previous_course')
    
#     prefetch_no_cash_queryset = exchange_direction_model.objects\
#                                                     .select_related('exchange')\
#                                                     .filter(is_active=True,
#                                                             exchange__is_active=True)\
#                                                     .order_by('-out_count',
#                                                               'in_count')
    
#     prefetch_filter = Prefetch('exchange_directions',
#                                 prefetch_no_cash_queryset)
#     directions_with_prefetch = direction_model.objects\
#                                         .prefetch_related(prefetch_filter)\
#                                         .all()

#     update_list = []

#     for direction in directions_with_prefetch:
#         best_exchange_direction = direction.exchange_directions.first()

#         if best_exchange_direction:

#             in_count = best_exchange_direction.in_count
#             out_count = best_exchange_direction.out_count

#             if in_count and out_count:

#                 if out_count == 1:
#                     actual_course = out_count / in_count
#                 else:
#                     actual_course = out_count

#                 if direction.valute_to_id == 'CASHUSD':
#                     # print('actual',direction.actual_course)
#                     direction.previous_course = direction.actual_course
#                     # print('previous',direction.previous_course)

#                 else:
#                     if direction_model == cash_models.Direction:
#                         direction.previous_course = None
#                     # print( direction.previous_course)
#                     # bulk_update_fileds.append('previous_course')
#                 # else:
#                 #     direction.previous_course = direction.actual_course

#                 direction.actual_course = actual_course
#         else:
#             direction.actual_course = None

#         # if direction.valute_to_id == 'CASHUSD':
#         #     print('previous',direction.previous_course)

#         update_list.append(direction)

#     direction_model.objects.bulk_update(update_list,
#                                         bulk_update_fields,
#                                         batch_size=1000)
#     # print(connection.queries)



def try_update_courses(direction_model: direction_union,
                       exchange_direction_model: exchange_direction_union):
    """
    Обновляет курсы для направлений.
    Теперь вместо prefetch_related используется Subquery,
    что позволяет доставать только лучший курс из exchange_directions.
    """

    bulk_update_fields = ['actual_course']
    if direction_model == cash_models.Direction:
        bulk_update_fields.append('previous_course')

    # подзапрос для лучшего направления обмена
    best_exchange_qs = exchange_direction_model.objects.filter(
        direction_id=OuterRef('pk'),
        is_active=True,
        exchange__is_active=True,
    ).order_by('-out_count', 'in_count')

    # добавляем поля best_in_count / best_out_count прямо в queryset
    directions = direction_model.objects.annotate(
        best_in_count=Subquery(best_exchange_qs.values('in_count')[:1]),
        best_out_count=Subquery(best_exchange_qs.values('out_count')[:1]),
    )

    update_list = []

    for direction in directions:
        in_count = direction.best_in_count
        out_count = direction.best_out_count

        actual_course = None
        if in_count and out_count:
            if out_count == 1:
                actual_course = out_count / in_count
            else:
                actual_course = out_count

        # логика previous_course
        if direction.valute_to_id == 'CASHUSD':
            direction.previous_course = direction.actual_course
        elif direction_model == cash_models.Direction:
            direction.previous_course = None

        direction.actual_course = actual_course
        update_list.append(direction)

    # массовое обновление
    direction_model.objects.bulk_update(
        update_list,
        bulk_update_fields,
        batch_size=1000
    )