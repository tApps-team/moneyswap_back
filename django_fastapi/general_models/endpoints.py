import json
import re

from time import time
from typing import List, Union, Literal
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from math import ceil
from random import choice, shuffle, randint
from collections import Counter

from asgiref.sync import async_to_sync

from django.db.models import Count, Q, OuterRef, Subquery, F, Prefetch, Sum, Value, IntegerField
from django.db.models.functions import Coalesce
from django.db import connection, transaction
from django.db.utils import IntegrityError
from django.core.exceptions import ObjectDoesNotExist

from django.utils import timezone

from fastapi import APIRouter, Request, Depends, HTTPException

from .utils.endpoints import get_valute_json
from general_models.models import (ExchangeAdmin,
                                   NewBaseAdminComment,
                                   NewBaseComment,
                                   NewBaseReview,
                                   Valute,
                                   Guest,
                                   FeedbackForm,
                                   #
                                   NewValute,
                                   Exchanger,
                                   Review,
                                   Comment,
                                   AdminComment,
                                   ExchangeAdminOrder,
                                   NewExchangeAdmin,
                                   NewExchangeAdminOrder,
                                   ExchangeLinkCount,
                                   en_type_valute_dict)
from general_models.utils.endpoints import (availabale_active_status_list,
                                            get_exchange,
                                            get_review_count_dict)
from general_models.utils.base import annotate_number_field, annotate_string_field


import no_cash.models as no_cash_models
from no_cash.endpoints import (no_cash_exchange_directions,
                               test_no_cash_exchange_directions,
                               no_cash_valutes,
                               no_cash_valutes_3)

import cash.models as cash_models
from cash.endpoints import (cash_valutes,
                            cash_exchange_directions,
                            test_cash_exchange_directions,
                            cash_valutes_3)
from cash.schemas import (NewSpecialCashDirectionMultiPrtnerExchangeRatesWithLocationModel,
                          ExtendedSpecialCashDirectionMultiPrtnerExchangeRatesWithLocationModel,
                          NewSpecialCashDirectionMultiPrtnerWithExchangeRatesWithAmlModel,
                          ExtendedSpecialCashDirectionMultiPrtnerWithExchangeRatesWithAmlModel,
                          NewSpecialCashDirectionMultiWithAmlModel,
                          ExtendedSpecialCashDirectionMultiWithAmlModel,
                          NewSpecialCashDirectionMultiWithLocationModel,
                          ExtendedSpecialCashDirectionMultiWithLocationModel,
                          CityModel)
from cash.models import Direction, Country, Exchange

import partners.models as partner_models

from partners.utils.endpoints import generate_actual_course

from .periodic_tasks import manage_periodic_task_for_parse_directions

from .utils.query_models import AvailableValutesQuery, SpecificDirectionsQuery
from .utils.endpoints import (check_exchage_by_name,
                              check_exchange_direction_by_exchanger,
                              check_perms_for_adding_comment,
                              check_perms_for_adding_review,
                              get_base_url,
                              get_exchange_dircetions_dict_tuple,
                              new_get_exchange_directions_count_dict,
                              get_exchange_with_direction_count,
                              new_check_perms_for_adding_comment,
                              new_check_perms_for_adding_review,
                              new_generate_top_exchanges_query_by_model,
                              new_send_comment_notifitation,
                              new_send_review_notifitation,
                              pust_to_send_bot,
                              send_comment_notifitation,
                              try_generate_icon_url,
                              generate_valute_for_schema,
                              get_exchange_directions,
                              generate_image_icon2,
                              generate_coin_for_schema,
                              send_review_notifitation)

from .schemas import (NewAddCommentSchema,
                      NewAddReviewSchema,
                      ExchangeListElementSchema,
                      NewExchangeLinkCountSchema,
                      NewReviewsByExchangeSchema,
                      NewSiteMapDirectonSchema2,
                      NewSpecialDirectionMultiWithAmlModel,
                      ExtendedSpecialDirectionMultiWithAmlModel,
                      NewSpecialPartnerNoCashDirectionSchema,
                      ExtendedSpecialPartnerNoCashDirectionSchema,
                      NewTopExchangeSchema,
                      PopularDirectionSchema,
                      ValuteModel,
                      ReviewViewSchema,
                      ReviewsByExchangeSchema,
                      AddReviewSchema,
                      CommentSchema,
                      CommentRoleEnum,
                      MultipleName,
                      ReviewCountSchema,
                      DetailExchangeSchema,
                      DirectionSideBarSchema,
                      ExchangeLinkCountSchema,
                      TopCoinSchema,
                      FeedbackFormSchema,
                      NewSpecificValuteSchema,
                      NewBlackListExchangeSchema,
                      BlackExchangeDetailSchema,
                      IncreasePopularCountSchema,
                      IncreaseExchangeLinkCountSchema)

from config import DEV_HANDLER_SECRET


common_router = APIRouter(tags=['Общее'])

#new common router
new_common_router = APIRouter(tags=['Общее (НОВЫЕ)'])


test_router = APIRouter(prefix='/test',
                          tags=['Общее(Changed)'])

#
review_router = APIRouter(prefix='/reviews',
                          tags=['Отзывы'])

#new review router
new_review_router = APIRouter(prefix='/reviews',
                          tags=['Отзывы (НОВЫЕ)'])
#


################################################################################################
# СИСТЕМНЫЕ АПИ РУЧКИ ДЛЯ ПЕРЕНОСА ДАННЫХ ИЗ СТАРЫХ ТАБЛИЦ В НОВЫЕ ( РЕДИЗАЙН БД )

# @test_router.get('/recreate_valute_records')
def recreate_valute_records(secret: str):
    if secret != DEV_HANDLER_SECRET:
        raise HTTPException(status_code=400)
    
    create_list = []
    for valute in Valute.objects.all():
        _d = valute.__dict__
        _d.pop('_state')
        create_list.append(NewValute(**_d))

    try:
        NewValute.objects.bulk_create(create_list)
    except Exception as ex:
        res = 'ERROR'
        print(ex)
    else:
        res = 'VALUTES ADDED!!!'
        print(res)
    
    return res


# @test_router.get('/recreate_directions_records')
def recreate_directions_records(secret: str):
    if secret != DEV_HANDLER_SECRET:
        raise HTTPException(status_code=400)

    no_cash_create_list = []
    for direction in no_cash_models.Direction.objects.select_related('valute_from',
                                                                      'valute_to').all():
        _d = direction.__dict__
        _d.pop('_state')
        _d.pop('id')
        no_cash_create_list.append(no_cash_models.NewDirection(**_d))

    try:
        no_cash_models.NewDirection.objects.bulk_create(no_cash_create_list)
    except Exception as ex:
        res = 'NO CASH DIRECTION ERROR'
        print(ex)
        return res

    cash_create_list = []
    for direction in cash_models.Direction.objects.select_related('valute_from',
                                                                      'valute_to').all():
        _d = direction.__dict__
        _d.pop('_state')
        _d.pop('id')
        _d.pop('display_name')
        cash_create_list.append(cash_models.NewDirection(**_d))

    try:
        cash_models.NewDirection.objects.bulk_create(cash_create_list)
    except Exception as ex:
        res = 'CASH DIRECTION ERROR'
        print(ex)
        return res
    else:
        res = 'NO CASH AND CASH DIRECTION ADDED!!!'
        print(res)

    return res



def parse_relative_date(text: str):
    """
    Преобразует строку вроде '1 год 3 месяца', '3 месяца', '2 года'
    в datetime.
    """
    years, months = 0, 0

    # ищем годы
    match_years = re.search(r"(\d+)\s*(год|года|лет)", text)
    if match_years:
        years = int(match_years.group(1))

    # ищем месяцы
    match_months = re.search(r"(\d+)\s*(месяц|месяца|месяцев)", text)
    if match_months:
        months = int(match_months.group(1))

    return timezone.now() - relativedelta(years=years, months=months)


def format_relative_date(dt: datetime) -> str:
    """
    Преобразует datetime в строку вроде '1 год 3 месяца', '3 месяца', '2 года'.
    От текущего времени (timezone.now()).
    """
    now = timezone.now().today()
    
    delta = relativedelta(now, dt)

    years = delta.years
    months = delta.months

    parts = []

    # склонения для лет
    if years:
        if years % 10 == 1 and years % 100 != 11:
            parts.append(f"{years} год")
        elif 2 <= years % 10 <= 4 and not (12 <= years % 100 <= 14):
            parts.append(f"{years} года")
        else:
            parts.append(f"{years} лет")

    # склонения для месяцев
    if months:
        if months % 10 == 1 and months % 100 != 11:
            parts.append(f"{months} месяц")
        elif 2 <= months % 10 <= 4 and not (12 <= months % 100 <= 14):
            parts.append(f"{months} месяца")
        else:
            parts.append(f"{months} месяцев")

    # если совсем ничего нет — значит "0 месяцев"
    if not parts:
        return "0 месяцев"

    return " ".join(parts)


# @test_router.get('/recreate_exchanger_records')
def recreate_exchanger_records(secret: str):
    if secret != DEV_HANDLER_SECRET:
        raise HTTPException(status_code=400)
    
    create_list = []
    exchange_name_set = set()
    for exchange_model in (no_cash_models.Exchange,
                           cash_models.Exchange,
                           partner_models.Exchange):
        for exchange in exchange_model.objects.all():
            if exchange.en_name not in exchange_name_set:
                
                exchange_name_set.add(exchange.en_name)
                # _d = model_to_dict(exchange)

                # if isinstance(exchange, partner_models.Exchange):
                #     _d.pop('id')
                _d = exchange.__dict__
                _d.pop('_state')
                _d.pop('id')
                if _d.get('age'):
                    _d['age'] = parse_relative_date(_d['age'])
                
                # _d['id'] = _id
                # print(_d)
                create_list.append(Exchanger(**_d))

    try:
        # Exchanger.objects.bulk_create(create_list)
        for exchanger in create_list:
            exchanger.save(force_insert=True)
    except Exception as ex:
        print(ex)
        res = 'ERROR'
    else:
        res = 'EXCHANGERS ADDED!!!'
        # print('len unique set', len(exchange_name_set))
        print(res)

    return res


@test_router.get('/recreate_auto_no_cash_links_records')
def recreate_auto_no_cash_links_records(secret: str):
    if secret != DEV_HANDLER_SECRET:
        raise HTTPException(status_code=400)
    
    create_list = []

    exchanger_dict = {e.en_name: e.pk for e in Exchanger.objects.all()}
    no_cash_exchange_direction_dict = {(d.direction.valute_from_id, d.direction.valute_to_id, d.exchange_id): d.pk\
                                        for d in no_cash_models.NewExchangeDirection.objects.select_related('direction').all()}

    for exchange_link in no_cash_models.ExchangeLinkCount.objects.select_related('exchange',
                                                                                 'exchange_direction',
                                                                                 'exchange_direction__direction').all():
        try:
            exchange_en_name = exchange_link.exchange.en_name
        except Exception:
            continue
        else:
            valute_from_id = exchange_link.exchange_direction.direction.valute_from_id
            valute_to_id = exchange_link.exchange_direction.direction.valute_to_id
            # city_id = exchange_link.exchange_direction.city_id

            if exchange_id := exchanger_dict.get(exchange_en_name):
                exchange_direction_dict_key = (valute_from_id, valute_to_id, exchange_id)

                if exchange_direction_id := no_cash_exchange_direction_dict.get(exchange_direction_dict_key):
                    data = {
                        'user_id': exchange_link.user_id,
                        'count': exchange_link.count,
                        'exchange_id': exchange_id,
                        'exchange_direction_id': exchange_direction_id,
                    }

                    create_list.append(no_cash_models.NewExchangeLinkCount(**data))
    try:
        _list = no_cash_models.NewExchangeLinkCount.objects.bulk_create(create_list,
                                                                ignore_conflicts=True)
        print(len(_list))
    except Exception as ex:
        print(ex)
        res = 'ERROR'
    else:
        res = 'EXCHANGER NO CASH LINKS ADDED!!!'
        print(res)

    return res


@test_router.get('/recreate_auto_cash_links_records')
def recreate_auto_cash_links_records(secret: str):
    if secret != DEV_HANDLER_SECRET:
        raise HTTPException(status_code=400)
    
    create_list = []

    exchanger_dict = {e.en_name: e.pk for e in Exchanger.objects.all()}
    cash_exchange_direction_dict = {(d.direction.valute_from_id, d.direction.valute_to_id, d.city_id, d.exchange_id): d.pk\
                                        for d in cash_models.NewExchangeDirection.objects.select_related('direction').all()}

    for exchange_link in cash_models.ExchangeLinkCount.objects.select_related('exchange',
                                                                                 'exchange_direction',
                                                                                 'exchange_direction__direction').all():
        try:
            exchange_en_name = exchange_link.exchange.en_name
        except Exception:
            continue
        else:
            valute_from_id = exchange_link.exchange_direction.direction.valute_from_id
            valute_to_id = exchange_link.exchange_direction.direction.valute_to_id
            city_id = exchange_link.exchange_direction.city_id

            if exchange_id := exchanger_dict.get(exchange_en_name):
                exchange_direction_dict_key = (valute_from_id, valute_to_id, city_id, exchange_id)

                if exchange_direction_id := cash_exchange_direction_dict.get(exchange_direction_dict_key):
                    data = {
                        'user_id': exchange_link.user_id,
                        'count': exchange_link.count,
                        'exchange_id': exchange_id,
                        'exchange_direction_id': exchange_direction_id,
                    }

                    create_list.append(cash_models.NewExchangeLinkCount(**data))
    try:
        _list = cash_models.NewExchangeLinkCount.objects.bulk_create(create_list,
                                                             ignore_conflicts=True)
        print(len(_list))
    except Exception as ex:
        print(ex)
        res = 'ERROR'
    else:
        res = 'EXCHANGER CASH LINKS ADDED!!!'
        print(res)

    return res


# @test_router.get('/recreate_partner_countries_records')
def recreate_partner_countries_records(secret: str):
    if secret != DEV_HANDLER_SECRET:
        raise HTTPException(status_code=400)
    
    exchanger_dict = {e.en_name: e.pk for e in Exchanger.objects.all()}
    try:
        for partner_country in partner_models.PartnerCountry.objects.select_related('exchange',
                                                                                    'country')\
                                                                    .prefetch_related('exclude_cities',
                                                                                      'working_days').all():
            # if partner_country.exchange.name == 'test_ex':
                _d = partner_country.__dict__
                exchange_en_name = partner_country.exchange.en_name
                new_exchage_id = exchanger_dict.get(exchange_en_name)
                
                if new_exchage_id:
                    _d.pop('_state')
                    _d.pop('id')
                    _d.pop('exchange_id')
                    prefetch_dict: dict = _d.pop('_prefetched_objects_cache')
                    exclude_cities = prefetch_dict.get('exclude_cities')
                    working_days = prefetch_dict.get('working_days')
                    _d['exchange_id'] = new_exchage_id

                    with transaction.atomic():
                        new_partner_country = partner_models.NewPartnerCountry.objects.create(**_d)

                        if exclude_cities:
                            new_partner_country.exclude_cities.add(*exclude_cities)
                        if working_days:
                            new_partner_country.working_days.add(*working_days)

    except Exception as ex:
        print(ex)
        res = 'ERROR'
    else:
        res = 'EXCHANGER PARTNER COUNTRIES ADDED!!!'
        print(res)

    return res


# @test_router.get('/recreate_partner_cities_records')
def recreate_partner_cities_records(secret: str):
    if secret != DEV_HANDLER_SECRET:
        raise HTTPException(status_code=400)
    
    exchanger_dict = {e.en_name: e.pk for e in Exchanger.objects.all()}
    try:
        for partner_country in partner_models.PartnerCity.objects.select_related('exchange',
                                                                                    'city')\
                                                                    .prefetch_related('working_days').all():
            # if partner_country.exchange.name == 'test_ex':
                _d = partner_country.__dict__
                exchange_en_name = partner_country.exchange.en_name
                new_exchage_id = exchanger_dict.get(exchange_en_name)
                
                if new_exchage_id:
                    _d.pop('_state')
                    _d.pop('id')
                    _d.pop('exchange_id')
                    prefetch_dict: dict = _d.pop('_prefetched_objects_cache')
                    # exclude_cities = prefetch_dict.get('exclude_cities')
                    working_days = prefetch_dict.get('working_days')
                    _d['exchange_id'] = new_exchage_id

                    with transaction.atomic():
                        new_partner_country = partner_models.NewPartnerCity.objects.create(**_d)

                        if working_days:
                            new_partner_country.working_days.add(*working_days)

    except Exception as ex:
        print(ex)
        res = 'ERROR'
    else:
        res = 'EXCHANGER PARTNER CITIES ADDED!!!'
        print(res)

    return res


# @test_router.get('/recreate_partner_city_direction_records')
def recreate_partner_city_direction_records(secret: str):
    if secret != DEV_HANDLER_SECRET:
        raise HTTPException(status_code=400)
    
    exchanger_dict = {e.en_name: e.pk for e in Exchanger.objects.all()}

    # try:
    for city_direction in partner_models.Direction.objects.select_related('exchange',
                                                                            'direction',
                                                                        'city',
                                                                        'city__city')\
                                                            .prefetch_related('direction_rates').all():
        # print(city_direction.__dict__)
        # break
        exchange_en_name = city_direction.exchange.en_name
        new_exchange_id = exchanger_dict.get(exchange_en_name)
        
        if new_exchange_id:
            try:
                new_city_id = partner_models.NewPartnerCity.objects.get(city_id=city_direction.city.city_id,
                                                                        exchange_id=new_exchange_id).pk
            except Exception:
                continue
            _valute_from = city_direction.direction.valute_from_id
            _valute_to = city_direction.direction.valute_to_id

            new_direction_id = cash_models.NewDirection.objects.get(valute_from_id=_valute_from,
                                                                    valute_to_id=_valute_to).pk
            # if city_direction.exchange.name == 'test_ex':
            _d = city_direction.__dict__
            _d.pop('_state')
            _d.pop('id')
            _d.pop('exchange_id')
            _d.pop('city_id')
            _d.pop('direction_id')
            prefetch_dict: dict = _d.pop('_prefetched_objects_cache')
            direction_rates = prefetch_dict.get('direction_rates')
            # print(direction_rates)
            _d['exchange_id'] = new_exchange_id
            _d['city_id'] = new_city_id
            _d['direction_id'] = new_direction_id
            # break

            with transaction.atomic():
                new_partner_city_direction = partner_models.NewDirection.objects.create(**_d)

                if direction_rates:
                    direction_rate_list = []
                    for rate in direction_rates:
                        # print(rate.__dict__)
                        rate_dict: dict = rate.__dict__
                        rate_dict.pop('_state')
                        rate_dict.pop('id')
                        rate_dict.pop('exchange_id')
                        rate_dict.pop('exchange_direction_id')
                        rate_dict['exchange_id'] = new_exchange_id
                        rate_dict['exchange_direction_id'] = new_partner_city_direction.pk
                        direction_rate_list.append(partner_models.NewDirectionRate(**rate_dict))
                    
                    partner_models.NewDirectionRate.objects.bulk_create(direction_rate_list)

    # except Exception as ex:
    #     print(ex)
    #     res = ex
    # else:
    res = 'EXCHANGER PARTNER CITY DIRECTIONS WITH DIRECTION RATES ADDED!!!'
    print(res)

    return res


# @test_router.get('/recreate_partner_country_direction_records')
def recreate_partner_country_direction_records(secret: str):
    if secret != DEV_HANDLER_SECRET:
        raise HTTPException(status_code=400)
    
    exchanger_dict = {e.en_name: e.pk for e in Exchanger.objects.all()}

    try:
        for country_direction in partner_models.CountryDirection.objects.select_related('exchange',
                                                                            'country',
                                                                            'country__country')\
                                                                .prefetch_related('direction_rates').all():
            exchange_en_name = country_direction.exchange.en_name
            new_exchange_id = exchanger_dict.get(exchange_en_name)
            
            if new_exchange_id:
                new_country_id = partner_models.NewPartnerCountry.objects.get(country_id=country_direction.country.country_id,
                                                                        exchange_id=new_exchange_id).pk
                # if city_direction.exchange.name == 'test_ex':
                _valute_from = country_direction.direction.valute_from_id
                _valute_to = country_direction.direction.valute_to_id

                new_direction_id = cash_models.NewDirection.objects.get(valute_from_id=_valute_from,
                                                                        valute_to_id=_valute_to).pk
                
                _d = country_direction.__dict__
                _d.pop('_state')
                _d.pop('id')
                _d.pop('exchange_id')
                _d.pop('country_id')
                _d.pop('direction_id')
                prefetch_dict: dict = _d.pop('_prefetched_objects_cache')
                direction_rates = prefetch_dict.get('direction_rates')
                # print(direction_rates)
                _d['exchange_id'] = new_exchange_id
                _d['country_id'] = new_country_id
                _d['direction_id'] = new_direction_id
                # break

                with transaction.atomic():
                    new_partner_country_direction = partner_models.NewCountryDirection.objects.create(**_d)

                    if direction_rates:
                        direction_rate_list = []
                        for rate in direction_rates:
                            # print(rate.__dict__)
                            rate_dict: dict = rate.__dict__
                            rate_dict.pop('_state')
                            rate_dict.pop('id')
                            rate_dict.pop('exchange_id')
                            rate_dict.pop('exchange_direction_id')
                            rate_dict['exchange_id'] = new_exchange_id
                            rate_dict['exchange_direction_id'] = new_partner_country_direction.pk
                            direction_rate_list.append(partner_models.NewCountryDirectionRate(**rate_dict))
                        
                        partner_models.NewCountryDirectionRate.objects.bulk_create(direction_rate_list)

    except Exception as ex:
        print(ex)
        res = 'ERROR'
    else:
        res = 'EXCHANGER PARTNER COUNTRY DIRECTIONS WITH DIRECTION RATES ADDED!!!'
        print(res)

    return res


# @test_router.get('/recreate_partner_noncash_direction_records')
def recreate_partner_noncash_direction_records(secret: str):
    if secret != DEV_HANDLER_SECRET:
        raise HTTPException(status_code=400)
    
    exchanger_dict = {e.en_name: e.pk for e in Exchanger.objects.all()}

    try:
        for noncash_direction in partner_models.NonCashDirection.objects.select_related('exchange')\
                                                                .prefetch_related('direction_rates').all():
            exchange_en_name = noncash_direction.exchange.en_name
            new_exchange_id = exchanger_dict.get(exchange_en_name)
            
            if new_exchange_id:

                _valute_from = noncash_direction.direction.valute_from_id
                _valute_to = noncash_direction.direction.valute_to_id

                new_direction_id = no_cash_models.NewDirection.objects.get(valute_from_id=_valute_from,
                                                                        valute_to_id=_valute_to).pk
                # if city_direction.exchange.name == 'test_ex':
                _d = noncash_direction.__dict__
                _d.pop('_state')
                _d.pop('id')
                _d.pop('exchange_id')
                _d.pop('direction_id')
                prefetch_dict: dict = _d.pop('_prefetched_objects_cache')
                direction_rates = prefetch_dict.get('direction_rates')
                # print(direction_rates)
                _d['exchange_id'] = new_exchange_id
                _d['direction_id'] = new_direction_id
                # break

                with transaction.atomic():
                    new_partner_noncash_direction = partner_models.NewNonCashDirection.objects.create(**_d)

                    if direction_rates:
                        direction_rate_list = []
                        for rate in direction_rates:
                            # print(rate.__dict__)
                            rate_dict: dict = rate.__dict__
                            rate_dict.pop('_state')
                            rate_dict.pop('id')
                            rate_dict.pop('exchange_id')
                            rate_dict.pop('exchange_direction_id')
                            rate_dict['exchange_id'] = new_exchange_id
                            rate_dict['exchange_direction_id'] = new_partner_noncash_direction.pk
                            direction_rate_list.append(partner_models.NewNonCashDirectionRate(**rate_dict))
                        
                        partner_models.NewNonCashDirectionRate.objects.bulk_create(direction_rate_list)

    except Exception as ex:
        print(ex)
        res = 'ERROR'
    else:
        res = 'EXCHANGER PARTNER NONCASH DIRECTIONS WITH DIRECTION RATES ADDED!!!'
        print(res)

    return res
    

# @test_router.get('/union_partner_city_link_count_records_by_marker')
def recreate_partner_city_link_count_records(secret: str):
    if secret != DEV_HANDLER_SECRET:
        raise HTTPException(status_code=400)
    
    link_dict = {}

    records_on_delete = []

    for exchange_link in partner_models.ExchangeLinkCount.objects.all():
        dict_key = (exchange_link.user_id, exchange_link.exchange_id, exchange_link.exchange_direction_id)

        if dict_key not in link_dict:
            link_dict[dict_key] = exchange_link
        else:
            link_dict[dict_key].count += exchange_link.count
            records_on_delete.append(exchange_link.pk)
    
    _update = partner_models.ExchangeLinkCount.objects.bulk_update(objs=list(link_dict.values()),
                                                         fields=['count'])
    
    _delete = partner_models.ExchangeLinkCount.objects.filter(pk__in=records_on_delete).delete()

    print('update', _update)
    print('delete', _delete)


# @test_router.get('/recreate_partner_city_link_count_records')
def recreate_partner_city_link_count_records(secret: str):
    if secret != DEV_HANDLER_SECRET:
        raise HTTPException(status_code=400)
    
    create_list = []

    exchanger_dict = {e.en_name: e.pk for e in Exchanger.objects.all()}
    partner_city_exchange_direction_dict = {(d.direction.valute_from_id, d.direction.valute_to_id, d.city.city_id, d.exchange_id): d.pk\
                                        for d in partner_models.NewDirection.objects.select_related('direction',
                                                                                                    'city').all()}

    for exchange_link in partner_models.ExchangeLinkCount.objects.select_related('exchange',
                                                                                 'exchange_direction',
                                                                                 'exchange_direction__direction',
                                                                                 'exchange_direction__city').all():
        try:
            exchange_en_name = exchange_link.exchange.en_name
        except Exception:
            print('catch error',exchange_link.__dict__)
            continue
        else:
            valute_from_id = exchange_link.exchange_direction.direction.valute_from_id
            valute_to_id = exchange_link.exchange_direction.direction.valute_to_id
            city_id = exchange_link.exchange_direction.city.city_id

            if exchange_id := exchanger_dict.get(exchange_en_name):
                exchange_direction_dict_key = (valute_from_id, valute_to_id, city_id, exchange_id)

                if exchange_direction_id := partner_city_exchange_direction_dict.get(exchange_direction_dict_key):
                    data = {
                        'user_id': exchange_link.user_id,
                        'count': exchange_link.count,
                        'exchange_id': exchange_id,
                        'exchange_direction_id': exchange_direction_id,
                    }

                    create_list.append(partner_models.NewExchangeLinkCount(**data))
                else:
                    print('exchange_direction_id not found', exchange_direction_dict_key, exchange_link.exchange.name, exchange_link.exchange_id)
            else:
                print('exchange_id not found')
    try:
        partner_models.NewExchangeLinkCount.objects.bulk_create(create_list)
    except Exception as ex:
        print(ex)
        res = 'ERROR'
    else:
        res = 'EXCHANGER PARTNER CITY LINKS ADDED!!!'
        print(res)
    
    return res


# @test_router.get('/union_partner_country_link_count_records_by_marker')
def union_partner_country_link_count_records_by_marker(secret: str):
    if secret != DEV_HANDLER_SECRET:
        raise HTTPException(status_code=400)
    
    link_dict = {}

    records_on_delete = []

    for exchange_link in partner_models.CountryExchangeLinkCount.objects.all():
        dict_key = (exchange_link.user_id, exchange_link.exchange_id, exchange_link.exchange_direction_id)

        if dict_key not in link_dict:
            link_dict[dict_key] = exchange_link
        else:
            link_dict[dict_key].count += exchange_link.count
            records_on_delete.append(exchange_link.pk)
    
    _update = partner_models.CountryExchangeLinkCount.objects.bulk_update(objs=list(link_dict.values()),
                                                         fields=['count'])
    
    _delete = partner_models.CountryExchangeLinkCount.objects.filter(pk__in=records_on_delete).delete()

    print('update', _update)
    print('delete', _delete)


# @test_router.get('/recreate_partner_country_link_count_records')
def recreate_partner_country_link_count_records(secret: str):
    if secret != DEV_HANDLER_SECRET:
        raise HTTPException(status_code=400)
    
    # partner_models.ExchangeLinkCount.objects.update(exchange_marker='city')
    
    create_list = []

    exchanger_dict = {e.en_name: e.pk for e in Exchanger.objects.all()}
    partner_country_exchange_direction_dict = {(d.direction.valute_from_id, d.direction.valute_to_id, d.country.country_id, d.exchange_id): d.pk\
                                        for d in partner_models.NewCountryDirection.objects.select_related('direction',
                                                                                                    'country').all()}

    for exchange_link in partner_models.CountryExchangeLinkCount.objects.select_related('exchange',
                                                                                 'exchange_direction',
                                                                                 'exchange_direction__direction',
                                                                                 'exchange_direction__country').all():
        try:
            exchange_en_name = exchange_link.exchange.en_name
        except Exception:
            print('catch error',exchange_link.__dict__)
            continue
        else:
            valute_from_id = exchange_link.exchange_direction.direction.valute_from_id
            valute_to_id = exchange_link.exchange_direction.direction.valute_to_id
            country_id = exchange_link.exchange_direction.country.country_id

            if exchange_id := exchanger_dict.get(exchange_en_name):
                exchange_direction_dict_key = (valute_from_id, valute_to_id, country_id, exchange_id)

                if exchange_direction_id := partner_country_exchange_direction_dict.get(exchange_direction_dict_key):
                    data = {
                        'user_id': exchange_link.user_id,
                        'count': exchange_link.count,
                        'exchange_id': exchange_id,
                        'exchange_direction_id': exchange_direction_id,
                    }

                    create_list.append(partner_models.NewCountryExchangeLinkCount(**data))
                else:
                    print('exchange_direction_id not found', exchange_direction_dict_key, exchange_link.exchange.name, exchange_link.exchange_id)
            else:
                print('exchange_id not found')
    try:
        partner_models.NewCountryExchangeLinkCount.objects.bulk_create(create_list)
    except Exception as ex:
        print(ex)
        res = 'ERROR'
    else:
        res = 'EXCHANGER PARTNER COUNTRY LINKS ADDED!!!'
        print(res)
    
    return res


# @test_router.get('/union_partner_noncash_link_count_records_by_marker')
def union_partner_noncash_link_count_records_by_marker(secret: str):
    if secret != DEV_HANDLER_SECRET:
        raise HTTPException(status_code=400)
    
    link_dict = {}

    records_on_delete = []

    for exchange_link in partner_models.NonCashExchangeLinkCount.objects.all():
        dict_key = (exchange_link.user_id, exchange_link.exchange_id, exchange_link.exchange_direction_id)

        if dict_key not in link_dict:
            link_dict[dict_key] = exchange_link
        else:
            link_dict[dict_key].count += exchange_link.count
            records_on_delete.append(exchange_link.pk)
    
    _update = partner_models.NonCashExchangeLinkCount.objects.bulk_update(objs=list(link_dict.values()),
                                                         fields=['count'])
    
    _delete = partner_models.NonCashExchangeLinkCount.objects.filter(pk__in=records_on_delete).delete()

    print('update', _update)
    print('delete', _delete)


# @test_router.get('/recreate_partner_noncash_link_count_records')
def recreate_partner_noncash_link_count_records(secret: str):
    if secret != DEV_HANDLER_SECRET:
        raise HTTPException(status_code=400)
    
    # partner_models.ExchangeLinkCount.objects.update(exchange_marker='city')
    
    create_list = []

    exchanger_dict = {e.en_name: e.pk for e in Exchanger.objects.all()}
    partner_noncash_exchange_direction_dict = {(d.direction.valute_from_id, d.direction.valute_to_id, d.exchange_id): d.pk\
                                        for d in partner_models.NewNonCashDirection.objects.select_related('direction').all()}

    for exchange_link in partner_models.NonCashExchangeLinkCount.objects.select_related('exchange',
                                                                                 'exchange_direction',
                                                                                 'exchange_direction__direction').all():
        try:
            exchange_en_name = exchange_link.exchange.en_name
        except Exception:
            print('catch error',exchange_link.__dict__)
            continue
        else:
            valute_from_id = exchange_link.exchange_direction.direction.valute_from_id
            valute_to_id = exchange_link.exchange_direction.direction.valute_to_id

            if exchange_id := exchanger_dict.get(exchange_en_name):
                exchange_direction_dict_key = (valute_from_id, valute_to_id, exchange_id)

                if exchange_direction_id := partner_noncash_exchange_direction_dict.get(exchange_direction_dict_key):
                    data = {
                        'user_id': exchange_link.user_id,
                        'count': exchange_link.count,
                        'exchange_id': exchange_id,
                        'exchange_direction_id': exchange_direction_id,
                    }

                    create_list.append(partner_models.NewNonCashExchangeLinkCount(**data))
                else:
                    print('exchange_direction_id not found', exchange_direction_dict_key, exchange_link.exchange.name, exchange_link.exchange_id)
            else:
                print('exchange_id not found')
    try:
        partner_models.NewNonCashExchangeLinkCount.objects.bulk_create(create_list)
    except Exception as ex:
        print(ex)
        res = 'ERROR'
    else:
        res = 'EXCHANGER PARTNER NONCASH LINKS ADDED!!!'
        print(res)
    
    return res


# @test_router.get('/recreate_exchanger_review_records')
def recreate_exchanger_review_records(secret: str):
    if secret != DEV_HANDLER_SECRET:
        raise HTTPException(status_code=400)
    
    exchanger_dict = {e.name: e.pk for e in Exchanger.objects.all()}

    create_list = []

    for review in NewBaseReview.objects.filter(review_from__in=('moneyswap', 'ai')).prefetch_related('comments',
                                                         'admin_comments').all():
        exchange_name = review.exchange_name

        _d = review.__dict__
        _d.pop('_state')
        _d.pop('id')
        _d.pop('exchange_name')
        prefetch_dict: dict = _d.pop('_prefetched_objects_cache')
        comments = prefetch_dict.get('comments')
        admin_comments = prefetch_dict.get('admin_comments')

        new_exchange_id = exchanger_dict.get(exchange_name)
        
        if new_exchange_id:
            _d['exchange_id'] = new_exchange_id
            
            with transaction.atomic():
                new_review = Review.objects.create(**_d)

                if comments:
                    comment_create_list = []
                    for comment in comments:
                        comment_dict: dict = comment.__dict__
                        comment_dict.pop('_state')
                        comment_dict.pop('id')
                        comment_dict.pop('review_id')
                        comment_dict['review_id'] = new_review.pk
                        comment_create_list.append(Comment(**comment_dict))
                    
                    Comment.objects.bulk_create(comment_create_list)
                
                if admin_comments:
                    admin_comment_create_list = []
                    for admin_comment in admin_comments:
                        admin_comment_dict: dict = admin_comment.__dict__
                        admin_comment_dict.pop('_state')
                        admin_comment_dict.pop('id')
                        admin_comment_dict.pop('review_id')
                        admin_comment_dict['review_id'] = new_review.pk
                        admin_comment_create_list.append(AdminComment(**admin_comment_dict))

                    AdminComment.objects.bulk_create(admin_comment_create_list)
            # create_list.append(Review(**_d))
        else:
            print('exchange_id not found', exchange_name)
    
    try:
        Review.objects.bulk_create(create_list)
    except Exception as ex:
        res = 'ERROR'
        print(ex)
    else:
        res = 'EXCHANGER REVIEWS WITH COMMENTS AND ADMIN COMMENTS ADDED!!!'

    return res


# @test_router.get('/recreate_partner_bankomat_records')
def recreate_partner_bankomat_records(secret: str):
    if secret != DEV_HANDLER_SECRET:
        raise HTTPException(status_code=400)
    try:
        for bankomat in partner_models.Bankomat.objects.prefetch_related('valutes').all():
            _d = bankomat.__dict__
            _d.pop('_state')
            _d.pop('id')
            prefetch_dict: dict = _d.pop('_prefetched_objects_cache')
            valutes = prefetch_dict.get('valutes')

            valute_name_list = [v.name for v in valutes]


            new_valute_list = list(NewValute.objects.filter(name__in=valute_name_list).values_list('pk', flat=True))

            # print(new_valute_list)
            with transaction.atomic():
                new_bankomat = partner_models.NewBankomat.objects.create(**_d)

                if new_valute_list:
                    new_bankomat.valutes.add(*new_valute_list)
    
    except Exception as ex:
        print(ex)
        res = 'ERROR'
    else:
        res = 'PARTNER BANKOMATS WITH RELATED VALUTES ADDED!!!'
        print(res)

    return res


# @test_router.get('/recreate_partner_custom_user_records')
def recreate_partner_custom_user_records(secret: str):
    if secret != DEV_HANDLER_SECRET:
        raise HTTPException(status_code=400)
    
    exchanger_dict = {e.en_name: e.pk for e in Exchanger.objects.all()}

    try:
        create_list = []
        for custom_user in partner_models.CustomUser.objects.select_related('exchange',
                                                                            'user').all():
            try:
                exchange_en_name = custom_user.exchange.en_name
            except Exception:
                continue
            else:
                new_exchange_id = exchanger_dict.get(exchange_en_name)
                
                if new_exchange_id:
                    _d = custom_user.__dict__
                    _d.pop('id')
                    _d.pop('_state')
                    _d.pop('exchange_id')
                    _d['exchange_id'] = new_exchange_id
                    create_list.append(partner_models.NewCustomUser(**_d))

        partner_models.NewCustomUser.objects.bulk_create(create_list)

    except Exception as ex:
        print(ex)
        res = 'ERROR'
    else:
        res = 'CUSTOM USERS ADDED!!!'
        print(res)

    return res


# @test_router.get('/recreate_partner_qrvalute_partner_records')
def recreate_partner_qrvalute_partner_records(secret: str):
    if secret != DEV_HANDLER_SECRET:
        raise HTTPException(status_code=400)
    
    exchanger_dict = {e.en_name: e.pk for e in Exchanger.objects.all()}
    
    try:
        for qr_partner in partner_models.QRValutePartner.objects.select_related('valute',
                                                                                'partner',
                                                                                'partner__exchange',
                                                                                'partner__user')\
                                                                .prefetch_related('bankomats').all():
            # print(qr_partner.__dict__)
            bankomats = qr_partner.bankomats.all()
            bankomat_name_list = [b.name for b in bankomats]

            if bankomat_name_list:
                new_bankomats = list(partner_models.NewBankomat.objects.filter(name__in=bankomat_name_list)\
                                                                        .values_list('pk', flat=True))
            else:
                new_bankomats = None
            
            try:
                partner_exchange_en_name = qr_partner.partner.exchange.en_name
            except Exception:
                continue
            else:
                partner_user_id = qr_partner.partner.user_id

                valute_name = qr_partner.valute.name

                new_valute_pk = NewValute.objects.get(name=valute_name).pk
                new_exchange_id = exchanger_dict.get(partner_exchange_en_name)
                
                if new_exchange_id:
                    new_custom_user_pk = partner_models.NewCustomUser.objects.get(user_id=partner_user_id,
                                                                            exchange_id=new_exchange_id).pk
                    _d = {
                        'valute_id': new_valute_pk,
                        'partner_id': new_custom_user_pk,
                    }
                    new_qr_partner = partner_models.NewQRValutePartner.objects.create(**_d)

                    if new_bankomats:
                        new_qr_partner.bankomats.add(*new_bankomats)

    except Exception as ex:
        print(ex)
        res = 'ERROR'
    else:
        res = 'QR PARTNER VALUTE ADDED!!!'
        print(res)

    return res


# @test_router.get('/recreate_exchange_admin_order_records')
def recreate_exchange_admin_order_records(secret: str):
    if secret != DEV_HANDLER_SECRET:
        raise HTTPException(status_code=400)
    
    exchanger_dict = {e.name: e.pk for e in Exchanger.objects.all()}

    create_list = []

    for exchange_admin_order in ExchangeAdminOrder.objects.all():
        _d = exchange_admin_order.__dict__
        _d.pop('_state')
        _d.pop('id')

        exchange_name = _d.pop('exchange_name')
        new_exchange_id = exchanger_dict.get(exchange_name)
        
        if new_exchange_id:
            _d['exchange_id'] = new_exchange_id
            create_list.append(NewExchangeAdminOrder(**_d))
    try:
        NewExchangeAdminOrder.objects.bulk_create(create_list)
    except Exception as ex:
        print(ex)
        res = 'ERROR'
    else:
        res = 'EXCHANGER ADMIN ORDERS ADDED!!!'
    
    return res


# @test_router.get('/recreate_exchange_admin_records')
def recreate_exchange_admin_records(secret: str):
    if secret != DEV_HANDLER_SECRET:
        raise HTTPException(status_code=400)
    
    exchanger_dict = {e.name: e.pk for e in Exchanger.objects.all()}

    exchange_admin_order_set = {(e.user_id, e.exchange.name) for e in NewExchangeAdminOrder.objects.select_related('exchange').all()}

    create_list = []
    exchange_name_set = set()

    for exchange_admin in ExchangeAdmin.objects.all():
        _d = exchange_admin.__dict__
        _user_id = exchange_admin.user_id
        exchange_name = _d.pop('exchange_name')
        if (_user_id, exchange_name) in exchange_admin_order_set:
            if exchange_name in exchange_name_set:
                print(f'duble {exchange_name}')
                continue
            else:
                exchange_name_set.add(exchange_name)

                _d.pop('_state')
                _d.pop('id')
                _d.pop('exchange_id')
                _d.pop('exchange_marker')

                new_exchange_id = exchanger_dict.get(exchange_name)
                
                if new_exchange_id:
                    _d['exchange_id'] = new_exchange_id
                    create_list.append(NewExchangeAdmin(**_d))
    try:
        NewExchangeAdmin.objects.bulk_create(create_list)
    except Exception as ex:
        print(ex)
        res = 'ERROR'
    else:
        res = 'EXCHANGER ADMINS ADDED!!!'
    
    return res


# @test_router.get('/recreate_backgound_task_exchangers')
def recreate_backgound_task_exchangers(secret: str):
    if secret != DEV_HANDLER_SECRET:
        raise HTTPException(status_code=400)
    
    exchangers = Exchanger.objects.filter(xml_url__isnull=False)\
                                    .exclude(active_status__in=('scam', 'skip'))\
                                    .all()
    
    try:
        for exchanger in exchangers:
            interval = exchanger.period_for_create
            if interval and interval > 0:
                manage_periodic_task_for_parse_directions(exchanger.pk,
                                                        interval)
    except Exception as ex:
        res = 'ERROR'
        print(ex)
    else:
        res = 'TASK HAS BEEN RECREATED SUCCESSFULLY'

    return res


@test_router.get('/create_exchangedirections_from_countrydirections')
def create_exchangedirections_from_countrydirections(secret: str):
    if secret != DEV_HANDLER_SECRET:
        raise HTTPException(status_code=400)
    
    create_list = []
    
    cities_prefetch = Prefetch('country__country__cities',
                               queryset=cash_models.City.objects.filter(is_parse=True))

    for country_direction in partner_models.NewCountryDirection.objects.select_related('country')\
                                                                    .prefetch_related('country__exclude_cities',
                                                                                      cities_prefetch).all():
        cities = set(country_direction.country.country.cities.all())
        exclude_cities = set(country_direction.country.exclude_cities.all())

        cities -= exclude_cities

        for city in cities:
            data = {
                'in_count': country_direction.in_count,
                'out_count': country_direction.out_count,
                'min_amount': country_direction.country.min_amount,
                'max_amount': country_direction.country.max_amount,
                'is_active': country_direction.is_active,
                'time_action': country_direction.time_update,
                'exchange_id': country_direction.exchange_id,
                'direction_id': country_direction.direction_id,
                'country_direction_id': country_direction.pk,
                'city_id': city.pk,
            }
            create_list.append(cash_models.NewExchangeDirection(**data))

        # break

    # print(create_list)

    cash_models.NewExchangeDirection.objects.bulk_create(create_list)

# @test_router.get('/run_parse_exchangers_info')
# def run_parse_exchangers_info(secret: str):
#     if secret != DEV_HANDLER_SECRET:
#         raise HTTPException(status_code=400)
    
#     parse_actual_exchanges_info.delay()

#     print('TASK RUNNING...')


# @test_router.get('/update_age_for_exchangers')
def update_age_for_exchangers(secret: str):
    if secret != DEV_HANDLER_SECRET:
        raise HTTPException(status_code=400)
    
    filename = './new_age.json'

    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    update_fields = [
        'age',
    ]
    update_list = []

    for exchanger in Exchanger.objects.all():
        if exchanger.en_name in data:
            age = data[exchanger.en_name]
            valid_age = parse_relative_date(age)
            exchanger.age = valid_age
            update_list.append(exchanger)
    
    len_update = Exchanger.objects.bulk_update(update_list,
                                               update_fields)

    return len_update
    

@test_router.post('/increase_popular_count')
def increase_popular_count(data: IncreasePopularCountSchema):

    if data.city_code_name is None:
        direction_model = no_cash_models.NewDirection
    else:
        direction_model = cash_models.NewDirection

    valute_from, valute_to = data.valute_from.upper(), data.valute_to.upper()

    try:
        direction_model.objects.filter(valute_from_id=valute_from,
                                       valute_to_id=valute_to)\
                                .update(popular_count=F('popular_count') + 1)
        
        if data.city_code_name:
            cash_models.City.objects.filter(code_name=data.city_code_name.upper())\
                                        .update(popular_count=F('popular_count') + 1)
    except Exception as ex:
        print(ex)
        raise HTTPException(status_code=400,
                            detail='error with try increase popular count')
    else:
        return {'status': 'success',
                'detail': 'increase popular count successfully'}


@test_router.post('/increase_link_count')
def increase_link_count(data: IncreaseExchangeLinkCountSchema):
    valute_from, valute_to = data.valute_from.upper(), data.valute_to.upper()
    direction_display = f'{valute_from} -> {valute_to}'
    insert_data = {
        'user_id': data.user_id,
        'exchange_id': data.exchange_id,
        'time_create': timezone.now(),
        'direction_display': direction_display,
        'city_id': data.city_id,
    }
    if data.city_id:
        _marker = 'Cash'
        exists_direction = cash_models.NewDirection.objects.filter(valute_from_id=valute_from,
                                                                   valute_to_id=valute_to)\
                                                            .exists()
    else:
        _marker = 'No cash'
        exists_direction = no_cash_models.NewDirection.objects.filter(valute_from_id=valute_from,
                                                                      valute_to_id=valute_to)\
                                                                .exists()
    if not exists_direction:
        raise HTTPException(status_code=404,
                            detail=f'{_marker} direction {direction_display} not found in DB')
    
    try:
        ExchangeLinkCount.objects.create(**insert_data)
    except Exception as ex:
        print(ex)
        raise HTTPException(status_code=400,
                            detail='error with try add exchange link count to DB')
    else:
        return {'status': 'success',
                'detail': 'exchange link count has benn added successfully'}
    
# @test_router.get('/test_increase')
def test_increase(secret: str):
    # ex_counts = ExchangeLinkCount.objects.all()

    # for _count in ex_counts:
    #     print(_count.__dict__, _count.time_create.astimezone())
    if secret != DEV_HANDLER_SECRET:
        raise HTTPException(status_code=400)
    
    create_list = []
    error_list = []
    error_count = 0
    for marker, model in (('no_cash',no_cash_models.NewExchangeLinkCount),
                  ('cash',cash_models.NewExchangeLinkCount),
                  ('city',partner_models.NewExchangeLinkCount),
                  ('country',partner_models.NewCountryExchangeLinkCount),
                  ('noncash',partner_models.NewNonCashExchangeLinkCount)):
        
        exchange_counts = model.objects.select_related('exchange_direction',
                                                       'exchange_direction__direction')
        if marker == 'cash':
            exchange_counts = exchange_counts.select_related('exchange_direction__city')
        elif marker == 'city':
            exchange_counts = exchange_counts.select_related('exchange_direction__city',
                                                             'exchange_direction__city__city')
            
        for _count in exchange_counts:
            if marker == 'cash':
                city_id = _count.exchange_direction.city_id
            elif marker == 'city':
                try:
                    city_id = _count.exchange_direction.city.city_id
                except Exception:
                    error_list.append((_count.pk,marker))
                    error_count += _count.count
                    continue
            else:
                city_id = None
            for i in range(_count.count):
                try:
                    direction_display = f'{_count.exchange_direction.direction.valute_from_id} -> {_count.exchange_direction.direction.valute_to_id}'
                except Exception:
                    error_list.append((_count.pk,marker))
                    error_count += _count.count
                    break

                data = {
                    'user_id': _count.user_id,
                    'exchange_id': _count.exchange_id,
                    'time_create': None,
                    'direction_display': direction_display,
                    'city_id': city_id,
                }
                create_list.append(ExchangeLinkCount(**data))
    
    try:
        ExchangeLinkCount.objects.bulk_create(create_list)
    except Exception as ex:
        print(ex)
    else:
        print(error_list)
        print(error_count)
        print('SUCCESS')


################################################################################################

# @common_router.get('/available_valutes_2')
def get_available_valutes2(request: Request,
                          query: AvailableValutesQuery = Depends()):
    params = query.params()
    if not params['city']:
        valute_dict = no_cash_valutes_3(request, params)
    else:
        valute_dict = cash_valutes_3(request, params)
    
    return valute_dict


# new available_valutes
@new_common_router.get('/available_valutes')
def available_valutes(request: Request,
                      query: AvailableValutesQuery = Depends()):
    params = query.params()
    if not params['city']:
        valute_dict = no_cash_valutes(request, params)
    else:
        valute_dict = cash_valutes(request, params)
    
    return valute_dict


@new_common_router.get('/all_valutes')
def all_valutes():
    valutes = NewValute.objects.all()
    
    return get_valute_json(valutes,
                           is_valute_query=True)


# @common_router.get('/specific_valute',
#                    response_model=SpecificValuteSchema,
#                    response_model_by_alias=False)
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
    

# new specific_valute
@new_common_router.get('/specific_valute',
                   response_model=NewSpecificValuteSchema,
                   response_model_by_alias=False)
def new_get_specific_valute(code_name: str):
    code_name = code_name.upper()
    try:
        valute = NewValute.objects.get(code_name=code_name)
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


# union_directions_response_models = Union[SpecialCashDirectionMultiPrtnerExchangeRatesWithLocationModel,
#                                          SpecialCashDirectionMultiPrtnerWithLocationModel,
#                                          SpecialCashDirectionMultiWithLocationModel,
#                                          SpecialCashDirectionMultiPrtnerWithExchangeRatesModel,
#                                          SpecialCashDirectionMultiPrtnerModel,
#                                          SpecialCashDirectionMultiModel,
#                                          SpecialDirectionMultiModel]

# new_test_union_directions_response_models = Union[SpecialCashDirectionMultiPrtnerExchangeRatesWithLocationModel,
#                                          SpecialCashDirectionMultiPrtnerWithLocationModel,
#                                          SpecialCashDirectionMultiWithLocationModel,
#                                          SpecialCashDirectionMultiPrtnerWithExchangeRatesWithAmlModel,
#                                          SpecialCashDirectionMultiPrtnerModel,
#                                          SpecialCashDirectionMultiWithAmlModel,
#                                          SpecialPartnerNoCashDirectionSchema,
#                                          SpecialDirectionMultiWithAmlModel]


# new_test_union_directions_response_models2 = Union[SpecialCashDirectionMultiPrtnerExchangeRatesWithLocationModel,
#                                          SpecialCashDirectionMultiPrtnerWithLocationModel,
#                                          SpecialCashDirectionMultiWithLocationModel,
#                                          SpecialCashDirectionMultiPrtnerWithExchangeRatesWithAmlModel,
#                                          SpecialCashDirectionMultiPrtnerModel,
#                                          SpecialCashDirectionMultiWithAmlModel,
#                                          SpecialPartnerNoCashDirectionSchema,
#                                          SpecialDirectionMultiWithAmlModel]


# @common_router.get('/directions',
#                    response_model=list[new_test_union_directions_response_models2],
#                    response_model_by_alias=False)
# def get_current_exchange_directions2(request: Request,
#                                     query: SpecificDirectionsQuery = Depends()):
#     params = query.params()
#     if not params['city']:
#         exchange_direction_list = test_no_cash_exchange_directions4(request, params)
#     else:
#         exchange_direction_list = test_cash_exchange_directions22(request, params)

#     # for query in connection.queries:
#     #     print(query)
#     #     print('*' * 8)

#     return exchange_direction_list

new_union_directions_response_models = Union[ExtendedSpecialCashDirectionMultiPrtnerExchangeRatesWithLocationModel,
                                              ExtendedSpecialCashDirectionMultiPrtnerWithExchangeRatesWithAmlModel,
                                              ExtendedSpecialCashDirectionMultiWithLocationModel,
                                              ExtendedSpecialCashDirectionMultiWithAmlModel,
                                              ExtendedSpecialPartnerNoCashDirectionSchema,
                                              ExtendedSpecialDirectionMultiWithAmlModel]

test_new_union_directions_response_models = Union[NewSpecialCashDirectionMultiPrtnerExchangeRatesWithLocationModel,
                                              NewSpecialCashDirectionMultiPrtnerWithExchangeRatesWithAmlModel,
                                              NewSpecialCashDirectionMultiWithLocationModel,
                                              NewSpecialCashDirectionMultiWithAmlModel,
                                              NewSpecialPartnerNoCashDirectionSchema,
                                              NewSpecialDirectionMultiWithAmlModel]


# new directions
@new_common_router.get('/directions',
                   response_model=list[new_union_directions_response_models],
                   response_model_by_alias=False)
def get_current_exchange_directions(request: Request,
                                    query: SpecificDirectionsQuery = Depends()):
    # print(len(connection.queries))
    start_time = time()
    params = query.params()

    if not params['city']:
        exchange_direction_list = no_cash_exchange_directions(request, params)
    else:
        exchange_direction_list = cash_exchange_directions(request, params)

    print(f'all run time /directions {time() - start_time} sec | {len(exchange_direction_list)} el')
    # print(len(connection.queries))

    return exchange_direction_list


@test_router.get('/directions',
                   response_model=list[test_new_union_directions_response_models],
                   response_model_by_alias=False)
def get_current_exchange_directions(request: Request,
                                    query: SpecificDirectionsQuery = Depends()):
    # print(len(connection.queries))
    start_time = time()
    params = query.params()

    if not params['city']:
        exchange_direction_list = test_no_cash_exchange_directions(request, params)
    else:
        exchange_direction_list = test_cash_exchange_directions(request, params)

    print(f'all run time /directions {time() - start_time} sec | {len(exchange_direction_list)} el')
    # print(len(connection.queries))

    return exchange_direction_list


# @common_router.get('/popular_directions',
#                    response_model=list[PopularDirectionSchema],
#                    response_model_by_alias=False)
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


@new_common_router.get('/popular_directions',
                   response_model=list[PopularDirectionSchema],
                   response_model_by_alias=False)
def new_get_popular_directions(segment_marker: Literal['cash',
                                                        'no_cash',
                                                        'both'],
                           limit: int = None):
    limit = 9 if limit is None else limit

    match segment_marker:
        case 'no_cash':
            directions = no_cash_models.NewDirection.objects.select_related('valute_from',
                                                                            'valute_to')\
                                                            .order_by('-is_popular',
                                                                      '-popular_count')\
                                                            .all()[:limit]
        case 'cash':
            directions = cash_models.NewDirection.objects.select_related('valute_from',
                                                                         'valute_to')\
                                                            .order_by('-is_popular',
                                                                      '-popular_count')\
                                                            .all()[:limit]
        case 'both':
            no_cash_directions = no_cash_models.NewDirection.objects.select_related('valute_from',
                                                                                    'valute_to')

            cash_directions = cash_models.NewDirection.objects.select_related('valute_from',
                                                                                'valute_to')

            
            directions = no_cash_directions.union(cash_directions).order_by('-is_popular',
                                                                            '-popular_count')[:limit]
    
    res = []

    for direction in directions:

        valute_from = generate_valute_for_schema(direction.valute_from)
        valute_to = generate_valute_for_schema(direction.valute_to)
        res.append(PopularDirectionSchema(valute_from=valute_from.__dict__,
                                          valute_to=valute_to.__dict__))

    return res


# @common_router.get('/random_directions',
#                    response_model=list[PopularDirectionSchema],
#                    response_model_by_alias=False)
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


@new_common_router.get('/random_directions',
                   response_model=list[PopularDirectionSchema],
                   response_model_by_alias=False)
def new_get_random_directions(segment_marker: Literal['cash',
                                                        'no_cash',
                                                        'both'],
                              limit: int = None):
    
    limit = 9 if limit is None else limit

    if limit <= 0:
        raise HTTPException(status_code=400,
                            detail=f'parameter "limit" must be positive number, given {limit}')

    match segment_marker:
        case 'no_cash':
            exchange_direction_pks = no_cash_models.NewExchangeDirection.objects\
                                                .select_related('exchange')\
                                                .filter(exchange__is_active=True,
                                                        is_active=True)\
                                                .order_by('direction_id')\
                                                .distinct('direction_id')\
                                                .values_list('direction_id',
                                                             flat=True)
            direction_pks = list(exchange_direction_pks)
            shuffle(direction_pks)

            directions = no_cash_models.NewDirection.objects.select_related('valute_from',
                                                                'valute_to')\
                                                .filter(pk__in=direction_pks[:limit])
        case 'cash':
            exchange_direction_pks = cash_models.NewExchangeDirection.objects\
                                                .select_related('exchange')\
                                                .filter(exchange__is_active=True,
                                                        is_active=True)\
                                                .order_by('direction_id')\
                                                .distinct('direction_id')\
                                                .values_list('direction_id',
                                                             flat=True)
            direction_pks = list(exchange_direction_pks)
            shuffle(direction_pks)

            directions = cash_models.NewDirection.objects.select_related('valute_from',
                                                                'valute_to')\
                                                .filter(pk__in=direction_pks[:limit])
        case 'both':
            no_cash_exchange_direction_pks = no_cash_models.NewExchangeDirection.objects\
                                                .select_related('exchange')\
                                                .filter(exchange__is_active=True,
                                                        is_active=True)\
                                                .order_by('direction_id')\
                                                .distinct('direction_id')\
                                                .values_list('direction_id',
                                                             flat=True)
            no_cash_direction_pks = list(no_cash_exchange_direction_pks)
            shuffle(no_cash_direction_pks)

            no_cash_directions = no_cash_models.NewDirection.objects.select_related('valute_from',
                                                                                    'valute_to')\
                                                .filter(pk__in=no_cash_direction_pks)[:limit]
            
            cash_exchange_direction_pks = cash_models.NewExchangeDirection.objects\
                                                .select_related('exchange')\
                                                .filter(exchange__is_active=True,
                                                        is_active=True)\
                                                .order_by('direction_id')\
                                                .distinct('direction_id')\
                                                .values_list('direction_id',
                                                             flat=True)
            cash_direction_pks = list(cash_exchange_direction_pks)
            shuffle(cash_direction_pks)

            cash_directions = cash_models.NewDirection.objects.select_related('valute_from',
                                                                                'valute_to')\
                                                .filter(pk__in=cash_direction_pks)[:limit]
            
            union_directions = no_cash_directions.union(cash_directions)
            directions = list(union_directions)
            shuffle(directions)

    res = []
    for direction in directions[:limit]:
        valute_from = generate_valute_for_schema(direction.valute_from)
        valute_to = generate_valute_for_schema(direction.valute_to)
        direction = PopularDirectionSchema(valute_from=valute_from.__dict__,
                                           valute_to=valute_to.__dict__)
        res.append(direction)

    return res


# @common_router.get('/similar_directions',
#                    response_model=list[PopularDirectionSchema],
#                    response_model_by_alias=False)
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


@new_common_router.get('/similar_directions',
                   response_model=list[PopularDirectionSchema],
                   response_model_by_alias=False)
def new_get_similar_directions(segment_marker: Literal['no_cash',
                                                         'cash'],
                                                         valute_from: str,
                                                         valute_to: str,
                                                         city: str = None,
                                                         limit: int = None):

    limit = 9 if limit is None else limit

    if limit <= 0:
        raise HTTPException(status_code=400,
                            detail=f'parameter "limit" must be positive number, given {limit}')
    
    city = None if city is None else city.upper()
    valute_from, valute_to = [el.upper() for el in (valute_from, valute_to)]

    if segment_marker == 'no_cash':
        direction_model = no_cash_models.NewDirection

        exchange_direction_model = no_cash_models.NewExchangeDirection
        partner_direction_model = partner_models.NewNonCashDirection

        similar_direction_filter = Q(direction__valute_from_id=valute_from,
                                     exchange__is_active=True,
                                     is_active=True) \
                                    | Q(direction__valute_to_id=valute_to,
                                        exchange__is_active=True,
                                        is_active=True)

        exchange_direction_pks = exchange_direction_model.objects.select_related('direction',
                                                                    'exchange')\
                                                    .exclude(direction__valute_from_id=valute_from,
                                                             direction__valute_to_id=valute_to)\
                                                    .filter(similar_direction_filter)\
                                                    .values_list('direction__pk',
                                                                 flat=True)

        partner_exchange_direction_pks = partner_direction_model.objects.select_related('direction',
                                                                                       'exchange')\
                                                    .exclude(direction__valute_from_id=valute_from,
                                                             direction__valute_to_id=valute_to)\
                                                    .filter(similar_direction_filter)\
                                                    .values_list('direction__pk',
                                                                 flat=True)
        
        similar_direction_pks = exchange_direction_pks.union(partner_exchange_direction_pks)


    else:
        if not city:
            raise HTTPException(status_code=400)

        direction_model = cash_models.NewDirection

        exchange_direction_model = cash_models.NewExchangeDirection
        partner_city_direction_model = partner_models.NewDirection
        partner_country_direction_model = partner_models.NewCountryDirection


        similar_direction_filter = Q(direction__valute_from=valute_from,
                                     city__code_name=city,
                                     exchange__is_active=True,
                                     is_active=True)\
                                | Q(direction__valute_to=valute_to,
                                    city__code_name=city,
                                    exchange__is_active=True,
                                    is_active=True)
        similar_partner_city_direction_filter = Q(direction__valute_from=valute_from,
                                             city__city__code_name=city,
                                             city__exchange__is_active=True,
                                             is_active=True)\
                                         | Q(direction__valute_to=valute_to,
                                             city__city__code_name=city,
                                             city__exchange__is_active=True,
                                             is_active=True)
        similar_partner_country_direction_filter = Q(direction__valute_from=valute_from,
                                             country__country__cities__code_name=city,
                                             country__exchange__is_active=True,
                                             is_active=True)\
                                         | Q(direction__valute_to=valute_to,
                                             country__country__cities__code_name=city,
                                             country__exchange__is_active=True,
                                             is_active=True)
        
        exchange_direction_pks = exchange_direction_model.objects.select_related('direction',
                                                                            'exchange,'
                                                                            'city')\
                                                    .exclude(city__code_name=city,
                                                             direction__valute_from=valute_from,
                                                             direction__valute_to=valute_to)\
                                                    .filter(similar_direction_filter)\
                                                    .values_list('direction__pk',
                                                                 flat=True)\
                                                    .all()
        partner_city_direction_pks = partner_city_direction_model.objects.select_related('direction',
                                                                                       'city',
                                                                                       'city__city',
                                                                                       'city__exchange')\
                                                    .exclude(city__city__code_name=city,
                                                             direction__valute_from=valute_from,
                                                             direction__valute_to=valute_to)\
                                                    .filter(similar_partner_city_direction_filter)\
                                                    .values_list('direction__pk',
                                                                 flat=True)\
                                                    .all()
        partner_country_direction_pks = partner_country_direction_model.objects.select_related('direction',
                                                                                       'country',
                                                                                       'country__country',
                                                                                       'country__exchange')\
                                                    .exclude(country__country__cities__code_name=city,
                                                             direction__valute_from=valute_from,
                                                             direction__valute_to=valute_to)\
                                                    .filter(similar_partner_country_direction_filter)\
                                                    .values_list('direction__pk',
                                                                 flat=True)\
                                                    .all()
        similar_direction_pks = exchange_direction_pks.union(partner_city_direction_pks,
                                                             partner_country_direction_pks)

    similar_direction_pks = list(similar_direction_pks)
    shuffle(similar_direction_pks)

    similar_directions = direction_model.objects.select_related('valute_from',
                                                                'valute_to')\
                                                .filter(pk__in=similar_direction_pks[:limit])

    for direction in similar_directions:
        valute_from = generate_valute_for_schema(direction.valute_from)
        valute_to = generate_valute_for_schema(direction.valute_to)
        direction = PopularDirectionSchema(valute_from=valute_from.__dict__,
                                           valute_to=valute_to.__dict__)

    # print(len(connection.queries))

    return similar_directions


# @common_router.get('/similar_cities_by_direction',
#                    response_model=list[CityModel])
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


@new_common_router.get('/similar_cities_by_direction',
                   response_model=list[CityModel])
def new_get_similar_cities_by_direction(valute_from: str,
                                        valute_to: str,
                                        city: str):
    valute_from, valute_to, city = [el.upper() for el in (valute_from, valute_to, city)]

    cash_direction_model = cash_models.NewExchangeDirection
    partner_city_direction_model = partner_models.NewDirection
    partner_country_direction_model = partner_models.NewCountryDirection

    try:
        city_model = cash_models.City.objects.select_related('country')\
                                            .get(code_name=city)
        direction_id = cash_models.NewDirection.objects.get(valute_from_id=valute_from,
                                                            valute_to_id=valute_to).pk
        _country = city_model.country
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404,
                            detail='City not found by given "city"')
    else:
        similar_cities = cash_direction_model.objects.select_related('direction',
                                                                'exchange',
                                                                'city')\
                                                    .exclude(city__code_name=city)\
                                                    .filter(direction__valute_from_id=valute_from,
                                                            direction__valute_to_id=valute_to,
                                                            is_active=True,
                                                            exchange__is_active=True)\
                                                    .values_list('city__pk',
                                                                 flat=True)
        
        similar_partner_cities = partner_city_direction_model.objects.select_related('direction',
                                                                                'city',
                                                                                'city__city',
                                                                                'city__exchange')\
                                                                .exclude(city__city__code_name=city)\
                                                                .filter(direction__valute_from_id=valute_from,
                                                                        direction__valute_to_id=valute_to,
                                                                        is_active=True,
                                                                        city__exchange__is_active=True)\
                                                                .values_list('city__city__pk',
                                                                            flat=True)
        
        similar_partner_country_directions = partner_country_direction_model.objects.select_related('direction',
                                                                                'country',
                                                                                'country__country',
                                                                                'country__exchange')\
                                                                .prefetch_related('country__country__cities',
                                                                                  'country__exclude_cities')\
                                                                .filter(direction__valute_from_id=valute_from,
                                                                        direction__valute_to_id=valute_to,
                                                                        is_active=True,
                                                                        country__exchange__is_active=True)
        
        country_cites_pk = set()
        for country_direction in similar_partner_country_directions:
            available_cities = country_direction.country.country.cities.all()
            available_city_pks = {c.pk for c in available_cities}

            exclude_cities = country_direction.country.exclude_cities.all()
            exclude_city_pks = {c.pk for c in exclude_cities}

            country_cites_pk = available_city_pks - exclude_city_pks
        
        similar_city_pks = set(similar_cities.union(similar_partner_cities))

        similar_city_pks |= country_cites_pk
        similar_city_pks -= set([city_model.pk])

        exchange_count_filter = Q(new_cash_directions__direction_id=direction_id,
                                new_cash_directions__exchange__is_active=True,
                                new_cash_directions__is_active=True)
        partner_city_exchange_count_filter = Q(new_partner_cities__partner_directions__direction_id=direction_id,
                                        new_partner_cities__partner_directions__is_active=True)
        partner_country_exchange_count_filter = Q(country__new_partner_countries__partner_directions__direction_id=direction_id,
                                                    country__new_partner_countries__partner_directions__is_active=True)

        cities = _country.cities\
                                    .annotate(exchange_count=Count('new_cash_directions',
                                                        filter=exchange_count_filter))\
                                    .filter(pk__in=similar_city_pks)\
                                    .order_by('pk')\
                                    .all()
        
        partner_cities = list(_country.cities\
                                    .annotate(partner_exchange_count=Count('new_partner_cities__partner_directions',
                                                                filter=partner_city_exchange_count_filter))\
                                    .filter(pk__in=similar_city_pks)\
                                    .values_list('partner_exchange_count',
                                                flat=True)\
                                    .order_by('pk')\
                                    .all())
        
        partner_country_cities = list(_country.cities\
                                    .annotate(partner_exchange_count=Count('country__new_partner_countries__partner_directions',
                                                                filter=partner_country_exchange_count_filter))\
                                    .filter(pk__in=similar_city_pks)\
                                    .values_list('partner_exchange_count',
                                                flat=True)\
                                    .order_by('pk')\
                                    .all())
                
        for idx in range(len(cities)):
            cities[idx].exchange_count += partner_cities[idx] + partner_country_cities[idx]

        return cities
    

@new_common_router.get('/extended_similar_cities_by_direction',
                   response_model=list[CityModel])
def new_get_extended_similar_cities_by_direction(valute_from: str,
                                                 valute_to: str,
                                                 city: str):
    valute_from, valute_to, city = [el.upper() for el in (valute_from, valute_to, city)]

    cash_direction_model = cash_models.NewExchangeDirection
    partner_city_direction_model = partner_models.NewDirection
    partner_country_direction_model = partner_models.NewCountryDirection

    try:
        city_model = cash_models.City.objects.select_related('country')\
                                            .get(code_name=city)
        direction_id = cash_models.NewDirection.objects.get(valute_from_id=valute_from,
                                                            valute_to_id=valute_to).pk
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404,
                            detail='City not found by given "city"')
    else:
        similar_cities = cash_direction_model.objects.select_related('direction',
                                                                'exchange',
                                                                'city')\
                                                    .exclude(city__code_name=city)\
                                                    .filter(direction__valute_from_id=valute_from,
                                                            direction__valute_to_id=valute_to,
                                                            is_active=True,
                                                            exchange__is_active=True)\
                                                    .values_list('city__pk',
                                                                 flat=True)
        
        similar_partner_cities = partner_city_direction_model.objects.select_related('direction',
                                                                                'city',
                                                                                'city__city',
                                                                                'city__exchange')\
                                                                .exclude(city__city__code_name=city)\
                                                                .filter(direction__valute_from_id=valute_from,
                                                                        direction__valute_to_id=valute_to,
                                                                        is_active=True,
                                                                        city__exchange__is_active=True)\
                                                                .values_list('city__city__pk',
                                                                            flat=True)
        
        similar_partner_country_directions = partner_country_direction_model.objects.select_related('direction',
                                                                                'country',
                                                                                'country__country',
                                                                                'country__exchange')\
                                                                .prefetch_related('country__country__cities',
                                                                                  'country__exclude_cities')\
                                                                .filter(direction__valute_from_id=valute_from,
                                                                        direction__valute_to_id=valute_to,
                                                                        is_active=True,
                                                                        country__exchange__is_active=True)
        
        country_cites_pk = set()
        for country_direction in similar_partner_country_directions:
            available_cities = country_direction.country.country.cities.all()
            available_city_pks = {c.pk for c in available_cities}

            exclude_cities = country_direction.country.exclude_cities.all()
            exclude_city_pks = {c.pk for c in exclude_cities}

            country_cites_pk = available_city_pks - exclude_city_pks
        
        similar_city_pks = set(similar_cities.union(similar_partner_cities))

        similar_city_pks |= country_cites_pk
        similar_city_pks -= set([city_model.pk])

        exchange_count_filter = Q(new_cash_directions__direction_id=direction_id,
                                new_cash_directions__exchange__is_active=True,
                                new_cash_directions__is_active=True)
        partner_city_exchange_count_filter = Q(new_partner_cities__partner_directions__direction_id=direction_id,
                                        new_partner_cities__partner_directions__is_active=True)
        partner_country_exchange_count_filter = Q(country__new_partner_countries__partner_directions__direction_id=direction_id,
                                                    country__new_partner_countries__partner_directions__is_active=True)

        cities = cash_models.City.objects\
                                    .annotate(exchange_count=Count('new_cash_directions',
                                                        filter=exchange_count_filter))\
                                    .filter(pk__in=similar_city_pks)\
                                    .order_by('pk')\
                                    .all()
        
        partner_cities = list(cash_models.City.objects\
                                    .annotate(partner_exchange_count=Count('new_partner_cities__partner_directions',
                                                                filter=partner_city_exchange_count_filter))\
                                    .filter(pk__in=similar_city_pks)\
                                    .values_list('partner_exchange_count',
                                                flat=True)\
                                    .order_by('pk')\
                                    .all())
        
        partner_country_cities = list(cash_models.City.objects\
                                    .annotate(partner_exchange_count=Count('country__new_partner_countries__partner_directions',
                                                                filter=partner_country_exchange_count_filter))\
                                    .filter(pk__in=similar_city_pks)\
                                    .values_list('partner_exchange_count',
                                                flat=True)\
                                    .order_by('pk')\
                                    .all())
                
        for idx in range(len(cities)):
            cities[idx].exchange_count += partner_cities[idx] + partner_country_cities[idx]

        return cities


# @common_router.get('/exchange_list',
#                    response_model=list[NewCommonExchangeSchema],
#                    response_model_by_alias=False)
def get_exchange_list():
    # print(len(connection.queries))

    # review_counts = new_get_reviews_count_filters(marker='exchange')

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

    review_counts = (
        NewBaseReview.objects
        .filter(moderation=True)
        .values('exchange_name')
        .annotate(
            positive_count=Count('id', filter=Q(grade='1') & Q(review_from__in=('moneyswap', 'ai'))),
            neutral_count=Count('id', filter=Q(grade='0') & Q(review_from__in=('moneyswap', 'ai'))),
            negative_count=Count('id', filter=Q(grade='-1') & Q(review_from__in=('moneyswap', 'ai'))),
        )
    )

    review_map = {r['exchange_name']: r for r in review_counts}

    result = get_exchange_dircetions_dict_tuple()

    # print('result',result)
    
    queries = []

    for exchange_marker, exchange_model in (('no_cash', no_cash_models.Exchange),
                                            ('cash', cash_models.Exchange),
                                            ('partner', partner_models.Exchange)):
        # review_counts = new_get_reviews_count_filters(exchange_marker)

        # exchange_query = exchange_model.objects\
        #                             .annotate(exchange_marker=annotate_string_field(exchange_marker))\
                                    # .annotate(positive_review_count=review_counts['positive'])\
                                    # .annotate(neutral_review_count=review_counts['neutral'])\
                                    # .annotate(negative_review_count=review_counts['negative'])\
                                    # .values('pk',
                                    #         'name',
                                    #         'reserve_amount',
                                    #         'course_count',
                                    #         'positive_review_count',
                                    #         'neutral_review_count',
                                    #         'negative_review_count',
                                    #         'is_active',
                                    #         'exchange_marker',
                                    #         'partner_link')\
                                    # .filter(is_active=True)
                                    # .all()

        # exchange_query = get_exchange_with_direction_count_for_exchange_list(exchange_list=exchange_query,
        #                                                                      exchange_marker=exchange_marker)
        exchange_query = exchange_model.objects\
                                    .annotate(exchange_marker=annotate_string_field(exchange_marker))\
                                    .values('pk',
                                            'name',
                                            'en_name',
                                            'reserve_amount',
                                            # 'direction_count',
                                            # 'positive_review_count',
                                            # 'neutral_review_count',
                                            # 'negative_review_count',
                                            'is_active',
                                            'active_status',
                                            'exchange_marker',
                                            'partner_link')\
                                    .filter(active_status__in=availabale_active_status_list)\
                                    .order_by()
                                    # .filter(is_active=True)\

        queries.append(exchange_query)

    exchange_list = queries[0].union(queries[1],queries[2],
                                     all=True)\
                                # .union(queries[2], all=True)
    
    exchange_dict = {}
    exchange_name_set = set()

    for exchange in exchange_list:
        exchange_name = exchange.get('name').lower()   # lower() для name !
        exchange_marker = exchange['exchange_marker']

        if exchange_name in exchange_name_set:
            try:
                if exchange['active_status'] != 'active':
                    exchange['direction_count'] = 0
                else:
                    exchange['direction_count'] = result[exchange_marker][exchange['pk']]
                    if exchange['direction_count'] == 0 and exchange['active_status'] == 'active':
                        exchange['active_status'] = 'inactive'
                        exchange['is_active'] = False
            except KeyError as ex:
                # print('1error',ex)
                exchange['direction_count'] = 0
                if exchange['active_status'] == 'active':
                    exchange['active_status'] = 'inactive'
                    exchange['is_active'] = False
            
            exchange_dict[exchange_name]['exchange_marker'] = 'both'

            exchange_dict[exchange_name]['direction_count'] += exchange.get('direction_count', 0)

            exchange_dict[exchange_name]['multiple_name'] = MultipleName(name=exchange['name'],
                                                          en_name=exchange['en_name'])

            if exchange_marker == 'no_cash':
                exchange_dict[exchange_name]['pk'] = exchange['pk'] # id no_cash обменников
        else:
            exchange['multiple_name'] = MultipleName(name=exchange['name'],
                                                          en_name=exchange['en_name'])
            # exchange['reviews'] = ReviewCountSchema(positive=exchange['positive_review_count'],
            #                                         neutral=exchange['neutral_review_count'],
            #                                         negative=exchange['negative_review_count'])
            try:
                exchange['reviews'] = ReviewCountSchema(positive=review_map[exchange.get('name')]['positive_count'],
                                                        neutral=review_map[exchange.get('name')]['neutral_count'],
                                                        negative=review_map[exchange.get('name')]['negative_count'])
            except KeyError:
                exchange['reviews'] = ReviewCountSchema(positive=0,
                                                        neutral=0,
                                                        negative=0)
            try:
                if exchange['active_status'] != 'active':
                    exchange['direction_count'] = 0
                else:
                    exchange['direction_count'] = result[exchange_marker][exchange['pk']]

                    if exchange['direction_count'] == 0 and exchange['active_status'] == 'active':
                        exchange['active_status'] = 'inactive'
                        exchange['is_active'] = False
                # exchange_dict[exchange_name] = exchange
                # exchange_name_set.add(exchange_name)
            except KeyError as ex:
                # print('2error',ex, exchange_marker)
                exchange['direction_count'] = 0
                
                if exchange['active_status'] == 'active':
                    exchange['active_status'] = 'inactive'
                    exchange['is_active'] = False
            
            exchange_dict[exchange_name] = exchange
            exchange_name_set.add(exchange_name)



    # print(len(connection.queries))
    # print(connection.queries[-1]['sql'])

    # print(len(exchange_dict))
    # print(exchange_dict)

    # result_list = [el for el in exchange_dict.values() if el['direction_count'] > 0]

    # return sorted(exchange_list,
                #   key=lambda el: el.get('name'))
    return sorted(exchange_dict.values(),
                  key=lambda el: (-el.get('is_active'), el.get('name')))


@new_common_router.get('/exchange_list',
                   response_model=list[ExchangeListElementSchema],
                   response_model_by_alias=False)
def new_get_exchange_list():

    review_count_dict = get_review_count_dict()


    exchange_query = Exchanger.objects\
                                .values('pk',
                                        'name',
                                        'en_name',
                                        'reserve_amount',
                                        'is_active',
                                        'active_status',
                                        'partner_link')\
                                .filter(active_status__in=availabale_active_status_list)
    
    exchange_direction_count_dict = new_get_exchange_directions_count_dict(exchange_query)
    
    exchange_list = []

    for exchange in exchange_query:
        exchange_id = exchange['pk']

        exchange['multiple_name'] = MultipleName(name=exchange['name'],
                                                    en_name=exchange['en_name'])
        try:
            exchange['reviews'] = ReviewCountSchema(positive=review_count_dict[exchange_id]['positive_count'],
                                                    neutral=review_count_dict[exchange_id]['neutral_count'],
                                                    negative=review_count_dict[exchange_id]['negative_count'])
        except KeyError:
            exchange['reviews'] = ReviewCountSchema(positive=0,
                                                    neutral=0,
                                                    negative=0)
        if exchange['active_status'] != 'active':
            exchange['direction_count'] = 0
        else:
            exchange['direction_count'] = exchange_direction_count_dict[exchange_id]

            if exchange['direction_count'] == 0 and exchange['active_status'] == 'active':
                exchange['active_status'] = 'inactive'
                exchange['is_active'] = False
        
        exchange_list.append(exchange)

    return sorted(exchange_list,
                  key=lambda el: (-el.get('is_active'),
                                  el.get('name')))


@new_common_router.get('/exchange_detail',
                   response_model=DetailExchangeSchema,
                   response_model_by_alias=False)
def new_get_exchange_detail_info(exchange_id: int):

    try:
        exchange = Exchanger.objects.values(
            'pk',
            'name',
            'en_name',
            'icon_url',
            'partner_link',
            'active_status',
            'is_active',
            'high_aml',
            'country',
            'reserve_amount',
            'age',
            'time_create',
            'time_disable',
        ).get(pk=exchange_id,
              active_status__in=availabale_active_status_list)

    except Exception as ex:
        print(ex)
        raise HTTPException(status_code=404,
                            detail='valid Exchanger not found by given "exchange_id"')
    else:
        exchange_direction_dict, segment_marker = new_get_exchange_directions_count_dict([exchange],
                                                                                         _pk=exchange_id)

        review_counts = (
            Review.objects
            .filter(moderation=True,
                    exchange_id=exchange_id)
            .values('exchange_id')
            .annotate(
                positive_count=Count('id', filter=Q(grade='1') & Q(review_from__in=('moneyswap', 'ai'))),
                neutral_count=Count('id', filter=Q(grade='0') & Q(review_from__in=('moneyswap', 'ai'))),
                negative_count=Count('id', filter=Q(grade='-1') & Q(review_from__in=('moneyswap', 'ai'))),
            )
        )

        review_map = {r['exchange_id']: r for r in review_counts}

        try:
            exchange['review_set'] = ReviewCountSchema(positive=review_map[exchange_id]['positive_count'],
                                                    neutral=review_map[exchange_id]['neutral_count'],
                                                    negative=review_map[exchange_id]['negative_count'])
        except KeyError:
            exchange['review_set'] = ReviewCountSchema(positive=0,
                                                       neutral=0,
                                                       negative=0)

        exchange['icon'] = generate_image_icon2(icon_url=exchange['icon_url'])

        exchange['multiple_name'] = MultipleName(name=exchange['name'],
                                                 en_name=exchange['en_name'])
        if age := exchange['age']:
            exchange['age'] = format_relative_date(age)
        
        exchange['course_count'] = exchange_direction_dict.get(exchange_id, 0)

        if exchange['course_count'] == 0 and exchange['active_status'] == 'active':
            exchange['active_status'] = 'inactive'

        elif exchange['active_status'] != 'active':
            exchange['course_count'] = 0

        exchange['segment_marker'] = None if exchange['course_count'] == 0 else segment_marker
        
        return exchange


# @common_router.get('/exchangers_blacklist',
#                    response_model=list[BlackListExchangeSchema],
#                    response_model_by_alias=False)
def get_black_exchange_list():
    queries = []

    for exchange_marker, exchange_model in (('no_cash', no_cash_models.Exchange),
                                            ('cash', cash_models.Exchange),
                                            ('partner', partner_models.Exchange)):

        exchange_query = exchange_model.objects\
                                    .annotate(exchange_marker=annotate_string_field(exchange_marker))\
                                    .values('pk',
                                            'name',
                                            'en_name',
                                            'active_status',
                                            'exchange_marker',
                                            'partner_link')\
                                    .filter(active_status='scam')\
                                    .order_by()

        queries.append(exchange_query)

    exchange_list = queries[0].union(queries[1],queries[2],
                                     all=True)
    
    similar_exchange_name_set = {exchange['name'] for exchange in exchange_list if exchange['name'].find('|') == -1}

    # print(similar_exchange_name_set)
    
    exchange_dict = {}
    exchange_name_set = set()
    unique_black_start_exchange_name_set = set()

    for exchange in exchange_list:
        exchange_name: str = exchange.get('name').lower()   # lower() для name !
        start_exchange_name = exchange['name'].split('|')[0].strip()
        exchange_marker = exchange['exchange_marker']

        if exchange_name in exchange_name_set:

            # if exchange_name.find('|') != -1:
            # unique_black_start_exchange_name_set.add(start_exchange_name)

            exchange_dict[exchange_name]['multiple_name'] = MultipleName(name=exchange['name'],
                                                                         en_name=exchange['en_name'])

            exchange_dict[exchange_name]['exchange_marker'] = 'both'

            if exchange_marker == 'no_cash':
                exchange_dict[exchange_name]['pk'] = exchange['pk'] # id no_cash обменников

        elif start_exchange_name in similar_exchange_name_set and exchange['name'] not in similar_exchange_name_set:
            continue
            # if any(key.startswith(start_exchange_name) for key in exchange_dict.keys()):
            #     for key in exchange_dict.keys():
            #         if key.startswith(start_exchange_name):
            #             del exchange_dict[key]
            #             exchange['multiple_name'] = MultipleName(name='|'.join(exchange['name'].split('|')[:2]).strip(),
            #                                                     en_name='|'.join(exchange['en_name'].split('|')[:2]).strip())
            #             exchange_dict[exchange_name] = exchange
            #             break
        else:
            if start_exchange_name in similar_exchange_name_set and exchange['name'] not in similar_exchange_name_set:
                continue

            exchange['multiple_name'] = MultipleName(name=exchange['name'],
                                                     en_name=exchange['en_name'])
            
            exchange_dict[exchange_name] = exchange

            # if exchange_name.find('|') != -1:
            unique_black_start_exchange_name_set.add(start_exchange_name)
            exchange_name_set.add(exchange_name)


    return sorted(exchange_dict.values(),
                  key=lambda el: el.get('name'))


@new_common_router.get('/exchangers_blacklist',
                   response_model=list[NewBlackListExchangeSchema],
                   response_model_by_alias=False)
def new_get_black_exchange_list():

    exchange_query = Exchanger.objects\
                                .filter(active_status='scam')\
                                .values('pk',
                                        'name',
                                        'en_name')\
                                .order_by('name')

    exchange_black_list = []

    for exchange in exchange_query:
        exchange_black_list.append({
            'pk': exchange['pk'],
            'multiple_name': MultipleName(name=exchange['name'],
                                          en_name=exchange['en_name']),
        })

    return exchange_black_list


# @common_router.get('/exchange_blacklist_detail',
#                    response_model=NewDetailBlackListExchangeSchema,
#                    response_model_by_alias=False)
def get_exchange_detail_info(exchange_id: int,
                             exchange_marker: str):

    exchange = get_exchange(exchange_id,
                            exchange_marker,
                            black_list_exchange=True)

    exchange = exchange.first()

    start_exchange_name = exchange.name.split('|')[0].strip()

    queries = []

    for _exchange_marker, exchange_model in (('no_cash', no_cash_models.Exchange),
                                            ('cash', cash_models.Exchange),
                                            ('partner', partner_models.Exchange)):

        exchange_query = exchange_model.objects\
                                    .values_list('partner_link',
                                                 flat=True)\
                                    .filter(active_status='scam',
                                            name__startswith=start_exchange_name)\
                                    .exclude(name=exchange.name)\
                                    .order_by()

        queries.append(exchange_query)

    linked_exchange_urls = queries[0].union(queries[1],
                                            queries[2],
                                            all=True)
    
    linked_exchange_urls = [get_base_url(link) if not link.startswith('https://t.me') else link for link in linked_exchange_urls]

    exchange.linked_urls = linked_exchange_urls

    if exchange_marker != 'partner' and not exchange.partner_link.startswith('https://t.me'):
        exchange.url = get_base_url(exchange.partner_link)
    else:
        exchange.url = exchange.partner_link

    exchange.icon = try_generate_icon_url(exchange)

    exchange.multiple_name = MultipleName(name=exchange.name,
                                          en_name=exchange.en_name)
    
    exchange.exchange_marker = exchange_marker
    
    return exchange


@new_common_router.get('/exchange_blacklist_detail',
                   response_model=BlackExchangeDetailSchema,
                   response_model_by_alias=False)
def new_get_black_exchange_detail_info(exchange_id: int):
    try:
        exchange = Exchanger.objects.prefetch_related('linked_url_list')\
                                    .get(pk=exchange_id,
                                         active_status='scam')
    except Exception as ex:
        print(ex)
        raise HTTPException(status_code=404,
                            detail='Exchanger with status "scam" not found by given "exchange_id"')
    else:
        linked_urls = [el.url for el in exchange.linked_url_list.all()]

        exchange.linked_urls = linked_urls

        if not exchange.partner_link.startswith('https://t.me'):
            exchange.url = get_base_url(exchange.partner_link)
        else:
            exchange.url = exchange.partner_link

        exchange.icon = try_generate_icon_url(exchange)

        exchange.multiple_name = MultipleName(name=exchange.name,
                                              en_name=exchange.en_name)
                
        return exchange


# @common_router.get('/exchange_detail',
#                    response_model=NewDetailExchangeSchema,
#                    response_model_by_alias=False)
def get_exchange_detail_info(exchange_id: int,
                             exchange_marker: str):

    exchange = get_exchange(exchange_id,
                            exchange_marker)
    exchange = get_exchange_with_direction_count(exchange,
                                                 exchange_id,
                                                 exchange_marker)
    exchange = exchange.first()

    review_counts = (
        NewBaseReview.objects
        .filter(moderation=True,
                exchange_name=exchange.name)
        .values('exchange_name')
        .annotate(
            positive_count=Count('id', filter=Q(grade='1') & Q(review_from__in=('moneyswap', 'ai'))),
            neutral_count=Count('id', filter=Q(grade='0') & Q(review_from__in=('moneyswap', 'ai'))),
            negative_count=Count('id', filter=Q(grade='-1') & Q(review_from__in=('moneyswap', 'ai'))),
        )
    )

    review_map = {r['exchange_name']: r for r in review_counts}

    # print(review_map)
    try:
        exchange.review_set = ReviewCountSchema(positive=review_map[exchange.name]['positive_count'],
                                                neutral=review_map[exchange.name]['neutral_count'],
                                                negative=review_map[exchange.name]['negative_count'])
    except KeyError:
        exchange.review_set = ReviewCountSchema(positive=0,
                                                neutral=0,
                                                negative=0)
    # exchange.review_set = ReviewCountSchema(positive=review_map[exchange.name]['positive_count'],
    #                                         neutral=review_map[exchange.name]['neutral_count'],
    #                                         negative=review_map[exchange.name]['negative_count'])
    exchange.icon = try_generate_icon_url(exchange)

    exchange.multiple_name = MultipleName(name=exchange.name,
                                          en_name=exchange.en_name)
    
    # if exchange.course_count is None or not exchange.course_count.isdigit():
    #     exchange.course_count = None
    # else:
    #     exchange.course_count = int(exchange.course_count)
    # print(exchange.direction_count)
    # print(exchange.city_direction_count)
    # print(exchange.country_direction_count)
    exchange.course_count = exchange.direction_count

    if exchange.course_count == 0 and exchange.active_status == 'active':
        exchange.active_status = 'inactive'

    elif exchange.active_status != 'active':
        exchange.course_count = 0
    
    return exchange


# @common_router.get('/direction_pair_by_exchange',
#                    response_model=list[DirectionSideBarSchema],
#                    response_model_by_alias=False)
def new_get_all_directions_by_exchange(exchange_id: int,
                                   exchange_marker: str):
    # print(len(connection.queries))
    exchange = get_exchange(exchange_id,
                            exchange_marker)
    
    exchange_directions_queryset = get_exchange_directions(exchange,
                                                           exchange_marker)
    
    if exchange_marker == 'both':
        try:
            no_cash_exchange_directions = exchange_directions_queryset\
                                            .select_related('exchange',
                                                            'direction',
                                                            'direction__valute_from',
                                                            'direction__valute_to')\
                                            .annotate(pair_count=Count('direction__exchange_directions',
                                                                    filter=Q(direction__exchange_directions__direction_id=F('direction_id'),
                                                                                direction__exchange_directions__is_active=True,
                                                                                direction__exchange_directions__exchange__is_active=True)),
                                                    marker=annotate_string_field('no_cash'))\
                                            .filter(exchange__is_active=True,
                                                    is_active=True)
            
            cash_exchange_directions_queryset = cash_models.Exchange.objects.get(name=exchange.first().name).directions

            #
            prefetch_cash = Prefetch('direction__exchange_directions',
                                     queryset=cash_models.ExchangeDirection.objects.select_related('exchange')\
                                                                                    .filter(exchange__is_active=True,
                                                                                            is_active=True))
            #
            cash_exchange_directions = cash_exchange_directions_queryset\
                                            .select_related('exchange',
                                                            'direction',
                                                            'direction__valute_from',
                                                            'direction__valute_to')\
                                            .prefetch_related(prefetch_cash)\
                                            .annotate(marker=annotate_string_field('cash'))\
                                            .filter(exchange__is_active=True,
                                                    is_active=True)

                                            # .annotate(pair_count=Count('direction__exchange_directions',
                                            #                         filter=Q(direction__exchange_directions__direction_id=F('direction_id'),
                                            #                                     direction__exchange_directions__is_active=True,
                                            #                                     direction__exchange_directions__exchange__is_active=True)),
            no_cash_prefetch_queryset = Prefetch('direction__partner_directions',
                                        partner_models.NonCashDirection.objects.filter(is_active=True,
                                                                                pk=F('pk')))
            prefetch_queryset = Prefetch('direction__partner_directions',
                                        partner_models.Direction.objects.filter(is_active=True,
                                                                                pk=F('pk')))

            no_cash_exchange_directions = no_cash_exchange_directions.prefetch_related(no_cash_prefetch_queryset)
            cash_exchange_directions = cash_exchange_directions.prefetch_related(prefetch_queryset)

            # exchange_directions = no_cash_exchange_directions.union(cash_exchange_directions)
            exchange_directions = list(no_cash_exchange_directions) + list(cash_exchange_directions)

            # print([el.marker for el in exchange_directions])

            check_direction_id_set = set()
            exchange_direction_list = []

            for exchange_direction in exchange_directions:
                if exchange_direction.direction_id not in check_direction_id_set:
                    #
                    if exchange_direction.marker == 'cash':
                        exchange_direction.pair_count = len(exchange_direction.direction.exchange_directions.all())
                    #
                    # exchange_direction_list.append(exchange_direction)
                    check_direction_id_set.add(exchange_direction.direction_id)
                
                    valute_from_icon = try_generate_icon_url(exchange_direction.direction.valute_from)
                    exchange_direction.direction.valute_from.icon_url = valute_from_icon

                    valute_to_icon = try_generate_icon_url(exchange_direction.direction.valute_to)
                    exchange_direction.direction.valute_to.icon_url = valute_to_icon

                    exchange_direction.valuteFrom = ValuteModel.model_construct(**exchange_direction.direction.valute_from.__dict__)
                    exchange_direction.valuteTo = ValuteModel.model_construct(**exchange_direction.direction.valute_to.__dict__)
                    exchange_direction.direction_type = exchange_direction.marker
                    
                    if exchange_direction.marker != 'no_cash':
                        # exchange_direction.direction_type = 'cash'
                        similar_partner_direction_count = len(exchange_direction.direction.partner_directions.all())
                        exchange_direction.pair_count += similar_partner_direction_count

                    if exchange_direction.pair_count > 0:
                        exchange_direction_list.append(exchange_direction)
        except Exception as ex:
            print(ex)
            raise HTTPException(status_code=400,
                                detail='error with "both" marker')    
        # for conn in connection.queries:
        #     print(conn)
        #     print('*' * 8)
        # print(len(connection.queries))
        return exchange_direction_list

    else:
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
    # for conn in connection.queries:
    #     print(conn)
    #     print('*' * 8)
    # print(len(connection.queries))
    return exchange_direction_list


@new_common_router.get('/direction_pair_by_exchange',
                   response_model=list[DirectionSideBarSchema],
                   response_model_by_alias=False)
def new_get_all_directions_by_exchange(exchange_id: int):

    no_cash_exchange_directions = no_cash_models.NewExchangeDirection.objects.select_related('exchange',
                                                                                       'direction__valute_from',
                                                                                       'direction__valute_to')\
                                                                        .filter(exchange_id=exchange_id,
                                                                                is_active=True,
                                                                                exchange__is_active=True)\
                                                                        .values_list('direction_id', flat=True)\
                                                                        .order_by()

    partner_noncash_exchange_directions = partner_models.NewNonCashDirection.objects.select_related('exchange',
                                                                                                    'direction__valute_from',
                                                                                                    'direction__valute_to')\
                                                                        .filter(exchange_id=exchange_id,
                                                                                is_active=True,
                                                                                exchange__is_active=True)\
                                                                        .values_list('direction_id', flat=True)\
                                                                        .order_by()

    no_cash_direction_pks = no_cash_exchange_directions.union(partner_noncash_exchange_directions)

    cash_exchange_directions = cash_models.NewExchangeDirection.objects.select_related('exchange',
                                                                                       'direction__valute_from',
                                                                                       'direction__valute_to')\
                                                                        .filter(exchange_id=exchange_id,
                                                                                is_active=True,
                                                                                exchange__is_active=True)\
                                                                        .values_list('direction_id', flat=True)\
                                                                        .order_by()

    partner_city_exchange_directions = partner_models.NewDirection.objects.select_related('exchange',
                                                                                       'direction__valute_from',
                                                                                       'direction__valute_to')\
                                                                        .filter(exchange_id=exchange_id,
                                                                                is_active=True,
                                                                                exchange__is_active=True)\
                                                                        .values_list('direction_id', flat=True)\
                                                                        .order_by()

    partner_country_exchange_directions = partner_models.NewCountryDirection.objects.select_related('exchange',
                                                                                                    'direction__valute_from',
                                                                                                    'direction__valute_to')\
                                                                        .filter(exchange_id=exchange_id,
                                                                                is_active=True,
                                                                                exchange__is_active=True)\
                                                                        .values_list('direction_id', flat=True)\
                                                                        .order_by()

    cash_direction_pks = cash_exchange_directions.union(partner_city_exchange_directions,
                                                        partner_country_exchange_directions)

    no_cash_exchange_direction_subquery = no_cash_models.NewExchangeDirection.objects.select_related('exchange')\
        .filter(
            direction_id=OuterRef('pk'),
            is_active=True,
            exchange__is_active=True,
        ).values('direction_id').annotate(pair_count=Count('id')).values('pair_count')

    partner_no_cash_exchange_direction_subquery = partner_models.NewNonCashDirection.objects.select_related('exchange')\
        .filter(
            direction_id=OuterRef('pk'),
            is_active=True,
            exchange__is_active=True,
        ).values('direction_id').annotate(pair_count=Count('id')).values('pair_count')


    no_cash_directions = no_cash_models.NewDirection.objects.select_related('valute_from',
                                                                            'valute_to').filter(pk__in=no_cash_direction_pks)\
                                                            .annotate(auto_pair_count=Subquery(no_cash_exchange_direction_subquery),
                                                                      partner_pair_count=Subquery(partner_no_cash_exchange_direction_subquery),
                                                                      direction_marker=annotate_string_field('no_cash'))\
                                                            .filter(Q(auto_pair_count__gt=0) | Q(partner_pair_count__gt=0))

    auto_pairs = (
        cash_models.NewExchangeDirection.objects
        .filter(is_active=True, exchange__is_active=True)
        .values('direction_id')
        .annotate(auto_pair_count=Count('id'))
    )

    partner_city_pairs = (
        partner_models.NewDirection.objects
        .filter(is_active=True, exchange__is_active=True)
        .values('direction_id')
        .annotate(partner_city_pair_count=Count('id'))
    )

    partner_country_pairs = (
        partner_models.NewCountryDirection.objects
        .filter(is_active=True, exchange__is_active=True)
        .values('direction_id')
        .annotate(partner_country_pair_count=Count('id'))
    )

    cash_directions = (
        cash_models.NewDirection.objects
        .select_related('valute_from', 'valute_to')
        .filter(pk__in=cash_direction_pks)
        .annotate(
            auto_pair_count=Coalesce(
                Subquery(auto_pairs.filter(direction_id=OuterRef('pk')).values('auto_pair_count')[:1]), 0
            ),
            partner_city_pair_count=Coalesce(
                Subquery(partner_city_pairs.filter(direction_id=OuterRef('pk')).values('partner_city_pair_count')[:1]), 0
            ),
            partner_country_pair_count=Coalesce(
                Subquery(partner_country_pairs.filter(direction_id=OuterRef('pk')).values('partner_country_pair_count')[:1]), 0
            ),
            direction_marker=annotate_string_field('cash'),
        )
        .filter(
            Q(auto_pair_count__gt=0) |
            Q(partner_city_pair_count__gt=0) |
            Q(partner_country_pair_count__gt=0)
        )
    )

    direction_pair_list = []
    for direction_query in (no_cash_directions, cash_directions):
        for direction in direction_query:
            valute_from_icon = try_generate_icon_url(direction.valute_from)
            direction.valute_from.icon_url = valute_from_icon

            valute_to_icon = try_generate_icon_url(direction.valute_to)
            direction.valute_to.icon_url = valute_to_icon

            pair_count = 0
            if direction.direction_marker == 'no_cash':
                for _count in (direction.auto_pair_count, direction.partner_pair_count):
                    if _count:
                        pair_count += _count

            else:
                for _count in (direction.auto_pair_count,
                               direction.partner_city_pair_count,
                               direction.partner_country_pair_count):
                    if _count:
                        pair_count += _count

            direction_dict = {
                'valuteFrom': ValuteModel.model_construct(**direction.valute_from.__dict__),
                'valuteTo': ValuteModel.model_construct(**direction.valute_to.__dict__),
                'direction_type': direction.direction_marker,
                'pair_count': pair_count,
            }
            direction_pair_list.append(direction_dict)

    return sorted(direction_pair_list,
                  key= lambda el: -el.get('pair_count'))


@common_router.post('/feedback_form')
def add_feedback_form(feedback: FeedbackFormSchema):
    if feedback.reasons.lower() == 'проблема с обменником':
        feedback.reasons = 'Проблемма с обменником'

    check_datetime = datetime.now() - timedelta(minutes=2)
    
    if FeedbackForm.objects.filter(reasons=feedback.reasons,
                                   username=feedback.username,
                                   email=feedback.email,
                                   time_create__gt=check_datetime)\
                            .exists():
        raise HTTPException(status_code=423)
        # return {'status': 'success',
        #         'details': 'duble feedback has been ignored'}

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
# @common_router.get('/actual_course')
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


@new_common_router.get('/actual_course')
def new_get_actual_course_for_direction(valute_from: str,
                                        valute_to: str):
    valute_from, valute_to = valute_from.upper(), valute_to.upper()
    
    direction = cash_models.NewDirection.objects\
                            .filter(valute_from_id=valute_from,
                                    valute_to_id=valute_to)\
                            .first()
    
    if not direction:
        direction = no_cash_models.NewDirection.objects\
                                    .filter(valute_from_id=valute_from,
                                            valute_to_id=valute_to).first()
        
    if not direction:
        raise HTTPException(status_code=404,
                            detail=f'Direction {valute_from} -> {valute_to} not found')
    
    return generate_actual_course(direction) 


# @common_router.get('/top_exchanges',
#                    response_model=list[TopExchangeSchema],
#                    response_model_by_alias=False)
def new_get_top_exchanges():
    limit = 10
    # print(len(connection.queries))
    # review_counts = new_get_reviews_count_filters(marker='exchange')

    review_counts = (
        NewBaseReview.objects
        .filter(moderation=True)
        .values('exchange_name')
        .annotate(
            positive_count=Count('id', filter=Q(grade='1') & Q(review_from__in=('moneyswap', 'ai'))),
            neutral_count=Count('id', filter=Q(grade='0') & Q(review_from__in=('moneyswap', 'ai'))),
            negative_count=Count('id', filter=Q(grade='-1') & Q(review_from__in=('moneyswap', 'ai'))),
        )
    )

    review_map = {r['exchange_name']: r for r in review_counts}

    no_cash_exchanges = new_generate_top_exchanges_query_by_model('no_cash')

    cash_exchanges = new_generate_top_exchanges_query_by_model('cash')

    partner_exchanges = new_generate_top_exchanges_query_by_model('partner')
    
    top_exchanges = no_cash_exchanges.union(cash_exchanges,
                                            partner_exchanges)
                                                
    for top_exchange in top_exchanges:
        try:
            top_exchange['reviews'] = ReviewCountSchema(positive=review_map[top_exchange['name']]['positive_count'],
                                                        neutral=review_map[top_exchange['name']]['neutral_count'],
                                                        negative=review_map[top_exchange['name']]['negative_count'])
        except Exception as ex:
            top_exchange['reviews'] = ReviewCountSchema(positive=0,
                                                        neutral=0,
                                                        negative=0)
            
        top_exchange['icon'] = generate_image_icon2(top_exchange['icon_url'])


    return sorted(top_exchanges,
                  key=lambda el: el.get('link_count'),
                  reverse=True)[:limit]


@new_common_router.get('/top_exchanges',
                   response_model=list[NewTopExchangeSchema],
                   response_model_by_alias=False)
def get_top_exchanges():
    limit = 10

    review_count_dict = get_review_count_dict()

    def link_counts():
        models = [
            no_cash_models.NewExchangeLinkCount,
            cash_models.NewExchangeLinkCount,
            partner_models.NewExchangeLinkCount,
            partner_models.NewCountryExchangeLinkCount,
            partner_models.NewNonCashExchangeLinkCount,
        ]
        counts = Counter()
        for m in models:
            for r in m.objects.values('exchange_id').annotate(total=Sum('count')):
                counts[r['exchange_id']] += r['total']
        return counts

    counts = link_counts()

    top_exchanger_ids = [exchange_id for exchange_id, total in counts.most_common(limit)]

    top_exchangers = (
        Exchanger.objects
        .filter(pk__in=top_exchanger_ids)
        .values('pk',
                'name',
                'icon_url')
    )
                                                
    for top_exchange in top_exchangers:
        top_exchange['total_link_count'] = counts.get(top_exchange['pk'], 0)
        # print(top_exchange['total_link_count'])
        try:
            top_exchange['reviews'] = ReviewCountSchema(positive=review_count_dict[top_exchange['pk']]['positive_count'],
                                                        neutral=review_count_dict[top_exchange['pk']]['neutral_count'],
                                                        negative=review_count_dict[top_exchange['pk']]['negative_count'])
        except Exception as ex:
            top_exchange['reviews'] = ReviewCountSchema(positive=0,
                                                        neutral=0,
                                                        negative=0)
            
        top_exchange['icon'] = generate_image_icon2(top_exchange['icon_url'])

    return sorted(top_exchangers, key=lambda el: (-el['total_link_count'],
                                                   el['name']))


# @common_router.get('/top_coins',
#                    response_model=list[TopCoinSchema],
#                    response_model_by_alias=False)
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


@new_common_router.get('/top_coins',
                   response_model=list[TopCoinSchema],
                   response_model_by_alias=False)
def new_get_top_coins():
    usd = 'CASHUSD'
    limit = 10
    top_coins = cash_models.NewDirection.objects.select_related('valute_from',
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


# @review_router.get('/reviews_by_exchange',
#                    response_model=NewReviewsByExchangeSchema)
def new_get_reviews_by_exchange(exchange_name: str,
                            page: int,
                            review_id: int = None,
                            element_on_page: int = None,
                            grade_filter: int = None):
    if page < 1:
        raise HTTPException(status_code=400,
                            detail='Параметр "page" должен быть положительным числом')
    
    if element_on_page is not None:
        if element_on_page < 1:
            raise HTTPException(status_code=400,
                                detail='Параметр "element_on_page" должен быть положительным числом')
    
    user_comment_subquery = NewBaseComment.objects.filter(
        review_id=OuterRef('pk'),
        moderation=True,
        review_from='moneyswap',
    ).values('review_id').annotate(
        total_count=Coalesce(Count('id'), Value(0))
    ).values('total_count')

    admin_comment_subquery = NewBaseAdminComment.objects.filter(
        review_id=OuterRef('pk'),
    ).values('review_id').annotate(
        total_count=Coalesce(Count('id'), Value(0))
    ).values('total_count')


    reviews = NewBaseReview.objects.select_related('guest')\
                                    .annotate(admin_comment_count=Subquery(admin_comment_subquery))\
                                    .annotate(user_comment_count=Subquery(user_comment_subquery))\
                                    .annotate(comment_count=Coalesce(F('admin_comment_count'), Value(0)) + Coalesce(F('user_comment_count'), Value(0)))\
                                    .filter(exchange_name=exchange_name,
                                            review_from__in=('moneyswap', 'ai'),
                                            moderation=True)\
                                    # .order_by('-time_create')

    if review_id:
        reviews = reviews.filter(pk=review_id)
        
        review_list = []

        for review in reviews:
            date, time = review.time_create.astimezone().strftime('%d.%m.%Y %H:%M').split()

            if review.username is None:
                if review.guest:
                    if review.guest.username:
                        review.username = review.guest.username
                    elif review.guest.first_name:
                        review.username = review.guest.first_name
                    else:
                        review.username = 'Гость'
                else:
                    review.username = 'Гость'
                        
            review.review_date = date
            review.review_time = time
            review_list.append(ReviewViewSchema(**review.__dict__))

        return NewReviewsByExchangeSchema(page=page,
                                    pages=1,
                                    exchange_name=exchange_name,
                                    element_on_page=len(review_list),
                                    content=review_list)
    
    reviews = reviews.order_by('-time_create')

    if grade_filter is not None:
        reviews = reviews.filter(grade=str(grade_filter))

    reviews = reviews.order_by('-time_create').all()
    
    pages = 1 if element_on_page is None else ceil(len(reviews) / element_on_page)

    if element_on_page:
        offset = (page - 1) * element_on_page
        limit = offset + element_on_page
        reviews = reviews[offset:limit]

    review_list = []
    for review in reviews:
        date, time = review.time_create.astimezone().strftime('%d.%m.%Y %H:%M').split()
        if review.username is None:
            if review.guest:
                if review.guest.username:
                    review.username = review.guest.username
                elif review.guest.first_name:
                    review.username = review.guest.first_name
                else:
                    review.username = 'Гость'
            else:
                review.username = 'Гость'

        review.review_date = date
        review.review_time = time
        review_list.append(ReviewViewSchema(**review.__dict__))

    return NewReviewsByExchangeSchema(page=page,
                                   pages=pages,
                                   exchange_name=exchange_name,
                                   element_on_page=len(review_list),
                                   content=review_list)


@new_review_router.get('/reviews_by_exchange',
                   response_model=ReviewsByExchangeSchema)
def get_reviews_by_exchange(exchange_id: int,
                            page: int,
                            review_id: int = None,
                            element_on_page: int = None,
                            grade_filter: int = None):
    if page < 1:
        raise HTTPException(status_code=400,
                            detail='Параметр "page" должен быть положительным числом')
    
    if element_on_page is not None:
        if element_on_page < 1:
            raise HTTPException(status_code=400,
                                detail='Параметр "element_on_page" должен быть положительным числом')
    
    user_comment_subquery = Comment.objects.filter(
        review_id=OuterRef('pk'),
        moderation=True,
        review_from='moneyswap',
    ).values('review_id').annotate(
        total_count=Coalesce(Count('id'), Value(0))
    ).values('total_count')

    admin_comment_subquery = AdminComment.objects.filter(
        review_id=OuterRef('pk'),
    ).values('review_id').annotate(
        total_count=Coalesce(Count('id'), Value(0))
    ).values('total_count')


    reviews = Review.objects.select_related('guest')\
                                    .annotate(admin_comment_count=Subquery(admin_comment_subquery))\
                                    .annotate(user_comment_count=Subquery(user_comment_subquery))\
                                    .annotate(comment_count=Coalesce(F('admin_comment_count'), Value(0)) + Coalesce(F('user_comment_count'), Value(0)))\
                                    .filter(exchange_id=exchange_id,
                                            review_from__in=('moneyswap', 'ai'),
                                            moderation=True)\

    if review_id:
        reviews = reviews.filter(pk=review_id)
        
        review_list = []

        for review in reviews:
            date, time = review.time_create.astimezone().strftime('%d.%m.%Y %H:%M').split()

            if review.username is None:
                if review.guest:
                    if review.guest.username:
                        review.username = review.guest.username
                    elif review.guest.first_name:
                        review.username = review.guest.first_name
                    else:
                        review.username = 'Гость'
                else:
                    review.username = 'Гость'
                        
            review.review_date = date
            review.review_time = time
            review_list.append(ReviewViewSchema(**review.__dict__))

        return ReviewsByExchangeSchema(page=page,
                                    pages=1,
                                    exchange_id=exchange_id,
                                    element_on_page=len(review_list),
                                    content=review_list)
    
    reviews = reviews.order_by('-time_create')

    if grade_filter is not None:
        reviews = reviews.filter(grade=str(grade_filter))

    reviews = reviews.order_by('-time_create').all()
    
    pages = 1 if element_on_page is None else ceil(len(reviews) / element_on_page)

    if element_on_page:
        offset = (page - 1) * element_on_page
        limit = offset + element_on_page
        reviews = reviews[offset:limit]

    review_list = []
    for review in reviews:
        date, time = review.time_create.astimezone().strftime('%d.%m.%Y %H:%M').split()
        if review.username is None:
            if review.guest:
                if review.guest.username:
                    review.username = review.guest.username
                elif review.guest.first_name:
                    review.username = review.guest.first_name
                else:
                    review.username = 'Гость'
            else:
                review.username = 'Гость'

        review.review_date = date
        review.review_time = time
        review_list.append(ReviewViewSchema(**review.__dict__))

    return ReviewsByExchangeSchema(page=page,
                                   pages=pages,
                                   exchange_id=exchange_id,
                                   element_on_page=len(review_list),
                                   content=review_list)


# @review_router.post('/add_review_by_exchange')
def new_add_review_by_exchange(review: NewAddReviewSchema):
    check_exchage_by_name(review.exchange_name)

    new_check_perms_for_adding_review(exchange_name=review.exchange_name,
                                      tg_id=review.tg_id)

    if review.grade != -1 and review.transaction_id is not None:
        raise HTTPException(status_code=423,
                            detail='Неотрицательный отзыв не требует номера транзакции')
    
    if not Guest.objects.filter(tg_id=review.tg_id).exists():
        raise HTTPException(status_code=404,
                            detail='User don`t exist in db')

    new_review = {
        'exchange_name': review.exchange_name,
        'guest_id': review.tg_id,
        'grade': review.grade,
        'text': review.text,
        'time_create': datetime.now(),
    }

    if review.transaction_id:
        new_review.update({'transaction_id': review.transaction_id})

    try:
        new_review_record = NewBaseReview.objects.create(**new_review)
    except Exception:
        raise HTTPException(status_code=400,
                            detail='Переданы некорректные данные')
    else:
        # уведомление об отзыве в бота уведомлений
        async_to_sync(send_review_notifitation)(new_review_record.pk)

        return {'status': 'success'}
    

@new_review_router.post('/add_review_by_exchange')
def add_review_by_exchange(review: AddReviewSchema):

    if not Exchanger.objects.filter(pk=review.exchange_id).exists():
        raise HTTPException(status_code=404,
                            detail=f'Exchanger not found by given "exchange_id"')

    check_perms_for_adding_review(exchange_id=review.exchange_id,
                                  tg_id=review.tg_id)

    if review.grade != -1 and review.transaction_id is not None:
        raise HTTPException(status_code=423,
                            detail='Неотрицательный отзыв не требует номера транзакции')
    
    if not Guest.objects.filter(tg_id=review.tg_id).exists():
        raise HTTPException(status_code=404,
                            detail='User doesn`t exists in db')

    new_review = {
        'exchange_id': review.exchange_id,
        'guest_id': review.tg_id,
        'grade': review.grade,
        'text': review.text,
        'time_create': timezone.now(),
    }

    if review.transaction_id:
        new_review.update({'transaction_id': review.transaction_id})

    try:
        new_review_record = Review.objects.create(**new_review)
    except Exception:
        raise HTTPException(status_code=400,
                            detail='Переданы некорректные данные')
    else:
        # уведомление об отзыве в бота уведомлений
        async_to_sync(new_send_review_notifitation)(new_review_record.pk)

        return {'status': 'success'}
    

# @review_router.get('/check_user_review_permission')
def check_user_review_permission(exchange_name: str,
                                 tg_id: int):
    return new_check_perms_for_adding_review(exchange_name,
                                             tg_id)


@new_review_router.get('/check_user_review_permission')
def new_check_user_review_permission(exchange_id: int,
                                     tg_id: int):
    return check_perms_for_adding_review(exchange_id,
                                         tg_id)


# @review_router.get('/get_comments_by_review',
#                    response_model=list[CommentSchema],
#                    response_model_exclude_none=True)
def new_get_comments_by_review(review_id: int):
    try:
        review = NewBaseReview.objects.get(pk=review_id)

        exchange_admin = ExchangeAdmin.objects.filter(exchange_name=review.exchange_name).first()
    except Exception as ex:
        print(ex)
        raise HTTPException(status_code=404,
                            detail='Review does not exist')
    
    user_comments = NewBaseComment.objects.select_related('review')\
                                    .annotate(role=annotate_string_field('user'))\
                                    .filter(review_id=review_id,
                                            review_from='moneyswap',
                                            moderation=True)\
                                    .values('id',
                                            'time_create',
                                            'text',
                                            'username',
                                            'role',
                                            'guest_id')\
                                    # .order_by('time_create')
    
    admin_comments = NewBaseAdminComment.objects.select_related('review')\
                                    .annotate(username=annotate_string_field('Администрация MoneySwap'))\
                                    .annotate(guest_id=annotate_number_field(1))\
                                    .annotate(role=annotate_string_field('admin'))\
                                    .filter(review_id=review_id)\
                                    .values('id',
                                            'time_create',
                                            'text',
                                            'username',
                                            'role',
                                            'guest_id')\
                                    # .order_by('time_create')
    
    comments = user_comments.union(admin_comments)

    if not comments:
        raise HTTPException(status_code=404)
    
    comment_list = []

    for comment in sorted(comments, key=lambda el: el.get('time_create')):

        if comment.get('role') == 'user':
            if exchange_admin and str(comment.get('guest_id')) == str(exchange_admin.user_id):

                comment['role'] = CommentRoleEnum.exchenger
                comment['username'] = f'Администратор {review.exchange_name}'
            else:
                if not comment.get('username'):
                    comment['username'] = f'Гость'

        date, time = comment.get('time_create').astimezone().strftime('%d.%m.%Y %H:%M').split()
        comment['comment_date'] = date
        comment['comment_time'] = time

        comment_list.append(comment)
    #
    # print(len(connection.queries))
    return comment_list


@new_review_router.get('/get_comments_by_review',
                   response_model=list[CommentSchema],
                   response_model_exclude_none=True)
def get_comments_by_review(review_id: int):
    try:
        user_comment_queryset = Comment.objects.select_related('guest')\
                                                .filter(review_id=review_id,
                                                        review_from='moneyswap',
                                                        moderation=True)\
                                                .annotate(role=annotate_string_field('user'))
        user_comment_prefetch = Prefetch('comments',
                                         queryset=user_comment_queryset)
        
        admin_comment_queryset = AdminComment.objects.filter(review_id=review_id)\
                                                    .annotate(role=annotate_string_field('admin'))\
                                                    .annotate(username=annotate_string_field('Администрация MoneySwap'))\
                                                    .annotate(guest_id=annotate_number_field(1))
        admin_comment_prefetch = Prefetch('admin_comments',
                                         queryset=admin_comment_queryset)
        
        review = Review.objects.select_related('exchange')\
                                .prefetch_related(user_comment_prefetch,admin_comment_prefetch)\
                                .get(pk=review_id)

        exchange_admin = NewExchangeAdmin.objects.filter(exchange_id=review.exchange_id).first()
    except Exception as ex:
        print(ex)
        raise HTTPException(status_code=404,
                            detail='Review not found by given "review_id"')
    
    comments = list(review.comments.all()) + list(review.admin_comments.all())

    if not comments:
        raise HTTPException(status_code=404,
                            detail='Comments not found for review by given "review_id"')
    
    comment_list = []

    for comment in sorted(comments, key=lambda el: el.time_create):
        comment_dict = {
            'id': comment.pk,
            'text': comment.text,
        }
        if comment.role == 'user':
            if exchange_admin and str(comment.guest_id) == str(exchange_admin.user_id):

                comment_dict['role'] = CommentRoleEnum.exchenger
                comment_dict['username'] = f'Администратор {review.exchange.name}'
            else:
                comment_dict['role'] = CommentRoleEnum.user
                if comment.username is None:
                    if comment.guest:
                        if comment.guest.username:
                            comment_dict['username'] = comment.guest.username
                        elif comment.guest.first_name:
                            comment_dict['username'] = comment.guest.first_name
                        else:
                            comment_dict['username'] = 'Гость'
                    else:
                        comment_dict['username'] = 'Гость'
                else:
                    comment_dict['username'] = 'Гость'
        else:
            comment_dict['role'] = CommentRoleEnum.admin
            comment_dict['username'] = comment.username

        date, time = comment.time_create.astimezone().strftime('%d.%m.%Y %H:%M').split()
        comment_dict['comment_date'] = date
        comment_dict['comment_time'] = time

        comment_list.append(comment_dict)
    #
    # print(len(connection.queries))
    return comment_list


# @review_router.post('/add_comment_by_review')
def new_add_comment_by_comment(comment: NewAddCommentSchema):

    new_check_perms_for_adding_comment(review_id=comment.review_id,
                                       user_id=comment.tg_id)

    new_comment = {
        'review_id': comment.review_id,
        'guest_id': comment.tg_id,
        'grade': comment.grade,
        'text': comment.text,
        'time_create': datetime.now(),
    }

    try:
        new_comment_record = NewBaseComment.objects.create(**new_comment)
    except Exception:
        raise HTTPException(status_code=400,
                            detail='Переданы некорректные данные')
    else:
        # уведомление об отзыве в бота уведомлений
        async_to_sync(send_comment_notifitation)(new_comment_record.pk)

        return {'status': 'success'}
    

@new_review_router.post('/add_comment_by_review')
def add_comment_by_comment(comment: NewAddCommentSchema):

    check_perms_for_adding_comment(review_id=comment.review_id,
                                   user_id=comment.tg_id)

    new_comment = {
        'review_id': comment.review_id,
        'guest_id': comment.tg_id,
        'grade': comment.grade, # зачем?
        'text': comment.text,
        'time_create': timezone.now(),
    }

    try:
        new_comment_record = Comment.objects.create(**new_comment)
    except Exception:
        raise HTTPException(status_code=400,
                            detail='Переданы некорректные данные')
    else:
        # уведомление об отзыве в бота уведомлений
        async_to_sync(new_send_comment_notifitation)(new_comment_record.pk)

        return {'status': 'success'}


# @review_router.get('/check_user_comment_permission')
def new_check_user_review_permission(review_id: int,
                                     tg_id: int):
    return new_check_perms_for_adding_comment(review_id,
                                              tg_id)


@new_review_router.get('/check_user_comment_permission')
def check_user_review_permission(review_id: int,
                                 tg_id: int):
    return check_perms_for_adding_comment(review_id,
                                              tg_id)


exchange_link_count_dict = {
    'cash': cash_models.ExchangeLinkCount,
    'no_cash': no_cash_models.ExchangeLinkCount,
    'partner': partner_models.ExchangeLinkCount,
}


# @common_router.post('/increase_link_count')
# def increase_link_count(data: ExchangeLinkCountSchema):
#     exchange_link_count: Union[cash_models.ExchangeLinkCount,
#                                no_cash_models.ExchangeLinkCount,
#                                partner_models.ExchangeLinkCount] = exchange_link_count_dict.get(data.exchange_marker)

#     if not exchange_link_count:
#         raise HTTPException(status_code=400,
#                             detail='invalid marker')

#     check_user = Guest.objects.filter(tg_id=data.user_id)

#     if not check_user.exists():
#         raise HTTPException(status_code=400)

#     exchange_link_count_queryset = exchange_link_count.objects\
#                                                 .filter(exchange_id=data.exchange_id,
#                                                         exchange_marker=data.exchange_marker,
#                                                         exchange_direction_id=data.exchange_direction_id,
#                                                         user_id=data.user_id)
#     if not exchange_link_count_queryset.exists():
#         try:
#             exchange_link_count_queryset = exchange_link_count.objects.create(user_id=data.user_id,
#                                                                             exchange_id=data.exchange_id,
#                                                                             exchange_marker=data.exchange_marker,
#                                                                             exchange_direction_id=data.exchange_direction_id,
#                                                                             count=1)
#         except IntegrityError:
#             raise HTTPException(status_code=400,
#                                 detail='Constraint error. This row already exists')
#             # return {'status': 'error',
#             #         'details': 'Constraint error. This row already exists'}
#     else:
#         exchange_link_count_queryset.update(count=F('count') + 1)

#     return {'status': 'success'}


new_exchange_link_count_dict = {
    'auto_cash': cash_models.NewExchangeLinkCount,
    'auto_noncash': no_cash_models.NewExchangeLinkCount,
    'city': partner_models.NewExchangeLinkCount,
    'country': partner_models.NewCountryExchangeLinkCount,
    'no_cash': partner_models.NewNonCashExchangeLinkCount,
}


@new_common_router.post('/increase_link_count')
def new_increase_link_count(data: NewExchangeLinkCountSchema):
    exchange_link_count: Union[no_cash_models.NewExchangeLinkCount,
                               cash_models.NewExchangeLinkCount,
                               partner_models.NewExchangeLinkCount,
                               partner_models.NewCountryExchangeLinkCount,
                               partner_models.NewNonCashExchangeLinkCount] = new_exchange_link_count_dict.get(data.direction_marker)

    if not exchange_link_count:
        raise HTTPException(status_code=400,
                            detail='invalid marker')

    check_user = Guest.objects.filter(tg_id=data.user_id)

    if not check_user.exists():
        raise HTTPException(status_code=400,
                            detail='invalid "user_id", User not found')

    exchange_link_count_queryset = exchange_link_count.objects\
                                                .filter(exchange_id=data.exchange_id,
                                                        exchange_direction_id=data.exchange_direction_id,
                                                        user_id=data.user_id)
    
    if not check_exchange_direction_by_exchanger(data):
        raise HTTPException(status_code=423,
                            detail=f'ExchageDirection by given "exchange_direction_id" not found by given "exchange_id"')

    if not exchange_link_count_queryset.exists():
        try:
            exchange_link_count_queryset = exchange_link_count.objects.create(user_id=data.user_id,
                                                                              exchange_id=data.exchange_id,
                                                                              exchange_direction_id=data.exchange_direction_id,
                                                                              count=1)
        except IntegrityError:
            raise HTTPException(status_code=400,
                                detail='Constraint error. This row already exists')

    else:
        exchange_link_count_queryset.update(count=F('count') + 1)

    return {'status': 'success'}


# @common_router.get('/sitemap_directions',
#                    response_model=NewSiteMapDirectonSchema)
def new_get_directions_for_sitemap(page: int,
                               element_on_page: int = None):
    
    if element_on_page is not None:
        if element_on_page < 1:
            raise HTTPException(status_code=400,
                                detail='Параметр "element_on_page" должен быть положительным числом')
    
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

    directions = no_cash_directions.union(cash_directions,
                                          partner_directions)

    result = []

    pages = 1 if element_on_page is None else ceil(len(directions) / element_on_page)

    if element_on_page:
        offset = (page - 1) * element_on_page
        limit = offset + element_on_page
        directions = directions[offset:limit]

    for direction in directions:
        valute_from, valute_to, exchange_marker, city = direction

        if exchange_marker == 'no_cash':
            city = None

        result.append(
            {
                'valute_from': valute_from,
                'valute_to': valute_to,
                'exchange_marker': exchange_marker,
                'city': city,
            }
        )

    return {
        'page': page,
        'pages': pages,
        'element_on_page': element_on_page,
        'directions': result,
    }


@new_common_router.get('/sitemap_directions',
                   response_model=NewSiteMapDirectonSchema2)
def get_directions_for_sitemap(page: int,
                               element_on_page: int = None):
    
    if element_on_page is not None:
        if element_on_page < 1:
            raise HTTPException(status_code=400,
                                detail='Параметр "element_on_page" должен быть положительным числом')
    
    no_cash_directions = no_cash_models.NewExchangeDirection.objects\
                                .select_related('exchange',
                                                'direction')\
                                .filter(is_active=True,
                                        exchange__is_active=True)\
                                .annotate(direction_marker=annotate_string_field('no_cash'))\
                                .values_list('direction__valute_from',
                                             'direction__valute_to',
                                             'direction_marker',
                                             'exchange__name')\
                                .order_by()\
                                .distinct('direction_id')

    cash_directions = cash_models.NewExchangeDirection.objects\
                                .select_related('exchange',
                                                'direction',
                                                'city')\
                                .filter(is_active=True,
                                        exchange__is_active=True)\
                                .annotate(direction_marker=annotate_string_field('cash'))\
                                .values_list('direction__valute_from',
                                             'direction__valute_to',
                                             'direction_marker',
                                             'city__code_name')\
                                .order_by()\
                                .distinct('direction_id',
                                          'city_id')

    partner_city_directions = partner_models.NewDirection.objects\
                                .select_related('direction',
                                                'exchange',
                                                'city',
                                                'city__city')\
                                .filter(is_active=True,
                                        exchange__is_active=True)\
                                .annotate(direction_marker=annotate_string_field('cash'))\
                                .values_list('direction__valute_from',
                                             'direction__valute_to',
                                             'direction_marker',
                                             'city__city__code_name')\
                                .order_by()\
                                .distinct('direction_id',
                                          'city__city_id')
    partner_noncash_directions = partner_models.NewNonCashDirection.objects\
                                .select_related('exchange',
                                                'direction')\
                                .filter(is_active=True,
                                        exchange__is_active=True)\
                                .annotate(direction_marker=annotate_string_field('no_cash'))\
                                .values_list('direction__valute_from',
                                             'direction__valute_to',
                                             'direction_marker',
                                             'exchange__name')\
                                .order_by()\
                                .distinct('direction_id')
    
    partner_country_directions = partner_models.NewCountryDirection.objects\
                                .select_related('direction',
                                                'exchange',
                                                'country',
                                                'country__country')\
                                .filter(is_active=True,
                                        exchange__is_active=True)\
                                .prefetch_related('country__country__cities',
                                                  'country__exclude_cities')\
                                .annotate(direction_marker=annotate_string_field('cash'))\
                                .order_by()\

    partner_country_direction_set = set()
    for country_direction in partner_country_directions:
        cities = [city.code_name for city in country_direction.country.country.cities.all()]
        exclude_cities = {city.code_name for city in country_direction.country.exclude_cities.all()}
        
        for city in cities:
            if city not in exclude_cities:
                direction_tuple = (
                    country_direction.direction.valute_from_id,
                    country_direction.direction.valute_to_id,
                    country_direction.direction_marker,
                    city,
                )
                if direction_tuple not in partner_country_direction_set:
                    partner_country_direction_set.add(direction_tuple)

    directions = no_cash_directions.union(cash_directions,
                                          partner_city_directions,
                                          partner_noncash_directions)

    result = []

    all_directions = list(set(directions) | partner_country_direction_set)

    pages = 1 if element_on_page is None else ceil(len(all_directions) / element_on_page)

    # print(len(all_directions))

    if element_on_page:
        offset = (page - 1) * element_on_page
        limit = offset + element_on_page
        all_directions = all_directions[offset:limit]

    for direction in all_directions:
        valute_from, valute_to, direction_marker, city = direction

        if direction_marker == 'no_cash':
            city = None

        result.append(
            {
                'valute_from': valute_from,
                'valute_to': valute_to,
                'direction_marker': direction_marker,
                'city': city,
            }
        )

    return {
        'page': page,
        'pages': pages,
        'element_on_page': element_on_page,
        'directions': result,
    }