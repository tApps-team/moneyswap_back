import os

from django.apps import apps
from django.conf import settings
from django.core.wsgi import get_wsgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
apps.populate(settings.INSTALLED_APPS)


from fastapi import FastAPI, APIRouter
from fastapi.middleware.wsgi import WSGIMiddleware
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from general_models.endpoints import common_router, review_router, test_router

from no_cash.endpoints import no_cash_router
from cash.endpoints import cash_router
from partners.auth.endpoints import auth_router
from partners.endpoints import partner_router, test_partner_router

from general_models.utils.http_exc import (CustomJSONException,
                                           my_json_exception_handle)

from general_models.api.v1 import api_router as api_v1_router
from general_models.api.v2 import api_router as api_v2_router


#Связывает Django и FastAPI
def get_application() -> FastAPI:
    app = FastAPI(title='MoneySwap API', debug=settings.DEBUG)

    CLIENT_ORIGINS = [
    "https://app.moneyswap.online",
    "https://www.moneyswap.online",
    "https://moneyswap.online",
    "https://partner.moneyswap.online",

    ]

    app.add_middleware(
        CORSMiddleware,
        # allow_origins=["*"],
        allow_origins=CLIENT_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(CustomJSONException,
                              my_json_exception_handle)

    app.include_router(api_v1_router)
    app.include_router(api_v2_router)

    # страница Swagger`а для API V2 с добавлением кастомного заголовка для тестирования
    @app.get("/docs/v2", include_in_schema=False)
    def custom_swagger_ui_html():
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>MoneySwap API V2</title>
            <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist/swagger-ui.css" />
        </head>
        <body>
            <div id="swagger-ui"></div>
            <script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>
            <script src="https://unpkg.com/swagger-ui-dist/swagger-ui-standalone-preset.js"></script>
            <script>
            const ui = SwaggerUIBundle({{
                url: '/openapi.json',
                dom_id: '#swagger-ui',
                presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIStandalonePreset
                ],
                requestInterceptor: function(request) {{
                request.headers['Moneyswap'] = 'true';
                return request;
                }}
            }});
            window.ui = ui;
            </script>
        </body>
        </html>
        """
        return HTMLResponse(html)

    app.mount(settings.DJANGO_PREFIX, WSGIMiddleware(get_wsgi_application()))

    return app


app = get_application()