from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles import views
from django.contrib.admin.models import LogEntry
from django.urls import path

from general_models.admin import custom_admin_site  # путь к твоему классу

from django.contrib import admin

# custom_admin_site = CustomAdminSite()

# class LogEntryAdmin(admin.ModelAdmin):
#     list_display = (
#         'user',
#     )

# custom_admin_site.register(LogEntry, LogEntryAdmin)

# urlpatterns = [
#     path('admin22/', custom_admin_site.urls),
# ]


admin.site.site_header = 'Админ панель базы данных MoneySwap'


def trigger_error(request):
    division_by_zero = 1 / 0


urlpatterns = [
    path("admin/action-forms/", include("django_admin_action_forms.urls")),
    path("admin/", admin.site.urls),
    path('admin22/', custom_admin_site.urls),
    path('sentry-debug/', trigger_error),
    path('summernote/', include('django_summernote.urls')),
    path("select2/", include("django_select2.urls")),
    ]


if settings.DEBUG:
    from django.urls import re_path

    urlpatterns += [
    path("__debug__/", include("debug_toolbar.urls")),
    ]

    urlpatterns += [re_path(r"^static/(?P<path>.*)$", views.serve)]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)