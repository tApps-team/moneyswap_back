from pydantic import BaseModel, Field


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