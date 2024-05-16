from typing import List
from datetime import datetime, timedelta

from django.db import connection

from fastapi import APIRouter, Request, Depends, HTTPException

from general_models.models import Valute

import no_cash.models as no_cash_models
from no_cash.endpoints import no_cash_valutes, no_cash_exchange_directions

import cash.models as cash_models
from cash.endpoints import  cash_valutes, cash_exchange_directions
from cash.schemas import SpecialCashDirectionMultiModel
from cash.models import Direction, Country, Exchange, Review

import partners.models as partner_models

from .utils.query_models import AvailableValutesQuery, SpecificDirectionsQuery
from .utils.http_exc import http_exception_json, review_exception_json

from .schemas import ValuteModel, EnValuteModel, SpecialDirectionMultiModel, ReviewViewSchema, ReviewsByExchangeSchema, AddReviewSchema


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
                            element_on_page: int = None):
    match exchange_marker:
        case 'no_cash':
            review_model = no_cash_models.Review
        case 'cash':
            review_model = cash_models.Review
        case 'partner':
            review_model = partner_models.Review  

    reviews = review_model.objects.select_related('guest')\
                                    .filter(exchange_id=exchange_id)\
                                    .all()
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
                                   element_on_page=len(review_list),
                                   content=review_list)


# Эндпоинт для добавления нового отзыва
# для определённого обменника
@review_router.post('/add_review_by_exchange')
def add_review_by_exchange(review: AddReviewSchema):
    
    match review.exchange_marker:
        case 'no_cash':
            review_model = no_cash_models.Review
        case 'cash':
            review_model = cash_models.Review
        case 'partner':
            review_model = partner_models.Review
    try:
        review_model.objects.create(
            exchange_id=review.exchange_id,
            guest_id=review.tg_id,
            grade=review.grade,
            text=review.text
            )
    except Exception:
        raise HTTPException(status_code=400)
    else:
        return {'status': 'success'}


# Эндпоинт для проверки пользователя,
# может ли он добавить новый отзыв
# для опеределённого обменника (один в день)
@review_router.get('/check_user_review_permission')
def check_user_review_permission(exchange_id: int,
                                 exchange_marker: str,
                                 tg_id: int):
    time_delta = timedelta(days=1)

    match exchange_marker:
        case 'no_cash':
            review_model = no_cash_models.Review
        case 'cash':
            review_model = cash_models.Review
        case 'partner':
            review_model = partner_models.Review

    check_time = datetime.now() - time_delta

    review = review_model.objects.select_related('guest')\
                                    .filter(exchange_id=exchange_id,
                                            guest_id=tg_id,
                                            time_create__gt=check_time)\
                                    .first()

    if review:
        next_time_review = review.time_create.astimezone() + time_delta
        review_exception_json(status_code=423,
                              param=next_time_review.strftime('%d.%m.%Y %H:%M'))

    
    return {'status': 'success'}