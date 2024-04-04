from typing import Annotated
from datetime import timedelta

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from partners.models import CustomUser

from .schemas import PartnerSchema, RefreshToken
from .utils import (get_current_partner,
                    authenticate_partner,
                    generate_tokens,
                    check_refresh_token_or_raise_exception,
                    )


auth_router = APIRouter(prefix='/auth',
                        tags=['JWT auth'])


partner_dependency = Annotated[dict, Depends(get_current_partner)]


# тестовый защищенный эндпоинт
@auth_router.get('/test_jwt')
def test_secure_api(partner: partner_dependency):
    user_id = partner.get('user_id')

    partner = CustomUser.objects.select_related('user',
                                                'exchange')\
                                .filter(pk=user_id).first()
    partner_model = PartnerSchema(pk=partner.pk,
                                  user=partner.user.username,
                                  exchange=partner.exchange.name)
    return partner_model


@auth_router.post('/token')
def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    partner = authenticate_partner(form_data.username,
                                   form_data.password)

    return generate_tokens(partner)
    

@auth_router.post('/refresh')
def refresh_tokens(token: RefreshToken):
    partner = check_refresh_token_or_raise_exception(token.refresh_token)
    return generate_tokens(partner)


# @auth_router.get('/logout')
# def logout(partner: partner_dependency):
#     user_id = partner.get('user_id')
#     CustomUser.objects.filter(pk=user_id).update(refresh_token=None)