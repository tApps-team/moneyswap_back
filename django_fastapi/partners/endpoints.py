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

from general_models.utils.endpoints import (get_valute_json_3,
                                            get_valute_json_4,
                                            try_generate_icon_url)
from general_models.utils.tasks import make_valid_values_for_dict
from general_models.utils.periodic_tasks import get_or_create_schedule
from general_models.schemas import MultipleName, MultipleName2
from general_models.models import ExchangeAdmin, ExchangeAdminOrder, Valute, Guest

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

from .auth.endpoints import partner_dependency

from .utils.admin import make_city_active

from .utils.endpoints import (generate_partner_cities,
                              generate_partner_countries,
                              generate_partner_directions_by_3,
                              generate_partner_directions_by_city,
                              generate_partner_directions_by_city2,
                              generate_valute_list,
                              generate_actual_course,
                              generate_valute_list2,
                              generate_partner_cities2, request_to_bot_exchange_admin_direction_notification,
                              try_add_bankomats_to_valute,
                              get_partner_bankomats_by_valute,
                              convert_min_max_count)

from .schemas import (AddPartnerCountrySchema,
                      AddPartnerDirectionSchema3,
                      AddBankomatSchema,
                      BankomatDetailSchema,
                      DeletePartnerDirectionSchema, DirectionSchema2, DirectionSchema3,
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



# @partner_router.get('/partner_cities',
#                     response_model=list[PartnerCitySchema2],
#                     response_model_by_alias=False)
# def get_partner_cities(partner: partner_dependency):
#     partner_id = partner.get('partner_id')

#     partner_cities = PartnerCity.objects.select_related('exchange',
#                                                         'city',
#                                                         'city__country',
#                                                         'exchange__account')\
#                                         .prefetch_related('working_days')\
#                                         .filter(exchange__account__pk=partner_id).all()

#     return generate_partner_cities2(partner_cities)


@partner_router.get('/partner_cities',
                    response_model=list[PartnerCitySchema3],
                    response_model_by_alias=False)
def get_partner_cities(partner: partner_dependency):
    partner_id = partner.get('partner_id')

    partner_cities = PartnerCity.objects.select_related('exchange',
                                                        'city',
                                                        'city__country',
                                                        'exchange__account')\
                                        .prefetch_related('working_days')\
                                        .filter(exchange__account__pk=partner_id).all()

    return generate_partner_cities2(partner_cities)


# @test_partner_router.get('/partner_countries',
#                     response_model=list[PartnerCountrySchema3],
#                     response_model_by_alias=False)
# def get_partner_countries(partner: partner_dependency):
#     partner_id = partner.get('partner_id')

#     partner_counrties = PartnerCountry.objects.select_related('exchange',
#                                                               'exchange__account',
#                                                               'country')\
#                                         .filter(exchange__account__pk=partner_id)\
#                                         .all()
    
#     return generate_partner_countries(partner_counrties)


@partner_router.get('/partner_countries',
                    response_model=list[PartnerCountrySchema3],
                    response_model_by_alias=False)
def get_partner_countries(partner: partner_dependency):
    partner_id = partner.get('partner_id')

    partner_counrties = PartnerCountry.objects.select_related('exchange',
                                                              'exchange__account',
                                                              'country')\
                                        .filter(exchange__account__pk=partner_id)\
                                        .all()
    
    return generate_partner_countries(partner_counrties)


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


# @partner_router.get('/directions_by_city',
#                     response_model=list[DirectionSchema])
# def get_partner_directions_by_city(partner: partner_dependency,
#                                    code_name: str):
#     partner_id = partner.get('partner_id')

#     directions = Direction.objects.select_related('city',
#                                                   'city__city',
#                                                   'city__exchange',
#                                                   'city__exchange__account',
#                                                   'direction',
#                                                   'direction__valute_from',
#                                                   'direction__valute_to')\
#                                     .filter(city__exchange__account__pk=partner_id,
#                                             city__city__code_name=code_name.upper())\
#                                     .all()

#     return generate_partner_directions_by_city(directions)


# @test_partner_router.get('/directions_by_counties',
#                     response_model=list[DirectionSchema])
# def get_partner_directions_by_city(partner: partner_dependency,
#                                    country_id: int):
#     partner_id = partner.get('partner_id')

#     country_directions = CountryDirection.objects.select_related('country')\
#                                                 .filter(country__pk=country_id)\
#                                                 .all()
    


#     # directions = Direction.objects.select_related('city',
#     #                                               'city__city',
#     #                                               'city__exchange',
#     #                                               'city__exchange__account',
#     #                                               'direction',
#     #                                               'direction__valute_from',
#     #                                               'direction__valute_to')\
#     #                                 .filter(city__exchange__account__pk=partner_id,
#     #                                         city__city__code_name=code_name.upper())\
#                                     .all()

#     return generate_partner_directions_by_city(directions)

# @test_partner_router.get('/directions_by',
#                     response_model=list[DirectionSchema])
# def get_partner_directions_by(partner: partner_dependency,
#                               id: int,
#                               marker: Literal['country', 'city']):
#     partner_id = partner.get('partner_id')

#     if marker == 'country':
#         direction_model = CountryDirection
#         additional_filter = Q(country__exchange__account__pk=partner_id,
#                               country__pk=id)
#     else:
#         direction_model = Direction
#         additional_filter = Q(city__exchange__account__pk=partner_id,
#                               city__pk=id)

#     directions = direction_model.objects.select_related(marker,
#                                                         f'{marker}__exchange',
#                                                         f'{marker}__exchange__account',
#                                                         'direction',
#                                                         'direction__valute_from',
#                                                         'direction__valute_to')\
#                                         .filter(additional_filter)\
#                                         .all()

#     return generate_partner_directions_by_city(directions)


# @partner_router.get('/directions_by',
#                     response_model=list[DirectionSchema])
# def get_partner_directions_by(partner: partner_dependency,
#                               id: int,
#                               marker: Literal['country', 'city']):
#     partner_id = partner.get('partner_id')

#     if marker == 'country':
#         direction_model = CountryDirection
#         additional_filter = Q(country__exchange__account__pk=partner_id,
#                               country__pk=id)
#     else:
#         direction_model = Direction
#         additional_filter = Q(city__exchange__account__pk=partner_id,
#                               city__pk=id)

#     directions = direction_model.objects.select_related(marker,
#                                                         f'{marker}__exchange',
#                                                         f'{marker}__exchange__account',
#                                                         'direction',
#                                                         'direction__valute_from',
#                                                         'direction__valute_to')\
#                                         .filter(additional_filter)\
#                                         .all()

#     return generate_partner_directions_by_city(directions)


# @test_partner_router.get('/directions_by',
#                     response_model=list[DirectionSchema3])
# def get_partner_directions_by(partner: partner_dependency,
#                               id: int,
#                               marker: Literal['country', 'city']):
#     print(len(connection.queries))
#     partner_id = partner.get('partner_id')

#     if marker == 'country':
#         direction_model = CountryDirection
#         direction_rate_model = CountryDirectionRate
#         additional_filter = Q(country__exchange__account__pk=partner_id,
#                               country__pk=id)
#     else:
#         direction_model = Direction
#         direction_rate_model = DirectionRate
#         additional_filter = Q(city__exchange__account__pk=partner_id,
#                               city__pk=id)
        
#     direction_rate_prefetch = Prefetch('direction_rates',
#                                        direction_rate_model.objects.order_by('min_rate_limit'))

#     directions = direction_model.objects.select_related(marker,
#                                                         f'{marker}__exchange',
#                                                         f'{marker}__exchange__account',
#                                                         'direction',
#                                                         'direction__valute_from',
#                                                         'direction__valute_to')\
#                                         .prefetch_related(direction_rate_prefetch)\
#                                         .filter(additional_filter)\
#                                         .all()

#     return generate_partner_directions_by_3(directions,
#                                                 marker)


@partner_router.get('/directions_by',
                    response_model=list[DirectionSchema3])
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


@partner_router.get('/no_cash_directions',
                    response_model=list[NoCashDirectionSchema])
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



# @partner_router.get('/directions_by',
#                     response_model=list[DirectionSchema2])
# def get_partner_directions_by(partner: partner_dependency,
#                               id: int,
#                               marker: Literal['country', 'city']):
#     partner_id = partner.get('partner_id')

#     if marker == 'country':
#         direction_model = CountryDirection
#         additional_filter = Q(country__exchange__account__pk=partner_id,
#                               country__pk=id)
#     else:
#         direction_model = Direction
#         additional_filter = Q(city__exchange__account__pk=partner_id,
#                               city__pk=id)

#     directions = direction_model.objects.select_related(marker,
#                                                         f'{marker}__exchange',
#                                                         f'{marker}__exchange__account',
#                                                         'direction',
#                                                         'direction__valute_from',
#                                                         'direction__valute_to')\
#                                         .filter(additional_filter)\
#                                         .all()

#     return generate_partner_directions_by_city2(directions,
#                                                 marker)


# @test_partner_router.get('/directions_by',
#                     response_model=list[DirectionSchema2])
# def get_partner_directions_by2(partner: partner_dependency,
#                               id: int,
#                               marker: Literal['country', 'city']):
#     partner_id = partner.get('partner_id')

#     if marker == 'country':
#         direction_model = CountryDirection
#         additional_filter = Q(country__exchange__account__pk=partner_id,
#                               country__pk=id)
#     else:
#         direction_model = Direction
#         additional_filter = Q(city__exchange__account__pk=partner_id,
#                               city__pk=id)

#     directions = direction_model.objects.select_related(marker,
#                                                         f'{marker}__exchange',
#                                                         f'{marker}__exchange__account',
#                                                         'direction',
#                                                         'direction__valute_from',
#                                                         'direction__valute_to')\
#                                         .filter(additional_filter)\
#                                         .all()

#     return generate_partner_directions_by_city2(directions,
#                                                 marker)


# @test_partner_router.get('/available_valutes')
# def get_available_valutes_for_partner2(base: str):
#     base = base.upper()

#     queries = CashDirection.objects.select_related('valute_from',
#                                                    'valute_to')\
#                                     .filter(valute_from__available_for_partners=True,
#                                             valute_to__available_for_partners=True)
    
#     if base == 'ALL':
#         marker = 'valute_from'
#         queries = queries.values_list('valute_from_id', flat=True)
#     else:
#         marker = 'valute_to'
#         queries = queries.filter(valute_from=base)
#         queries = queries.values_list('valute_to_id', flat=True)

#     # return generate_valute_list2(queries, marker)
#     return get_valute_json_4(queries)


# @partner_router.get('/available_valutes')
# def get_available_valutes_for_partner(base: str):
#     base = base.upper()

#     queries = CashDirection.objects.select_related('valute_from',
#                                                    'valute_to')\
#                                     .filter(valute_from__available_for_partners=True,
#                                             valute_to__available_for_partners=True)
    
#     if base == 'ALL':
#         marker = 'valute_from'
#     else:
#         marker = 'valute_to'
#         queries = queries.filter(valute_from=base)

#     return generate_valute_list2(queries, marker)

@partner_router.get('/available_valutes')
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


# @partner_router.get('/no_cash_available_valutes')
# def get_no_cash_available_valutes_for_partner(base: str):
#     base = base.upper()

#     queries = NoCashDirection.objects.select_related('valute_from',
#                                                      'valute_to')\
#                                     .filter(valute_from__available_for_partners=True,
#                                             valute_to__available_for_partners=True)
    
#     if base == 'ALL':
#         marker = 'valute_from'
#         queries = queries.values_list('valute_from_id', flat=True)
#     else:
#         marker = 'valute_to'
#         queries = queries.filter(valute_from=base)
#         queries = queries.values_list('valute_to_id', flat=True)

#     # return generate_valute_list2(queries, marker)
#     return get_valute_json_4(queries)


@partner_router.post('/change_password')
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


@partner_router.get('/actual_course',
                    response_model=ActualCourseSchema)
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
    

# @partner_router.get('/account_info',
#                     response_model=AccountInfoSchema)
# def get_account_info(partner: partner_dependency):
#     partner_id = partner.get('partner_id')

#     try:
#         exchange = Exchange.objects.select_related('account')\
#                                     .get(account__pk=partner_id)
#     except ObjectDoesNotExist:
#         raise HTTPException(status_code=404)
#     else:
#         exchange.title = AccountTitleSchema(ru=exchange.name,
#                                             en=exchange.en_name)
        
#         return exchange


@partner_router.get('/account_info',
                    response_model=NewAccountInfoSchema)
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
        
        exchange.title = AccountTitleSchema(ru=exchange.name,
                                            en=exchange.en_name)
        
        return exchange


@partner_router.get('/switch_notification_activity')
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


@partner_router.post('/add_admin_exchange_order')
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
        

@partner_router.post('/edit_admin_exchange_order')
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
                exchange_admin_query.delete()
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
        

@partner_router.delete('/delete_admin_exchange_order')
def edit_admin_exchange_order(partner: partner_dependency):
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
        


@test_partner_router.get('/dev_handler')
def test_direction(secret: str):
    if secret != DEV_HANDLER_SECRET:
        raise HTTPException(status_code=400)
    
    from django_celery_beat.models import PeriodicTask

    try:
        # task = PeriodicTask.objects.get(name='check_update_time_for_directions_task')
        task = PeriodicTask.objects.get(name='exchange_admin_notifications_task')
        interval = get_or_create_schedule(12, IntervalSchedule.HOURS)
        task.interval = interval
        task.save()
    except Exception as ex:
        print(ex)
    # else:
        # amount = fields_to_update['amount']
        # unit_time = fields_to_update['unit_time']
        # schedule = get_or_create_schedule(amount,
        #                                   UNIT_TIME_CHOICES[unit_time])
        # task.interval = schedule
        # task.save()
    
    # update_fields = [
    #     'exchange_id',
    # ]
    
    # for _marker, _model in (('city', Direction), ('country', CountryDirection)):
    #     # if _marker == 'city':
    #         # related_model = PartnerCity
    #     # else:
    #     #     related_model = PartnerCountry

    #     # select_related_field = f'{_marker}__exchange'

    #     update_list = []

    #     for direction in _model.objects.select_related(_marker).all():
    #         if _marker == 'city':
    #             exchange_id = direction.city.exchange_id
    #         else:
    #             exchange_id = direction.country.exchange_id

    #         direction.exchange_id = exchange_id

    #         update_list.append(direction)
        
    #     with transaction.atomic():
    #     # if dict_for_parse:
    #         # for direction in dict_for_parse.values():
    #             # direction.is_active = False
    #             # update_list.append(direction)
    #         # direction_ids = [el.pk for el in dict_for_parse.values()]
    #         # ExchangeDirection.objects.filter(pk__in=direction_ids).update(is_active=False)
    #         try:
    #             _model.objects.bulk_update(update_list, update_fields)
    #         except Exception as ex:
    #             print('DEV BULK UPDATE ERROR', ex)



def get_valid_active_direction_str(direction):
    _timedelta = direction.time_update - (timezone.now() - timedelta(days=3))
    total_seconds = int(_timedelta.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    formatted_time = f"{hours:02d} часов {minutes:02d} минут]"
    return f'{direction} (активно✅, отключится через {formatted_time}🕚)'



# @test_partner_router.get('/test_partner_notification')
# def test_direction():
#     # print((len(connection.queries)))
#     partner_exchange_admins = ExchangeAdmin.objects.filter(exchange_marker='partner')\
#                                                     .values_list('exchange_id', 'user_id')
    
#     # print('sql' ,partner_exchange_admins)
    
#     partner_exchange_admin_dict = {el[0]: el[-1] for el in partner_exchange_admins}

#     # print('dict',partner_exchange_admin_dict)
#     prefetch_timedetla = timezone.now() - timedelta(days=2,
#                                                     hours=12)
    
#     prefetch_city_direction_query = Prefetch('city_directions',
#                                              queryset=Direction.objects.select_related('direction__valute_from',
#                                                                                        'direction__valute_to',
#                                                                                        'city__city',
#                                                                                        'city__exchange')\
#                                                                         .filter(Q(is_active=False) | \
#                                                                                 Q(is_active=True,
#                                                                                   time_update__lte=prefetch_timedetla)))

#     prefetch_country_direction_query = Prefetch('country_directions',
#                                              queryset=CountryDirection.objects.select_related('direction__valute_from',
#                                                                                               'direction__valute_to',
#                                                                                               'country__country',
#                                                                                               'country__exchange')\
#                                                                         .filter(Q(is_active=False) | \
#                                                                                 Q(is_active=True,
#                                                                                   time_update__lte=prefetch_timedetla)))

#     prefetch_noncash_direction_query = Prefetch('no_cash_directions',
#                                              queryset=NonCashDirection.objects.select_related('direction__valute_from',
#                                                                                               'direction__valute_to',
#                                                                                               'exchange')\
#                                                                         .filter(Q(is_active=False) | \
#                                                                                 Q(is_active=True,
#                                                                                   time_update__lte=prefetch_timedetla)))

#     exchange_list = Exchange.objects.filter(pk__in=list(partner_exchange_admin_dict.keys())).prefetch_related(prefetch_city_direction_query,
#                                                                                                               prefetch_country_direction_query,
#                                                                                                               prefetch_noncash_direction_query)
#     # exchange_list = Exchange.objects.prefetch_related(prefetch_city_direction_query,
#     #                                                   prefetch_country_direction_query,
#     #                                                   prefetch_noncash_direction_query).all()

#     # exchange_list = Exchange.objects.prefetch_related(prefetch_noncash_direction_query).all()


#     for exchange in exchange_list:
#         print(exchange)

#         if exchange.name != 'test_ex':
#             continue

#         # без доп SQL запросов
#         city_direction_count = len(exchange.city_directions.all())
#         country_direction_count = len(exchange.country_directions.all())
#         no_cash_direction_count = len(exchange.no_cash_directions.all())

#         total_count = city_direction_count + country_direction_count \
#                         + no_cash_direction_count
        
#         _text = f'🔔 <b>Уведомление об актуализации курсов направлений обменника <u>{exchange.name}</u></b> \n\n'
#         _text += f'Кол-во направлений, требующих внимания: {total_count}\n\nИз них: \n- направлений на уровне городов - {city_direction_count}\n- направлений на уровне стран - {country_direction_count}\n- безналичных направлений - {no_cash_direction_count}'
#         # print(f'Кол-во направлений, требующих наблюдений или обновлений: {total_count}')
#         # print('активные направления города', active_city_direction_count)
#         # print(f'Из них {city_direction_count} направлений на уровне городов, {country_direction_count} на уровне стран, {no_cash_direction_count} безналичных направлений')

#         if total_count == 0:
#             continue

#         default_slice = 5

#         city_active_list = []
#         city_unactive_list = []

#         for c in exchange.city_directions.all():
#             if c.is_active:
#                 city_active_list.append(c)
#             else:
#                 city_unactive_list.append(c)

#         # city_active_directions_text = '\n\n'.join(f'{direction} (активно✅, отключится через {direction.time_update - (timezone.now() - timedelta(days=3))}🕚)' for direction in city_active_list[:default_slice])
#         city_active_directions_text = '\n\n'.join(f'{get_valid_active_direction_str(direction)}' for direction in city_active_list[:default_slice])

#         if len(city_active_list[default_slice:]):
#             city_active_directions_text += f'\n <i>** <u>и еще {len(city_active_list[default_slice:])} активных направлений</u></i>'

#         city_unactive_directions_text = '\n\n'.join(f'{direction} (выключено❗️)' for direction in city_unactive_list[:default_slice])

#         if len(city_unactive_list[default_slice:]):
#             city_unactive_directions_text += f'\n <i>** <u>и еще {len(city_unactive_list[default_slice:])} неактивных направлений</u></i>'

#         country_active_list = []
#         country_unactive_list = []

#         for c in exchange.country_directions.all():
#             if c.is_active:
#                 country_active_list.append(c)
#             else:
#                 country_unactive_list.append(c)

#         # country_active_directions_text = '\n\n'.join(f'{direction} (активно✅, отключится через {direction.time_update - (timezone.now() - timedelta(days=3))}🕚)' for direction in country_active_list[:default_slice])
#         country_active_directions_text = '\n\n'.join(f'{get_valid_active_direction_str(direction)}' for direction in country_active_list[:default_slice])

#         if len(country_active_list[default_slice:]):
#             country_active_directions_text += f'\n <i>** <u>и еще {len(country_active_list[default_slice:])} активных направлений</u></i>'

#         country_unactive_directions_text = '\n\n'.join(f'{direction} (выключено❗️)' for direction in country_unactive_list[:default_slice])

#         if len(country_unactive_list[default_slice:]):
#             country_unactive_directions_text += f'\n <i>** <u>и еще {len(country_unactive_list[default_slice:])} неактивных направлений</u></i>'

#         no_cash_active_list = []
#         no_cash_unactive_list = []

#         for c in exchange.no_cash_directions.all():
#             if c.is_active:
#                 no_cash_active_list.append(c)
#             else:
#                 no_cash_unactive_list.append(c)

#         # no_cash_active_directions_text = '\n\n'.join(f'{str(direction).strip()} (активно✅, отключится через {direction.time_update - (timezone.now() - timedelta(days=3))}🕚)' for direction in no_cash_active_list[:default_slice])
#         no_cash_active_directions_text = '\n\n'.join(f'{get_valid_active_direction_str(direction)}' for direction in no_cash_active_list[:default_slice])

#         if len(country_active_list[default_slice:]):
#             no_cash_active_directions_text += f'\n <i>** <u>и еще {len(no_cash_active_list[default_slice:])} активных направлений</u></i>'

#         no_cash_unactive_directions_text = ' \n\n'.join(f'{str(direction).strip()} (выключено❗️)' for direction in no_cash_unactive_list[:default_slice])

#         if len(no_cash_unactive_list[default_slice:]):
#             no_cash_unactive_directions_text += f'\n <i>** <u>и еще {len(no_cash_unactive_list[default_slice:])} неактивных направлений</u></i>'

#         # print(_text)
#         # print('<u>Направления городов, требующие внимания:</u>')
#         # if city_active_directions_text:
#         #     print(city_active_directions_text, '\n')
#         # if city_unactive_directions_text:
#         #     print(city_unactive_directions_text, '\n')
#         # print('<u>Направления стран, требующие внимания:</u>')
#         # if country_active_directions_text:
#         #     print(country_active_directions_text, '\n')
#         # if country_unactive_directions_text:
#         #     print(country_unactive_directions_text, '\n')
#         # print('<u>Безналичные направления, требующие внимания:</u>')
#         # if no_cash_active_directions_text:
#         #     print( no_cash_active_directions_text, '\n')
#         # if no_cash_unactive_directions_text:
#         #     print(no_cash_unactive_directions_text, '\n')

#         # print('*' * 8)
#         _text += '\n\n<u>Направления городов, требующие внимания:</u>\n'
#         if city_active_directions_text:
#             _text += f'{city_active_directions_text}\n'
#         if city_unactive_directions_text:
#             _text += f'{city_unactive_directions_text}\n'

#         _text += '\n\n<u>Направления стран, требующие внимания:</u>\n'
        
#         if country_active_directions_text:
#             _text += f'{country_active_directions_text}\n'
#         if country_unactive_directions_text:
#             _text += f'{country_unactive_directions_text}\n'

#         _text += '\n\n<u>Безналичные направления, требующие внимания:</u>\n'

#         if no_cash_active_directions_text:
#             _text += f'{no_cash_active_directions_text}\n'
#         if no_cash_unactive_directions_text:
#             _text += f'{no_cash_unactive_directions_text}\n'

#         # print('<u>Направления городов, требующие внимания:</u>')
#         # if city_active_directions_text:
#             # print(city_active_directions_text, '\n')
#         # if city_unactive_directions_text:
#         #     print(city_unactive_directions_text, '\n')
#         # print('<u>Направления стран, требующие внимания:</u>')
#         # if country_active_directions_text:
#         #     print(country_active_directions_text, '\n')
#         # if country_unactive_directions_text:
#             # print(country_unactive_directions_text, '\n')
#         # print('<u>Безналичные направления, требующие внимания:</u>')
#         # if no_cash_active_directions_text:
#         #     print( no_cash_active_directions_text, '\n')
#         # if no_cash_unactive_directions_text:
#         #     print(no_cash_unactive_directions_text, '\n')


#         user_id = partner_exchange_admin_dict.get(exchange.pk)

#         t = bool(user_id and user_id == 686339126)

#         # print(t)

#         if user_id and user_id == 686339126:
#             # print('make request...')
#             # запрос на API бота для отправки уведомления админу обменника ( user_id )
#             async_to_sync(request_to_bot_exchange_admin_direction_notification)(user_id,
#                                                                                 _text)
#     # print((len(connection.queries)))


# @partner_router.post('/add_partner_city')
# def add_partner_city(partner: partner_dependency,
#                      city: AddPartnerCitySchema2):
#     # print(len(connection.queries))
#     partner_id = partner.get('partner_id')
#     try:
#         city_model = City.objects.get(code_name=city.city)
#         exchange = Exchange.objects.select_related('account')\
#                                     .get(account__pk=partner_id)
#     except Exception:
#         raise HTTPException(status_code=404)
#     else:
#         data = city.model_dump()
#         data['city'] = city_model
#         data['exchange'] = exchange

#         working_days = data.pop('working_days')

#         working_days_set = {working_day.capitalize() for working_day in working_days\
#                             if working_days[working_day]}
        
#         weekdays = data.pop('weekdays')

#         weekends = data.pop('weekends')

#         data.update(
#             {
#                 'time_from': weekdays.get('time_from'),
#                 'time_to': weekdays.get('time_to'),
#                 'weekend_time_from': weekends.get('time_from'),
#                 'weekend_time_to': weekends.get('time_to'),
#             }
#         )

#         try:
#             new_partner_city = PartnerCity.objects.create(**data)
#             make_city_active(city_model)
#         except IntegrityError:
#             raise HTTPException(status_code=423, # ?
#                                 detail='Такой город уже существует')
#         else:
#             new_partner_city.working_days\
#                 .add(*WorkingDay.objects.filter(code_name__in=working_days_set))
#             # print(len(connection.queries))
#             return {'status': 'success',
#                     'details': f'Партнёрский город {city_model.name} добавлен'}


# @partner_router.post('/add_partner_city')
# def add_partner_city(partner: partner_dependency,
#                      city: AddPartnerCitySchema3):
#     # print(len(connection.queries))
#     partner_id = partner.get('partner_id')
#     try:
#         city_model = City.objects.get(code_name=city.city)
#         exchange = Exchange.objects.select_related('account')\
#                                     .get(account__pk=partner_id)
#     except Exception:
#         raise HTTPException(status_code=404)
#     else:
#         data = city.model_dump()
#         data['city'] = city_model
#         data['exchange'] = exchange

#         working_days = data.pop('working_days')

#         working_days_set = {working_day.capitalize() for working_day in working_days\
#                             if working_days[working_day]}
        
#         weekdays = data.pop('weekdays')

#         weekends = data.pop('weekends')

#         data.update(
#             {
#                 'time_from': weekdays.get('time_from'),
#                 'time_to': weekdays.get('time_to'),
#                 'weekend_time_from': weekends.get('time_from'),
#                 'weekend_time_to': weekends.get('time_to'),
#             }
#         )

#         try:
#             new_partner_city = PartnerCity.objects.create(**data)
#             make_city_active(city_model)
#         except IntegrityError:
#             raise HTTPException(status_code=423, # ?
#                                 detail='Такой город уже существует')
#         else:
#             new_partner_city.working_days\
#                 .add(*WorkingDay.objects.filter(code_name__in=working_days_set))
#             # print(len(connection.queries))
#             return {'status': 'success',
#                     'details': f'Партнёрский город {city_model.name} добавлен'}
        

# @test_partner_router.post('/add_partner_city_country')
# def add_partner_city_country(partner: partner_dependency,
#                              data: AddPartnerCityCountrySchema):
#     # print(len(connection.queries))
#     partner_id = partner.get('partner_id')
#     try:
#         # city_model = City.objects.get(code_name=city.city)
#         exchange = Exchange.objects.select_related('account')\
#                                     .get(account__pk=partner_id)
#     except Exception:
#         raise HTTPException(status_code=404)
#     else:
#         _data = data.model_dump()
#         # data['city'] = city_model
#         _data['exchange'] = exchange

#         _id = _data.pop('id')
#         marker = _data.pop('marker')

#         working_days = _data.pop('working_days')

#         working_days_set = {working_day.capitalize() for working_day in working_days\
#                             if working_days[working_day]}
        
#         weekdays = _data.pop('weekdays')

#         weekends = _data.pop('weekends')

#         _data.update(
#             {
#                 'time_from': weekdays.get('time_from'),
#                 'time_to': weekdays.get('time_to'),
#                 'weekend_time_from': weekends.get('time_from'),
#                 'weekend_time_to': weekends.get('time_to'),
#             }
#         )

#         try:
#             if marker == 'country':
#                 _model = PartnerCountry
#                 _data.update({
#                     'country_id': _id,
#                 })
#             else:
#                 _model = PartnerCity
#                 _data.update({
#                     'city_id': _id,
#                 })
#             # new_partner_city = PartnerCity.objects.create(**data)
#             new_obj = _model.objects.create(**_data)
#             # make_city_active(city_model)
#         except IntegrityError:
#             raise HTTPException(status_code=423, # ?
#                                 detail='Такой город уже существует')
#         else:
#             new_obj.working_days\
#                 .add(*WorkingDay.objects.filter(code_name__in=working_days_set))
            
#             # name = new_obj.city.name if marker == 'city' else new_obj.country.name
#             if marker == 'city':
#                 name = new_obj.city.name
#                 _text = 'город'
#                 suffix = ''
#             else:
#                 name = new_obj.country.name
#                 _text = 'страна'
#                 suffix = 'а'
#             # print(len(connection.queries))
#             return {'status': 'success',
#                     'details': f'Партнёрский {_text} {name} добавлен{suffix}'}
        

@partner_router.post('/add_partner_city_country')
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
            # make_city_active(city_model)
        except IntegrityError:
            raise HTTPException(status_code=423, # ?
                                detail='Такой город уже существует')
        else:
            new_obj.working_days\
                .add(*WorkingDay.objects.filter(code_name__in=working_days_set))
            
            # name = new_obj.city.name if marker == 'city' else new_obj.country.name
            if marker == 'city':
                name = new_obj.city.name
                _text = 'город'
                suffix = ''
            else:
                name = new_obj.country.name
                _text = 'страна'
                suffix = 'а'
            # print(len(connection.queries))
            return {'status': 'success',
                    'details': f'Партнёрский {_text} {name} добавлен{suffix}'}
        

# @test_partner_router.patch('/edit_partner_city_country')
# def edit_partner_city_country(partner: partner_dependency,
#                              data: AddPartnerCityCountrySchema):
#     # print(len(connection.queries))
#     partner_id = partner.get('partner_id')
#     try:
#         # city_model = City.objects.get(code_name=city.city)
#         exchange = Exchange.objects.select_related('account')\
#                                     .get(account__pk=partner_id)
#     except Exception:
#         raise HTTPException(status_code=404)
#     else:
#         _data = data.model_dump()
#         # data['city'] = city_model
#         _data['exchange'] = exchange

#         _id = _data.pop('id')
#         marker = _data.pop('marker')

#         working_days = _data.pop('working_days')

#         working_days_set = {working_day.capitalize() for working_day in working_days\
#                             if working_days[working_day]}
        

#         unworking_day_names = {working_day.capitalize() for working_day in working_days \
#                                 if not working_days[working_day]}
    
#     # working_day_names = {working_day.capitalize() for working_day in working_days \
#     #                      if working_days[working_day]}
    
#     # with transaction.atomic():
#     #     partner_city = partner_city.first()

#     #     # partner_city.working_days.through.objects\
#     #     #         .filter(workingday__code_name__in=unworking_day_names).delete()
#     #     partner_city.working_days\
#     #                 .remove(*WorkingDay.objects.filter(code_name__in=unworking_day_names))


#     #     partner_city.working_days\
#     #                 .add(*WorkingDay.objects.filter(code_name__in=working_day_names))
#     # # print(len(connection.queries))
#     # return {'status': 'success',
#     #         'details': f'Партнёрский город {partner_city.city.name} успешно изменён'}
        
#         weekdays = _data.pop('weekdays')

#         weekends = _data.pop('weekends')

#         _data.update(
#             {
#                 'time_from': weekdays.get('time_from'),
#                 'time_to': weekdays.get('time_to'),
#                 'weekend_time_from': weekends.get('time_from'),
#                 'weekend_time_to': weekends.get('time_to'),
#             }
#         )


#         if marker == 'country':
#             _model = PartnerCountry
#         else:
#             _model = PartnerCity
#         with transaction.atomic():
#             obj_to_update = _model.objects.select_related(marker,
#                                             'exchange',
#                                             'exchange__account')\
#                                         .filter(pk=_id,
#                                                 exchange__account__pk=partner_id)
            
#             if not obj_to_update:
#                 raise HTTPException(status_code=404)
#             # else:
#             obj_to_update.update(**_data)
#             obj_to_update = obj_to_update.first()

#             obj_to_update.working_days\
#                         .remove(*WorkingDay.objects.filter(code_name__in=unworking_day_names))

#             obj_to_update.working_days\
#                 .add(*WorkingDay.objects.filter(code_name__in=working_days_set))
            
#         if marker == 'city':
#             name = obj_to_update.city.name
#             _text = 'город'
#             suffix = ''
#             prefix = 'ий'
#         else:
#             name = obj_to_update.country.name
#             _text = 'страна'
#             suffix = 'а'
#             prefix = 'ая'
#         # print(len(connection.queries))
#         return {'status': 'success',
#                 'details': f'Партнёрск{prefix} {_text} {name} изменен{suffix}'}


@partner_router.patch('/edit_partner_city_country')
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


# @test_partner_router.delete('/delete_partner_city_country')
# def delete_partner_city_country(partner: partner_dependency,
#                                 data: DeletePartnerCityCountrySchema):
#     partner_id = partner.get('partner_id')
    
#     if data.marker == 'country':
#         _model = PartnerCountry
#     else:
#         _model = PartnerCity

#     _model.objects.select_related('exchange',
#                                   'exchange__account')\
#                     .filter(pk=data.id,
#                             exchange__account__pk=partner_id)\
#                     .delete()


@partner_router.delete('/delete_partner_city_country')
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


# @test_partner_router.post('/add_partner_country')
# def add_partner_country(partner: partner_dependency,
#                         country: AddPartnerCountrySchema):
#     # print(len(connection.queries))
#     partner_id = partner.get('partner_id')
#     try:
#         exchange = Exchange.objects.select_related('account')\
#                                     .get(account__pk=partner_id)
#         country = PartnerCountry.objects.create(country_id=country.country_id,
#                                                 exchange=exchange)
#         # city_model = City.objects.get(code_name=city.city)
#         # exchange = Exchange.objects.select_related('account')\
#         #                             .get(account__pk=partner_id)
#     except Exception:
#         raise HTTPException(status_code=404)
#     else:
#         return {
#             'status': 'success',
#             'details': 'partner country successfully added',
#         }


# @test_partner_router.post('/edit_partner_country')
# def edit_partner_country(partner: partner_dependency,
#                         country: AddPartnerCountrySchema):
#     # print(len(connection.queries))
#     partner_id = partner.get('partner_id')
    
#     data = country.model_dump()
#     country_id = data.pop('country_id')
#     # try:
#         # exchange = Exchange.objects.select_related('account')\
#         #                             .get(account__pk=partner_id)
#     partner_country = PartnerCountry.objects.select_related('country',
#                                                     'exchange',
#                                                     'exchange__account')\
#                                     .filter(pk=country_id,
#                                             exchange__account__pk=partner_id)
#     # city_model = City.objects.get(code_name=city.city)
#     # exchange = Exchange.objects.select_related('account')\
#     #                             .get(account__pk=partner_id)
#     if not partner_country:
#         raise HTTPException(status_code=404)
    
#     working_days = data.pop('working_days')

#     weekdays = data.pop('weekdays')
#     weekends = data.pop('weekends')

#     data.update(
#         {
#             'time_from': weekdays.get('time_from'),
#             'time_to': weekdays.get('time_to'),
#             'weekend_time_from': weekends.get('time_from'),
#             'weekend_time_to': weekends.get('time_to'),
#         }
#     )


#     unworking_day_names = {working_day.capitalize() for working_day in working_days \
#                             if not working_days[working_day]}
    
#     working_day_names = {working_day.capitalize() for working_day in working_days \
#                          if working_days[working_day]}
#     try:
#         with transaction.atomic():
#             partner_country.update(**data)
#             partner_country = partner_country.first()

#             # partner_city.working_days.through.objects\
#             #         .filter(workingday__code_name__in=unworking_day_names).delete()
#             partner_country.working_days\
#                         .remove(*WorkingDay.objects.filter(code_name__in=unworking_day_names))


#             partner_country.working_days\
#                         .add(*WorkingDay.objects.filter(code_name__in=working_day_names))
#         # print(len(connection.queries))
#         return {'status': 'success',
#                 'details': f'Партнёрский страна {partner_country.country.name} успешно изменёна'}

#     except Exception as ex:
#         print('EDIT PARTNER COUNTRY ERROR', ex)
#         raise HTTPException(status_code=400)
#     # else:
#     #     return {
#     #         'status': 'success',
#     #         'details': 'partner country successfully added',
#     #     }


# @test_partner_router.delete('/delete_partner_country')
# def delete_partner_country(partner: partner_dependency,
#                            country: DeletePartnerCountrySchema):
#     # print(len(connection.queries))
#     partner_id = partner.get('partner_id')

#     partner_country = PartnerCountry.objects.select_related('exchange',
#                                                             'exchange__account')\
#                                             .filter(exchange__account__pk=partner_id,
#                                                     pk=country.country_id)
#     if not partner_country:
#         raise HTTPException(status_code=404)
    
#     partner_country.delete()

#     return {
#         'status': 'success',
#         'details': 'partner country successfully deleted',
#     }
        # exchange = Exchange.objects.select_related('account')\
        #                             .get(account__pk=partner_id)
        # country = PartnerCountry.objects.create(country_id=country.country_id,
        #                                         exchange=exchange)
        # city_model = City.objects.get(code_name=city.city)
        # exchange = Exchange.objects.select_related('account')\
        #                             .get(account__pk=partner_id)
    # except Exception:
    #     raise HTTPException(status_code=404)
    # else:
    #     return {
    #         'status': 'success',
    #         'details': 'partner country successfully deleted',
    #     }
        # data = city.model_dump()
        # data['city'] = city_model
        # data['exchange'] = exchange

        # working_days = data.pop('working_days')

        # working_days_set = {working_day.capitalize() for working_day in working_days\
        #                     if working_days[working_day]}
        
        # weekdays = data.pop('weekdays')

        # weekends = data.pop('weekends')

        # data.update(
        #     {
        #         'time_from': weekdays.get('time_from'),
        #         'time_to': weekdays.get('time_to'),
        #         'weekend_time_from': weekends.get('time_from'),
        #         'weekend_time_to': weekends.get('time_to'),
        #     }
        # )

        # try:
        #     new_partner_city = PartnerCity.objects.create(**data)
        #     make_city_active(city_model)
        # except IntegrityError:
        #     raise HTTPException(status_code=423, # ?
        #                         detail='Такой город уже существует')
        # else:
        #     new_partner_city.working_days\
        #         .add(*WorkingDay.objects.filter(code_name__in=working_days_set))
        #     # print(len(connection.queries))
        #     return {'status': 'success',
        #             'details': f'Партнёрский город {city_model.name} добавлен'}


# @partner_router.patch('/edit_partner_city')
# def edit_partner_city(partner: partner_dependency,
#                        edited_city: AddPartnerCitySchema2):
#     # print(len(connection.queries))
#     partner_id = partner.get('partner_id')

#     partner_city = PartnerCity.objects.select_related('exchange',
#                                                       'exchange__account',
#                                                       'city')\
#                                         .filter(exchange__account__pk=partner_id,
#                                                 city__code_name=edited_city.city)
#     if not partner_city:
#         raise HTTPException(status_code=404)
    
#     data = edited_city.model_dump()
#     working_days = data.pop('working_days')
#     data.pop('city')

#     weekdays = data.pop('weekdays')
#     weekends = data.pop('weekends')

#     data.update(
#         {
#             'time_from': weekdays.get('time_from'),
#             'time_to': weekdays.get('time_to'),
#             'weekend_time_from': weekends.get('time_from'),
#             'weekend_time_to': weekends.get('time_to'),
#         }
#     )

#     partner_city.update(**data)

#     unworking_day_names = {working_day.capitalize() for working_day in working_days \
#                             if not working_days[working_day]}
    
#     working_day_names = {working_day.capitalize() for working_day in working_days \
#                          if working_days[working_day]}
    
#     partner_city = partner_city.first()

#     partner_city.working_days.through.objects\
#             .filter(workingday__code_name__in=unworking_day_names).delete()

#     partner_city.working_days\
#                 .add(*WorkingDay.objects.filter(code_name__in=working_day_names))
#     # print(len(connection.queries))
#     return {'status': 'success',
#             'details': f'Партнёрский город {partner_city.city.name} успешно изменён'}


# @partner_router.patch('/edit_partner_city')
# def edit_partner_city(partner: partner_dependency,
#                        edited_city: AddPartnerCitySchema3):
#     # print(len(connection.queries))
#     partner_id = partner.get('partner_id')

#     partner_city = PartnerCity.objects.select_related('exchange',
#                                                       'exchange__account',
#                                                       'city')\
#                                         .filter(exchange__account__pk=partner_id,
#                                                 city__code_name=edited_city.city)
#     if not partner_city:
#         raise HTTPException(status_code=404)
    
#     data = edited_city.model_dump()
#     working_days = data.pop('working_days')
#     data.pop('city')

#     weekdays = data.pop('weekdays')
#     weekends = data.pop('weekends')

#     data.update(
#         {
#             'time_from': weekdays.get('time_from'),
#             'time_to': weekdays.get('time_to'),
#             'weekend_time_from': weekends.get('time_from'),
#             'weekend_time_to': weekends.get('time_to'),
#         }
#     )

#     partner_city.update(**data)

#     unworking_day_names = {working_day.capitalize() for working_day in working_days \
#                             if not working_days[working_day]}
    
#     working_day_names = {working_day.capitalize() for working_day in working_days \
#                          if working_days[working_day]}
    
#     with transaction.atomic():
#         partner_city = partner_city.first()

#         # partner_city.working_days.through.objects\
#         #         .filter(workingday__code_name__in=unworking_day_names).delete()
#         partner_city.working_days\
#                     .remove(*WorkingDay.objects.filter(code_name__in=unworking_day_names))


#         partner_city.working_days\
#                     .add(*WorkingDay.objects.filter(code_name__in=working_day_names))
#     # print(len(connection.queries))
#     return {'status': 'success',
#             'details': f'Партнёрский город {partner_city.city.name} успешно изменён'}



# @test_partner_router.patch('/edit_partner_city')
# def edit_partner_city2(partner: partner_dependency,
#                        edited_city: AddPartnerCitySchema3):
#     # print(len(connection.queries))
#     partner_id = partner.get('partner_id')

#     partner_city = PartnerCity.objects.select_related('exchange',
#                                                       'exchange__account',
#                                                       'city')\
#                                         .filter(exchange__account__pk=partner_id,
#                                                 city__code_name=edited_city.city)
#     if not partner_city:
#         raise HTTPException(status_code=404)
    
#     data = edited_city.model_dump()
#     working_days = data.pop('working_days')
#     data.pop('city')

#     weekdays = data.pop('weekdays')
#     weekends = data.pop('weekends')

#     data.update(
#         {
#             'time_from': weekdays.get('time_from'),
#             'time_to': weekdays.get('time_to'),
#             'weekend_time_from': weekends.get('time_from'),
#             'weekend_time_to': weekends.get('time_to'),
#         }
#     )

#     partner_city.update(**data)

#     unworking_day_names = {working_day.capitalize() for working_day in working_days \
#                             if not working_days[working_day]}
    
#     working_day_names = {working_day.capitalize() for working_day in working_days \
#                          if working_days[working_day]}
    
#     partner_city = partner_city.first()

#     partner_city.working_days.through.objects\
#             .filter(workingday__code_name__in=unworking_day_names).delete()

#     partner_city.working_days\
#                 .add(*WorkingDay.objects.filter(code_name__in=working_day_names))
#     # print(len(connection.queries))
#     return {'status': 'success',
#             'details': f'Партнёрский город {partner_city.city.name} успешно изменён'}



# @partner_router.delete('/delete_partner_city')
# def delete_partner_city(partner: partner_dependency,
#                         city_id: int):
#     partner_id = partner.get('partner_id')

#     city_on_delete = PartnerCity.objects.select_related('exchange__account')\
#                                         .filter(exchange__account__pk=partner_id,
#                                                 pk=city_id)
    
#     if not city_on_delete:
#         raise HTTPException(status_code=404)
    
#     city_on_delete.delete()

#     return {'status': 'success',
#             'details': 'Партнёрский город удалён'}


# @partner_router.post('/add_partner_direction')
# def add_partner_direction(partner: partner_dependency,
#                           new_direction: AddPartnerDirectionSchema2):
#     partner_id = partner.get('partner_id')

#     data = new_direction.model_dump()

#     valute_from = data.pop('valute_from')
#     valute_to = data.pop('valute_to')
#     try:
#         city = PartnerCity.objects.select_related('exchange',
#                                                   'exchange__account',
#                                                   'city')\
#                                     .get(exchange__account__pk=partner_id,
#                                         city__code_name=data['city'])    

#         direction = CashDirection.objects.select_related('valute_from',
#                                                         'valute_to')\
#                                             .get(valute_from__code_name=valute_from,
#                                                  valute_to__code_name=valute_to)
#     except Exception:
#         raise HTTPException(status_code=404)
#     else:
#         data['city'] = city
#         data['direction'] = direction

#         try:
#             Direction.objects.create(**data)
#             return {'status': 'success',
#                     'details': f'Партнерское направление {direction.display_name} добавлено'}
#         except IntegrityError:
#             raise HTTPException(status_code=423,
#                                 detail='Такое направление уже существует')


# @partner_router.post('/add_partner_direction')
# def add_partner_direction(partner: partner_dependency,
#                           new_direction: AddPartnerDirectionSchema):
#     partner_id = partner.get('partner_id')

#     data = new_direction.model_dump()

#     valute_from = data.pop('valute_from')
#     valute_to = data.pop('valute_to')
#     try:
#         city = PartnerCity.objects.select_related('exchange',
#                                                   'exchange__account',
#                                                   'city')\
#                                     .get(exchange__account__pk=partner_id,
#                                         city__code_name=data['city'])    

#         direction = CashDirection.objects.select_related('valute_from',
#                                                         'valute_to')\
#                                             .get(valute_from__code_name=valute_from,
#                                                  valute_to__code_name=valute_to)
#     except Exception:
#         raise HTTPException(status_code=404)
#     else:
#         data['city'] = city
#         data['direction'] = direction

#         try:
#             Direction.objects.create(**data)
#             return {'status': 'success',
#                     'details': f'Партнерское направление {direction.display_name} добавлено'}
#         except IntegrityError:
#             raise HTTPException(status_code=423,
#                                 detail='Такое направление уже существует')

        

# @test_partner_router.post('/add_partner_direction')
# def add_partner_direction2(partner: partner_dependency,
#                           new_direction: AddPartnerDirectionSchema2):
#     partner_id = partner.get('partner_id')

#     data = new_direction.model_dump()

#     _id = data.pop('id')
#     valute_from = data.pop('valute_from')
#     valute_to = data.pop('valute_to')
#     marker = data.pop('marker')
    
#     foreign_key_name = 'country_id' if marker == 'country' else 'city_id'
#     foreign_key_model = PartnerCountry if marker == 'country' else PartnerCity

#     direction_model = CountryDirection if marker == 'country' else Direction


#     check_partner = foreign_key_model.objects.select_related('exchange',
#                                                              'exchange__account')\
#                                             .filter(pk=_id,
#                                                     exchange__account__pk=partner_id)\
#                                             .exists()
    
#     # print(check_partner)
    
#     if not check_partner:
#         raise HTTPException(status_code=404)
        
#     try:
#         direction = CashDirection.objects.select_related('valute_from',
#                                                         'valute_to')\
#                                         .prefetch_related('partner_country_directions')\
#                                             .get(valute_from__code_name=valute_from,
#                                                  valute_to__code_name=valute_to)
#     except Exception as ex:
#         print(ex)
#         raise HTTPException(status_code=404)
#     else:
#         data[foreign_key_name] = _id
#         data['direction'] = direction

#         try:
#             if marker == 'city':
#                 city = PartnerCity.objects.select_related('city')\
#                                             .get(pk=_id)
#                 country_direction = CountryDirection.objects.select_related('country',
#                                                                             'country__country',
#                                                                             'country__exchange',
#                                                                             'country__exchange__account',
#                                                                             'direction')\
#                                         .prefetch_related('country__country__cities')\
#                                         .filter(country__country__cities__code_name=city.city.code_name,
#                                                 country__exchange__account=partner_id,
#                                                 direction__valute_from=valute_from,
#                                                 direction__valute_to=valute_to)
                
#                 if country_direction.exists():
#                     raise HTTPException(status_code=424,
#                                         detail='Такое направление уже существует на уровне партнерской страны')

#             direction_model.objects.create(**data)
#             return {'status': 'success',
#                     'details': f'Партнерское направление {direction.display_name} добавлено'}
#         except IntegrityError as ex:
#             print(ex)
#             raise HTTPException(status_code=423,
#                                 detail='Такое направление уже существует')

# @partner_router.post('/add_partner_direction')
# def add_partner_direction(partner: partner_dependency,
#                           new_direction: AddPartnerDirectionSchema3):
#     partner_id = partner.get('partner_id')

#     data = new_direction.model_dump()

#     _id = data.pop('id')
#     valute_from = data.pop('valute_from')
#     valute_to = data.pop('valute_to')
#     marker = data.pop('marker')
#     bankomats = data.pop('bankomats')
    
#     foreign_key_name = 'country_id' if marker == 'country' else 'city_id'
#     foreign_key_model = PartnerCountry if marker == 'country' else PartnerCity

#     direction_model = CountryDirection if marker == 'country' else Direction


#     check_partner = foreign_key_model.objects.select_related('exchange',
#                                                              'exchange__account')\
#                                             .filter(pk=_id,
#                                                     exchange__account__pk=partner_id)\
#                                             .exists()
    
#     # print(check_partner)
    
#     if not check_partner:
#         raise HTTPException(status_code=404)
        
#     try:
#         direction = CashDirection.objects.select_related('valute_from',
#                                                         'valute_to')\
#                                         .prefetch_related('partner_country_directions')\
#                                             .get(valute_from__code_name=valute_from,
#                                                  valute_to__code_name=valute_to)
#     except Exception as ex:
#         print(ex)
#         raise HTTPException(status_code=404)
#     else:
#         data[foreign_key_name] = _id
#         data['direction'] = direction

#         try:
#             if marker == 'city':
#                 city = PartnerCity.objects.select_related('city')\
#                                             .get(pk=_id)
#                 country_direction = CountryDirection.objects.select_related('country',
#                                                                             'country__country',
#                                                                             'country__exchange',
#                                                                             'country__exchange__account',
#                                                                             'direction')\
#                                         .prefetch_related('country__country__cities')\
#                                         .filter(country__country__cities__code_name=city.city.code_name,
#                                                 country__exchange__account=partner_id,
#                                                 direction__valute_from=valute_from,
#                                                 direction__valute_to=valute_to)
                
#                 if country_direction.exists():
#                     raise HTTPException(status_code=424,
#                                         detail='Такое направление уже существует на уровне партнерской страны')
#             with transaction.atomic():
#                 direction_model.objects.create(**data)
#                 if bankomats:
#                     try_add_bankomats_to_valute(partner_id,
#                                                 valute_to,
#                                                 bankomats)
#             return {'status': 'success',
#                     'details': f'Партнерское направление {direction.display_name} добавлено'}
#         except IntegrityError as ex:
#             print(ex)
#             raise HTTPException(status_code=423,
#                                 detail='Такое направление уже существует')


@partner_router.post('/add_partner_direction')
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


@partner_router.post('/add_partner_no_cash_direction')
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


# @test_partner_router.post('/add_partner_direction')
# def add_partner_direction(partner: partner_dependency,
#                           new_direction: NewAddPartnerDirectionSchema):
#     partner_id = partner.get('partner_id')

#     data = new_direction.model_dump()

#     _id = data.pop('id')
#     valute_from = data.pop('valute_from')
#     valute_to = data.pop('valute_to')
#     marker = data.pop('marker')
#     bankomats = data.pop('bankomats')
#     exchange_rates = data.pop('exchange_rates')
    
#     foreign_key_name = 'country_id' if marker == 'country' else 'city_id'
#     foreign_key_model = PartnerCountry if marker == 'country' else PartnerCity

#     direction_model = CountryDirection if marker == 'country' else Direction


#     check_partner = foreign_key_model.objects.select_related('exchange',
#                                                              'exchange__account')\
#                                             .filter(pk=_id,
#                                                     exchange__account__pk=partner_id)\
#                                             .exists()
    
#     # print(check_partner)
    
#     if not check_partner:
#         raise HTTPException(status_code=404)
        
#     try:
#         direction = CashDirection.objects.select_related('valute_from',
#                                                         'valute_to')\
#                                         .prefetch_related('partner_country_directions')\
#                                             .get(valute_from__code_name=valute_from,
#                                                  valute_to__code_name=valute_to)
#     except Exception as ex:
#         print(ex)
#         raise HTTPException(status_code=404)
#     else:
#         data[foreign_key_name] = _id
#         data['direction'] = direction

#         if len(exchange_rates) > 4:
#             raise HTTPException(status_code=400,
#                                 detail='Количество доп объемов для направления должно быть не больше 3 шт')


#         main_exchange_rate, additional_exchange_rates = exchange_rates[0], exchange_rates[1:]

#         # print(main_exchange_rate)

#         convert_min_max_count(main_exchange_rate,
#                               marker='main')
        
#         # print(main_exchange_rate)

#         main_exchange_rate.pop('rate_coefficient')

#         data.update(main_exchange_rate)

#         try:
#             if marker == 'city':
#                 city = PartnerCity.objects.select_related('city')\
#                                             .get(pk=_id)
#                 country_direction = CountryDirection.objects.select_related('country',
#                                                                             'country__country',
#                                                                             'country__exchange',
#                                                                             'country__exchange__account',
#                                                                             'direction')\
#                                         .prefetch_related('country__country__cities')\
#                                         .filter(country__country__cities__code_name=city.city.code_name,
#                                                 country__exchange__account=partner_id,
#                                                 direction__valute_from=valute_from,
#                                                 direction__valute_to=valute_to)
                
#                 if country_direction.exists():
#                     raise HTTPException(status_code=424,
#                                         detail='Такое направление уже существует на уровне партнерской страны')
            
#             with transaction.atomic():
#                 new_partner_dirction = direction_model.objects.create(**data)
#                 if bankomats:
#                     try_add_bankomats_to_valute(partner_id,
#                                                 valute_to,
#                                                 bankomats)
#                 if additional_exchange_rates:
#                     partner = CustomUser.objects.filter(pk=partner_id).get()
#                     exchange_id = partner.exchange_id

#                     min_count_list = [_exchange_rate.get('min_count') for _exchange_rate in additional_exchange_rates]

#                     if len(min_count_list) != len(set(min_count_list)):
#                             raise HTTPException(status_code=400,
#                                                 detail='Несколько записей об объемах содержат одинаковые min_count')

#                     bulk_create_list = []

#                     for additional_exchange_rate in additional_exchange_rates:
                        
#                         if not additional_exchange_rate.get('min_count'):
#                             raise HTTPException(status_code=400,
#                                                 detail='Одна или несколько записей об объемах содержит пустой min_count')

#                         if not additional_exchange_rate.get('rate_coefficient'):
#                             raise HTTPException(status_code=400,
#                                                 detail='Одна или несколько записей об объемах содержит пустой rate_coefficient')


#                         sub_foreign_key_model = DirectionRate if foreign_key_name == 'city_id'\
#                                                                 else CountryDirectionRate
#                         exchange_rate_data = {
#                             'exchange_id': exchange_id,
#                             'exchange_direction_id': new_partner_dirction.pk,
#                         }

#                         convert_min_max_count(additional_exchange_rate,
#                                               marker='additional')
                        
#                         exchange_rate_data.update(additional_exchange_rate)
                        
#                         new_exchangedirection_rate = sub_foreign_key_model(**exchange_rate_data)

#                         bulk_create_list.append(new_exchangedirection_rate)
                    
#                     sub_foreign_key_model.objects.bulk_create(bulk_create_list)

#             return {'status': 'success',
#                     'details': f'Партнерское направление {direction.display_name} добавлено'}
#         except IntegrityError as ex:
#             print(ex)
#             raise HTTPException(status_code=423,
#                                 detail='Такое направление уже существует')
        

# @partner_router.post('/add_partner_direction')
# def add_partner_direction(partner: partner_dependency,
#                           new_direction: AddPartnerDirectionSchema2):
#     partner_id = partner.get('partner_id')

#     data = new_direction.model_dump()

#     _id = data.pop('id')
#     valute_from = data.pop('valute_from')
#     valute_to = data.pop('valute_to')
#     marker = data.pop('marker')
    
#     foreign_key_name = 'country_id' if marker == 'country' else 'city_id'
#     foreign_key_model = PartnerCountry if marker == 'country' else PartnerCity

#     direction_model = CountryDirection if marker == 'country' else Direction


#     check_partner = foreign_key_model.objects.select_related('exchange',
#                                                              'exchange__account')\
#                                             .filter(pk=_id,
#                                                     exchange__account__pk=partner_id)\
#                                             .exists()
    
#     # print(check_partner)
    
#     if not check_partner:
#         raise HTTPException(status_code=404)
        
#     try:
#         direction = CashDirection.objects.select_related('valute_from',
#                                                         'valute_to')\
#                                         .prefetch_related('partner_country_directions')\
#                                             .get(valute_from__code_name=valute_from,
#                                                  valute_to__code_name=valute_to)
#     except Exception as ex:
#         print(ex)
#         raise HTTPException(status_code=404)
#     else:
#         data[foreign_key_name] = _id
#         data['direction'] = direction

#         try:
#             if marker == 'city':
#                 city = PartnerCity.objects.select_related('city')\
#                                             .get(pk=_id)
#                 country_direction = CountryDirection.objects.select_related('country',
#                                                                             'country__country',
#                                                                             'country__exchange',
#                                                                             'country__exchange__account',
#                                                                             'direction')\
#                                         .prefetch_related('country__country__cities')\
#                                         .filter(country__country__cities__code_name=city.city.code_name,
#                                                 country__exchange__account=partner_id,
#                                                 direction__valute_from=valute_from,
#                                                 direction__valute_to=valute_to)
                
#                 if country_direction.exists():
#                     raise HTTPException(status_code=424,
#                                         detail='Такое направление уже существует на уровне партнерской страны')

#             direction_model.objects.create(**data)
#             return {'status': 'success',
#                     'details': f'Партнерское направление {direction.display_name} добавлено'}
#         except IntegrityError as ex:
#             print(ex)
#             raise HTTPException(status_code=423,
#                                 detail='Такое направление уже существует')


# @partner_router.patch('/edit_partner_directions')
# def edit_partner_directions_by_city(partner: partner_dependency,
#                                     response_body: ListEditedPartnerDirectionSchema):
#     # print(len(connection.queries))
#     partner_id = partner.get('partner_id')

#     data: dict = response_body.model_dump()

#     city_code_name = data['city']
#     edited_direction_list = data['directions']

#     partner_directions = Direction.objects\
#                                     .select_related('city',
#                                                     'city__city',
#                                                     'city__exchange__account',
#                                                     'direction',
#                                                     'direction__valute_from',
#                                                     'direction__valute_to')\
#                                     .filter(city__exchange__account__pk=partner_id)

#     city = PartnerCity.objects.select_related('exchange',
#                                               'exchange__account',
#                                               'city')\
#                                 .filter(exchange__account__pk=partner_id,
#                                         city__code_name=city_code_name)
    
#     try:
#         with transaction.atomic():
#             for edited_direction in edited_direction_list:
#                 _id = edited_direction.pop('id')
#                 edited_direction['time_update'] = datetime.now()
#                 partner_directions.filter(pk=_id).update(**edited_direction)

#             city.update(time_update=timezone.now())
#     except Exception:
#         raise HTTPException(status_code=400)
#     else:
#         return {'status': 'success',
#                 'details': f'updated {len(edited_direction_list)} directions'}
    

# @test_partner_router.patch('/edit_partner_directions')
# def edit_partner_directions_by2(partner: partner_dependency,
#                                response_body: ListEditedPartnerDirectionSchema2):
#     # print(len(connection.queries))
#     partner_id = partner.get('partner_id')

#     data: dict = response_body.model_dump()

#     location_id = data['id']
#     marker = data['marker']
#     edited_direction_list = data['directions']

#     city = None

#     if marker == 'country':
#         direction_model = CountryDirection
#         _filter = Q(country__exchange__account__pk=partner_id,
#                     country__pk=location_id)
#     else:
#         direction_model = Direction
#         _filter = Q(city__exchange__account__pk=partner_id,
#                     city__pk=location_id)
#         city = PartnerCity.objects.select_related('exchange',
#                                                 'exchange__account',
#                                                 'city')\
#                                     .filter(exchange__account__pk=partner_id,
#                                             pk=location_id)

#     partner_directions = direction_model.objects\
#                                     .select_related(marker,
#                                                     f'{marker}__exchange__account',
#                                                     'direction',
#                                                     'direction__valute_from',
#                                                     'direction__valute_to')\
#                                     .filter(_filter)
#     try:
#         with transaction.atomic():
#             for edited_direction in edited_direction_list:
#                 _id = edited_direction.pop('id')
#                 edited_direction['time_update'] = datetime.now()
#                 partner_directions.filter(pk=_id).update(**edited_direction)

#             if city:
#                 city.update(time_update=timezone.now())
#     except Exception:
#         raise HTTPException(status_code=400)
#     else:
#         return {'status': 'success',
#                 'details': f'updated {len(edited_direction_list)} directions'}
    

# @partner_router.patch('/edit_partner_directions')
# def edit_partner_directions_by(partner: partner_dependency,
#                                response_body: ListEditedPartnerDirectionSchema2):
#     # print(len(connection.queries))
#     partner_id = partner.get('partner_id')

#     data: dict = response_body.model_dump()

#     location_id = data['id']
#     marker = data['marker']
#     edited_direction_list = data['directions']

#     city = None

#     if marker == 'country':
#         direction_model = CountryDirection
#         _filter = Q(country__exchange__account__pk=partner_id,
#                     country__pk=location_id)
#     else:
#         direction_model = Direction
#         _filter = Q(city__exchange__account__pk=partner_id,
#                     city__pk=location_id)
#         city = PartnerCity.objects.select_related('exchange',
#                                                 'exchange__account',
#                                                 'city')\
#                                     .filter(exchange__account__pk=partner_id,
#                                             pk=location_id)

#     partner_directions = direction_model.objects\
#                                     .select_related(marker,
#                                                     f'{marker}__exchange__account',
#                                                     'direction',
#                                                     'direction__valute_from',
#                                                     'direction__valute_to')\
#                                     .filter(_filter)
#     try:
#         with transaction.atomic():
#             for edited_direction in edited_direction_list:
#                 _id = edited_direction.pop('id')
#                 edited_direction['time_update'] = datetime.now()
#                 partner_directions.filter(pk=_id).update(**edited_direction)

#             if city:
#                 city.update(time_update=timezone.now())
#     except Exception:
#         raise HTTPException(status_code=400)
#     else:
#         return {'status': 'success',
#                 'details': f'updated {len(edited_direction_list)} directions'}


@partner_router.patch('/edit_partner_directions')
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


@partner_router.patch('/edit_partner_no_cash_directions')
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


# @test_partner_router.patch('/edit_partner_directions')
# def edit_partner_directions_by(partner: partner_dependency,
#                                response_body: NewListEditedPartnerDirectionSchema):
#     # print(len(connection.queries))
#     partner_id = partner.get('partner_id')

#     data: dict = response_body.model_dump()

#     location_id = data['id']
#     marker = data['marker']
#     edited_direction_list = data['directions']

#     city = None

#     if marker == 'country':
#         direction_model = CountryDirection
#         direction_rate_model = CountryDirectionRate
#         _filter = Q(country__exchange__account__pk=partner_id,
#                     country__pk=location_id)
#     else:
#         direction_model = Direction
#         direction_rate_model = DirectionRate
#         _filter = Q(city__exchange__account__pk=partner_id,
#                     city__pk=location_id)
#         city = PartnerCity.objects.select_related('exchange',
#                                                 'exchange__account',
#                                                 'city')\
#                                     .filter(exchange__account__pk=partner_id,
#                                             pk=location_id)

#     partner_directions = direction_model.objects\
#                                     .select_related(marker,
#                                                     f'{marker}__exchange__account',
#                                                     'direction',
#                                                     'direction__valute_from',
#                                                     'direction__valute_to')\
#                                     .filter(_filter)
#                                     # .prefetch_related('direction_rates')\
#     try:
#         with transaction.atomic():
#             for edited_direction in edited_direction_list:
#                 _id = edited_direction.pop('id')
                
#                 exchange_rates: list[dict] = edited_direction.pop('exchange_rates')
                
#                 main_exchange_rate, additional_exchange_rates = exchange_rates[0], exchange_rates[1:]

#                 convert_min_max_count(main_exchange_rate,
#                                     marker='main')
                
#                 # print(main_exchange_rate)

#                 main_exchange_rate.pop('rate_coefficient')
#                 main_exchange_rate.pop('id')

#                 edited_direction['time_update'] = datetime.now()
#                 edited_direction.update(main_exchange_rate)

#                 # print(edited_direction)

#                 partner_directions.filter(pk=_id).update(**edited_direction)

#                 min_count_list = [_exchange_rate.get('min_count') for _exchange_rate in additional_exchange_rates]

#                 if len(min_count_list) != len(set(min_count_list)):
#                         raise HTTPException(status_code=400,
#                                             detail='Несколько записей об объемах содержат одинаковые min_count')

#                 # current_partner_diretction = partner_directions.get(pk=_id)

#                 # direction_rates = current_partner_diretction.direction_rates.all()

#                 # print(direction_rates)

#                 # direction_rates_dict = {direction_rate.min_rate_limit: direction_rate\
#                 #                          for direction_rate in direction_rates}
                
#                 # print(direction_rates_dict)

#                 direction_rate_id_set = set(direction_rate_model.objects\
#                                                         .filter(exchange_direction_id=_id)\
#                                                         .values_list('pk', flat=True))

#                 # direction_rate_id_set = {el.get('id') for el in additional_exchange_rates}

#                 for additional_exchange_rate in additional_exchange_rates:
                    
#                     if not additional_exchange_rate.get('min_count'):
#                         raise HTTPException(status_code=400,
#                                             detail='Одна или несколько записей об объемах содержит пустой min_count')

#                     if not additional_exchange_rate.get('rate_coefficient'):
#                         raise HTTPException(status_code=400,
#                                             detail='Одна или несколько записей об объемах содержит пустой rate_coefficient')

#                     _direction_rate_id = additional_exchange_rate.pop('id')

#                     convert_min_max_count(additional_exchange_rate,
#                                           marker='additional')
                    
#                     direction_rate_model.objects.filter(pk=_direction_rate_id)\
#                                                 .update(**additional_exchange_rate)
                    
#                     direction_rate_id_set.remove(_direction_rate_id)
                
#                 if direction_rate_id_set:
#                     print('in delete', direction_rate_id_set)
#                     direction_rate_model.objects.filter(pk__in=direction_rate_id_set).delete()

#             if city:
#                 city.update(time_update=timezone.now())
#     except Exception as ex:
#         print('EXCEPTION', ex)
#         raise HTTPException(status_code=400)
#     else:
#         return {'status': 'success',
#                 'details': f'updated {len(edited_direction_list)} directions'}
    

@partner_router.delete('/delete_partner_direction')
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


exchange_link_count_dict = {
    'city': ExchangeLinkCount,
    'country': CountryExchangeLinkCount,
    'no_cash': NonCashExchangeLinkCount,
}

@partner_router.post('/increase_link_count')
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

# @test_partner_router.delete('/delete_partner_direction')
# def delete_partner_direction2(partner: partner_dependency,
#                              data: DeletePartnerDirectionSchema):
#     partner_id = partner.get('partner_id')
    
#     if data.marker == 'country':
#         _model = CountryDirection
#         _filter = Q(country_id=data.id,
#                     country__exchange__account__pk=partner_id)
#     else:
#         _model = Direction
#         _filter = Q(city_id=data.id,
#                     city__exchange__account__pk=partner_id)

#     _model.objects.select_related(data.marker,
#                                   f'{data.marker}__exchange',
#                                   f'{data.marker}__exchange__account')\
#                     .filter(_filter,
#                             pk=data.direction_id)\
#                     .delete()
#     return {'status': 'success',
#             'details': 'Партнёрское направление удалено'}


# @partner_router.delete('/delete_partner_direction')
# def delete_partner_direction(partner: partner_dependency,
#                              direction_id: int):
#     partner_id = partner.get('partner_id')
    
#     try:
#         direction_on_delete = Direction.objects.select_related('city__exchange__account')\
#                                                 .get(city__exchange__account__pk=partner_id,
#                                                         pk=direction_id)
#     except ObjectDoesNotExist:
#         raise HTTPException(status_code=404)
    
#     direction_on_delete.delete()

#     return {'status': 'success',
#             'details': 'Партнёрское направление удалено'}
@partner_router.get('/bankomats_by_valute',
                         response_model=list[BankomatDetailSchema],
                         response_model_by_alias=False)
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


# @test_partner_router.get('/bankomats_by_valute',
#                          response_model=list[BankomatDetailSchema],
#                          response_model_by_alias=False)
# def get_bankomat_list_by_valute(partner: partner_dependency,
#                                 valute: str):
#     partner_id = partner.get('partner_id')
    
#     try:
#         if Valute.objects.get(pk=valute).type_valute != 'ATM QR':
#             raise HTTPException(status_code=400,
#                                 detail='Некорректная валюта')
#     except Exception:
#         raise HTTPException(status_code=400,
#                             detail='Некорректная валюта')
    
#     return get_partner_bankomats_by_valute(partner_id,
#                                            valute)
    
    # bankomats = Bankomat.objects.all()

    # partner_valute = QRValutePartner.objects.filter(partner_id=partner_id,
    #                                                 valute_id=valute)
                                                
    # partner_bankomats = []

    # if partner_valute.exists():
    #     partner_valute = partner_valute.first()

    #     partner_valute_bankomats = partner_valute.bankomats\
    #                                                 .values_list('pk',
    #                                                             flat=True)
    #     for bankomat in bankomats:
    #         partner_bankomat = {
    #             'id': bankomat.pk,
    #             'name': bankomat.name,
    #             'available': bankomat.pk in partner_valute_bankomats
    #         }
    #         partner_bankomats.append(partner_bankomat)
    # else:
    #     for bankomat in bankomats:
    #         partner_bankomat = {
    #             'id': bankomat.pk,
    #             'name': bankomat.name,
    #             'available': False,
    #         }
    #         partner_bankomats.append(partner_bankomat)
    
    # return partner_bankomats


# @test_partner_router.post('/add_partner_direction')
# def add_partner_direction(partner: partner_dependency,
#                           new_direction: AddPartnerDirectionSchema3):
#     partner_id = partner.get('partner_id')

#     data = new_direction.model_dump()

#     _id = data.pop('id')
#     valute_from = data.pop('valute_from')
#     valute_to = data.pop('valute_to')
#     marker = data.pop('marker')
#     bankomats = data.pop('bankomats')
    
#     foreign_key_name = 'country_id' if marker == 'country' else 'city_id'
#     foreign_key_model = PartnerCountry if marker == 'country' else PartnerCity

#     direction_model = CountryDirection if marker == 'country' else Direction


#     check_partner = foreign_key_model.objects.select_related('exchange',
#                                                              'exchange__account')\
#                                             .filter(pk=_id,
#                                                     exchange__account__pk=partner_id)\
#                                             .exists()
    
#     # print(check_partner)
    
#     if not check_partner:
#         raise HTTPException(status_code=404)
        
#     try:
#         direction = CashDirection.objects.select_related('valute_from',
#                                                         'valute_to')\
#                                         .prefetch_related('partner_country_directions')\
#                                             .get(valute_from__code_name=valute_from,
#                                                  valute_to__code_name=valute_to)
#     except Exception as ex:
#         print(ex)
#         raise HTTPException(status_code=404)
#     else:
#         data[foreign_key_name] = _id
#         data['direction'] = direction

#         try:
#             if marker == 'city':
#                 city = PartnerCity.objects.select_related('city')\
#                                             .get(pk=_id)
#                 country_direction = CountryDirection.objects.select_related('country',
#                                                                             'country__country',
#                                                                             'country__exchange',
#                                                                             'country__exchange__account',
#                                                                             'direction')\
#                                         .prefetch_related('country__country__cities')\
#                                         .filter(country__country__cities__code_name=city.city.code_name,
#                                                 country__exchange__account=partner_id,
#                                                 direction__valute_from=valute_from,
#                                                 direction__valute_to=valute_to)
                
#                 if country_direction.exists():
#                     raise HTTPException(status_code=424,
#                                         detail='Такое направление уже существует на уровне партнерской страны')
#             with transaction.atomic():
#                 direction_model.objects.create(**data)
#                 if bankomats:
#                     try_add_bankomats_to_valute(partner_id,
#                                                 valute_to,
#                                                 bankomats)
#             return {'status': 'success',
#                     'details': f'Партнерское направление {direction.display_name} добавлено'}
#         except IntegrityError as ex:
#             print(ex)
#             raise HTTPException(status_code=423,
#                                 detail='Такое направление уже существует')