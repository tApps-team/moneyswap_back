from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from .schemas import RefreshToken
from .utils import (get_current_partner,
                    new_get_current_partner,
                    authenticate_partner,
                    generate_tokens,
                    get_partner_or_raise_exception,
                    new_authenticate_partner,
                    new_get_partner_or_raise_exception,
                    )


auth_router = APIRouter(prefix='/auth',
                        tags=['JWT auth'])

new_auth_router = APIRouter(prefix='/auth',
                            tags=['JWT auth(НОВОЕ)'])


partner_dependency = Annotated[dict, Depends(get_current_partner)]
new_partner_dependency = Annotated[dict, Depends(new_get_current_partner)]



@auth_router.post('/token')
def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    partner = authenticate_partner(form_data.username,
                                   form_data.password)

    return generate_tokens(partner)


@new_auth_router.post('/token')
def new_login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    partner = new_authenticate_partner(form_data.username,
                                       form_data.password)

    return generate_tokens(partner)
    

@auth_router.post('/refresh')
def refresh_tokens(token: RefreshToken):
    partner = get_partner_or_raise_exception(token.refresh_token)
    return generate_tokens(partner)


@new_auth_router.post('/refresh')
def new_refresh_tokens(token: RefreshToken):
    partner = new_get_partner_or_raise_exception(token.refresh_token)
    return generate_tokens(partner)