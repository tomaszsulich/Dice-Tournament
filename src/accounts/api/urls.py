import djoser.urls
import djoser.urls.jwt
from django.urls import include, path

from .views import logout, profile

urlpatterns = [
    path("auth/", include(djoser.urls)),
    path("auth/", include(djoser.urls.jwt)),
    path("auth/logout/", logout),
    path("profile/", profile),
]
