from typing import Any

from general_models.models import Exchanger
# import no_cash.models as no_cash_models

# import cash.models as cash_models


# def update_exchange_to_db(pk: int,
#                           exchange_marker: str,
#                           data_for_update: dict[str, Any]):
#     model = no_cash_models if exchange_marker == 'no_cash' else cash_models

#     print('date_to_update', data_for_update)

#     model.Exchange.objects.filter(pk=pk)\
#                             .update(**data_for_update)
    

# def update_exchange_to_db(en_name: str,
#                           data_for_update: dict[str, Any]):

#     print(f'date_to_update {en_name}', data_for_update)

#     filename = './new_age.json'

#     with open(filename, 'w', encoding='')

    # Exchanger.objects.filter(pk=pk)\
    #                         .update(**data_for_update)

import json
import os
import tempfile

def add_to_json_dict(filename: str, key: str, value: str):
    # если файла нет — создаём новый словарь
    if not os.path.exists(filename):
        data = {key: value}
    else:
        # читаем существующий JSON
        with open(filename, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError("Файл содержит не словарь")
            except json.JSONDecodeError:
                data = {}

        # обновляем или добавляем новую пару
        data[key] = value

    print(f'запись {key}: {value}')

    # безопасная запись через временный файл (атомарно)
    dirn = os.path.dirname(filename) or "."
    with tempfile.NamedTemporaryFile("w", delete=False, dir=dirn, encoding="utf-8") as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmpname = tmp.name
    os.replace(tmpname, filename)