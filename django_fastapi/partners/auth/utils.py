from typing import Annotated
from datetime import timedelta, datetime

from fastapi import Depends
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordBearer

from django.contrib.auth.models import User
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from jose import jwt, JWTError

from config import JWT_SECRET_KEY, JWT_ALGORITHM

from partners.models import CustomUser, NewCustomUser


EXPIRES_ACCESS_TOKEN = timedelta(days=1)
EXPIRES_REFRESH_TOKEN = timedelta(days=60)

o2auth_bearer = OAuth2PasswordBearer(tokenUrl=f'{settings.FASTAPI_PREFIX}/auth/token',
                                     scheme_name='Version1')
new_o2auth_bearer = OAuth2PasswordBearer(tokenUrl=f'{settings.FASTAPI_PREFIX}/v2/auth/token',
                                         scheme_name='Version2')


def authenticate_partner(username: str,
                         password: str):
    http_exc_401 = HTTPException(status_code=401)

    try:
        user = User.objects.select_related('moderator_account')\
                            .get(username=username)
        
        if not user.check_password(password):
            raise http_exc_401
        
        partner = user.moderator_account

        return partner
        
    except ObjectDoesNotExist:
        raise http_exc_401
    

def new_authenticate_partner(username: str,
                             password: str):
    http_exc_401 = HTTPException(status_code=401)

    try:
        user = User.objects.select_related('new_moderator_account')\
                            .get(username=username)
        
        if not user.check_password(password):
            raise http_exc_401
        
        partner = user.new_moderator_account

        return partner
        
    except ObjectDoesNotExist:
        raise http_exc_401


def create_token(partner_id: int,
                 expires_delta: timedelta):
    encode = {
        'id': partner_id,
        }
    expires = datetime.now() + expires_delta
    encode.update({'exp': expires.timestamp()})

    return jwt.encode(encode,
                      JWT_SECRET_KEY,
                      algorithm=JWT_ALGORITHM)


def generate_tokens(partner: CustomUser):
    access_token = create_token(partner.pk,
                                EXPIRES_ACCESS_TOKEN)
    refresh_token = create_token(partner.pk,
                                 EXPIRES_REFRESH_TOKEN)
    add_refresh_token_to_db(partner,
                            refresh_token)
    
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'bearer',
    }


def get_current_partner(token: Annotated[str, Depends(o2auth_bearer)]):
    try:
        payload = jwt.decode(token,
                             JWT_SECRET_KEY,
                             algorithms=[JWT_ALGORITHM])
        partner_id = payload.get('id')

        if not partner_id:
            raise JWTError()
        
        return {'partner_id': partner_id}
        
    except JWTError:
        raise HTTPException(status_code=401)
    

def new_get_current_partner(token: Annotated[str, Depends(new_o2auth_bearer)]):
    try:
        payload = jwt.decode(token,
                             JWT_SECRET_KEY,
                             algorithms=[JWT_ALGORITHM])
        partner_id = payload.get('id')

        if not partner_id:
            raise JWTError()
        
        return {'partner_id': partner_id}
        
    except JWTError:
        raise HTTPException(status_code=401)
        

def get_partner_or_raise_exception(refresh_token: str):
    http_exc_400 = HTTPException(status_code=400)

    try:
        payload = jwt.decode(refresh_token,
                             JWT_SECRET_KEY,
                             algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise http_exc_400
    else:
        partner_id = payload.get('id')

        if not partner_id:
            raise http_exc_400

        partner = CustomUser.objects.filter(pk=partner_id).first()
        
        if not partner:
            raise http_exc_400
        
        if refresh_token != partner.refresh_token:
            raise http_exc_400
        
        return partner
    

def new_get_partner_or_raise_exception(refresh_token: str):
    http_exc_400 = HTTPException(status_code=400)

    try:
        payload = jwt.decode(refresh_token,
                             JWT_SECRET_KEY,
                             algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise http_exc_400
    else:
        partner_id = payload.get('id')

        if not partner_id:
            raise http_exc_400

        partner = NewCustomUser.objects.filter(pk=partner_id).first()
        
        if not partner:
            raise http_exc_400
        
        if refresh_token != partner.refresh_token:
            raise http_exc_400
        
        return partner
            

def add_refresh_token_to_db(partner: CustomUser,
                            refresh_token: str):
    partner.refresh_token = refresh_token
    partner.save()