from typing import Any

import no_cash.models as no_cash_models

import cash.models as cash_models


def update_exchange_to_db(pk: int,
                          exchange_marker: str,
                          data_for_update: dict[str, Any]):
    model = no_cash_models if exchange_marker == 'no_cash' else cash_models

    print('date_to_update', data_for_update)

    model.Exchange.objects.filter(pk=pk)\
                            .update(**data_for_update)