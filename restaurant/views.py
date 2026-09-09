from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveUpdateAPIView

from .models import InventoryItem, MenuItem, Order, Reservation
from .serializers import (
    InventoryItemSerializer,
    MenuItemSerializer,
    OrderSerializer,
    ReservationSerializer,
)


class MenuItemListView(ListAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer


class ReservationCreateView(CreateAPIView):
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer


class OrderCreateView(CreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

class InventoryListView(ListAPIView):
    queryset = InventoryItem.objects.all()
    serializer_class = InventoryItemSerializer


class InventoryDetailView(RetrieveUpdateAPIView):
    queryset = InventoryItem.objects.all()
    serializer_class = InventoryItemSerializer
    http_method_names = ["get", "patch", "head", "options"]
