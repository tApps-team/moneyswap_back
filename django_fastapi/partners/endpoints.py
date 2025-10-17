from datetime import datetime, timedelta
from typing import Literal, Union

from fastapi import APIRouter
from fastapi.exceptions import HTTPException

from django.utils import timezone
from django.db import connection, transaction
from django.db.models import Q, Prefetch, F
from django.db.utils import IntegrityError
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist

from django_celery_beat.models import IntervalSchedule

from asgiref.sync import async_to_sync

from cash.models import Country, City, Direction as CashDirection

from no_cash.models import Direction as NoCashDirection

from general_models.utils.endpoints import (get_valute_json,
                                            get_valute_json_3,
                                            get_valute_json_4,
                                            try_generate_icon_url)
from general_models.utils.tasks import make_valid_values_for_dict
from general_models.utils.periodic_tasks import get_or_create_schedule
from general_models.schemas import MultipleName, MultipleName2
from general_models.models import (ExchangeAdmin,
                                   NewExchangeAdmin,
                                   ExchangeAdminOrder,
                                   NewExchangeAdminOrder,
                                   Exchanger,
                                   Valute,
                                   NewValute,
                                   Guest)

import cash.models as cash_models
import no_cash.models as no_cash_models
import partners.models as partner_models

from .models import (CustomUser, PartnerCity,
                     Direction,
                     Exchange,
                     WorkingDay,
                     PartnerCountry,
                     CountryDirection,
                     QRValutePartner,
                     Bankomat,
                     ExchangeLinkCount,
                     CountryExchangeLinkCount,
                     NonCashExchangeLinkCount,
                     DirectionRate,
                     CountryDirectionRate,
                     NonCashDirection,
                     NonCashDirectionRate)

from .auth.endpoints import partner_dependency, new_partner_dependency

from .utils.admin import make_city_active

from .utils.endpoints import (generate_partner_cities,
                              generate_partner_countries,
                              generate_partner_directions_by,
                              generate_partner_directions_by_3,
                              generate_partner_directions_by_city,
                              generate_partner_directions_by_city2,
                              generate_valute_list,
                              generate_actual_course,
                              generate_valute_list2,
                              generate_partner_cities2,
                              get_bankomats_by_valute,
                              new_try_add_bankomats_to_valute,
                              request_to_bot_exchange_admin_direction_notification,
                              try_add_bankomats_to_valute,
                              get_partner_bankomats_by_valute,
                              convert_min_max_count)

from .schemas import (AddPartnerCountrySchema,
                      AddPartnerDirectionSchema3,
                      AddBankomatSchema,
                      BankomatDetailSchema,
                      DeletePartnerDirectionSchema, DirectionSchema2, DirectionSchema3, EditExcludedCitySchema, ExcludedCitiesByPartnerCountry,
                      ListEditedPartnerDirectionSchema2,
                      DeletePartnerCityCountrySchema, NewAccountInfoSchema, NoCashDirectionSchema,
                      PartnerCitySchema,
                      CountrySchema,
                      CitySchema,
                      DirectionSchema,
                      NewPasswordSchema,
                      AccountInfoSchema,
                      AccountTitleSchema,
                      AddPartnerCitySchema,
                      AddPartnerDirectionSchema,
                      ActualCourseSchema,
                      ListEditedPartnerDirectionSchema,
                      AddPartnerCitySchema2,
                      CountrySchema2,
                      CitySchema2,
                      PartnerCitySchema2,
                      AddPartnerDirectionSchema2,
                      PartnerCitySchema3,
                      AddPartnerCitySchema3,
                      PartnerCountrySchema,
                      AddPartnerCityCountrySchema,
                      DeletePartnerCountrySchema,
                      PartnerCountrySchema3,
                      ExchangeLinkCountSchema,
                      NewAddPartnerDirectionSchema,
                      NewListEditedPartnerDirectionSchema,
                      AddPartnerNoCashDirectionSchema,
                      ListEditedPartnerNoCashDirectionSchema)

from config import DEV_HANDLER_SECRET


partner_router = APIRouter(prefix='/partner',
                           tags=['Partners'])

test_partner_router = APIRouter(prefix='/test/partner',
                           tags=['Partners(Changed)'])

new_partner_router = APIRouter(prefix='/partner',
                           tags=['Partners(НОВОЕ)'])



# @partner_router.get('/partner_cities',
#                     response_model=list[PartnerCitySchema3],
#                     response_model_by_alias=False)
def get_partner_cities(partner: partner_dependency):
    partner_id = partner.get('partner_id')

    partner_cities = PartnerCity.objects.select_related('exchange',
                                                        'city',
                                                        'city__country',
                                                        'exchange__account')\
                                        .prefetch_related('working_days')\
                                        .filter(exchange__account__pk=partner_id).all()

    return generate_partner_cities2(partner_cities)


@new_partner_router.get('/partner_cities',
                    response_model=list[PartnerCitySchema3],
                    response_model_by_alias=False)
def new_get_partner_cities(partner: new_partner_dependency):
    partner_id = partner.get('partner_id')

    partner_cities = partner_models.NewPartnerCity.objects.select_related('exchange',
                                                        'city',
                                                        'city__country',
                                                        'exchange__account')\
                                        .prefetch_related('working_days')\
                                        .filter(exchange__account__pk=partner_id).all()

    return generate_partner_cities2(partner_cities)


# @partner_router.get('/partner_countries',
#                     response_model=list[PartnerCountrySchema3],
#                     response_model_by_alias=False)
def get_partner_countries(partner: partner_dependency):
    partner_id = partner.get('partner_id')

    partner_counrties = PartnerCountry.objects.select_related('exchange',
                                                              'exchange__account',
                                                              'country')\
                                        .filter(exchange__account__pk=partner_id)\
                                        .all()
    
    return generate_partner_countries(partner_counrties)


@new_partner_router.get('/partner_countries',
                    response_model=list[PartnerCountrySchema3],
                    response_model_by_alias=False)
def new_get_partner_countries(partner: new_partner_dependency):
    partner_id = partner.get('partner_id')

    partner_counrties = partner_models.NewPartnerCountry.objects.select_related('exchange',
                                                                                'exchange__account',
                                                                                'country')\
                                        .filter(exchange__account__pk=partner_id)\
                                        .all()
    
    return generate_partner_countries(partner_counrties)


# @partner_router.get('/cities_for_exclude_by_partner_country',
#                     response_model=ExcludedCitiesByPartnerCountry,
#                     response_model_by_alias=False)
def get_cities_for_exclude_by_partner_country(partner: partner_dependency,
                                              country_id: int):
    # print(len(connection.queries))
    partner_id = partner.get('partner_id')

    prefect_cities_query = Prefetch('country__cities',
                                    queryset=City.objects.filter(is_parse=True).order_by('name'))
    
    prefetch_excluded_cities_query = Prefetch('exclude_cities',
                                              queryset=City.objects.filter(is_parse=True).order_by('name'))

    try:
        partner_country = PartnerCountry.objects.select_related('exchange',
                                                                'exchange__account',
                                                                'country')\
                                                .prefetch_related(prefect_cities_query,
                                                                prefetch_excluded_cities_query)\
                                            .get(exchange__account__pk=partner_id,
                                                    pk=country_id)
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404,
                            detail='PartnerCountry not found in DB')
    # print(partner_country.__dict__)

    country = partner_country.country

    # print(country.__dict__)


    cities = country.cities.all()

    exclude_cities = partner_country.exclude_cities.all()

    exclude_cities_set = set(exclude_cities)

    # print(cities)

    # print(exclude_cities)

    # for query in connection.queries:
    #     print(query)
    #     print('*' * 8)

    # print(len(connection.queries))

    # active_cities = [city for city in cities if city not in set(exclude_cities)]

    active_response = []

    for city in cities:
        if city not in exclude_cities_set:
            # data = {
            #     'id': city.pk,
            #     'name': city.name,
            # }
            data = {
                'id': city.pk,
                'name': MultipleName(name=city.name,
                                     en_name=city.en_name),
                'code_name': city.code_name,
            }

            active_response.append(data)

    unactive_response = []

    for city in exclude_cities:
            data = {
                'id': city.pk,
                'name': MultipleName(name=city.name,
                                     en_name=city.en_name),
                'code_name': city.code_name,
            }
            unactive_response.append(data)

    response = {
        'country_id': country_id,
        'active_pks': active_response,
        'unactive_pks': unactive_response,
    }

    # print('RESPONSE', response)
    return response
    # return generate_partner_countries(partner_counrties)


@new_partner_router.get('/cities_for_exclude_by_partner_country',
                    response_model=ExcludedCitiesByPartnerCountry,
                    response_model_by_alias=False)
def new_get_cities_for_exclude_by_partner_country(partner: new_partner_dependency,
                                                  country_id: int):
    partner_id = partner.get('partner_id')

    prefect_cities_query = Prefetch('country__cities',
                                    queryset=City.objects.filter(is_parse=True).order_by('name'))
    
    prefetch_excluded_cities_query = Prefetch('exclude_cities',
                                              queryset=City.objects.filter(is_parse=True).order_by('name'))

    try:
        partner_country = partner_models.NewPartnerCountry.objects.select_related('exchange',
                                                                                  'exchange__account',
                                                                                  'country')\
                                                .prefetch_related(prefect_cities_query,
                                                                prefetch_excluded_cities_query)\
                                                .get(exchange__account__pk=partner_id,
                                                     pk=country_id)
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404,
                            detail='PartnerCountry not found in DB')

    country = partner_country.country

    cities = country.cities.all()

    exclude_cities = partner_country.exclude_cities.all()

    exclude_cities_set = set(exclude_cities)

    active_response = []

    for city in cities:
        if city not in exclude_cities_set:

            data = {
                'id': city.pk,
                'name': MultipleName(name=city.name,
                                     en_name=city.en_name),
                'code_name': city.code_name,
            }

            active_response.append(data)

    unactive_response = []

    for city in exclude_cities:
            data = {
                'id': city.pk,
                'name': MultipleName(name=city.name,
                                     en_name=city.en_name),
                'code_name': city.code_name,
            }
            unactive_response.append(data)

    response = {
        'country_id': country_id,
        'active_pks': active_response,
        'unactive_pks': unactive_response,
    }

    return response


# @partner_router.patch('/edit_excluded_cities_by_partner_country')
def edit_excluded_cities_by_partner_country(partner: partner_dependency,
                                            data: EditExcludedCitySchema):
    # print(len(connection.queries))
    partner_id = partner.get('partner_id')

    unactive_city_pks = data.unactive_pks
    active_city_pks = data.active_pks
    country_id = data.country_id

    # prefect_cities_query = Prefetch('country__cities',
    #                                 queryset=City.objects.filter(is_parse=True).order_by('name'))
    
    # prefetch_excluded_cities_query = Prefetch('exclude_cities',
    #                                           queryset=City.objects.filter(is_parse=True).order_by('name'))

    try:
        partner_country = PartnerCountry.objects.select_related('exchange',
                                                                'exchange__account',
                                                                'country')\
                                                .prefetch_related('exclude_cities')\
                                            .get(exchange__account__pk=partner_id,
                                                    pk=country_id)
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404,
                            detail='PartnerCountry not found in DB')
    else:
        try:
            with transaction.atomic():
                partner_country.exclude_cities.remove(*active_city_pks)
                partner_country.exclude_cities.add(*unactive_city_pks)
                
        except Exception as ex:
            print(ex)
            raise HTTPException(status_code=400,
                                detail='Error with try save related records (Exclude City) to DB')
        else:
            return {'status': 'success'}


@new_partner_router.patch('/edit_excluded_cities_by_partner_country')
def new_edit_excluded_cities_by_partner_country(partner: new_partner_dependency,
                                                data: EditExcludedCitySchema):

    partner_id = partner.get('partner_id')

    unactive_city_pks = data.unactive_pks
    active_city_pks = data.active_pks
    country_id = data.country_id

    try:
        partner_country = partner_models.NewPartnerCountry.objects.select_related('exchange',
                                                                                  'exchange__account',
                                                                                  'country')\
                                                .prefetch_related('exclude_cities',
                                                                  'country__cities')\
                                                .get(exchange__account__pk=partner_id,
                                                     pk=country_id)
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404,
                            detail='Partner Country not found by given "country_id"')
    else:
        # добавить проверку что переданные id городов принадлежат к стране !!!
        country_cities = set(city.pk for city in partner_country.country.cities.all())
        given_cities_pks = set(active_city_pks + unactive_city_pks)

        if len(given_cities_pks - country_cities) > 0:
            raise HTTPException(status_code=400,
                                detail=f'active_pks or unactive_pks has invalid "pk", not from {partner_country.country.en_name} country')
        
        try:
            with transaction.atomic():
                partner_country.exclude_cities.remove(*active_city_pks)
                partner_country.exclude_cities.add(*unactive_city_pks)
                
        except Exception as ex:
            print(ex)
            raise HTTPException(status_code=400,
                                detail='Error with try save related records (Exclude City) to DB')
        else:
            return {'status': 'success',
                    'detail': 'excluded_cities has been updated'}


@partner_router.get('/countries',
                    response_model=list[CountrySchema2],
                    response_model_by_alias=False)
def get_countries():
    countries = Country.objects.all()
    
    for country in countries:
        country.multiple_name = MultipleName(name=country.name,
                                             en_name=country.en_name)
        country.country_flag = try_generate_icon_url(country)
    
    return countries


@partner_router.get('/cities',
                    response_model=list[CitySchema2],
                    response_model_by_alias=False)
def get_cities_for_country(country_name: str):
    cities =  City.objects.select_related('country')\
                            .filter(country__name=country_name).all()
    
    for city in cities:
        city.multiple_name = MultipleName(name=city.name,
                                          en_name=city.en_name)
    
    return cities


# @partner_router.get('/directions_by',
#                     response_model=list[DirectionSchema3])
def get_partner_directions_by(partner: partner_dependency,
                              id: int,
                              marker: Literal['country', 'city']):
    print(len(connection.queries))
    partner_id = partner.get('partner_id')

    if marker == 'country':
        direction_model = CountryDirection
        direction_rate_model = CountryDirectionRate
        additional_filter = Q(country__exchange__account__pk=partner_id,
                              country__pk=id)
    else:
        direction_model = Direction
        direction_rate_model = DirectionRate
        additional_filter = Q(city__exchange__account__pk=partner_id,
                              city__pk=id)
        
    direction_rate_prefetch = Prefetch('direction_rates',
                                       direction_rate_model.objects.order_by('min_rate_limit'))

    directions = direction_model.objects.select_related(marker,
                                                        f'{marker}__exchange',
                                                        f'{marker}__exchange__account',
                                                        'direction',
                                                        'direction__valute_from',
                                                        'direction__valute_to')\
                                        .prefetch_related(direction_rate_prefetch)\
                                        .filter(additional_filter)\
                                        .all()

    return generate_partner_directions_by_3(directions,
                                                marker)


# @new_partner_router.get('/directions_by',
#                     response_model=list[DirectionSchema3])
def new_get_partner_directions_by(partner: new_partner_dependency,
                                  id: int,
                                  marker: Literal['country', 'city']):
    # print(len(connection.queries))
    partner_id = partner.get('partner_id')

    if marker == 'country':
        direction_model = partner_models.NewCountryDirection
        direction_rate_model = partner_models.NewCountryDirectionRate
        additional_filter = Q(exchange__account__pk=partner_id,
                              country__pk=id)
    else:
        direction_model = partner_models.NewDirection
        direction_rate_model = partner_models.NewDirectionRate
        additional_filter = Q(exchange__account__pk=partner_id,
                              city__pk=id)
        
    direction_rate_prefetch = Prefetch('direction_rates',
                                       direction_rate_model.objects.order_by('min_rate_limit'))

    directions = direction_model.objects.select_related(marker,
                                                        f'exchange',
                                                        f'exchange__account',
                                                        'direction',
                                                        'direction__valute_from',
                                                        'direction__valute_to')\
                                        .prefetch_related(direction_rate_prefetch)\
                                        .filter(additional_filter)\
                                        .all()

    return generate_partner_directions_by(directions,
                                          marker)


# @partner_router.get('/no_cash_directions',
#                     response_model=list[NoCashDirectionSchema])
def get_partner_no_cash_directions(partner: partner_dependency):
    # print(len(connection.queries))
    partner_id = partner.get('partner_id')
    marker = 'no_cash'

    # if marker == 'country':
    #     direction_model = CountryDirection
    #     direction_rate_model = CountryDirectionRate
    #     additional_filter = Q(country__exchange__account__pk=partner_id,
    #                           country__pk=id)
    # else:
    #     direction_model = Direction
    #     direction_rate_model = DirectionRate
    #     additional_filter = Q(city__exchange__account__pk=partner_id,
    #                           city__pk=id)
        
    direction_rate_prefetch = Prefetch('direction_rates',
                                       NonCashDirectionRate.objects.order_by('min_rate_limit'))

    directions = NonCashDirection.objects.select_related('exchange',
                                                         'exchange__account',
                                                         'direction',
                                                        'direction__valute_from',
                                                        'direction__valute_to')\
                                        .prefetch_related(direction_rate_prefetch)\
                                        .filter(exchange__account__pk=partner_id)\
                                        .all()

    return generate_partner_directions_by_3(directions,
                                                marker)


@new_partner_router.get('/no_cash_directions',
                    response_model=list[NoCashDirectionSchema])
def new_get_partner_no_cash_directions(partner: new_partner_dependency):

    partner_id = partner.get('partner_id')
    marker = 'no_cash'
        
    direction_rate_prefetch = Prefetch('direction_rates',
                                       partner_models.NewNonCashDirectionRate.objects.order_by('min_rate_limit'))

    directions = partner_models.NewNonCashDirection.objects.select_related('exchange',
                                                                           'exchange__account',
                                                                           'direction',
                                                                           'direction__valute_from',
                                                                           'direction__valute_to')\
                                                            .prefetch_related(direction_rate_prefetch)\
                                                            .filter(exchange__account__pk=partner_id)\
                                                            .all()

    return generate_partner_directions_by(directions,
                                          marker)


# @partner_router.get('/available_valutes')
def get_available_valutes_for_partner2(base: str,
                                       is_no_cash: bool = False):
    base = base.upper()

    direction_model = CashDirection if not is_no_cash else NoCashDirection

    queries = direction_model.objects.select_related('valute_from',
                                                   'valute_to')\
                                    .filter(valute_from__available_for_partners=True,
                                            valute_to__available_for_partners=True)
    
    if base == 'ALL':
        marker = 'valute_from'
        queries = queries.values_list('valute_from_id', flat=True)
    else:
        marker = 'valute_to'
        queries = queries.filter(valute_from=base)
        queries = queries.values_list('valute_to_id', flat=True)

    # return generate_valute_list2(queries, marker)
    return get_valute_json_4(queries)


@new_partner_router.get('/available_valutes')
def get_available_valutes_for_partner(base: str,
                                      is_no_cash: bool = False):
    base = base.upper()

    direction_model = cash_models.NewDirection if not is_no_cash else no_cash_models.NewDirection

    queries = direction_model.objects.select_related('valute_from',
                                                     'valute_to')\
                                        .filter(valute_from__available_for_partners=True,
                                                valute_to__available_for_partners=True)
    
    if base == 'ALL':
        queries = queries.values_list('valute_from_id', flat=True)
    else:
        queries = queries.filter(valute_from=base)
        queries = queries.values_list('valute_to_id', flat=True)

    return get_valute_json(queries)


# @partner_router.post('/change_password')
def change_user_password(partner: partner_dependency,
                         new_password: NewPasswordSchema):
    partner_id = partner.get('partner_id')

    try:
        user = User.objects.select_related('moderator_account')\
                            .get(moderator_account__pk=partner_id)
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404)
    else:
        user.set_password(new_password.new_password)
        user.save()

        return {'status': 'success',
                'details': 'password changed'}
    

@new_partner_router.post('/change_password')
def new_change_user_password(partner: new_partner_dependency,
                             new_password: NewPasswordSchema):
    partner_id = partner.get('partner_id')

    try:
        user = User.objects.select_related('new_moderator_account')\
                            .get(new_moderator_account__pk=partner_id)
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404)
    else:
        user.set_password(new_password.new_password)
        user.save()

        return {'status': 'success',
                'details': 'password changed'}


# @partner_router.get('/actual_course',
#                     response_model=ActualCourseSchema)
def get_actual_course_for_direction(partner: partner_dependency,
                                    valute_from: str,
                                    valute_to: str):
    valute_from, valute_to = valute_from.upper(), valute_to.upper()

    direction = CashDirection.objects.select_related('valute_from',
                                                     'valute_to')\
                                        .filter(valute_from__code_name=valute_from,
                                                valute_to__code_name=valute_to).first()

    if not direction:
        raise HTTPException(status_code=404)
    
    return generate_actual_course(direction)


@new_partner_router.get('/actual_course',
                    response_model=ActualCourseSchema)
def new_get_actual_course_for_direction(partner: new_partner_dependency,
                                        valute_from: str,
                                        valute_to: str):
    valute_from, valute_to = valute_from.upper(), valute_to.upper()

    try:
        direction = cash_models.NewDirection.objects.select_related('valute_from',
                                                                    'valute_to')\
                                                    .filter(valute_from_id=valute_from,
                                                            valute_to_id=valute_to).get()
    except ObjectDoesNotExist:
        try:
            direction = no_cash_models.NewDirection.objects.select_related('valute_from',
                                                                           'valute_to')\
                                                            .filter(valute_from_id=valute_from,
                                                                    valute_to_id=valute_to).get()
        except ObjectDoesNotExist:
            raise HTTPException(status_code=404,
                                detail=f'Direction not found by given {valute_from} -> {valute_to}')
    
    return generate_actual_course(direction)


# @partner_router.get('/account_info',
#                     response_model=NewAccountInfoSchema)
def get_account_info(partner: partner_dependency):
    partner_id = partner.get('partner_id')

    try:
        exchange = Exchange.objects.select_related('account')\
                                    .get(account__pk=partner_id)
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404)
    else:
        exchange_admin = ExchangeAdmin.objects.select_related('user')\
                                                .filter(exchange_name=exchange.name,
                                                        exchange_marker='partner')
        exchange_admin_order = ExchangeAdminOrder.objects.filter(exchange_name=exchange.name)
        
        if exchange_admin.exists():
            exchange_admin = exchange_admin.first()
            user = exchange_admin.user

            name = user.username or user.first_name or user.last_name or None
            
            link = f'https://t.me/{user.username}' if user.username else f'tg://user?id={exchange_admin.user_id}'

            exchange.telegram = {
                'id': user.tg_id,
                'name': name,
                'link': link,
                'notification': exchange_admin.notification,
            }

            # if exchange_admin_order.exists():
                # exchange_admin_order = exchange_admin_order.first()
        exchange.has_exchange_admin_order = exchange_admin_order.exists()
        
        exchange.title = AccountTitleSchema(ru=exchange.name,
                                            en=exchange.en_name)
        
        return exchange


@new_partner_router.get('/account_info',
                        response_model=NewAccountInfoSchema)
def new_get_account_info(partner: new_partner_dependency):
    partner_id = partner.get('partner_id')

    try:
        exchange = Exchanger.objects.select_related('account')\
                                    .get(account__pk=partner_id)
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404,
                            detail='Exchanger not found')
    else:
        exchange_admin = NewExchangeAdmin.objects.select_related('user')\
                                                .filter(exchange_id=exchange.pk)
        exchange_admin_order = NewExchangeAdminOrder.objects.filter(exchange_id=exchange.pk)
        
        if exchange_admin.exists():
            exchange_admin = exchange_admin.first()
            user = exchange_admin.user

            name = user.username or user.first_name or user.last_name or None
            
            link = f'https://t.me/{user.username}' if user.username else f'tg://user?id={exchange_admin.user_id}'

            exchange.telegram = {
                'id': user.tg_id,
                'name': name,
                'link': link,
                'notification': exchange_admin.notification,
            }

        exchange.has_exchange_admin_order = exchange_admin_order.exists()
        
        exchange.title = AccountTitleSchema(ru=exchange.name,
                                            en=exchange.en_name)
        
        return exchange


# @partner_router.get('/switch_notification_activity')
def switch_notification_activity(partner: partner_dependency):
    partner_id = partner.get('partner_id')

    try:
        exchange = Exchange.objects.select_related('account')\
                                    .get(account__pk=partner_id)
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404,
                            detail='Exchange not found')
    else:
        try:
            exchange_admin = ExchangeAdmin.objects.select_related('user')\
                                                    .get(exchange_name=exchange.name,
                                                            exchange_marker='partner')
        except ObjectDoesNotExist:
            raise HTTPException(status_code=404,
                                detail=f'ExchangeAdmin for Exchange {exchange.name} not found')
        else:
            try:
                new_value = not exchange_admin.notification
                exchange_admin.notification = new_value
                exchange_admin.save()
            except Exception as ex:
                raise HTTPException(status_code=500,
                                    detail='DB error with try add new record')
            else:
                return new_value


@new_partner_router.get('/switch_notification_activity')
def new_switch_notification_activity(partner: new_partner_dependency):
    partner_id = partner.get('partner_id')

    try:
        exchange = Exchanger.objects.select_related('account')\
                                    .get(account__pk=partner_id)
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404,
                            detail='Exchange not found')
    else:
        try:
            exchange_admin = NewExchangeAdmin.objects.select_related('user')\
                                                    .get(exchange_id=exchange)
        except ObjectDoesNotExist:
            raise HTTPException(status_code=404,
                                detail=f'ExchangeAdmin for Exchange {exchange.name} not found')
        else:
            try:
                new_value = not exchange_admin.notification
                exchange_admin.notification = new_value
                exchange_admin.save()
            except Exception as ex:
                raise HTTPException(status_code=500,
                                    detail='DB error with try add new record')
            else:
                return new_value


# @partner_router.post('/add_admin_exchange_order')
def add_admin_exchange_order(partner: partner_dependency,
                             tg_id: int):
    partner_id = partner.get('partner_id')

    try:
        exchange = Exchange.objects.select_related('account')\
                                    .get(account__pk=partner_id)
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404,
                            detail='Exchanger not found in DB')
    else:
        if ExchangeAdminOrder.objects.filter(exchange_name=exchange.name).exists():
            raise HTTPException(status_code=423,
                                detail='Order for this exchanger exists in DB yet')
        try:
            data = {
                'user_id': tg_id,
                'exchange_name': exchange.name,
                'time_create': timezone.now(),

            }
            ExchangeAdminOrder.objects.create(**data)
        except Exception as ex:
            print(ex)
            raise HTTPException(status_code=400,
                                detail='Error with creating ExchangeAdminOrder')
        else:
            return 'https://t.me/MoneySwap_robot?start=partner_admin_activate'
        

@new_partner_router.post('/add_admin_exchange_order')
def new_add_admin_exchange_order(partner: new_partner_dependency,
                                 tg_id: int):
    partner_id = partner.get('partner_id')

    try:
        exchange = Exchanger.objects.select_related('account',
                                                    'exchange_admin')\
                                    .get(account__pk=partner_id)
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404,
                            detail='Exchanger not found in DB')
    else:
        if hasattr(exchange, 'exchange_admin'):
            raise HTTPException(status_code=423,
                                detail='Exchange admin exists in DB yet')
        if NewExchangeAdminOrder.objects.filter(exchange_id=exchange.pk).exists():
            raise HTTPException(status_code=423,
                                detail='Order for this exchanger exists in DB yet')
        try:
            data = {
                'user_id': tg_id,
                'exchange_id': exchange.pk,
                'time_create': timezone.now(),

            }
            NewExchangeAdminOrder.objects.create(**data)
        except Exception as ex:
            print(ex)
            raise HTTPException(status_code=400,
                                detail='Error with creating ExchangeAdminOrder')
        else:
            return 'https://t.me/MoneySwap_robot?start=new_partner_admin_activate'
        

# @partner_router.post('/edit_admin_exchange_order')
def edit_admin_exchange_order(partner: partner_dependency,
                             tg_id: int):
    partner_id = partner.get('partner_id')

    try:
        exchange = Exchange.objects.select_related('account')\
                                    .get(account__pk=partner_id)
        exchange_admin_order_query = ExchangeAdminOrder.objects.filter(exchange_name=exchange.name,
                                                                       moderation=True)
        exchange_admin_query = ExchangeAdmin.objects.filter(exchange_name=exchange.name)

    except ObjectDoesNotExist:
        raise HTTPException(status_code=404,
                            detail='Exchanger not found in DB')
    else:
        if not exchange_admin_order_query.exists() and \
            not exchange_admin_query.exists():
            raise HTTPException(status_code=423,
                                detail='Order for this exchanger or ExchangeAdmin does not exist in DB')
        try:
            with transaction.atomic():
                # exchange_admin_query.delete()
                exchange_admin_order_query.update(user_id=tg_id,
                                                  moderation=False)
            # data = {
            #     'user_id': tg_id,
            #     'exchange_name': exchange.name,
            #     'time_create': timezone.now(),

            # }
            # ExchangeAdminOrder.objects.create(**data)
        except Exception as ex:
            print(ex)
            raise HTTPException(status_code=400,
                                detail='Error with editing ExchangeAdminOrder')
        else:
            return 'https://t.me/MoneySwap_robot?start=partner_admin_activate'
        

@new_partner_router.post('/edit_admin_exchange_order')
def new_edit_admin_exchange_order(partner: new_partner_dependency,
                                  tg_id: int):
    partner_id = partner.get('partner_id')

    try:
        exchange = Exchanger.objects.select_related('account',
                                                    'exchange_admin')\
                                    .get(account__pk=partner_id)
        exchange_admin_order_query = NewExchangeAdminOrder.objects.filter(exchange_id=exchange.pk,
                                                                          moderation=True)

    except ObjectDoesNotExist:
        raise HTTPException(status_code=404,
                            detail='Exchanger not found in DB')
    else:
        if not exchange_admin_order_query.exists()\
            and not hasattr(exchange, 'exchange_admin'):
            raise HTTPException(status_code=423,
                                detail='Order for this exchanger or ExchangeAdmin does not exist in DB')
        try:
            with transaction.atomic():
                exchange_admin_order_query.update(user_id=tg_id,
                                                  moderation=False)

        except Exception as ex:
            print(ex)
            raise HTTPException(status_code=400,
                                detail='Error with editing ExchangeAdminOrder')
        else:
            return 'https://t.me/MoneySwap_robot?start=new_partner_admin_activate'
        

# @partner_router.delete('/delete_admin_exchange_order')
def edit_admin_exchange_order(partner: partner_dependency):
    partner_id = partner.get('partner_id')

    try:
        exchange = Exchange.objects.select_related('account')\
                                    .get(account__pk=partner_id)
        exchange_admin_order_query = ExchangeAdminOrder.objects.filter(exchange_name=exchange.name)
        exchange_admin_query = ExchangeAdmin.objects.filter(exchange_name=exchange.name)

    except ObjectDoesNotExist:
        raise HTTPException(status_code=404,
                            detail='Exchanger not found in DB')
    else:
        if not exchange_admin_order_query.exists() and \
            not exchange_admin_query.exists():
            raise HTTPException(status_code=423,
                                detail='Order for this exchanger or ExchangeAdmin does not exist in DB')
        try:
            with transaction.atomic():
                exchange_admin_query.delete()
                exchange_admin_order_query.delete()
            # data = {
            #     'user_id': tg_id,
            #     'exchange_name': exchange.name,
            #     'time_create': timezone.now(),

            # }
            # ExchangeAdminOrder.objects.create(**data)
        except Exception as ex:
            print(ex)
            raise HTTPException(status_code=400,
                                detail='Error with delete ExchangeAdminOrder and ExchangeAdmin records')
        else:
            return {'status': 'success',
                    'detail': 'ExchangeAdmin and ExchangeAdminOrder deleted successfully'}


@new_partner_router.delete('/delete_admin_exchange_order')
def new_edit_admin_exchange_order(partner: new_partner_dependency):
    partner_id = partner.get('partner_id')

    try:
        exchange = Exchanger.objects.select_related('account')\
                                    .get(account__pk=partner_id)
        exchange_admin_order_query = NewExchangeAdminOrder.objects.filter(exchange_id=exchange.pk)
        exchange_admin_query = NewExchangeAdmin.objects.filter(exchange_id=exchange.pk)

    except ObjectDoesNotExist:
        raise HTTPException(status_code=404,
                            detail='Exchanger not found in DB')
    else:
        if not exchange_admin_order_query.exists()\
            and not exchange_admin_query.exists():
            raise HTTPException(status_code=423,
                                detail='Order for this exchanger and ExchangeAdmin does not exist in DB')
        try:
            with transaction.atomic():
                exchange_admin_query.delete()
                exchange_admin_order_query.delete()

        except Exception as ex:
            print(ex)
            raise HTTPException(status_code=400,
                                detail='Error with delete ExchangeAdminOrder and ExchangeAdmin records')
        else:
            return {'status': 'success',
                    'detail': 'ExchangeAdmin and ExchangeAdminOrder deleted successfully'}


def get_valid_active_direction_str(direction):
    _timedelta = direction.time_update - (timezone.now() - timedelta(days=3))
    total_seconds = int(_timedelta.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    formatted_time = f"{hours:02d} часов {minutes:02d} минут]"
    return f'{direction} (активно✅, отключится через {formatted_time}🕚)'
        

# @partner_router.post('/add_partner_city_country')
def add_partner_city_country(partner: partner_dependency,
                             data: AddPartnerCityCountrySchema):
    # print(len(connection.queries))
    partner_id = partner.get('partner_id')
    try:
        # city_model = City.objects.get(code_name=city.city)
        exchange = Exchange.objects.select_related('account')\
                                    .get(account__pk=partner_id)
    except Exception:
        raise HTTPException(status_code=404)
    else:
        _data = data.model_dump()
        # data['city'] = city_model
        _data['exchange'] = exchange

        _id = _data.pop('id')
        marker = _data.pop('marker')

        working_days = _data.pop('working_days')

        working_days_set = {working_day.capitalize() for working_day in working_days\
                            if working_days[working_day]}
        
        weekdays = _data.pop('weekdays')

        weekends = _data.pop('weekends')

        _data.update(
            {
                'time_from': weekdays.get('time_from'),
                'time_to': weekdays.get('time_to'),
                'weekend_time_from': weekends.get('time_from'),
                'weekend_time_to': weekends.get('time_to'),
            }
        )

        try:
            if marker == 'country':
                _model = PartnerCountry
                _data.update({
                    'country_id': _id,
                })
            else:
                _model = PartnerCity
                _data.update({
                    'city_id': _id,
                })
            # new_partner_city = PartnerCity.objects.create(**data)
            new_obj = _model.objects.create(**_data)
            if marker == 'city':
                make_city_active(new_obj.city)
        except IntegrityError:
            raise HTTPException(status_code=423, # ?
                                detail='Такой город уже существует')
        else:
            new_obj.working_days\
                .add(*WorkingDay.objects.filter(code_name__in=working_days_set))
            
            # name = new_obj.city.name if marker == 'city' else new_obj.country.name
            # if marker == 'city':
            #     name = new_obj.city.name
            #     _text = 'город'
            #     suffix = ''
            # else:
            #     name = new_obj.country.name
            #     _text = 'страна'
            #     suffix = 'а'
            # print(len(connection.queries))
            # return {'status': 'success',
            #         'details': f'Партнёрский {_text} {name} добавлен{suffix}'}
            return {'location_id': new_obj.pk}
        

@new_partner_router.post('/add_partner_city_country')
def add_partner_city_country(partner: new_partner_dependency,
                             data: AddPartnerCityCountrySchema):

    partner_id = partner.get('partner_id')
    try:

        exchange = Exchanger.objects.select_related('account')\
                                    .get(account__pk=partner_id)
    except Exception:
        raise HTTPException(status_code=404)
    else:
        _data = data.model_dump()

        _data['exchange'] = exchange

        _id = _data.pop('id')
        marker = _data.pop('marker')

        working_days = _data.pop('working_days')

        working_days_set = {working_day.capitalize() for working_day in working_days\
                            if working_days[working_day]}
        
        weekdays = _data.pop('weekdays')

        weekends = _data.pop('weekends')

        _data.update(
            {
                'time_from': weekdays.get('time_from'),
                'time_to': weekdays.get('time_to'),
                'weekend_time_from': weekends.get('time_from'),
                'weekend_time_to': weekends.get('time_to'),
            }
        )

        try:
            if marker == 'country':
                _model = partner_models.NewPartnerCountry
                _data.update({
                    'country_id': _id,
                })
            else:
                _model = partner_models.NewPartnerCity
                _data.update({
                    'city_id': _id,
                })

            new_obj = _model.objects.create(**_data)
            
            if marker == 'city':
                make_city_active(new_obj.city)

        except IntegrityError:
            _text = 'Такая страна' if marker == 'country' else 'Такой город'
            raise HTTPException(status_code=423,
                                detail=f'{_text} уже существует')
        else:
            new_obj.working_days\
                .add(*WorkingDay.objects.filter(code_name__in=working_days_set))

            return {'location_id': new_obj.pk,
                    'marker': marker}


# @partner_router.patch('/edit_partner_city_country')
def edit_partner_city_country(partner: partner_dependency,
                             data: AddPartnerCityCountrySchema):
    # print(len(connection.queries))
    partner_id = partner.get('partner_id')
    try:
        # city_model = City.objects.get(code_name=city.city)
        exchange = Exchange.objects.select_related('account')\
                                    .get(account__pk=partner_id)
    except Exception:
        raise HTTPException(status_code=404)
    else:
        _data = data.model_dump()
        # data['city'] = city_model
        _data['exchange'] = exchange

        _id = _data.pop('id')
        marker = _data.pop('marker')

        working_days = _data.pop('working_days')

        working_days_set = {working_day.capitalize() for working_day in working_days\
                            if working_days[working_day]}
        

        unworking_day_names = {working_day.capitalize() for working_day in working_days \
                                if not working_days[working_day]}
    
    # working_day_names = {working_day.capitalize() for working_day in working_days \
    #                      if working_days[working_day]}
    
    # with transaction.atomic():
    #     partner_city = partner_city.first()

    #     # partner_city.working_days.through.objects\
    #     #         .filter(workingday__code_name__in=unworking_day_names).delete()
    #     partner_city.working_days\
    #                 .remove(*WorkingDay.objects.filter(code_name__in=unworking_day_names))


    #     partner_city.working_days\
    #                 .add(*WorkingDay.objects.filter(code_name__in=working_day_names))
    # # print(len(connection.queries))
    # return {'status': 'success',
    #         'details': f'Партнёрский город {partner_city.city.name} успешно изменён'}
        
        weekdays = _data.pop('weekdays')

        weekends = _data.pop('weekends')

        _data.update(
            {
                'time_from': weekdays.get('time_from'),
                'time_to': weekdays.get('time_to'),
                'weekend_time_from': weekends.get('time_from'),
                'weekend_time_to': weekends.get('time_to'),
            }
        )


        if marker == 'country':
            _model = PartnerCountry
        else:
            _model = PartnerCity
        with transaction.atomic():
            obj_to_update = _model.objects.select_related(marker,
                                            'exchange',
                                            'exchange__account')\
                                        .filter(pk=_id,
                                                exchange__account__pk=partner_id)
            
            if not obj_to_update:
                raise HTTPException(status_code=404)
            # else:
            obj_to_update.update(**_data)
            obj_to_update = obj_to_update.first()

            obj_to_update.working_days\
                        .remove(*WorkingDay.objects.filter(code_name__in=unworking_day_names))

            obj_to_update.working_days\
                .add(*WorkingDay.objects.filter(code_name__in=working_days_set))
            
        if marker == 'city':
            name = obj_to_update.city.name
            _text = 'город'
            suffix = ''
            prefix = 'ий'
        else:
            name = obj_to_update.country.name
            _text = 'страна'
            suffix = 'а'
            prefix = 'ая'
        # print(len(connection.queries))
        return {'status': 'success',
                'details': f'Партнёрск{prefix} {_text} {name} изменен{suffix}'}


@new_partner_router.patch('/edit_partner_city_country')
def new_edit_partner_city_country(partner: new_partner_dependency,
                                  data: AddPartnerCityCountrySchema):

    partner_id = partner.get('partner_id')

    _data = data.model_dump()

    _id = _data.pop('id')
    marker = _data.pop('marker')

    working_days = _data.pop('working_days')

    working_days_set = {working_day.capitalize() for working_day in working_days\
                        if working_days[working_day]}
    

    unworking_day_names = {working_day.capitalize() for working_day in working_days \
                            if not working_days[working_day]}
    
    weekdays = _data.pop('weekdays')

    weekends = _data.pop('weekends')

    _data.update(
        {
            'time_from': weekdays.get('time_from'),
            'time_to': weekdays.get('time_to'),
            'weekend_time_from': weekends.get('time_from'),
            'weekend_time_to': weekends.get('time_to'),
            'time_update': timezone.now(),
        }
    )

    if marker == 'country':
        _model = partner_models.NewPartnerCountry
    else:
        _model = partner_models.NewPartnerCity
    with transaction.atomic():
        obj_to_update = _model.objects.select_related(marker,
                                                        'exchange',
                                                        'exchange__account')\
                                        .filter(pk=_id,
                                                exchange__account__pk=partner_id)
        
        if not obj_to_update.exists():
            raise HTTPException(status_code=404,
                                detail=f'{marker.capitalize()} not found by given "id"')

        obj_to_update.update(**_data)
        obj_to_update = obj_to_update.first()

        obj_to_update.working_days\
                    .remove(*WorkingDay.objects.filter(code_name__in=unworking_day_names))

        obj_to_update.working_days\
            .add(*WorkingDay.objects.filter(code_name__in=working_days_set))
        
    if marker == 'city':
        name = obj_to_update.city.name
        _text = 'город'
        suffix = ''
        prefix = 'ий'
    else:
        name = obj_to_update.country.name
        _text = 'страна'
        suffix = 'а'
        prefix = 'ая'

    return {'status': 'success',
            'details': f'Партнёрск{prefix} {_text} {name} изменен{suffix}'}


# @partner_router.delete('/delete_partner_city_country')
def delete_partner_city_country(partner: partner_dependency,
                                data: DeletePartnerCityCountrySchema):
    partner_id = partner.get('partner_id')
    
    if data.marker == 'country':
        _model = PartnerCountry
    else:
        _model = PartnerCity

    _model.objects.select_related('exchange',
                                  'exchange__account')\
                    .filter(pk=data.id,
                            exchange__account__pk=partner_id)\
                    .delete()
    

@new_partner_router.delete('/delete_partner_city_country')
def new_delete_partner_city_country(partner: new_partner_dependency,
                                    data: DeletePartnerCityCountrySchema):
    partner_id = partner.get('partner_id')
    
    if data.marker == 'country':
        _model = partner_models.NewPartnerCountry
    else:
        _model = partner_models.NewPartnerCity
    try:
         _model.objects.select_related('exchange',
                                    'exchange__account')\
                        .filter(pk=data.id,
                                exchange__account__pk=partner_id)\
                        .delete()

    except Exception as ex:
        print(ex)
        raise HTTPException(status_code=500,
                            detail=f'Error with try delete {data.marker} by given "id"')
    else:
        return f'{data.marker.capitalize()} has been deleted'


# @partner_router.post('/add_partner_direction')
def add_partner_direction(partner: partner_dependency,
                          new_direction: NewAddPartnerDirectionSchema):
    partner_id = partner.get('partner_id')

    data = new_direction.model_dump()

    _id = data.pop('id')
    valute_from = data.pop('valute_from')
    valute_to = data.pop('valute_to')
    marker = data.pop('marker')
    bankomats = data.pop('bankomats')
    exchange_rates = data.pop('exchange_rates')
    
    foreign_key_name = 'country_id' if marker == 'country' else 'city_id'
    foreign_key_model = PartnerCountry if marker == 'country' else PartnerCity

    direction_model = CountryDirection if marker == 'country' else Direction


    # check_partner = foreign_key_model.objects.select_related('exchange',
    #                                                          'exchange__account')\
    #                                         .filter(pk=_id,
    #                                                 exchange__account__pk=partner_id)\
                                            # .exists()
    check_partner = foreign_key_model.objects.select_related('exchange',
                                                             'exchange__account')\
                                            .filter(pk=_id,
                                                    exchange__account__pk=partner_id)\
                                            # .exists()


    # print(check_partner)
    
    # if not check_partner:
    if not check_partner.exists():
        raise HTTPException(status_code=404)
        
    try:
        direction = CashDirection.objects.select_related('valute_from',
                                                        'valute_to')\
                                        .prefetch_related('partner_country_directions')\
                                            .get(valute_from__code_name=valute_from,
                                                 valute_to__code_name=valute_to)
    except Exception as ex:
        print(ex)
        raise HTTPException(status_code=404)
    else:
        data[foreign_key_name] = _id
        data['direction'] = direction
        data['exchange_id'] = check_partner.first().exchange_id

        if len(exchange_rates) > 4:
            raise HTTPException(status_code=400,
                                detail='Количество доп объемов для направления должно быть не больше 3 шт')


        main_exchange_rate, additional_exchange_rates = exchange_rates[0], exchange_rates[1:]

        # print(main_exchange_rate)

        convert_min_max_count(main_exchange_rate,
                              marker='main')
        
        # print(main_exchange_rate)

        main_exchange_rate.pop('rate_coefficient')

        data.update(main_exchange_rate)

        # make_valid_values_for_dict(data)

        try:
            if marker == 'city':
                city = PartnerCity.objects.select_related('city')\
                                            .get(pk=_id)
                country_direction = CountryDirection.objects.select_related('country',
                                                                            'country__country',
                                                                            'country__exchange',
                                                                            'country__exchange__account',
                                                                            'direction')\
                                        .prefetch_related('country__country__cities')\
                                        .filter(country__country__cities__code_name=city.city.code_name,
                                                country__exchange__account=partner_id,
                                                direction__valute_from=valute_from,
                                                direction__valute_to=valute_to)
                
                if country_direction.exists():
                    raise HTTPException(status_code=424,
                                        detail='Такое направление уже существует на уровне партнерской страны')
            
            with transaction.atomic():
                new_partner_dirction = direction_model.objects.create(**data)
                if bankomats:
                    try_add_bankomats_to_valute(partner_id,
                                                valute_to,
                                                bankomats)
                if additional_exchange_rates:
                    partner = CustomUser.objects.filter(pk=partner_id).get()
                    exchange_id = partner.exchange_id

                    min_count_list = [_exchange_rate.get('min_count') for _exchange_rate in additional_exchange_rates]

                    if len(min_count_list) != len(set(min_count_list)):
                            raise HTTPException(status_code=400,
                                                detail='Несколько записей об объемах содержат одинаковые min_count')

                    bulk_create_list = []

                    for additional_exchange_rate in additional_exchange_rates:
                        
                        if not additional_exchange_rate.get('min_count'):
                            raise HTTPException(status_code=400,
                                                detail='Одна или несколько записей об объемах содержит пустой min_count')

                        if not additional_exchange_rate.get('rate_coefficient'):
                            raise HTTPException(status_code=400,
                                                detail='Одна или несколько записей об объемах содержит пустой rate_coefficient')


                        sub_foreign_key_model = DirectionRate if foreign_key_name == 'city_id'\
                                                                else CountryDirectionRate
                        exchange_rate_data = {
                            'exchange_id': exchange_id,
                            'exchange_direction_id': new_partner_dirction.pk,
                        }

                        convert_min_max_count(additional_exchange_rate,
                                              marker='additional')
                        
                        exchange_rate_data.update(additional_exchange_rate)

                        # make_valid_values_for_dict(exchange_rate_data)
                        
                        new_exchangedirection_rate = sub_foreign_key_model(**exchange_rate_data)

                        bulk_create_list.append(new_exchangedirection_rate)
                    
                    sub_foreign_key_model.objects.bulk_create(bulk_create_list)

            return {'status': 'success',
                    'details': f'Партнерское направление {direction.display_name} добавлено'}
        except IntegrityError as ex:
            print(ex)
            raise HTTPException(status_code=423,
                                detail='Такое направление уже существует')


@new_partner_router.post('/add_partner_direction')
def new_add_partner_direction(partner: new_partner_dependency,
                              new_direction: NewAddPartnerDirectionSchema):
    partner_id = partner.get('partner_id')

    data = new_direction.model_dump()

    _id = data.pop('id')
    valute_from = data.pop('valute_from')
    valute_to = data.pop('valute_to')
    valute_from, valute_to = valute_from.upper(), valute_to.upper()
    marker = data.pop('marker')
    bankomats = data.pop('bankomats')
    exchange_rates = data.pop('exchange_rates')
    
    foreign_key_name = 'country_id' if marker == 'country' else 'city_id'
    foreign_key_model = partner_models.NewPartnerCountry if marker == 'country' \
                                                    else partner_models.NewPartnerCity

    direction_model = partner_models.NewCountryDirection if marker == 'country' \
                                                    else partner_models.NewDirection

    check_partner = foreign_key_model.objects.select_related('exchange',
                                                             'exchange__account')\
                                            .filter(pk=_id,
                                                    exchange__account__pk=partner_id)\

    if not check_partner.exists():
        raise HTTPException(status_code=404)
        
    try:
        direction = cash_models.NewDirection.objects.select_related('valute_from',
                                                                    'valute_to')\
                                                    .get(valute_from_id=valute_from,
                                                        valute_to_id=valute_to)
    except ObjectDoesNotExist as ex:
        print(ex)
        raise HTTPException(status_code=404,
                            detail=f'Direction {valute_from} -> {valute_to} not found')
    else:
        partner_location_obj = check_partner.first()

        data[foreign_key_name] = _id
        data['direction'] = direction
        data['exchange_id'] = partner_location_obj.exchange_id

        if len(exchange_rates) > 4:
            raise HTTPException(status_code=400,
                                detail='Количество доп объемов для направления должно быть не больше 3 шт')


        main_exchange_rate, additional_exchange_rates = exchange_rates[0], exchange_rates[1:]

        convert_min_max_count(main_exchange_rate,
                              marker='main')

        main_exchange_rate.pop('rate_coefficient')

        data.update(main_exchange_rate)

        try:
            if marker == 'city':
                city = partner_models.NewPartnerCity.objects.select_related('city')\
                                                            .get(pk=_id)
                country_direction = partner_models.NewCountryDirection.objects\
                                        .select_related('country',
                                                        'country__country',
                                                        'exchange',
                                                        'exchange__account',
                                                        'direction')\
                                        .prefetch_related('country__country__cities')\
                                        .filter(country__country__cities__code_name=city.city.code_name,
                                                exchange__account=partner_id,
                                                direction__valute_from_id=valute_from,
                                                direction__valute_to_id=valute_to)
                
                if country_direction.exists():
                    raise HTTPException(status_code=424,
                                        detail='Такое направление уже существует на уровне партнерской страны')
            
            with transaction.atomic():
                new_partner_direction = direction_model.objects.create(**data)
                if bankomats:
                    new_try_add_bankomats_to_valute(partner_id,
                                                    valute_to,
                                                    bankomats)
                if additional_exchange_rates:
                    exchange_id = partner_location_obj.exchange_id

                    min_count_list = [_exchange_rate.get('min_count') for _exchange_rate in additional_exchange_rates]

                    if len(min_count_list) != len(set(min_count_list)):
                            raise HTTPException(status_code=400,
                                                detail='Несколько записей об объемах содержат одинаковые min_count')

                    bulk_create_list = []

                    for additional_exchange_rate in additional_exchange_rates:
                        
                        if not additional_exchange_rate.get('min_count'):
                            raise HTTPException(status_code=400,
                                                detail='Одна или несколько записей об объемах содержит пустой min_count')

                        if not additional_exchange_rate.get('rate_coefficient'):
                            raise HTTPException(status_code=400,
                                                detail='Одна или несколько записей об объемах содержит пустой rate_coefficient')


                        sub_foreign_key_model = partner_models.NewDirectionRate if foreign_key_name == 'city_id'\
                                                                else partner_models.NewCountryDirectionRate
                        exchange_rate_data = {
                            'exchange_id': exchange_id,
                            'exchange_direction_id': new_partner_direction.pk,
                        }

                        convert_min_max_count(additional_exchange_rate,
                                              marker='additional')
                        
                        exchange_rate_data.update(additional_exchange_rate)
                        
                        new_exchangedirection_rate = sub_foreign_key_model(**exchange_rate_data)

                        bulk_create_list.append(new_exchangedirection_rate)
                    
                    sub_foreign_key_model.objects.bulk_create(bulk_create_list)

            return {'status': 'success',
                    'details': f'Партнерское направление {valute_from} -> {valute_to} добавлено'}
        except IntegrityError as ex:
            print(ex)
            _location_text = 'города' if marker == 'city' else 'страны'
            raise HTTPException(status_code=423,
                                detail=f'Такое направление на уровне {_location_text} уже существует')


# @partner_router.post('/add_partner_no_cash_direction')
def add_partner_direction(partner: partner_dependency,
                          new_direction: AddPartnerNoCashDirectionSchema):
    partner_id = partner.get('partner_id')

    data = new_direction.model_dump()

    valute_from = data.pop('valute_from')
    valute_to = data.pop('valute_to')
    # __min_amount = data.pop('min_amount')
    # __max_amount = data.pop('max_amount')
    exchange_rates = data.pop('exchange_rates')
        
    try:
        direction = NoCashDirection.objects.select_related('valute_from',
                                                           'valute_to')\
                                            .get(valute_from__code_name=valute_from,
                                                 valute_to__code_name=valute_to)
        partner = CustomUser.objects.filter(pk=partner_id).get()
        exchange_id = partner.exchange_id
    except Exception as ex:
        print(ex)
        raise HTTPException(status_code=404)
    else:
        # data['direction'] = direction
        data.update(
            {'direction_id': direction.pk,
             'exchange_id': exchange_id}
        )

        if len(exchange_rates) > 4:
            raise HTTPException(status_code=400,
                                detail='Количество доп объемов для направления должно быть не больше 3 шт')

        main_exchange_rate, additional_exchange_rates = exchange_rates[0], exchange_rates[1:]

        # convert_min_max_count(main_exchange_rate,
        #                       marker='main')

        main_exchange_rate.pop('rate_coefficient')
        main_exchange_rate.pop('min_count')
        main_exchange_rate.pop('max_count')

        data.update(main_exchange_rate)
        # make_valid_values_for_dict(data)

        try:
            with transaction.atomic():
                new_partner_dirction = NonCashDirection.objects.create(**data)

                if additional_exchange_rates:
                    partner = CustomUser.objects.filter(pk=partner_id).get()
                    exchange_id = partner.exchange_id

                    min_count_list = [_exchange_rate.get('min_count') for _exchange_rate in additional_exchange_rates]

                    if len(min_count_list) != len(set(min_count_list)):
                            raise HTTPException(status_code=400,
                                                detail='Несколько записей об объемах содержат одинаковые min_count')

                    bulk_create_list = []

                    for additional_exchange_rate in additional_exchange_rates:
                        
                        if not additional_exchange_rate.get('min_count'):
                            raise HTTPException(status_code=400,
                                                detail='Одна или несколько записей об объемах содержит пустой min_count')

                        if not additional_exchange_rate.get('rate_coefficient'):
                            raise HTTPException(status_code=400,
                                                detail='Одна или несколько записей об объемах содержит пустой rate_coefficient')


                        exchange_rate_data = {
                            'exchange_id': exchange_id,
                            'exchange_direction_id': new_partner_dirction.pk,
                        }

                        convert_min_max_count(additional_exchange_rate,
                                              marker='additional')
                        
                        exchange_rate_data.update(additional_exchange_rate)
                        
                        # make_valid_values_for_dict(exchange_rate_data)

                        new_exchangedirection_rate = NonCashDirectionRate(**exchange_rate_data)

                        bulk_create_list.append(new_exchangedirection_rate)
                    
                    NonCashDirectionRate.objects.bulk_create(bulk_create_list)

            return {'status': 'success',
                    'details': f'Партнерское направление {direction.valute_from_id} -> {direction.valute_to_id} добавлено'}
        except IntegrityError as ex:
            print(ex)
            raise HTTPException(status_code=423,
                                detail='Такое направление уже существует')


@new_partner_router.post('/add_partner_no_cash_direction')
def new_add_partner_noncash_direction(partner: new_partner_dependency,
                                      new_direction: AddPartnerNoCashDirectionSchema):
    partner_id = partner.get('partner_id')

    data = new_direction.model_dump()

    valute_from = data.pop('valute_from')
    valute_to = data.pop('valute_to')
    valute_from, valute_to = valute_from.upper(), valute_to.upper()

    exchange_rates = data.pop('exchange_rates')
        
    try:
        direction = no_cash_models.NewDirection.objects.select_related('valute_from',
                                                                       'valute_to')\
                                            .get(valute_from_id=valute_from,
                                                 valute_to_id=valute_to)
    except ObjectDoesNotExist as ex:
        print(ex)
        raise HTTPException(status_code=404,
                            detail=f'Direction {valute_from} -> {valute_to} not found')
    try:
        partner = partner_models.NewCustomUser.objects.filter(pk=partner_id).get()
        exchange_id = partner.exchange_id
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404,
                            detail=f'Partner account not found by given JWT token')
    else:
        data.update(
            {'direction_id': direction.pk,
             'exchange_id': exchange_id,
             'min_amount': new_direction.min_amount,
             'max_amount': new_direction.max_amount}
        )

        if len(exchange_rates) > 4:
            raise HTTPException(status_code=400,
                                detail='Количество доп объемов для направления должно быть не больше 3 шт')

        main_exchange_rate, additional_exchange_rates = exchange_rates[0], exchange_rates[1:]

        # convert_min_max_count(main_exchange_rate,
        #                       marker='main')

        main_exchange_rate.pop('rate_coefficient')
        main_exchange_rate.pop('min_count')
        main_exchange_rate.pop('max_count')

        data.update(main_exchange_rate)

        try:
            with transaction.atomic():
                new_partner_dirction = partner_models.NewNonCashDirection.objects.create(**data)

                if additional_exchange_rates:

                    min_count_list = [_exchange_rate.get('min_count') for _exchange_rate in additional_exchange_rates]

                    if len(min_count_list) != len(set(min_count_list)):
                            raise HTTPException(status_code=400,
                                                detail='Несколько записей об объемах содержат одинаковые min_count')

                    bulk_create_list = []

                    for additional_exchange_rate in additional_exchange_rates:
                        
                        if not additional_exchange_rate.get('min_count'):
                            raise HTTPException(status_code=400,
                                                detail='Одна или несколько записей об объемах содержит пустой min_count')

                        if not additional_exchange_rate.get('rate_coefficient'):
                            raise HTTPException(status_code=400,
                                                detail='Одна или несколько записей об объемах содержит пустой rate_coefficient')


                        exchange_rate_data = {
                            'exchange_id': exchange_id,
                            'exchange_direction_id': new_partner_dirction.pk,
                        }

                        convert_min_max_count(additional_exchange_rate,
                                              marker='additional')
                        
                        exchange_rate_data.update(additional_exchange_rate)

                        new_exchangedirection_rate = partner_models.NewNonCashDirectionRate(**exchange_rate_data)

                        bulk_create_list.append(new_exchangedirection_rate)
                    
                    partner_models.NewNonCashDirectionRate.objects.bulk_create(bulk_create_list)

            return {'status': 'success',
                    'details': f'Партнерское направление {valute_from} -> {valute_to} добавлено'}
        except IntegrityError as ex:
            print(ex)
            raise HTTPException(status_code=423,
                                detail='Такое безналичное направление уже существует')


# @partner_router.patch('/edit_partner_directions')
def edit_partner_directions_by(partner: partner_dependency,
                               response_body: NewListEditedPartnerDirectionSchema):
    # print(len(connection.queries))
    partner_id = partner.get('partner_id')

    data: dict = response_body.model_dump()

    location_id = data['id']
    marker = data['marker']
    edited_direction_list = data['directions']

    city = None

    if marker == 'country':
        direction_model = CountryDirection
        direction_rate_model = CountryDirectionRate
        _filter = Q(country__exchange__account__pk=partner_id,
                    country__pk=location_id)
    else:
        direction_model = Direction
        direction_rate_model = DirectionRate
        _filter = Q(city__exchange__account__pk=partner_id,
                    city__pk=location_id)
        city = PartnerCity.objects.select_related('exchange',
                                                'exchange__account',
                                                'city')\
                                    .filter(exchange__account__pk=partner_id,
                                            pk=location_id)

    partner_directions = direction_model.objects\
                                    .select_related(marker,
                                                    f'{marker}__exchange__account',
                                                    'direction',
                                                    'direction__valute_from',
                                                    'direction__valute_to')\
                                    .filter(_filter)
                                    # .prefetch_related('direction_rates')\
    try:
        with transaction.atomic():
            for edited_direction in edited_direction_list:
                _id = edited_direction.pop('id')
                
                exchange_rates: list[dict] = edited_direction.pop('exchange_rates')
                
                main_exchange_rate, additional_exchange_rates = exchange_rates[0], exchange_rates[1:]

                convert_min_max_count(main_exchange_rate,
                                    marker='main')
                
                # print(main_exchange_rate)

                main_exchange_rate.pop('rate_coefficient')
                main_exchange_rate.pop('id')

                edited_direction['time_update'] = datetime.now()
                edited_direction.update(main_exchange_rate)

                # print(edited_direction)

                partner_directions.filter(pk=_id).update(**edited_direction)

                min_count_list = [_exchange_rate.get('min_count') for _exchange_rate in additional_exchange_rates]

                if len(min_count_list) != len(set(min_count_list)):
                        raise HTTPException(status_code=400,
                                            detail='Несколько записей об объемах содержат одинаковые min_count')

                # current_partner_diretction = partner_directions.get(pk=_id)

                # direction_rates = current_partner_diretction.direction_rates.all()

                # print(direction_rates)

                # direction_rates_dict = {direction_rate.min_rate_limit: direction_rate\
                #                          for direction_rate in direction_rates}
                
                # print(direction_rates_dict)

                direction_rate_id_set = set(direction_rate_model.objects\
                                                        .filter(exchange_direction_id=_id)\
                                                        .values_list('pk', flat=True))

                # direction_rate_id_set = {el.get('id') for el in additional_exchange_rates}

                for additional_exchange_rate in additional_exchange_rates:
                    
                    if not additional_exchange_rate.get('min_count'):
                        raise HTTPException(status_code=400,
                                            detail='Одна или несколько записей об объемах содержит пустой min_count')

                    if not additional_exchange_rate.get('rate_coefficient'):
                        raise HTTPException(status_code=400,
                                            detail='Одна или несколько записей об объемах содержит пустой rate_coefficient')

                    _direction_rate_id = additional_exchange_rate.pop('id')

                    convert_min_max_count(additional_exchange_rate,
                                          marker='additional')
                    
                    direction_rate_model.objects.filter(pk=_direction_rate_id)\
                                                .update(**additional_exchange_rate)
                    
                    direction_rate_id_set.remove(_direction_rate_id)
                
                if direction_rate_id_set:
                    print('in delete', direction_rate_id_set)
                    direction_rate_model.objects.filter(pk__in=direction_rate_id_set).delete()

            if city:
                city.update(time_update=timezone.now())
    except Exception as ex:
        print('EXCEPTION', ex)
        raise HTTPException(status_code=400)
    else:
        return {'status': 'success',
                'details': f'updated {len(edited_direction_list)} directions'}
    

@new_partner_router.patch('/edit_partner_directions')
def new_edit_partner_directions_by(partner: new_partner_dependency,
                                   response_body: NewListEditedPartnerDirectionSchema):
    partner_id = partner.get('partner_id')

    data: dict = response_body.model_dump()

    location_id = data['id']
    marker = data['marker']
    edited_direction_list = data['directions']

    city = None

    if marker == 'country':
        direction_model = partner_models.NewCountryDirection
        direction_rate_model = partner_models.NewCountryDirectionRate
        _filter = Q(exchange__account__pk=partner_id,
                    country__pk=location_id)
    else:
        direction_model = partner_models.NewDirection
        direction_rate_model = partner_models.NewDirectionRate
        _filter = Q(exchange__account__pk=partner_id,
                    city__pk=location_id)
        city = partner_models.NewPartnerCity.objects.select_related('exchange',
                                                                    'exchange__account',
                                                                    'city')\
                                    .filter(exchange__account__pk=partner_id,
                                            pk=location_id)

    partner_directions = direction_model.objects\
                                    .select_related(marker,
                                                    'exchange__account',
                                                    'direction',
                                                    'direction__valute_from',
                                                    'direction__valute_to')\
                                    .filter(_filter)

    try:
        with transaction.atomic():
            for edited_direction in edited_direction_list:
                _id = edited_direction.pop('id')
                
                exchange_rates: list[dict] = edited_direction.pop('exchange_rates')
                
                main_exchange_rate, additional_exchange_rates = exchange_rates[0], exchange_rates[1:]

                convert_min_max_count(main_exchange_rate,
                                    marker='main')

                main_exchange_rate.pop('rate_coefficient')
                main_exchange_rate.pop('id')

                edited_direction['time_update'] = timezone.now()
                edited_direction.update(main_exchange_rate)

                partner_directions.filter(pk=_id).update(**edited_direction)

                min_count_list = [_exchange_rate.get('min_count') for _exchange_rate in additional_exchange_rates]

                if len(min_count_list) != len(set(min_count_list)):
                        raise HTTPException(status_code=400,
                                            detail='Несколько записей об объемах содержат одинаковые min_count')

                direction_rate_id_set = set(direction_rate_model.objects\
                                                        .filter(exchange_direction_id=_id)\
                                                        .values_list('pk', flat=True))

                for additional_exchange_rate in additional_exchange_rates:
                    
                    if not additional_exchange_rate.get('min_count'):
                        raise HTTPException(status_code=400,
                                            detail='Одна или несколько записей об объемах содержит пустой min_count')

                    if not additional_exchange_rate.get('rate_coefficient'):
                        raise HTTPException(status_code=400,
                                            detail='Одна или несколько записей об объемах содержит пустой rate_coefficient')

                    _direction_rate_id = additional_exchange_rate.pop('id')

                    convert_min_max_count(additional_exchange_rate,
                                          marker='additional')
                    
                    direction_rate_model.objects.filter(pk=_direction_rate_id)\
                                                .update(**additional_exchange_rate)
                    
                    direction_rate_id_set.remove(_direction_rate_id)
                
                if direction_rate_id_set:
                    print('in delete', direction_rate_id_set)
                    direction_rate_model.objects.filter(pk__in=direction_rate_id_set).delete()

            if city:
                city.update(time_update=timezone.now())
    except Exception as ex:
        print('EXCEPTION', ex)
        raise HTTPException(status_code=400)
    else:
        return {'status': 'success',
                'details': f'updated {len(edited_direction_list)} directions'}


# @partner_router.patch('/edit_partner_no_cash_directions')
def edit_partner_no_cash_directions(partner: partner_dependency,
                                    response_body: ListEditedPartnerNoCashDirectionSchema):
    # print(len(connection.queries))
    partner_id = partner.get('partner_id')

    data: dict = response_body.model_dump()

    # location_id = data['id']
    # marker = data['marker']
    edited_direction_list = data['directions']

    city = None

    # if marker == 'country':
    #     direction_model = CountryDirection
    #     direction_rate_model = CountryDirectionRate
    #     _filter = Q(country__exchange__account__pk=partner_id,
    #                 country__pk=location_id)
    # else:
    #     direction_model = Direction
    #     direction_rate_model = DirectionRate
    #     _filter = Q(city__exchange__account__pk=partner_id,
    #                 city__pk=location_id)
    #     city = PartnerCity.objects.select_related('exchange',
    #                                             'exchange__account',
    #                                             'city')\
    #                                 .filter(exchange__account__pk=partner_id,
    #                                         pk=location_id)

    partner_directions = NonCashDirection.objects\
                                    .select_related('exchange',
                                                    'direction',
                                                    'direction__valute_from',
                                                    'direction__valute_to')\
                                    .filter(exchange__account__pk=partner_id)
                                    # .prefetch_related('direction_rates')\
    try:
        with transaction.atomic():
            for edited_direction in edited_direction_list:
                _id = edited_direction.pop('id')
                
                exchange_rates: list[dict] = edited_direction.pop('exchange_rates')
                
                main_exchange_rate, additional_exchange_rates = exchange_rates[0], exchange_rates[1:]

                convert_min_max_count(main_exchange_rate,
                                    marker='main')
                
                # print(main_exchange_rate)

                main_exchange_rate.pop('rate_coefficient')
                main_exchange_rate.pop('id')

                edited_direction['time_update'] = datetime.now()
                edited_direction.update(main_exchange_rate)

                # print(edited_direction)

                partner_directions.filter(pk=_id).update(**edited_direction)

                min_count_list = [_exchange_rate.get('min_count') for _exchange_rate in additional_exchange_rates]

                if len(min_count_list) != len(set(min_count_list)):
                        raise HTTPException(status_code=400,
                                            detail='Несколько записей об объемах содержат одинаковые min_count')

                # current_partner_diretction = partner_directions.get(pk=_id)

                # direction_rates = current_partner_diretction.direction_rates.all()

                # print(direction_rates)

                # direction_rates_dict = {direction_rate.min_rate_limit: direction_rate\
                #                          for direction_rate in direction_rates}
                
                # print(direction_rates_dict)

                direction_rate_id_set = set(NonCashDirectionRate.objects\
                                                        .filter(exchange_direction_id=_id)\
                                                        .values_list('pk', flat=True))

                # direction_rate_id_set = {el.get('id') for el in additional_exchange_rates}

                for additional_exchange_rate in additional_exchange_rates:
                    
                    if not additional_exchange_rate.get('min_count'):
                        raise HTTPException(status_code=400,
                                            detail='Одна или несколько записей об объемах содержит пустой min_count')

                    if not additional_exchange_rate.get('rate_coefficient'):
                        raise HTTPException(status_code=400,
                                            detail='Одна или несколько записей об объемах содержит пустой rate_coefficient')

                    _direction_rate_id = additional_exchange_rate.pop('id')

                    convert_min_max_count(additional_exchange_rate,
                                          marker='additional')
                    
                    NonCashDirectionRate.objects.filter(pk=_direction_rate_id)\
                                                .update(**additional_exchange_rate)
                    
                    direction_rate_id_set.remove(_direction_rate_id)
                
                if direction_rate_id_set:
                    print('in delete', direction_rate_id_set)
                    NonCashDirectionRate.objects.filter(pk__in=direction_rate_id_set).delete()

            # if city:
            #     city.update(time_update=timezone.now())
    except Exception as ex:
        print('EXCEPTION', ex)
        raise HTTPException(status_code=400)
    else:
        return {'status': 'success',
                'details': f'updated {len(edited_direction_list)} directions'}
    

@new_partner_router.patch('/edit_partner_no_cash_directions')
def new_edit_partner_no_cash_directions(partner: new_partner_dependency,
                                        response_body: ListEditedPartnerNoCashDirectionSchema):
    partner_id = partner.get('partner_id')

    data: dict = response_body.model_dump()

    edited_direction_list = data['directions']

    partner_directions = partner_models.NewNonCashDirection.objects\
                                    .select_related('exchange',
                                                    'direction',
                                                    'direction__valute_from',
                                                    'direction__valute_to')\
                                    .filter(exchange__account__pk=partner_id)

    try:
        with transaction.atomic():
            for edited_direction in edited_direction_list:
                _id = edited_direction.pop('id')
                
                exchange_rates: list[dict] = edited_direction.pop('exchange_rates')
                
                main_exchange_rate, additional_exchange_rates = exchange_rates[0], exchange_rates[1:]

                convert_min_max_count(main_exchange_rate,
                                    marker='main')

                main_exchange_rate.pop('rate_coefficient')
                main_exchange_rate.pop('id')

                edited_direction['time_update'] = datetime.now()
                edited_direction.update(main_exchange_rate)

                partner_directions.filter(pk=_id).update(**edited_direction)

                min_count_list = [_exchange_rate.get('min_count') for _exchange_rate in additional_exchange_rates]

                if len(min_count_list) != len(set(min_count_list)):
                        raise HTTPException(status_code=400,
                                            detail='Несколько записей об объемах содержат одинаковые min_count')

                direction_rate_id_set = set(partner_models.NewNonCashDirectionRate.objects\
                                                        .filter(exchange_direction_id=_id)\
                                                        .values_list('pk', flat=True))

                for additional_exchange_rate in additional_exchange_rates:
                    
                    if not additional_exchange_rate.get('min_count'):
                        raise HTTPException(status_code=400,
                                            detail='Одна или несколько записей об объемах содержит пустой min_count')

                    if not additional_exchange_rate.get('rate_coefficient'):
                        raise HTTPException(status_code=400,
                                            detail='Одна или несколько записей об объемах содержит пустой rate_coefficient')

                    _direction_rate_id = additional_exchange_rate.pop('id')

                    convert_min_max_count(additional_exchange_rate,
                                          marker='additional')
                    
                    partner_models.NewNonCashDirectionRate.objects.filter(pk=_direction_rate_id)\
                                                .update(**additional_exchange_rate)
                    
                    direction_rate_id_set.remove(_direction_rate_id)
                
                if direction_rate_id_set:
                    print('in delete', direction_rate_id_set)
                    partner_models.NewNonCashDirectionRate.objects.filter(pk__in=direction_rate_id_set).delete()

    except Exception as ex:
        print('EXCEPTION', ex)
        raise HTTPException(status_code=400)
    else:
        return {'status': 'success',
                'details': f'updated {len(edited_direction_list)} directions'}


# @partner_router.delete('/delete_partner_direction')
def delete_partner_direction(partner: partner_dependency,
                             data: DeletePartnerDirectionSchema):
    partner_id = partner.get('partner_id')
    
    if data.marker == 'country':
        if data.id is None:
            raise HTTPException(status_code=400,
                                detail='field "id" is required')
        
        _model = CountryDirection
        _filter = Q(country_id=data.id,
                    country__exchange__account__pk=partner_id)
        select_related_fileds = f'{data.marker}, {data.marker}__exchange, {data.marker}__exchange__account'
    elif data.marker == 'city':
        if data.id is None:
            raise HTTPException(status_code=400,
                                detail='field "id" is required')
        
        _model = Direction
        _filter = Q(city_id=data.id,
                    city__exchange__account__pk=partner_id)
        select_related_fileds = f'{data.marker}, {data.marker}__exchange, {data.marker}__exchange__account'
    elif data.marker == 'no_cash':
        _model = NonCashDirection
        _filter = Q(exchange__account__pk=partner_id)
        select_related_fileds = 'exchange, exchange__account'

    # _model.objects.select_related(data.marker,
    #                               f'{data.marker}__exchange',
    #                               f'{data.marker}__exchange__account')\
    #                 .filter(_filter,
    #                         pk=data.direction_id)\
    #                 .delete()
    _model.objects.select_related(select_related_fileds)\
                    .filter(_filter,
                            pk=data.direction_id)\
                    .delete()
    return {'status': 'success',
            'details': 'Партнёрское направление удалено'}


@new_partner_router.delete('/delete_partner_direction')
def new_delete_partner_direction(partner: new_partner_dependency,
                                 data: DeletePartnerDirectionSchema):
    partner_id = partner.get('partner_id')
    
    if data.marker == 'country':
        if data.id is None:
            raise HTTPException(status_code=400,
                                detail='field "id" is required')
        
        _model = partner_models.NewCountryDirection
        _filter = Q(country_id=data.id,
                    exchange__account__pk=partner_id)
        select_related_fields = f'{data.marker}, exchange, exchange__account'
    elif data.marker == 'city':
        if data.id is None:
            raise HTTPException(status_code=400,
                                detail='field "id" is required')
        
        _model = partner_models.NewDirection
        _filter = Q(city_id=data.id,
                    exchange__account__pk=partner_id)
        select_related_fields = f'{data.marker}, exchange, exchange__account'
    elif data.marker == 'no_cash':
        _model = partner_models.NewNonCashDirection
        _filter = Q(exchange__account__pk=partner_id)
        select_related_fields = 'exchange, exchange__account'
    try:
        _model.objects.select_related(select_related_fields)\
                        .filter(_filter,
                                pk=data.direction_id)\
                        .delete()
    except Exception as ex:
        print(ex)
        raise HTTPException(status_code=500,
                            detail=f'Error with try delete {data.marker} Direction, direction_id: {data.direction_id}')
    
    return {'status': 'success',
            'details': 'Партнёрское направление удалено'}


exchange_link_count_dict = {
    'city': ExchangeLinkCount,
    'country': CountryExchangeLinkCount,
    'no_cash': NonCashExchangeLinkCount,
}

# @partner_router.post('/increase_link_count')
def increase_link_count(data: ExchangeLinkCountSchema):
    exchange_link_count: Union[ExchangeLinkCount,
                               CountryExchangeLinkCount] = exchange_link_count_dict.get(data.direction_marker)

    if not exchange_link_count:
        raise HTTPException(status_code=400,
                            detail='invalid marker')

    check_user = Guest.objects.filter(tg_id=data.user_id)

    if not check_user.exists():
        raise HTTPException(status_code=400)

    exchange_link_count_queryset = exchange_link_count.objects\
                                                .filter(exchange_id=data.exchange_id,
                                                        exchange_marker=data.direction_marker,
                                                        exchange_direction_id=data.exchange_direction_id,
                                                        user_id=data.user_id)
    if not exchange_link_count_queryset.exists():
        try:
            exchange_link_count_queryset = exchange_link_count.objects.create(user_id=data.user_id,
                                                                            exchange_id=data.exchange_id,
                                                                            exchange_marker=data.direction_marker,
                                                                            exchange_direction_id=data.exchange_direction_id,
                                                                            count=1)
        except IntegrityError:
            raise HTTPException(status_code=400,
                                detail='Constraint error. This row already exists')
            # return {'status': 'error',
            #         'details': 'Constraint error. This row already exists'}
    else:
        exchange_link_count_queryset.update(count=F('count') + 1)

    return {'status': 'success'}


# @partner_router.get('/bankomats_by_valute',
#                          response_model=list[BankomatDetailSchema],
#                          response_model_by_alias=False)
def get_bankomat_list_by_valute(partner: partner_dependency,
                                valute: str):
    partner_id = partner.get('partner_id')
    
    try:
        if Valute.objects.get(pk=valute).type_valute != 'ATM QR':
            raise HTTPException(status_code=400,
                                detail='Некорректная валюта')
    except Exception as ex:
        print('here', ex)
        raise HTTPException(status_code=400,
                            detail='Некорректная валюта')
    
    return get_partner_bankomats_by_valute(partner_id,
                                           valute)


@new_partner_router.get('/bankomats_by_valute',
                         response_model=list[BankomatDetailSchema],
                         response_model_by_alias=False)
def new_get_bankomat_list_by_valute(partner: new_partner_dependency,
                                    valute_id: int):
    partner_id = partner.get('partner_id')
    
    try:
        valute = NewValute.objects.get(pk=valute_id)
    except ObjectDoesNotExist:
            raise HTTPException(status_code=404,
                                detail='Valute not found by given "valute_id"')
    
    if valute.type_valute != 'ATM QR':
            raise HTTPException(status_code=400,
                                detail='Некорректная валюта')
    
    return get_bankomats_by_valute(partner_id,
                                   valute_id)