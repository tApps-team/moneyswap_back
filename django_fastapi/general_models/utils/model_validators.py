from django.core.exceptions import ValidationError


def is_positive_validate(value: int):
    if value < 0:
        raise ValidationError(f'Частота должна быть положительной, передано: {value}')
    

def custom_timeout_validate(value: int):
    if value < 0 or value > 15:
        raise ValidationError(f'Число должно быть положительным и не более 15, передано: {value}')