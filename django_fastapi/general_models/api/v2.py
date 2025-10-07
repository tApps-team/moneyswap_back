from django.conf import settings

from fastapi import APIRouter

from general_models.endpoints import common_router, new_review_router, test_router, new_common_router

from no_cash.endpoints import no_cash_router
from cash.endpoints import cash_router, new_cash_router
from partners.auth.endpoints import auth_router, new_auth_router
from partners.endpoints import partner_router, test_partner_router, new_partner_router


api_router = APIRouter(prefix=settings.FASTAPI_PREFIX + '/v2')

api_router.include_router(new_common_router)
api_router.include_router(new_review_router)
api_router.include_router(new_cash_router)
api_router.include_router(new_auth_router)
api_router.include_router(new_partner_router)
# api_router.include_router(no_cash_router)
# api_router.include_router(test_router)
# api_router.include_router(test_partner_router)