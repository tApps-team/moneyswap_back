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

from partners.models import CustomUser


EXPIRES_ACCESS_TOKEN = timedelta(seconds=60)
EXPIRES_REFRESH_TOKEN = timedelta(days=60)

o2auth_bearer = OAuth2PasswordBearer(tokenUrl=f'{settings.FASTAPI_PREFIX}/auth/token')


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


def create_token(user_id: int,
                 expires_delta: timedelta):
    encode = {
        'id': user_id
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
        user_id = payload.get('id')

        if not user_id:
            raise JWTError()
        
        return {'user_id': user_id}
        
    except JWTError:
        raise HTTPException(status_code=401)
        

def check_refresh_token_or_raise_exception(token: str):
    http_exc_400 = HTTPException(status_code=400)

    try:
        payload = jwt.decode(token,
                             JWT_SECRET_KEY,
                             algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise http_exc_400
    else:
        user_id = payload.get('id')

        if not user_id:
            raise http_exc_400

        partner = CustomUser.objects.filter(pk=user_id).first()
        
        if not partner:
            raise http_exc_400
        
        if token != partner.refresh_token:
            raise http_exc_400
        
        return partner
            

def add_refresh_token_to_db(partner: CustomUser,
                            refresh_token: str):
    partner.refresh_token = refresh_token
    partner.save()