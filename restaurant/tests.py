from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

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
