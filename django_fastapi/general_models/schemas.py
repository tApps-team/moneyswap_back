# from fastapi import FastAPI, File, UploadFile
from typing import Literal, Optional
from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


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


class NewSpecificValuteSchema(BaseModel):
    id: int
    name: MultipleName = Field(alias='multiple_name')
    code_name: str
    icon_url: str | None = Field(alias='icon')
    type_valute: MultipleName = Field(alias='multiple_type')


class ReviewCountSchema(BaseModel):
    positive: int = Field(default=0)
    neutral: int = Field(default=0)
    negative: int = Field(default=0)


class NewSpecialDirectionMultiModel(BaseModel):
    id: int
    name: MultipleName
    exchange_id: int
    partner_link: str | None
    is_vip: bool
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
    # direction_marker: str


class ExtendedSpecialDirectionMultiModel(NewSpecialDirectionMultiModel):
    direction_marker: str


class InfoSchema(BaseModel):
    high_aml: bool


class NewSpecialDirectionMultiWithAmlModel(NewSpecialDirectionMultiModel):
    info: InfoSchema


class ExtendedSpecialDirectionMultiWithAmlModel(ExtendedSpecialDirectionMultiModel):
    info: InfoSchema


class PartnerExchangeRate(BaseModel):
    min_count: int | None
    max_count: int | None
    in_count: float
    out_count: float
    rate_coefficient: float | None = Field(default=None)


class NewSpecialPartnerNoCashDirectionSchema(NewSpecialDirectionMultiWithAmlModel):
    exchange_rates: list[PartnerExchangeRate] | None


class ExtendedSpecialPartnerNoCashDirectionSchema(ExtendedSpecialDirectionMultiWithAmlModel):
    exchange_rates: list[PartnerExchangeRate] | None


class ReviewViewSchema(BaseModel):
    id: int
    username: str | None = Field(default='Гость')
    review_date: str
    review_time: str
    grade: int
    text: str
    comment_count: int
    review_from: Literal['moneyswap', 'bestchange', 'ai']

    @field_validator('review_from', mode='before')
    def force_review_from(cls, w):
        return 'moneyswap'


class ReviewsByExchangeSchema(BaseModel):
    pages: int
    page: int
    element_on_page: int
    exchange_id: int
    content: list[ReviewViewSchema]


class NewReviewsByExchangeSchema(BaseModel):
    pages: int
    page: int
    element_on_page: int
    #
    exchange_name: str
    #
    content: list[ReviewViewSchema]


class AddReviewSchema(BaseModel):
    exchange_id: int
    tg_id: int
    text: str
    grade: int
    transaction_id: str | None


class NewAddReviewSchema(BaseModel):
    exchange_name: str
    tg_id: int
    text: str
    grade: int
    transaction_id: str | None


class AddCommentSchema(BaseModel):
    exchange_marker: str
    review_id: int
    tg_id: int
    text: str
    grade: int


class NewAddCommentSchema(BaseModel):
    review_id: int
    tg_id: int
    text: str
    grade: int


class CommentRoleEnum(str, Enum):
    admin = 'admin'
    exchenger = 'exchanger'
    user = 'user'


class CommentSchema(BaseModel):
    id: int
    comment_date: str
    comment_time: str
    text: str
    role: CommentRoleEnum
    name: str | None = Field(alias='username',
                             default=None)



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

class NewValuteTypeListSchema(BaseModel):
    id: int
    name: ValuteTypeNameSchema
    code_name: str
    type_valute: str
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


class NewValuteListSchema(BaseModel):
    id: int
    name: ValuteTypeNameSchema
    currencies: list[NewValuteTypeListSchema]


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
    courses: int | None = Field(alias='direction_count')
    url: str | None = Field(alias='partner_link')
    reviews: ReviewCountSchema


class NewCommonExchangeSchema(BaseModel):
    id: int = Field(alias='pk')
    # exchangerName: str = Field(alias='name')
    exchangerName: MultipleName = Field(alias='multiple_name')
    exchange_marker: str
    workStatus: str = Field(alias='active_status')
    reserves: str | None = Field(alias='reserve_amount')
    courses: int | None = Field(alias='direction_count')
    url: str | None = Field(alias='partner_link')
    reviews: ReviewCountSchema


class ExchangeListElementSchema(BaseModel):
    id: int = Field(alias='pk')
    exchangerName: MultipleName = Field(alias='multiple_name')
    workStatus: str = Field(alias='active_status')
    reserves: str | None = Field(alias='reserve_amount')
    courses: int | None = Field(alias='direction_count')
    url: str | None = Field(alias='partner_link')
    reviews: ReviewCountSchema


class BlackListExchangeSchema(BaseModel):
    id: int = Field(alias='pk')
    # exchangerName: str = Field(alias='name')
    exchangerName: MultipleName = Field(alias='multiple_name')
    exchange_marker: str
    # workStatus: str = Field(alias='active_status')
    # reserves: str | None = Field(alias='reserve_amount')
    # courses: int | None = Field(alias='direction_count')
    # url: str | None
    # reviews: ReviewCountSchema


class NewBlackListExchangeSchema(BaseModel):
    id: int = Field(alias='pk')
    exchangerName: MultipleName = Field(alias='multiple_name')


class DetailBlackListExchangeSchema(BaseModel):
    id: int = Field(alias='pk')
    # exchangerName: str = Field(alias='name')
    exchangerName: MultipleName = Field(alias='multiple_name')
    iconUrl: str | None = Field(alias='icon',
                                default=None)
    exchange_marker: str
    # workStatus: str = Field(alias='active_status')
    # reserves: str | None = Field(alias='reserve_amount')
    # courses: int | None = Field(alias='direction_count')
    url: str | None
    # reviews: ReviewCountSchema


class NewDetailBlackListExchangeSchema(DetailBlackListExchangeSchema):
    linked_urls: list


class BlackExchangeDetailSchema(BaseModel):
    id: int = Field(alias='pk')
    exchangerName: MultipleName = Field(alias='multiple_name')
    iconUrl: str | None = Field(alias='icon',
                                default=None)
    url: str | None
    linked_urls: list[str]


class DetailExchangeSchema(BaseModel):
    id: int = Field(alias='pk')
    exchangerName: MultipleName = Field(alias='multiple_name')
    iconUrl: str | None = Field(alias='icon',
                                default=None)
    url: str = Field(alias='partner_link')
    high_aml: bool
    workStatus: str = Field(alias='active_status')
    reviews: ReviewCountSchema = Field(alias='review_set')
    country: str | None
    segment_marker: str | None
    amountReserves: str | None = Field(alias='reserve_amount',
                                       default=None)
    exchangeRates: int | None = Field(alias='course_count',
                                      default=None)
    open: str | None = Field(alias='age',
                             default=None)
    openOnMoneySwap: datetime | None = Field(alias='time_create',
                                        default=None)
    closedOnMoneySwap: datetime | None = Field(alias='time_disable',
                                        default=None)
    

class NewDetailExchangeSchema(BaseModel):
    exchangerName: MultipleName = Field(alias='multiple_name')
    iconUrl: str | None = Field(alias='icon',
                                default=None)
    url: str = Field(alias='partner_link')
    high_aml: bool
    workStatus: str = Field(alias='active_status')
    reviews: ReviewCountSchema = Field(alias='review_set')
    country: str | None
    amountReserves: str | None = Field(alias='reserve_amount',
                                       default=None)
    exchangeRates: int | None = Field(alias='course_count',
                                      default=None)
    open: str | None = Field(alias='age',
                             default=None)
    openOnMoneySwap: datetime | None = Field(alias='time_create',
                                        default=None)
    closedOnMoneySwap: datetime | None = Field(alias='time_disable',
                                        default=None)


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


class NewExchangeLinkCountSchema(BaseModel):
    user_id: int
    exchange_id: int
    direction_marker: Literal['auto_noncash',
                              'auto_cash',
                              'city',
                              'country',
                              'no_cash']
    exchange_direction_id: int



class TopExchangeSchema(BaseModel):
    id: int = Field(alias='pk')
    name: str
    iconUrl: str = Field(alias='icon')
    reviewCount: ReviewCountSchema = Field(alias='reviews')
    exchangerMarker: str = Field(alias='exchange_marker')


class NewTopExchangeSchema(BaseModel):
    id: int = Field(alias='pk')
    name: str
    iconUrl: str = Field(alias='icon')
    reviewCount: ReviewCountSchema = Field(alias='reviews')


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
    'Проблемма с обменником',
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


class SiteMapDirectonSchemaNew(BaseModel):
    valute_from : str
    valute_to: str
    direction_marker: str
    city: str | None


class NewSiteMapDirectonSchema(BaseModel):
    page: int
    pages: int
    element_on_page: int | None = Field(default=None)
    directions: list[SiteMapDirectonSchema]


class NewSiteMapDirectonSchema2(BaseModel):
    page: int
    pages: int
    element_on_page: int | None = Field(default=None)
    directions: list[SiteMapDirectonSchemaNew]


class IncreasePopularCountSchema(BaseModel):
    valute_from: str
    valute_to: str
    city_code_name: Optional[str] = None


class IncreaseExchangeLinkCountSchema(BaseModel):
    user_id: int
    exchange_id : int
    valute_from: str
    valute_to: str
    city_id: Optional[int] = None