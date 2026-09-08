from django.urls import path

from .views import MenuItemListView, OrderCreateView, ReservationCreateView


urlpatterns = [
    path("menu/", MenuItemListView.as_view(), name="menu-list"),
    path("reservations/", ReservationCreateView.as_view(), name="reservation-create"),
    path("orders/", OrderCreateView.as_view(), name="order-create"),
]
