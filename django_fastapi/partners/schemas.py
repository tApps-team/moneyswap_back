from typing import List, Literal

from pydantic import BaseModel, Field, RootModel

from general_models.schemas import MultipleName


class WeekDaySchema(BaseModel):
    time_from: str | None
    time_to: str | None


class AddBankomatSchema(BaseModel):
    id: int
    available: bool


class BankomatDetailSchema(AddBankomatSchema):
    name: str
    icon: str | None


class PartnerCityInfoSchema(BaseModel):
    delivery: bool | None
    office: bool | None
    working_days: dict[str, bool]
    time_from: str | None = Field(default=None)
    time_to: str | None = Field(default=None)


class PartnerCityInfoSchema2(BaseModel):
    delivery: bool | None
    office: bool | None
    working_days: dict[str, bool]
    # time_from: str | None = Field(default=None)
    # time_to: str | None = Field(default=None)
    weekdays: WeekDaySchema
    weekends: WeekDaySchema
    bankomats: list[BankomatDetailSchema] | None


class UpdatedTimeByPartnerCitySchema(BaseModel):
    date: str | None
    time: str | None


class PartnerCitySchema(BaseModel):
    id: int
    name: str
    code_name: str
    country: str
    country_flag: str
    info: PartnerCityInfoSchema
    updated: UpdatedTimeByPartnerCitySchema


class PartnerCitySchema2(BaseModel):
    id: int
    name: MultipleName = Field(alias='city_multiple_name')
    code_name: str
    country: MultipleName = Field(alias='country_multiple_name')
    country_flag: str
    info: PartnerCityInfoSchema2
    updated: UpdatedTimeByPartnerCitySchema


class PartnerCitySchema3(BaseModel):
    id: int
    name: MultipleName = Field(alias='city_multiple_name')
    code_name: str
    country: MultipleName = Field(alias='country_multiple_name')
    country_flag: str
    info: PartnerCityInfoSchema2
    updated: UpdatedTimeByPartnerCitySchema
    max_amount: float | None
    min_amount: float | None


class PartnerCountrySchema3(BaseModel):
    id: int
    name: MultipleName = Field(alias='country_multiple_name')
    country_flag: str
    info: PartnerCityInfoSchema2
    updated: UpdatedTimeByPartnerCitySchema
    max_amount: float | None
    min_amount: float | None


class PartnerCountrySchema(BaseModel):
    id: int = Field(alias='pk')
    name: MultipleName = Field(alias='multiple_name')
    country_flag: str | None


class CountrySchema(BaseModel):
    id: int
    name: str
    country_flag: str


class CountrySchema2(BaseModel):
    id: int
    name: MultipleName = Field(alias='multiple_name')
    country_flag: str


class CitySchema(BaseModel):
    id: int = Field(alias='pk')
    name: str
    code_name: str


class CitySchema2(BaseModel):
    id: int = Field(alias='pk')
    name: MultipleName = Field(alias='multiple_name')
    code_name: str


class DirectionSchema(BaseModel):
    id: int
    valute_from: str
    icon_valute_from: str | None
    valute_to: str
    icon_valute_to: str | None
    in_count: float | None = Field(default=None)
    in_count_type: str
    out_count: float | None = Field(default=None)
    out_count_type: str
    is_active: bool


class DirectionSchema2(BaseModel):
    id: int
    valute_from: str
    icon_valute_from: str | None
    valute_to: str
    icon_valute_to: str | None
    in_count: float | None = Field(default=None)
    in_count_type: str
    out_count: float | None = Field(default=None)
    out_count_type: str
    is_active: bool
    bankomats: list[BankomatDetailSchema] | None


class PartnerExchangeRate(BaseModel):
    min_count: int | None
    max_count: int | None
    in_count: float
    out_count: float
    rate_coefficient: float | None = Field(default=None)


class PartnerExchangeRateForEdit(PartnerExchangeRate):
    id: int | None = Field(default=None)


class DirectionSchema3(BaseModel):
    id: int
    valute_from: str
    icon_valute_from: str | None
    valute_to: str
    icon_valute_to: str | None
    # in_count: float | None = Field(default=None)
    in_count_type: str
    # out_count: float | None = Field(default=None)
    out_count_type: str
    is_active: bool
    bankomats: list[BankomatDetailSchema] | None
    exchange_rates: list[PartnerExchangeRateForEdit]


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



class AddPartnerCitySchema2(BaseModel):
    city: str
    has_delivery: bool = Field(alias='delivery')
    has_office: bool = Field(alias='office')
    weekdays: WeekDaySchema
    weekends: WeekDaySchema
    # time_from: str
    # time_to: str
    working_days: dict


class AddPartnerCitySchema3(BaseModel):
    city: str
    has_delivery: bool = Field(alias='delivery')
    has_office: bool = Field(alias='office')
    weekdays: WeekDaySchema
    weekends: WeekDaySchema
    working_days: dict
    min_amount: float | None
    max_amount: float | None


class AddPartnerCountrySchema(BaseModel):
    country_id: int
    has_delivery: bool = Field(alias='delivery')
    has_office: bool = Field(alias='office')
    weekdays: WeekDaySchema
    weekends: WeekDaySchema
    working_days: dict
    min_amount: float | None
    max_amount: float | None


class DeletePartnerCountrySchema(BaseModel):
    country_id: int


class AddPartnerCityCountrySchema(BaseModel):
    id: int
    marker: Literal['country', 'city']
    has_delivery: bool = Field(alias='delivery')
    has_office: bool = Field(alias='office')
    weekdays: WeekDaySchema
    weekends: WeekDaySchema
    working_days: dict
    min_amount: float | None
    max_amount: float | None
    # has_delivery: bool = Field(alias='delivery')
    # has_office: bool = Field(alias='office')
    # weekdays: WeekDaySchema
    # weekends: WeekDaySchema
    # working_days: dict
    # min_amount: float | None
    # max_amount: float | None


class DeletePartnerDirectionSchema(BaseModel):
    id: int
    marker: Literal['country', 'city']
    direction_id: int


class DeletePartnerCityCountrySchema(BaseModel):
    id: int
    marker: Literal['country', 'city']


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


class AddPartnerDirectionSchema2(PartnerDirectionSchema):
    id: int
    marker: Literal['country', 'city']
    valute_from: str
    valute_to: str


# class BankomatSchema(BaseModel):
#     id: int = Field(alias='pk')
#     name: str
#     available: bool

# class AddBankomatSchema(BaseModel):
#     id: int
#     available: bool


# class BankomatDetailSchema(AddBankomatSchema):
#     name: str


class AddPartnerDirectionSchema3(AddPartnerDirectionSchema2):
    bankomats: list[AddBankomatSchema] | None


# class PartnerExchangeRate(BaseModel):
#     min_count: int | None
#     max_count: int | None
#     in_count: float
#     out_count: float
#     rate_coefficient: float | None = Field(default=None)


# class PartnerExchangeRateForEdit(PartnerExchangeRate):
#     id: int | None = Field(default=None)


class NewAddPartnerDirectionSchema(BaseModel):
    id: int
    marker: Literal['country', 'city']
    valute_from: str
    valute_to: str
    is_active: bool
    bankomats: list[AddBankomatSchema] | None
    exchange_rates: list[PartnerExchangeRate]
    # id: int
    # valute_from: str
    # valute_to: str
    # is_active: bool


class EditedPartnerDirectionSchema(PartnerDirectionSchema):
    id: int
#     city: str
#     valute_from: str
#     valute_to: str
#     in_count: float
#     out_count: float
#     is_active: bool


# class ListEditedPartnerDirectionSchema(RootModel):
#     root: List[EditedPartnerDirectionSchema]


class ListEditedPartnerDirectionSchema(BaseModel):
    city: str
    directions: List[EditedPartnerDirectionSchema]


class ListEditedPartnerDirectionSchema2(BaseModel):
    id: int
    marker: Literal['country', 'city']
    directions: List[EditedPartnerDirectionSchema]


class NewEditedPartnerDirectionSchema(BaseModel):
    id: int
    is_active: bool
    exchange_rates: list[PartnerExchangeRateForEdit]


class NewListEditedPartnerDirectionSchema(BaseModel):
    id: int
    marker: Literal['country', 'city']
    directions: List[NewEditedPartnerDirectionSchema]


class CountryDirectionWithLocationSchema(BaseModel):
    id: int
    country_id: int
    direction_id: int
    

class ExchangeLinkCountSchema(BaseModel):
    user_id: int
    exchange_id: int
    direction_marker: str
    exchange_direction_id: int