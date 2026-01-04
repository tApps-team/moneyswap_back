from fastapi import Query, HTTPException
from fastapi.openapi.models import Example

from pydantic import BaseModel, validator


#Описание для Swagger`a
#Query параметры для эндпоинта /available_valutes
class AvailableValutesQuery:
    def __init__(self,
                 city: str = Query(description='Кодовое сокращение города',
                                   example='msk',
                                   default=None),
                 base: str = Query(description='Кодовое сокращение валюты',
                                   openapi_examples={
                                       'Валюты, доступные для обмена': Example(value='all'),
                                       'Валюты, в которые можно обменять': Example(value='btc'),
                                   })):
        self.city = None if not city else city.upper()
        self.base = base.upper()

    def params(self):
        return {
            'city': self.city,
            'base': self.base,
        }
    

#Описание для Swagger`a
#Query параметры для эндпоинта /directions
class SpecificDirectionsQuery:
    def __init__(self,
                 city: str = Query(description='Кодовое сокращение города',
                                   example='msk',
                                   default=None),
                 valute_from: str = Query(description='Кодовое сокращение валюты',
                                          example='btc'),
                 valute_to: str = Query(description='Кодовое сокращение валюты',
                                        example='cashrub')):
        # if valute_from and not valute_from.isalpha():
        #     raise HTTPException(
        #         status_code=400,
        #         detail='Incorrect value "valute_from"'
        #     )

        # if valute_to and not valute_to.isalpha():
        #     raise HTTPException(
        #         status_code=400,
        #         detail='Incorrect value "valute_to"'
        # )
        if city and not city.isalpha():
            raise HTTPException(
                status_code=400,
                detail='Incorrect value "city"'
        )
        self.city = None if not city else city.upper()
        self.valute_from = valute_from.upper()
        self.valute_to = valute_to.upper()

    def params(self):
        return {
            'city': self.city,
            'valute_from': self.valute_from,
            'valute_to': self.valute_to,
        }