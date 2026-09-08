from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    InventoryItem,
    MenuItem,
    Order,
    OrderItem,
    Reservation,
    RestaurantTable,
)


class MenuItemModelTests(TestCase):
    def test_menu_item_can_be_created_and_persisted(self):
        menu_item = MenuItem.objects.create(
            name="Margherita Pizza",
            description="Classic tomato and mozzarella pizza",
            price=Decimal("12.50"),
        )

        saved_item = MenuItem.objects.get(pk=menu_item.pk)

        self.assertEqual(saved_item.name, "Margherita Pizza")
        self.assertEqual(
            saved_item.description,
            "Classic tomato and mozzarella pizza",
        )
        self.assertEqual(saved_item.price, Decimal("12.50"))
        self.assertTrue(saved_item.is_available)
        self.assertIsNotNone(saved_item.created_at)
        self.assertIsNotNone(saved_item.updated_at)

    def test_menu_item_string_representation_uses_name(self):
        menu_item = MenuItem.objects.create(
            name="Pasta",
            price=Decimal("9.00"),
        )

        self.assertEqual(str(menu_item), "Pasta")


class RestaurantTableModelTests(TestCase):
    def test_table_can_be_created_and_persisted(self):
        table = RestaurantTable.objects.create(
            number=5,
            capacity=4,
        )

        saved_table = RestaurantTable.objects.get(pk=table.pk)

        self.assertEqual(saved_table.number, 5)
        self.assertEqual(saved_table.capacity, 4)
        self.assertTrue(saved_table.is_active)
        self.assertEqual(str(saved_table), "Table 5")

    def test_table_number_must_be_unique(self):
        RestaurantTable.objects.create(
            number=5,
            capacity=4,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RestaurantTable.objects.create(
                    number=5,
                    capacity=2,
                )


class InventoryItemModelTests(TestCase):
    def test_inventory_item_can_be_created_and_persisted(self):
        item = InventoryItem.objects.create(
            name="Tomatoes",
            quantity=Decimal("25.50"),
            unit="kg",
            reorder_level=Decimal("5.00"),
        )

        saved_item = InventoryItem.objects.get(pk=item.pk)

        self.assertEqual(saved_item.name, "Tomatoes")
        self.assertEqual(saved_item.quantity, Decimal("25.50"))
        self.assertEqual(saved_item.unit, "kg")
        self.assertEqual(saved_item.reorder_level, Decimal("5.00"))

    def test_inventory_item_name_must_be_unique(self):
        InventoryItem.objects.create(
            name="Tomatoes",
            quantity=Decimal("10.00"),
            unit="kg",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                InventoryItem.objects.create(
                    name="Tomatoes",
                    quantity=Decimal("5.00"),
                    unit="kg",
                )


class ReservationModelTests(TestCase):
    def test_reservation_can_reference_a_restaurant_table(self):
        table = RestaurantTable.objects.create(
            number=3,
            capacity=4,
        )

        reserved_at = timezone.now()
        reservation = Reservation.objects.create(
            table=table,
            customer_name="Ahmed",
            customer_phone="01000000000",
            reserved_at=reserved_at,
            party_size=3,
        )

        saved_reservation = Reservation.objects.get(pk=reservation.pk)

        self.assertEqual(saved_reservation.table, table)
        self.assertEqual(saved_reservation.customer_name, "Ahmed")
        self.assertEqual(saved_reservation.customer_phone, "01000000000")
        self.assertEqual(saved_reservation.reserved_at, reserved_at)
        self.assertEqual(saved_reservation.party_size, 3)
        self.assertEqual(
            saved_reservation.status,
            Reservation.Status.PENDING,
        )
        self.assertIn(saved_reservation, table.reservations.all())

    def test_reservation_string_representation_includes_customer_and_table(self):
        table = RestaurantTable.objects.create(
            number=2,
            capacity=2,
        )
        reservation = Reservation.objects.create(
            table=table,
            customer_name="Sara",
            customer_phone="01000000001",
            reserved_at=timezone.now(),
            party_size=2,
        )

        self.assertEqual(str(reservation), "Sara - Table 2")


class OrderModelTests(TestCase):
    def test_order_can_be_created_with_default_status(self):
        order = Order.objects.create()

        saved_order = Order.objects.get(pk=order.pk)

        self.assertIsNone(saved_order.table)
        self.assertEqual(saved_order.status, Order.Status.PENDING)
        self.assertIsNotNone(saved_order.created_at)
        self.assertIsNotNone(saved_order.updated_at)
        self.assertEqual(str(saved_order), f"Order {saved_order.pk}")

    def test_order_can_reference_a_restaurant_table(self):
        table = RestaurantTable.objects.create(
            number=1,
            capacity=2,
        )

        order = Order.objects.create(table=table)

        self.assertEqual(order.table, table)
        self.assertIn(order, table.orders.all())


class OrderItemModelTests(TestCase):
    def test_order_item_references_order_and_menu_item(self):
        order = Order.objects.create()
        menu_item = MenuItem.objects.create(
            name="Burger",
            price=Decimal("8.50"),
        )

        order_item = OrderItem.objects.create(
            order=order,
            menu_item=menu_item,
            quantity=2,
            unit_price=Decimal("8.50"),
        )

        saved_item = OrderItem.objects.get(pk=order_item.pk)

        self.assertEqual(saved_item.order, order)
        self.assertEqual(saved_item.menu_item, menu_item)
        self.assertEqual(saved_item.quantity, 2)
        self.assertEqual(saved_item.unit_price, Decimal("8.50"))
        self.assertIn(saved_item, order.items.all())
        self.assertIn(saved_item, menu_item.order_items.all())
        self.assertEqual(str(saved_item), "2 x Burger")

    def test_deleting_order_cascades_to_order_items(self):
        order = Order.objects.create()
        menu_item = MenuItem.objects.create(
            name="Salad",
            price=Decimal("6.00"),
        )

        order_item = OrderItem.objects.create(
            order=order,
            menu_item=menu_item,
            quantity=1,
            unit_price=Decimal("6.00"),
        )

        order.delete()

        self.assertFalse(OrderItem.objects.filter(pk=order_item.pk).exists())


class MenuItemListAPITests(APITestCase):
    def test_menu_list_returns_multiple_items(self):
        MenuItem.objects.create(
            name="Margherita Pizza",
            description="Classic tomato and mozzarella pizza",
            price=Decimal("12.50"),
            is_available=True,
        )
        MenuItem.objects.create(
            name="Pasta",
            description="Creamy pasta",
            price=Decimal("9.00"),
            is_available=False,
        )

        response = self.client.get("/menu/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 2)

        first_item = response.data[0]
        self.assertEqual(
            set(first_item.keys()),
            {
                "id",
                "name",
                "description",
                "price",
                "is_available",
                "created_at",
                "updated_at",
            },
        )
        self.assertEqual(first_item["name"], "Margherita Pizza")
        self.assertEqual(first_item["description"], "Classic tomato and mozzarella pizza")
        self.assertEqual(first_item["price"], "12.50")
        self.assertTrue(first_item["is_available"])

    def test_menu_list_returns_empty_collection_when_no_items_exist(self):
        response = self.client.get("/menu/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_menu_list_returns_all_items_without_filtering(self):
        items = [
            MenuItem.objects.create(name="Pizza", price=Decimal("12.50")),
            MenuItem.objects.create(name="Salad", price=Decimal("6.00")),
            MenuItem.objects.create(name="Soup", price=Decimal("5.00")),
        ]

        response = self.client.get("/menu/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item["id"] for item in response.data},
            {item.id for item in items},
        )


class ReservationCreateAPITests(APITestCase):
    def setUp(self):
        self.table = RestaurantTable.objects.create(
            number=10,
            capacity=4,
        )
        self.second_table = RestaurantTable.objects.create(
            number=11,
            capacity=4,
        )
        self.reserved_at = timezone.datetime(
            2026,
            9,
            8,
            18,
            0,
            tzinfo=timezone.get_current_timezone(),
        )

    def reservation_payload(self, **overrides):
        payload = {
            "table": self.table.pk,
            "customer_name": "Ahmed",
            "customer_phone": "01000000000",
            "reserved_at": self.reserved_at.isoformat(),
            "duration_minutes": 60,
            "party_size": 2,
        }
        payload.update(overrides)
        return payload

    def test_successful_reservation_is_created(self):
        response = self.client.post(
            "/reservations/",
            self.reservation_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Reservation.objects.count(), 1)

        reservation = Reservation.objects.get()
        self.assertEqual(reservation.table, self.table)
        self.assertEqual(reservation.customer_name, "Ahmed")
        self.assertEqual(reservation.duration_minutes, 60)
        self.assertEqual(reservation.party_size, 2)
        self.assertEqual(
            response.data["table"],
            self.table.pk,
        )
        self.assertEqual(response.data["duration_minutes"], 60)
        self.assertEqual(response.data["status"], Reservation.Status.PENDING)

    def test_overlapping_reservation_is_rejected(self):
        Reservation.objects.create(
            table=self.table,
            customer_name="Existing Customer",
            customer_phone="01000000001",
            reserved_at=self.reserved_at,
            duration_minutes=60,
            party_size=2,
        )

        response = self.client.post(
            "/reservations/",
            self.reservation_payload(
                customer_name="New Customer",
                reserved_at=(
                    self.reserved_at + timezone.timedelta(minutes=30)
                ).isoformat(),
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)
        self.assertEqual(Reservation.objects.count(), 1)

    def test_non_overlapping_reservation_is_accepted(self):
        Reservation.objects.create(
            table=self.table,
            customer_name="Existing Customer",
            customer_phone="01000000001",
            reserved_at=self.reserved_at,
            duration_minutes=60,
            party_size=2,
        )

        response = self.client.post(
            "/reservations/",
            self.reservation_payload(
                customer_name="New Customer",
                reserved_at=(
                    self.reserved_at + timezone.timedelta(minutes=120)
                ).isoformat(),
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Reservation.objects.count(), 2)

    def test_different_table_is_accepted_for_same_time(self):
        Reservation.objects.create(
            table=self.table,
            customer_name="Existing Customer",
            customer_phone="01000000001",
            reserved_at=self.reserved_at,
            duration_minutes=60,
            party_size=2,
        )

        response = self.client.post(
            "/reservations/",
            self.reservation_payload(
                table=self.second_table.pk,
                customer_name="Second Table Customer",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Reservation.objects.count(), 2)

    def test_cancelled_reservation_does_not_block_new_reservation(self):
        Reservation.objects.create(
            table=self.table,
            customer_name="Cancelled Customer",
            customer_phone="01000000001",
            reserved_at=self.reserved_at,
            duration_minutes=60,
            party_size=2,
            status=Reservation.Status.CANCELLED,
        )

        response = self.client.post(
            "/reservations/",
            self.reservation_payload(customer_name="New Customer"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Reservation.objects.count(), 2)

    def test_exact_end_start_boundary_does_not_conflict(self):
        Reservation.objects.create(
            table=self.table,
            customer_name="First Customer",
            customer_phone="01000000001",
            reserved_at=self.reserved_at,
            duration_minutes=60,
            party_size=2,
        )

        response = self.client.post(
            "/reservations/",
            self.reservation_payload(
                customer_name="Boundary Customer",
                reserved_at=(
                    self.reserved_at + timezone.timedelta(minutes=60)
                ).isoformat(),
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Reservation.objects.count(), 2)

    def test_invalid_table_is_rejected(self):
        response = self.client.post(
            "/reservations/",
            self.reservation_payload(table=999999),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("table", response.data)
        self.assertEqual(Reservation.objects.count(), 0)

    def test_non_positive_duration_is_rejected(self):
        response = self.client.post(
            "/reservations/",
            self.reservation_payload(duration_minutes=0),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("duration_minutes", response.data)
        self.assertEqual(Reservation.objects.count(), 0)
