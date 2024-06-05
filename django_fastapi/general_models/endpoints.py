from typing import List
from datetime import datetime, timedelta
from math import ceil

from django.db.models import Count
from django.db import connection

from fastapi import APIRouter, Request, Depends, HTTPException

from general_models.models import Valute, BaseAdminComment

import no_cash.models as no_cash_models
from no_cash.endpoints import no_cash_valutes, no_cash_exchange_directions

import cash.models as cash_models
from cash.endpoints import  cash_valutes, cash_exchange_directions
from cash.schemas import SpecialCashDirectionMultiModel
from cash.models import Direction, Country, Exchange, Review

import partners.models as partner_models

from .utils.query_models import AvailableValutesQuery, SpecificDirectionsQuery
from .utils.http_exc import http_exception_json, review_exception_json
from .utils.endpoints import check_exchage_marker, check_perms_for_adding_review

from .schemas import (ValuteModel,
                      EnValuteModel,
                      SpecialDirectionMultiModel,
                      ReviewViewSchema,
                      ReviewsByExchangeSchema,
                      AddReviewSchema,
                      CommentSchema,
                      CommentRoleEnum)


common_router = APIRouter(tags=['Общее'])

#
review_router = APIRouter(prefix='/reviews',
                          tags=['Отзывы'])
#


# Эндпоинт для получения доступных валют
@common_router.get('/available_valutes',
                 response_model=dict[str, dict[str, List[ValuteModel | EnValuteModel]]])
def get_available_valutes(request: Request,
                          query: AvailableValutesQuery = Depends()):
    params = query.params()
    if not params['city']:
        json_dict = no_cash_valutes(request, params)
    else:
        json_dict = cash_valutes(request, params)
    
    return json_dict


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