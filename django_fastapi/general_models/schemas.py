# from fastapi import FastAPI, File, UploadFile
from typing import Literal
from enum import Enum

from pydantic import BaseModel, Field


class MultipleName(BaseModel):
    ru: str = Field(alias='name')
    en: str = Field(alias='en_name')


class MultipleName2(BaseModel):
    ru: str
    en: str


#Схема валюты для отображения в json ответе
class ValuteModel(BaseModel):
    id: int
    name: str
    code_name: str
    icon_url: str | None


#Схема валюты для английской версии для отображения в json ответе
class EnValuteModel(BaseModel):
    id: int
    name: str = Field(alias='en_name')
    code_name: str
    icon_url: str | None


class SpecificValuteSchema(BaseModel):
    name: MultipleName = Field(alias='multiple_name')
    code_name: str
    icon_url: str | None = Field(alias='icon')
    type_valute: MultipleName = Field(alias='multiple_type')


#Схема готового направления для отображения в json ответе
class SpecialDirectionModel(BaseModel):
    id: int
    name: str
    # name: MultipleName
    partner_link: str | None
    valute_from: str
    icon_valute_from: str | None
    valute_to: str
    icon_valute_to: str | None
    in_count: float
    out_count: float
    min_amount: str
    max_amount: str


class ReviewCountSchema(BaseModel):
    positive: int
    neutral: int
    negative: int


class SpecialDirectionMultiModel(BaseModel):
    id: int
    # name: str
    name: MultipleName
    exchange_id: int
    exchange_marker: str
    partner_link: str | None
    is_vip: bool
    # review_count: int
    review_count: ReviewCountSchema
    valute_from: str
    icon_valute_from: str | None
    valute_to: str
    icon_valute_to: str | None
    in_count: float
    out_count: float
    min_amount: str | None
    max_amount: str | None
    exchange_direction_id: int


class InfoSchema(BaseModel):
    high_aml: bool


class SpecialDirectionMultiWithAmlModel(SpecialDirectionMultiModel):
    info: InfoSchema


class ReviewViewSchema(BaseModel):
    id: int
    username: str
    review_date: str
    review_time: str
    grade: int
    text: str
    comment_count: int


class ReviewsByExchangeSchema(BaseModel):
    pages: int
    page: int
    element_on_page: int
    #
    exchange_id: int
    exchange_marker: str
    #
    content: list[ReviewViewSchema]


class AddReviewSchema(BaseModel):
    exchange_id: int
    exchange_marker: str
    tg_id: int
    text: str
    grade: int
    transaction_id: str | None



class CommentRoleEnum(str, Enum):
    admin = 'admin'
    exchenger = 'exchenger'
    user = 'user'


class CommentSchema(BaseModel):
    id: int
    comment_date: str
    comment_time: str
    text: str
    role: CommentRoleEnum
    name: str | None = Field(default=None)



class ValuteTypeNameSchema(BaseModel):
    ru: str
    en: str


class ValuteTypeListSchema(BaseModel):
    id: str
    name: ValuteTypeNameSchema
    code_name: str
    icon_url: str
    # is_popular: bool

class ValuteTypeListSchema1(BaseModel):
    id: str
    name: ValuteTypeNameSchema
    code_name: str
    icon_url: str
    is_popular: bool

class ValuteTypeListSchema2(BaseModel):
    id: str
    name: ValuteTypeNameSchema
    code_name: str
    type_valute: str
    icon_url: str
    is_popular: bool


class ValuteListSchema(BaseModel):
    id: int
    name: ValuteTypeNameSchema
    currencies: list[ValuteTypeListSchema]


class ValuteListSchema1(BaseModel):
    id: int
    name: ValuteTypeNameSchema
    currencies: list[ValuteTypeListSchema1]


class ValuteListSchema2(BaseModel):
    id: int
    name: ValuteTypeNameSchema
    currencies: list[ValuteTypeListSchema2]
    



class PopularDirectionSchema(BaseModel):
    valute_from: SpecificValuteSchema
    valute_to: SpecificValuteSchema


class CommonExchangeSchema(BaseModel):
    id: int = Field(alias='pk')
    exchangerName: str = Field(alias='name')
    exchange_marker: str
    workStatus: bool = Field(alias='is_active')
    reserves: str | None = Field(alias='reserve_amount')
    courses: str | None = Field(alias='course_count')
    url: str | None = Field(alias='partner_link')
    reviews: ReviewCountSchema



class DetailExchangeSchema(BaseModel):
    name: str
    iconUrl: str | None = Field(alias='icon',
                                default=None)
    url: str = Field(alias='partner_link')
    workStatus: bool = Field(alias='is_active')
    reviews: ReviewCountSchema = Field(alias='review_set')
    country: str | None
    amountReserves: str | None = Field(alias='reserve_amount',
                                       default=None)
    exchangeRates: int | None = Field(alias='course_count',
                                      default=None)
    open: str | None = Field(alias='age',
                             default=None)
    openOnMoneySwap: str | None = Field(default=None)


class DirectionSideBarSchema(BaseModel):
    valuteFrom: ValuteModel
    valuteTo: ValuteModel
    pairCount: int | None = Field(alias='pair_count',
                                  default=None)
    direction_type: str
    # cityCodeName: str | None = Field(default=None)



class ExchangeLinkCountSchema(BaseModel):
    user_id: int
    exchange_id: int
    exchange_marker: str
    exchange_direction_id: int



class TopExchangeSchema(BaseModel):
    id: int = Field(alias='pk')
    name: str
    iconUrl: str = Field(alias='icon')
    reviewCount: ReviewCountSchema = Field(alias='reviews')
    exchangerMarker: str = Field(alias='exchange_marker')


class TopCoinSchema(BaseModel):
    name: str
    code_name: str
    iconUrl: str = Field(alias='icon')
    course: float = Field(alias='actual_course')
    isIncrease: bool | None = Field(alias='is_increase')
    percent: float | None


feedback_reasons_listeral = Literal[
    'Ошибка',
    'Проблема с обменником',
    'Сотрудничество',
    'Другое',
]

class FeedbackFormSchema(BaseModel):
    username: str
    email: str
    reasons: feedback_reasons_listeral
    description: str



class SiteMapDirectonSchema(BaseModel):
    valute_from : str
    valute_to: str
    exchange_marker: str
    city: str | None