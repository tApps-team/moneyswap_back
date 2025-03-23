from django.db.models import Q
from django.core.exceptions import ValidationError


def get_limit_direction():
    first_limit = Q(valute_from__type_valute='Криптовалюта',
                    valute_to__type_valute='Наличные')
                    # actual_course__isnull=False)
    second_filter = Q(valute_from__type_valute='Наличные',
                      valute_to__type_valute='Криптовалюта')
                    # actual_course__isnull=False)
    third_filter = Q(valute_from__type_valute='Наличные',
                      valute_to__type_valute='Наличные')
    fourth_filter = Q(valute_from__type_valute='Банкинг',
                      valute_to__type_valute='Наличные')
    fifth_filter = Q(valute_from__type_valute='Банкинг',
                      valute_to__type_valute='ATM QR')
    
    return first_limit | second_filter | third_filter | fourth_filter | fifth_filter


def get_limit_vautes():
    return Q(type_valute='ATM QR')


def is_positive_validator(value: float):
    if value < 0:
        raise ValidationError('Значение должно быть положительным числом')