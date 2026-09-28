from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from shelf import views

router = DefaultRouter()
router.register("runs", views.DetectorRunViewSet, basename="run")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("api/skus/", views.SKUList.as_view()),
    path("api/observations/", views.ObservationList.as_view()),
    path("api/signals/pack-changes/", views.pack_changes),
    path("api/signals/launches/", views.launches),
    path("api/signals/price-index/", views.price_index),
    path("api/signals/brief/", views.weekly_brief),
]
