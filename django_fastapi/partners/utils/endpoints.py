from collections import defaultdict

from django.db.models import Count, Q
from django.db import connection

from general_models.utils.endpoints import try_generate_icon_url, get_reviews_count_filters

from general_models.schemas import MultipleName, MultipleName2

from cash.models import Direction as CashDirection

from partners.models import Direction, PartnerCity

from partners.schemas import (PartnerCityInfoSchema,
                              UpdatedTimeByPartnerCitySchema,
                              PartnerCitySchema2,
                              WeekDaySchema,
                              PartnerCityInfoSchema2)


WORKING_DAYS_DICT = {
     'Пн': False,
     'Вт': False,
     'Ср': False,
     'Чт': False,
     'Пт': False,
     'Сб': False,
     'Вс': False,
}


def get_course_count(direction):
        if direction is None:
            return 0
        actual_course = direction.direction.actual_course
        return actual_course if actual_course is not None else 0


def get_partner_in_out_count(actual_course: float | None):
    if actual_course is None:
        return None
    
    if actual_course < 1:
        in_count = 1 / actual_course
        out_count = 1
    else:
         in_count = 1
         out_count = actual_course

    return (
         in_count,
         out_count,
    )


# def get_partner_directions(city: str,
#                            valute_from: str,
#                            valute_to: str):
#     direction_name = valute_from + ' -> ' + valute_to

#     review_counts = get_reviews_count_filters('partner_direction')

#     directions = Direction.objects\
#                             .select_related('direction',
#                                             'direction__valute_from',
#                                             'direction__valute_to',
#                                             'city',
#                                             'city__city',
#                                             'city__exchange')\
#                             .annotate(positive_review_count=review_counts['positive'])\
#                             .annotate(neutral_review_count=review_counts['neutral'])\
#                             .annotate(negative_review_count=review_counts['negative'])\
#                             .filter(direction__display_name=direction_name,
#                                     city__city__code_name=city,
#                                     is_active=True,
#                                     city__exchange__partner_link__isnull=False)

#     for direction in directions:
#         direction.exchange = direction.city.exchange
#         direction.exchange_marker = 'partner'
#         direction.valute_from = valute_from
#         direction.valute_to = valute_to
#         direction.min_amount = None
#         direction.max_amount = None
#         direction.params = None
#         direction.fromfee = None
#         #
#         working_days = WORKING_DAYS_DICT.copy()
#         [working_days.__setitem__(day.code_name, True)\
#           for day in direction.city.working_days.all()]

#         direction.info = PartnerCityInfoSchema(
#             delivery=direction.city.has_delivery,
#             office=direction.city.has_office,
#             working_days=working_days,
#             time_from=direction.city.time_from,
#             time_to=direction.city.time_to
#             )
#         #
#     return directions


def get_partner_directions(valute_from: str,
                           valute_to: str,
                           city: str = None):
    direction_name = valute_from + ' -> ' + valute_to

    review_counts = get_reviews_count_filters('partner_direction')

    directions = Direction.objects\
                            .select_related('direction',
                                            'direction__valute_from',
                                            'direction__valute_to',
                                            'city',
                                            'city__city',
                                            'city__exchange')\
                            .annotate(positive_review_count=review_counts['positive'])\
                            .annotate(neutral_review_count=review_counts['neutral'])\
                            .annotate(negative_review_count=review_counts['negative'])\
                            .filter(direction__display_name=direction_name,
                                    is_active=True,
                                    city__exchange__is_active=True,
                                    city__exchange__partner_link__isnull=False)
    if city:
        directions = directions.filter(city__city__code_name=city)

    for direction in directions:
        direction.exchange = direction.city.exchange
        direction.exchange_marker = 'partner'
        direction.valute_from = valute_from
        direction.valute_to = valute_to
        direction.min_amount = str(direction.min_amount)
        direction.max_amount = str(direction.max_amount)
        direction.params = None
        direction.fromfee = None
        #
        working_days = WORKING_DAYS_DICT.copy()
        [working_days.__setitem__(day.code_name, True)\
          for day in direction.city.working_days.all()]

        direction.info = PartnerCityInfoSchema(
            delivery=direction.city.has_delivery,
            office=direction.city.has_office,
            working_days=working_days,
            time_from=direction.city.time_from,
            time_to=direction.city.time_to
            )
        #
    return directions


def get_partner_directions_with_location(valute_from: str,
                                         valute_to: str):
    direction_name = valute_from + ' -> ' + valute_to

    review_counts = get_reviews_count_filters('partner_direction')

    directions = Direction.objects\
                            .select_related('direction',
                                            'direction__valute_from',
                                            'direction__valute_to',
                                            'city',
                                            'city__city',
                                            'city__city__country',
                                            'city__exchange')\
                            .annotate(positive_review_count=review_counts['positive'])\
                            .annotate(neutral_review_count=review_counts['neutral'])\
                            .annotate(negative_review_count=review_counts['negative'])\
                            .filter(direction__display_name=direction_name,
                                    is_active=True,
                                    city__exchange__partner_link__isnull=False)

    for direction in directions:
        direction.exchange = direction.city.exchange
        direction.exchange_marker = 'partner'
        direction.valute_from = valute_from
        direction.valute_to = valute_to
        direction.min_amount = None
        direction.max_amount = None
        direction.params = None
        direction.fromfee = None

        working_days = WORKING_DAYS_DICT.copy()
        [working_days.__setitem__(day.code_name, True)\
          for day in direction.city.working_days.all()]

        direction.info = PartnerCityInfoSchema(
            delivery=direction.city.has_delivery,
            office=direction.city.has_office,
            working_days=working_days,
            time_from=direction.city.time_from,
            time_to=direction.city.time_to
            )

    return directions


def generate_partner_cities(partner_cities: list[PartnerCity]):
    for city in partner_cities:
        city.name = city.city.name
        city.code_name = city.city.code_name
        city.country = city.city.country.name
        city.country_flag = try_generate_icon_url(city.city.country)

        # working_days = WORKING_DAYS_DICT.copy()
        # [working_days.__setitem__(day.code_name, True) for day in city.working_days.all()]
        working_days = {key.upper(): value \
                        for key, value in WORKING_DAYS_DICT.items()}
        
        [working_days.__setitem__(day.code_name.upper(), True) \
         for day in city.working_days.all()]

        city.info = PartnerCityInfoSchema(delivery=city.has_delivery,
                                          office=city.has_office,
                                          working_days=working_days,
                                          time_from=city.time_from,
                                          time_to=city.time_to)
        date = time = None

        if city.time_update:
            date, time = city.time_update.astimezone().strftime('%d.%m.%Y %H:%M').split()
        
        city.updated = UpdatedTimeByPartnerCitySchema(date=date,
                                                      time=time)
        
    # print(len(connection.queries))
    return partner_cities


def generate_partner_cities2(partner_cities: list[PartnerCity]):
    for city in partner_cities:
        city.city_multiple_name = MultipleName(name=city.city.name,
                                               en_name=city.city.en_name)
        city.code_name = city.city.code_name
        city.country_multiple_name = MultipleName(name=city.city.country.name,
                                                  en_name=city.city.country.en_name)
        city.country_flag = try_generate_icon_url(city.city.country)

        weekdays = WeekDaySchema(time_from=city.time_from,
                                      time_to=city.time_to)

        weekends = WeekDaySchema(time_from=city.weekend_time_from,
                                      time_to=city.weekend_time_to)


        # working_days = WORKING_DAYS_DICT.copy()
        working_days = {key.upper(): value \
                        for key, value in WORKING_DAYS_DICT.items()}
        
        [working_days.__setitem__(day.code_name.upper(), True) \
         for day in city.working_days.all()]

        city.info = PartnerCityInfoSchema2(delivery=city.has_delivery,
                                          office=city.has_office,
                                          working_days=working_days,
                                          weekdays=weekdays,
                                          weekends=weekends)
        date = time = None

        if city.time_update:
            date, time = city.time_update.astimezone().strftime('%d.%m.%Y %H:%M').split()
        
        city.updated = UpdatedTimeByPartnerCitySchema(date=date,
                                                      time=time)
        
    # print(len(connection.queries))
    return partner_cities


def generate_partner_directions_by_city(directions: list[Direction]):
    for direction in directions:
        direction.valute_from = direction.direction.valute_from.code_name
        direction.icon_valute_from = try_generate_icon_url(direction.direction.valute_from)
        direction.in_count_type = direction.direction.valute_from.type_valute

        direction.valute_to = direction.direction.valute_to.code_name
        direction.icon_valute_to = try_generate_icon_url(direction.direction.valute_to)
        direction.out_count_type = direction.direction.valute_to.type_valute

    # print(len(connection.queries))
    return directions


def generate_valute_list(queries: list[CashDirection],
                         marker: str):
    valute_list = sorted({query.__getattribute__(marker) for query in queries},
                         key=lambda el: el.code_name)

    json_dict = defaultdict(list)

    for _id, valute in enumerate(valute_list, start=1):
        type_valute = valute.type_valute

        valute_dict = {
            'id': _id,
            'name': valute.name,
            'code_name': valute.code_name,
            'icon_url': try_generate_icon_url(valute),
            'type_valute': type_valute,
        }

        json_dict[type_valute].append(valute_dict)
    # print(len(connection.queries))
    return json_dict


def generate_valute_list2(queries: list[CashDirection],
                         marker: str):
    valute_list = sorted({query.__getattribute__(marker) for query in queries},
                         key=lambda el: el.code_name)

    json_dict = defaultdict(list)

    for _id, valute in enumerate(valute_list, start=1):
        type_valute = valute.type_valute

        valute_dict = {
            'id': _id,
            'name': MultipleName2(ru=valute.name,
                                 en=valute.en_name),
            'code_name': valute.code_name,
            'icon_url': try_generate_icon_url(valute),
            'type_valute': type_valute,
        }

        json_dict[type_valute].append(valute_dict)
    # print(len(connection.queries))
    return json_dict


def generate_actual_course(direction: CashDirection):
    in_out_count = get_partner_in_out_count(direction.actual_course)
    icon_valute_from = try_generate_icon_url(direction.valute_from)
    icon_valute_to = try_generate_icon_url(direction.valute_to)

    if in_out_count is not None:
        in_count, out_count = in_out_count
    else:
        in_count = out_count = 0

    return {
        'valute_from': direction.valute_from.code_name,
        'icon_valute_from': icon_valute_from,
        'in_count': in_count,
        'valute_to': direction.valute_to.code_name,
        'icon_valute_to': icon_valute_to,
        'out_count': out_count,
    }