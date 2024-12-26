from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles import views
from django.views.generic import RedirectView


admin.site.site_header = 'Админ панель базы данных MoneySwap'


def trigger_error(request):
    division_by_zero = 1 / 0


urlpatterns = [
    path("admin/action-forms/", include("django_admin_action_forms.urls")),
    path("admin/", admin.site.urls),
    path('sentry-debug/', trigger_error),
    path('summernote/', include('django_summernote.urls')),
    re_path(r'^favicon\.ico$', RedirectView.as_view(url='/static/general_models/favicon.ico', permanent=True)),
    ]


if settings.DEBUG:
    from django.urls import re_path

    urlpatterns += [
    path("__debug__/", include("debug_toolbar.urls")),
    ]

    urlpatterns += [re_path(r"^static/(?P<path>.*)$", views.serve)]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)