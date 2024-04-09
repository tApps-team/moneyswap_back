from typing import List

from pydantic import BaseModel, Field, RootModel


class PartnerCityInfoSchema(BaseModel):
    delivery: bool | None
    office: bool | None
    working_days: dict[str, bool]
    time_from: str | None = Field(default=None)
    time_to: str | None = Field(default=None)


class PartnerCitySchema(BaseModel):
    id: int
    name: str
    code_name: str
    country: str
    country_flag: str
    info: PartnerCityInfoSchema


class CountrySchema(BaseModel):
    id: int
    name: str
    country_flag: str


class CitySchema(BaseModel):
    id: int = Field(alias='pk')
    name: str
    code_name: str


class DirectionSchema(BaseModel):
    id: int
    valute_from: str
    icon_valute_from: str
    valute_to: str
    icon_valute_to: str
    in_count: float
    out_count: float
    is_active: bool


class NewPasswordSchema(BaseModel):
    new_password: str


class AccountTitleSchema(BaseModel):
    ru: str
    en: str


class AccountInfoSchema(BaseModel):
    title: AccountTitleSchema
    partner_link: str | None


class ActualCourseSchema(BaseModel):
    valute_from: str
    icon_valute_from: str
    in_count: float
    valute_to: str
    icon_valute_to: str
    out_count: float


class AddPartnerCitySchema(BaseModel):
    city: str
    has_delivery: bool = Field(alias='delivery')
    has_office: bool = Field(alias='office')
    time_from: str
    time_to: str
    working_days: dict


class PartnerDirectionSchema(BaseModel):
    in_count: float    
    out_count: float
    is_active: bool


class AddPartnerDirectionSchema(PartnerDirectionSchema):
    city: str
    valute_from: str
    # id: int
    # in_count: float
    valute_to: str
    # out_count: float
    # is_active: bool


class EditedPartnerDirectionSchema(PartnerDirectionSchema):
    id: int
#     city: str
#     valute_from: str
#     valute_to: str
#     in_count: float
#     out_count: float
#     is_active: bool


class ListEditedPartnerDirectionSchema(RootModel):
    root: List[EditedPartnerDirectionSchema]