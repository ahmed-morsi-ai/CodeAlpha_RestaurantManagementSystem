from rest_framework.generics import CreateAPIView, ListAPIView

from .models import MenuItem, Order, Reservation
from .serializers import (
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
