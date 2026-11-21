from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Jessna Event"
admin.site.site_title = "Jessna Event"

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/", include("invitations.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
