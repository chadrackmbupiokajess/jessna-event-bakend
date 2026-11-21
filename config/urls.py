from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

admin.site.site_header = "Jessna Event"
admin.site.site_title = "Jessna Event"

urlpatterns = [
    path("django-admin/", admin.site.urls),
    # Alias pratique : /admin/ redirige vers l'interface Django officielle.
    path("admin/", RedirectView.as_view(url="/django-admin/", permanent=False)),
    path("api/", include("invitations.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
