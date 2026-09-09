from django.urls import path

from .views import (
    InventoryDetailView,
    InventoryListView,
    MenuItemListView,
    OrderCreateView,
    ReservationCreateView,
)


urlpatterns = [
    path("menu/", MenuItemListView.as_view(), name="menu-list"),
    path("inventory/", InventoryListView.as_view(), name="inventory-list"),
    path("inventory/<int:pk>/", InventoryDetailView.as_view(), name="inventory-detail"),
    path("reservations/", ReservationCreateView.as_view(), name="reservation-create"),
    path("orders/", OrderCreateView.as_view(), name="order-create"),
]
