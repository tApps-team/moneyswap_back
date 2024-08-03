from typing import List
from datetime import datetime, timedelta
from math import ceil
from random import choice, shuffle

from django.db.models import Count, Q, OuterRef, Subquery
from django.db import connection
from django.core.exceptions import ObjectDoesNotExist

from fastapi import APIRouter, Request, Depends, HTTPException

from general_models.models import Valute, BaseAdminComment, en_type_valute_dict

import no_cash.models as no_cash_models
from no_cash.endpoints import no_cash_valutes, no_cash_exchange_directions, no_cash_valutes_2

import cash.models as cash_models
from cash.endpoints import  cash_valutes, cash_exchange_directions, cash_valutes_2
from cash.schemas import SpecialCashDirectionMultiModel, CityModel
from cash.models import Direction, Country, Exchange, Review

import partners.models as partner_models

from .utils.query_models import AvailableValutesQuery, SpecificDirectionsQuery
from .utils.http_exc import http_exception_json, review_exception_json
from .utils.endpoints import (check_exchage_marker,
                              check_perms_for_adding_review,
                              try_generate_icon_url,
                              generate_valute_for_schema)

from .schemas import (PopularDirectionSchema,
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
                      MultipleName)


common_router = APIRouter(tags=['Общее'])

#
review_router = APIRouter(prefix='/reviews',
                          tags=['Отзывы'])
#


# Эндпоинт для получения доступных валют
@common_router.get('/available_valutes',
                   response_model=dict[str, dict[str, list[ValuteModel | EnValuteModel]]],
                   response_model_by_alias=False)
def get_available_valutes(request: Request,
                          query: AvailableValutesQuery = Depends()):
    params = query.params()
    if not params['city']:
        json_dict = no_cash_valutes(request, params)
    else:
        json_dict = cash_valutes(request, params)
    
    return json_dict

#
@common_router.get('/available_valutes_2')
def get_available_valutes(request: Request,
                          query: AvailableValutesQuery = Depends()):
    params = query.params()
    if not params['city']:
        json_dict = no_cash_valutes_2(request, params)
    else:
        json_dict = cash_valutes_2(request, params)
    
    return json_dict
#


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
@common_router.get('/directions',
                 response_model=List[SpecialCashDirectionMultiModel | SpecialDirectionMultiModel],
                 response_model_by_alias=False)
def get_current_exchange_directions(request: Request,
                                    query: SpecificDirectionsQuery = Depends()):
    params = query.params()
    if not params['city']:
        json_dict = no_cash_exchange_directions(request, params)
    else:
        json_dict = cash_exchange_directions(request, params)
    
    return json_dict


@common_router.get('/popular_directions',
                   response_model=list[PopularDirectionSchema],
                   response_model_by_alias=False)
def get_popular_directions(exchange_marker: str,
                           limit: int = None):
    limit = 9 if limit is None else limit
    print(len(connection.queries))
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
    print(connection.queries)
    print(len(connection.queries))

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
        # direction_model = no_cash_models.Direction
        # similar_direction_filter = Q(valute_from_id=valute_from) | Q(valute_to_id=valute_to)

        # similar_directions = direction_model.objects.select_related('valute_from',
        #                                                             'valute_to')\
        #                                             .exclude(valute_from_id=valute_from,
        #                                                      valute_to_id=valute_to)\
        #                                             .filter(similar_direction_filter)\
        #                                             .all()[:limit]
        direction_model = no_cash_models.ExchangeDirection
        similar_direction_filter = Q(direction__valute_from_id=valute_from,
                                     exchange__is_active=True,
                                     is_active=True) \
                                    | Q(direction__valute_to_id=valute_to,
                                        exchange__is_active=True,
                                        is_active=True)

        similar_directions = direction_model.objects.select_related('direction',
                                                                    'exchange')\
                                                    .exclude(direction__valute_from_id=valute_from,
                                                             direction__valute_to_id=valute_to)\
                                                    .filter(similar_direction_filter)\
                                                    .all()[:limit]

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
                                             exchange__is_active=True,
                                             is_active=True)\
                                         | Q(direction__valute_to=valute_to,
                                             city__city__code_name=city,
                                             exchange__is_active=True,
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
                                                                                       'exchange,'
                                                                                       'city',
                                                                                       'city__city')\
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
    print(len(connection.queries))
    valute_from, valute_to, city = [el.upper() for el in (valute_from, valute_to, city)]

    direction_model = cash_models.ExchangeDirection
    partner_direction_model = partner_models.Direction

    city_model = cash_models.City.objects.select_related('country')\
                                        .get(code_name=city)


    similar_cities = direction_model.objects.select_related('direction',
                                                            'city')\
                                                .exclude(city__code_name=city)\
                                                .filter(direction__valute_from=valute_from,
                                                        direction__valute_to=valute_to)\
                                                .values_list('city__pk', flat=True)\
                                                .all()
    
    similar_partner_cities = partner_direction_model.objects.select_related('direction',
                                                                            'city',
                                                                            'city__city')\
                                                            .exclude(city__city__code_name=city)\
                                                            .filter(direction__valute_from=valute_from,
                                                                    direction__valute_to=valute_to)\
                                                            .values_list('city__city__pk',
                                                                         flat=True)\
                                                            .all()
    
    similar_city_pks = similar_cities.union(similar_partner_cities)
    print(similar_city_pks)

    exchange_count_filter = Q(cash_directions__direction__valute_from=valute_from,
                              cash_directions__direction__valute_to=valute_to,
                              cash_directions__is_active=True)
    partner_exchange_count_filter = Q(partner_cities__partner_directions__direction__valute_from=valute_from,
                                      partner_cities__partner_directions__direction__valute_to=valute_to,
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
    print(len(connection.queries))
    # print(connection.queries[-1])
    # 4 queries
    return cities


# Эндпоинт для получения актуального курса обмена
# для выбранного направления
@common_router.get('/actual_course')
def get_actual_course_for_direction(valute_from: str, valute_to: str):
    direction = Direction.objects\
                            .get(display_name=f'{valute_from.upper()} -> {valute_to.upper()}')
    return direction.actual_course


# Эндпоинт для получения списка отзывов
# для определённого обменника
@review_router.get('/reviews_by_exchange',
                   response_model=ReviewsByExchangeSchema)
def get_reviews_by_exchange(exchange_id: int,
                            exchange_marker: str,
                            page: int,
                            element_on_page: int = None,
                            grade_filter: int = None):
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
                                            moderation=True)\
                                    .order_by('-time_create')
    
    pages = 1 if element_on_page is None else ceil(len(reviews) / element_on_page)

    # if element_on_page:
    #     pages = ceil(len(reviews) / element_on_page)


    # if element_on_page:
    #     pages = len(reviews) // element_on_page

    #     if len(reviews) % element_on_page != 0:
    #         pages += 1
    
    if grade_filter is not None:
        reviews = reviews.filter(grade=str(grade_filter))

    # reviews = reviews.all() if grade_filter is None\
    #              else reviews.filter(grade=str(grade_filter)).all()

    reviews = reviews.all()


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


# @review_router.get('/popular_directions',
#                    response_model=list[PopularDirectionSchema],
#                    response_model_by_alias=False)
# def get_popular_directions(exchange_marker: str,
#                            limit: int = None):
#     if exchange_marker == 'no_cash':
#         directions = no_cash_models.PopularDirection\
#                                             .objects\
#                                             .get(name='Безналичные популярные направления')\
#                                             .directions\
#                                             .select_related('valute_from',
#                                                             'valute_to')\
#                                             .order_by('-popular_count')\
#                                             .all()
#         print(directions)
#         res = []
#         for direction in directions:
#             valute_from = direction.valute_from
#             valute_from.icon = try_generate_icon_url(valute_from)
#             print(valute_from.icon)
#             valute_from.multiple_name = MultipleName(
#                                     name=valute_from.name,
#                                     en_name=valute_from.en_name
#                                             )
#             valute_from.multiple_type = MultipleName(
#                                     name=valute_from.type_valute,
#                                     en_name=en_type_valute_dict[valute_from.type_valute]
#                                             )
#             valute_to = direction.valute_to
#             valute_to.icon = try_generate_icon_url(valute_to)
#             valute_to.multiple_name = MultipleName(
#                                         name=valute_to.name,
#                                         en_name=valute_to.en_name
#                                         )
#             valute_to.multiple_type = MultipleName(
#                                         name=valute_to.type_valute,
#                                         en_name=en_type_valute_dict[valute_to.type_valute]
#                                         )
#             res.append(PopularDirectionSchema(valute_from=valute_from.__dict__,
#                                               valute_to=valute_to.__dict__))
#             # print(direction.__dict__)
        
#         return res