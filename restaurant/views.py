from rest_framework.generics import CreateAPIView, ListAPIView

from .models import MenuItem, Reservation
from .serializers import MenuItemSerializer, ReservationSerializer


class MenuItemListView(ListAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer


class ReservationCreateView(CreateAPIView):
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
