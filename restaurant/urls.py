from django.urls import path

from .views import MenuItemListView


urlpatterns = [
    path("menu/", MenuItemListView.as_view(), name="menu-list"),
]
