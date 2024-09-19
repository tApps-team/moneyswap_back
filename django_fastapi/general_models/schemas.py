# from fastapi import FastAPI, File, UploadFile
from enum import Enum

from pydantic import BaseModel, Field


class MultipleName(BaseModel):
    ru: str = Field(alias='name')
    en: str = Field(alias='en_name')


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


class ValuteListSchema(BaseModel):
    id: int
    name: ValuteTypeNameSchema
    currencies: list[ValuteTypeListSchema]



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
    iconUrl: str | None = Field(alias='icon_url',
                                default=None)
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
    # cityCodeName: str | None = Field(default=None)
