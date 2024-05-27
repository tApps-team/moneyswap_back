# from fastapi import FastAPI, File, UploadFile
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


class ReviewsByExchangeSchema(BaseModel):
    page: int
    element_on_page: int
    content: list[ReviewViewSchema]


class AddReviewSchema(BaseModel):
    exchange_id: int
    exchange_marker: str
    tg_id: int
    text: str
    grade: int
    transaction_id: int | None