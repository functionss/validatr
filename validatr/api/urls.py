from django.urls import path, include
from rest_framework.routers import DefaultRouter

from validatr.api.assets.views import AssetViewset, EchoViewset

router = DefaultRouter()
router.register(r"assets", AssetViewset, basename="image")
router.register(r"echo", EchoViewset, basename="echo")

urlpatterns = [
    path("", include(router.urls)),
]
