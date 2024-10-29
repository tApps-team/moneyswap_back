from datetime import datetime

from fastapi import APIRouter
from fastapi.exceptions import HTTPException

from django.utils import timezone
from django.db import connection, transaction
from django.db.utils import IntegrityError
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist

from cash.models import Country, City, Direction as CashDirection

from general_models.utils.endpoints import try_generate_icon_url
from general_models.schemas import MultipleName, MultipleName2

from .models import PartnerCity, Direction, Exchange, WorkingDay

from .auth.endpoints import partner_dependency

from .utils.admin import make_city_active

from .utils.endpoints import (generate_partner_cities,
                              generate_partner_directions_by_city,
                              generate_valute_list,
                              generate_actual_course,
                              generate_valute_list2,
                              generate_partner_cities2)

from .schemas import (PartnerCitySchema,
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
                      AddPartnerCitySchema3)


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



@test_partner_router.get('/partner_cities',
                    response_model=list[PartnerCitySchema3],
                    response_model_by_alias=False)
def get_partner_cities2(partner: partner_dependency):
    partner_id = partner.get('partner_id')

    partner_cities = PartnerCity.objects.select_related('exchange',
                                                        'city',
                                                        'city__country',
                                                        'exchange__account')\
                                        .prefetch_related('working_days')\
                                        .filter(exchange__account__pk=partner_id).all()

    return generate_partner_cities2(partner_cities)


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


@partner_router.get('/directions_by_city',
                    response_model=list[DirectionSchema])
def get_partner_directions_by_city(partner: partner_dependency,
                                   code_name: str):
    partner_id = partner.get('partner_id')

    directions = Direction.objects.select_related('city',
                                                  'city__city',
                                                  'city__exchange',
                                                  'city__exchange__account',
                                                  'direction',
                                                  'direction__valute_from',
                                                  'direction__valute_to')\
                                    .filter(city__exchange__account__pk=partner_id,
                                            city__city__code_name=code_name.upper())\
                                    .all()

    return generate_partner_directions_by_city(directions)


@partner_router.get('/available_valutes')
def get_available_valutes_for_partner(base: str):
    base = base.upper()

    queries = CashDirection.objects.select_related('valute_from',
                                                   'valute_to')\
                                    .filter(valute_from__available_for_partners=True,
                                            valute_to__available_for_partners=True)
    
    if base == 'ALL':
        marker = 'valute_from'
    else:
        marker = 'valute_to'
        queries = queries.filter(valute_from=base)

    return generate_valute_list2(queries, marker)


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
    

@partner_router.get('/account_info',
                    response_model=AccountInfoSchema)
def get_account_info(partner: partner_dependency):
    partner_id = partner.get('partner_id')

    try:
        exchange = Exchange.objects.select_related('account')\
                                    .get(account__pk=partner_id)
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404)
    else:
        exchange.title = AccountTitleSchema(ru=exchange.name,
                                            en=exchange.en_name)
        
        return exchange


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


@partner_router.post('/add_partner_city')
def add_partner_city(partner: partner_dependency,
                     city: AddPartnerCitySchema3):
    # print(len(connection.queries))
    partner_id = partner.get('partner_id')
    try:
        city_model = City.objects.get(code_name=city.city)
        exchange = Exchange.objects.select_related('account')\
                                    .get(account__pk=partner_id)
    except Exception:
        raise HTTPException(status_code=404)
    else:
        data = city.model_dump()
        data['city'] = city_model
        data['exchange'] = exchange

        working_days = data.pop('working_days')

        working_days_set = {working_day.capitalize() for working_day in working_days\
                            if working_days[working_day]}
        
        weekdays = data.pop('weekdays')

        weekends = data.pop('weekends')

        data.update(
            {
                'time_from': weekdays.get('time_from'),
                'time_to': weekdays.get('time_to'),
                'weekend_time_from': weekends.get('time_from'),
                'weekend_time_to': weekends.get('time_to'),
            }
        )

        try:
            new_partner_city = PartnerCity.objects.create(**data)
            make_city_active(city_model)
        except IntegrityError:
            raise HTTPException(status_code=423, # ?
                                detail='Такой город уже существует')
        else:
            new_partner_city.working_days\
                .add(*WorkingDay.objects.filter(code_name__in=working_days_set))
            # print(len(connection.queries))
            return {'status': 'success',
                    'details': f'Партнёрский город {city_model.name} добавлен'}


@test_partner_router.post('/add_partner_city')
def add_partner_city2(partner: partner_dependency,
                     city: AddPartnerCitySchema3):
    # print(len(connection.queries))
    partner_id = partner.get('partner_id')
    try:
        city_model = City.objects.get(code_name=city.city)
        exchange = Exchange.objects.select_related('account')\
                                    .get(account__pk=partner_id)
    except Exception:
        raise HTTPException(status_code=404)
    else:
        data = city.model_dump()
        data['city'] = city_model
        data['exchange'] = exchange

        working_days = data.pop('working_days')

        working_days_set = {working_day.capitalize() for working_day in working_days\
                            if working_days[working_day]}
        
        weekdays = data.pop('weekdays')

        weekends = data.pop('weekends')

        data.update(
            {
                'time_from': weekdays.get('time_from'),
                'time_to': weekdays.get('time_to'),
                'weekend_time_from': weekends.get('time_from'),
                'weekend_time_to': weekends.get('time_to'),
            }
        )

        try:
            new_partner_city = PartnerCity.objects.create(**data)
            make_city_active(city_model)
        except IntegrityError:
            raise HTTPException(status_code=423, # ?
                                detail='Такой город уже существует')
        else:
            new_partner_city.working_days\
                .add(*WorkingDay.objects.filter(code_name__in=working_days_set))
            # print(len(connection.queries))
            return {'status': 'success',
                    'details': f'Партнёрский город {city_model.name} добавлен'}


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


@partner_router.patch('/edit_partner_city')
def edit_partner_city(partner: partner_dependency,
                       edited_city: AddPartnerCitySchema3):
    # print(len(connection.queries))
    partner_id = partner.get('partner_id')

    partner_city = PartnerCity.objects.select_related('exchange',
                                                      'exchange__account',
                                                      'city')\
                                        .filter(exchange__account__pk=partner_id,
                                                city__code_name=edited_city.city)
    if not partner_city:
        raise HTTPException(status_code=404)
    
    data = edited_city.model_dump()
    working_days = data.pop('working_days')
    data.pop('city')

    weekdays = data.pop('weekdays')
    weekends = data.pop('weekends')

    data.update(
        {
            'time_from': weekdays.get('time_from'),
            'time_to': weekdays.get('time_to'),
            'weekend_time_from': weekends.get('time_from'),
            'weekend_time_to': weekends.get('time_to'),
        }
    )

    partner_city.update(**data)

    unworking_day_names = {working_day.capitalize() for working_day in working_days \
                            if not working_days[working_day]}
    
    working_day_names = {working_day.capitalize() for working_day in working_days \
                         if working_days[working_day]}
    
    partner_city = partner_city.first()

    partner_city.working_days.through.objects\
            .filter(workingday__code_name__in=unworking_day_names).delete()

    partner_city.working_days\
                .add(*WorkingDay.objects.filter(code_name__in=working_day_names))
    # print(len(connection.queries))
    return {'status': 'success',
            'details': f'Партнёрский город {partner_city.city.name} успешно изменён'}



@test_partner_router.patch('/edit_partner_city')
def edit_partner_city2(partner: partner_dependency,
                       edited_city: AddPartnerCitySchema3):
    # print(len(connection.queries))
    partner_id = partner.get('partner_id')

    partner_city = PartnerCity.objects.select_related('exchange',
                                                      'exchange__account',
                                                      'city')\
                                        .filter(exchange__account__pk=partner_id,
                                                city__code_name=edited_city.city)
    if not partner_city:
        raise HTTPException(status_code=404)
    
    data = edited_city.model_dump()
    working_days = data.pop('working_days')
    data.pop('city')

    weekdays = data.pop('weekdays')
    weekends = data.pop('weekends')

    data.update(
        {
            'time_from': weekdays.get('time_from'),
            'time_to': weekdays.get('time_to'),
            'weekend_time_from': weekends.get('time_from'),
            'weekend_time_to': weekends.get('time_to'),
        }
    )

    partner_city.update(**data)

    unworking_day_names = {working_day.capitalize() for working_day in working_days \
                            if not working_days[working_day]}
    
    working_day_names = {working_day.capitalize() for working_day in working_days \
                         if working_days[working_day]}
    
    partner_city = partner_city.first()

    partner_city.working_days.through.objects\
            .filter(workingday__code_name__in=unworking_day_names).delete()

    partner_city.working_days\
                .add(*WorkingDay.objects.filter(code_name__in=working_day_names))
    # print(len(connection.queries))
    return {'status': 'success',
            'details': f'Партнёрский город {partner_city.city.name} успешно изменён'}



@partner_router.delete('/delete_partner_city')
def delete_partner_city(partner: partner_dependency,
                        city_id: int):
    partner_id = partner.get('partner_id')

    city_on_delete = PartnerCity.objects.select_related('exchange__account')\
                                        .filter(exchange__account__pk=partner_id,
                                                pk=city_id)
    
    if not city_on_delete:
        raise HTTPException(status_code=404)
    
    city_on_delete.delete()

    return {'status': 'success',
            'details': 'Партнёрский город удалён'}


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


@partner_router.post('/add_partner_direction')
def add_partner_direction(partner: partner_dependency,
                          new_direction: AddPartnerDirectionSchema):
    partner_id = partner.get('partner_id')

    data = new_direction.model_dump()

    valute_from = data.pop('valute_from')
    valute_to = data.pop('valute_to')
    try:
        city = PartnerCity.objects.select_related('exchange',
                                                  'exchange__account',
                                                  'city')\
                                    .get(exchange__account__pk=partner_id,
                                        city__code_name=data['city'])    

        direction = CashDirection.objects.select_related('valute_from',
                                                        'valute_to')\
                                            .get(valute_from__code_name=valute_from,
                                                 valute_to__code_name=valute_to)
    except Exception:
        raise HTTPException(status_code=404)
    else:
        data['city'] = city
        data['direction'] = direction

        try:
            Direction.objects.create(**data)
            return {'status': 'success',
                    'details': f'Партнерское направление {direction.display_name} добавлено'}
        except IntegrityError:
            raise HTTPException(status_code=423,
                                detail='Такое направление уже существует')

        

@test_partner_router.post('/add_partner_direction')
def add_partner_direction2(partner: partner_dependency,
                          new_direction: AddPartnerDirectionSchema):
    partner_id = partner.get('partner_id')

    data = new_direction.model_dump()

    valute_from = data.pop('valute_from')
    valute_to = data.pop('valute_to')
    try:
        city = PartnerCity.objects.select_related('exchange',
                                                  'exchange__account',
                                                  'city')\
                                    .get(exchange__account__pk=partner_id,
                                        city__code_name=data['city'])    

        direction = CashDirection.objects.select_related('valute_from',
                                                        'valute_to')\
                                            .get(valute_from__code_name=valute_from,
                                                 valute_to__code_name=valute_to)
    except Exception:
        raise HTTPException(status_code=404)
    else:
        data['city'] = city
        data['direction'] = direction

        try:
            Direction.objects.create(**data)
            return {'status': 'success',
                    'details': f'Партнерское направление {direction.display_name} добавлено'}
        except IntegrityError:
            raise HTTPException(status_code=423,
                                detail='Такое направление уже существует')


@partner_router.patch('/edit_partner_directions')
def edit_partner_directions_by_city(partner: partner_dependency,
                                    response_body: ListEditedPartnerDirectionSchema):
    # print(len(connection.queries))
    partner_id = partner.get('partner_id')

    data: dict = response_body.model_dump()

    city_code_name = data['city']
    edited_direction_list = data['directions']

    partner_directions = Direction.objects\
                                    .select_related('city',
                                                    'city__city',
                                                    'city__exchange__account',
                                                    'direction',
                                                    'direction__valute_from',
                                                    'direction__valute_to')\
                                    .filter(city__exchange__account__pk=partner_id)

    city = PartnerCity.objects.select_related('exchange',
                                              'exchange__account',
                                              'city')\
                                .filter(exchange__account__pk=partner_id,
                                        city__code_name=city_code_name)
    
    try:
        with transaction.atomic():
            for edited_direction in edited_direction_list:
                _id = edited_direction.pop('id')
                edited_direction['time_update'] = datetime.now()
                partner_directions.filter(pk=_id).update(**edited_direction)

            city.update(time_update=timezone.now())
    except Exception:
        raise HTTPException(status_code=400)
    else:
        return {'status': 'success',
                'details': f'updated {len(edited_direction_list)} directions'}


@partner_router.delete('/delete_partner_direction')
def delete_partner_direction(partner: partner_dependency,
                             direction_id: int):
    partner_id = partner.get('partner_id')
    
    try:
        direction_on_delete = Direction.objects.select_related('city__exchange__account')\
                                                .get(city__exchange__account__pk=partner_id,
                                                        pk=direction_id)
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404)
    
    direction_on_delete.delete()

    return {'status': 'success',
            'details': 'Партнёрское направление удалено'}
