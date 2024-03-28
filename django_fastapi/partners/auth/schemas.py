from pydantic import BaseModel


class PartnerSchema(BaseModel):
    pk: int
    user: str
    exchange: str


class RefreshToken(BaseModel):
    refresh_token: str