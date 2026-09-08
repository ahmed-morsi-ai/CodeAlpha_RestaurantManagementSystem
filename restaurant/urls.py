from django.urls import path

from .views import MenuItemListView, ReservationCreateView


urlpatterns = [
    path("menu/", MenuItemListView.as_view(), name="menu-list"),
    path("reservations/", ReservationCreateView.as_view(), name="reservation-create"),
]
