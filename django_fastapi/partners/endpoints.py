from fastapi import APIRouter

from django.db import connection
from django.contrib.auth.models import User

from cash.models import Country, City, Direction as CashDirection

from general_models.utils.endpoints import try_generate_icon_url

from .models import PartnerCity, Direction

from .auth.endpoints import partner_dependency

from .utils.endpoints import generate_partner_cities, generate_partner_directions_by_city, generate_valute_list

from .schemas import PartnerCitySchema, CountrySchema, CitySchema, DirectionSchema, NewPasswordSchema


partner_router = APIRouter(prefix='/partner',
                           tags=['Partners'])


@partner_router.get('/partner_cities',
                    response_model=list[PartnerCitySchema])
def get_partner_cities(partner: partner_dependency):
    partner_id = partner.get('user_id')

    partner_cities = PartnerCity.objects.select_related('exchange',
                                                        'city',
                                                        'city__country',
                                                        'exchange__account')\
                                        .prefetch_related('working_days')\
                                        .filter(exchange__account__pk=partner_id).all()

    return generate_partner_cities(partner_cities)


@partner_router.get('/countries',
                    response_model=list[CountrySchema])
def get_countries():
    countries = Country.objects.all()
    
    for country in countries:
        country.country_flag = try_generate_icon_url(country)

    # [country.__setattr__('country_flag', try_generate_icon_url(country))\
    #   for country in countries]
    
    return countries


@partner_router.get('/cities',
                    response_model=list[CitySchema],
                    response_model_by_alias=False)
def get_cities_for_country(country_name: str):
    return City.objects.select_related('country')\
                        .filter(country__name=country_name).all()


@partner_router.get('/directions_by_city',
                    response_model=list[DirectionSchema])
def get_partner_directions_by_city(partner: partner_dependency,
                                   code_name: str):
    # print(len(connection.queries))
    partner_id = partner.get('user_id')

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

    # print(len(connection.queries))
    return generate_partner_directions_by_city(directions)


@partner_router.get('/available_valutes')
def get_available_valutes_for_partner(base: str):
    # print(len(connection.queries))
    base = base.upper()

    queries = CashDirection.objects.select_related('valute_from',
                                                   'valute_to')\
                                    .filter(actual_course__isnull=False)
    
    if base == 'ALL':
        marker = 'valute_from'
    else:
        marker = 'valute_to'
        queries = queries.filter(valute_from=base)
    # marker = 'valute_from' if base == 'ALL' else 'valute_to'

    return generate_valute_list(queries, marker)
        

@partner_router.post('/change_password')
def change_user_password(partner: partner_dependency,
                         new_password: NewPasswordSchema):
    partner_id = partner.get('user_id')

    user = User.objects.select_related('moderator_account')\
                        .get(moderator_account__pk=partner_id)
    user.set_password(new_password.new_password)
    user.save()