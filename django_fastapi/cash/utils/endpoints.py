from django.db.models import Count, Q
from django.db import connection

from cash.models import Country
from cash.schemas import MultipleName

from general_models.utils.endpoints import try_generate_icon_url


def get_available_countries(countries):

    '''
    Возвращает QuerySet доступных стран с необходимыми данными
    '''

    # country_names = sorted({city.country.name for city in cities})
    
    # countries = Country.objects.filter(name__in=country_names)\
    #                             .prefetch_related('cities').all()

    for country in countries:
        #
        # country.city_list = [el for el in country.cities.all()\
        #                       if el.is_parse == True or el.has_partner_cities == True]
        #
        # country.city_list = list(filter(lambda el: el.is_parse == True,
        #                                 country.cities.all()))
        
        # country.city_list = country.cities.annotate(direction_count=Count('cash_directions',
        #                                                                   filter=Q(cash_directions__is_active=True)))\
        #                                     .annotate(partner_direction_count=Count('partner_cities',
        #                                                                             filter=Q(partner_cities__partner_directions__is_active=True)))\
        #                                     .filter(Q(direction_count__gt=0) | Q(partner_direction_count__gt=0))\
        #                                     .all()
        # print(country.city_list)
        country.city_list = country.cities.all()

        for city in country.city_list:
            city.name = MultipleName(name=city.name,
                                     en_name=city.en_name)
        
        country.country_flag = try_generate_icon_url(country)

        country.name = MultipleName(name=country.name,
                                   en_name=country.en_name)
    print(len(connection.queries))
    print(connection.queries)

    return countries


def get_available_countries2(countries):

    '''
    Возвращает QuerySet доступных стран с необходимыми данными
    '''

    for country in countries:

        country.city_list = country.cities.distinct().all()

        # if country.partner_countries.exists():
        #     partner_cities = country.partner_countries.partner_cities.values_list('city', flat=True)
            # country.city_list += country.partner_countries.partner_cities.values_list('city', flat=True)

        # print(country.city_list)

        for city in country.city_list:
            # print(city)
            city.name = MultipleName(name=city.name,
                                     en_name=city.en_name)
        
        country.country_flag = try_generate_icon_url(country)

        country.name = MultipleName(name=country.name,
                                   en_name=country.en_name)
    # print(len(connection.queries))
    # print(connection.queries)

    return countries