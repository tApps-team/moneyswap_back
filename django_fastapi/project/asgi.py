import os
import time
import logging

from django.apps import apps
from django.conf import settings
from django.core.wsgi import get_wsgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
apps.populate(settings.INSTALLED_APPS)


from fastapi import FastAPI, APIRouter, Request
from fastapi.middleware.wsgi import WSGIMiddleware
from starlette.middleware.cors import CORSMiddleware

from prometheus_fastapi_instrumentator import Instrumentator

from general_models.endpoints import common_router, review_router
from no_cash.endpoints import no_cash_router
from cash.endpoints import cash_router
from partners.auth.endpoints import auth_router
from partners.endpoints import partner_router

from general_models.utils.http_exc import (CustomJSONException,
                                           my_json_exception_handle)


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

#Связывает Django и FastAPI
def get_application() -> FastAPI:
    app = FastAPI(title='BestChangeTgBot API', debug=settings.DEBUG)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Instrumentator().instrument(app).expose(app)
    
    api_router = APIRouter(prefix=settings.FASTAPI_PREFIX)
    api_router.include_router(common_router)
    api_router.include_router(review_router)
    api_router.include_router(no_cash_router)
    api_router.include_router(cash_router)
    api_router.include_router(auth_router)
    api_router.include_router(partner_router)

    app.add_exception_handler(CustomJSONException,
                              my_json_exception_handle)

    app.include_router(api_router)
    app.mount('/', WSGIMiddleware(get_wsgi_application()))

    return app


app = get_application()


@app.middleware("http")
async def log_request_time(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logging.info(f"Request: {request.url.path} completed in {process_time:.4f} seconds")
    return response