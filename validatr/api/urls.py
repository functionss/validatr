"""validatr URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# from django.contrib import admin
# from django.urls import path

# urlpatterns = [
#     path('admin/', admin.site.urls),
# ]


from django.urls import path, include
from rest_framework.routers import DefaultRouter


from validatr.api.assets.image.views import ImageAssetViewset

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(
    r"assets/image",
    ImageAssetViewset,
    basename="image",
)

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path("", include(router.urls)),
]