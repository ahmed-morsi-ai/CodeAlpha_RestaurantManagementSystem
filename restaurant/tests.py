from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    InventoryItem,
    MenuItem,
    MenuItemIngredient,
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


class OrderCreateAPITests(APITestCase):
    def setUp(self):
        self.table = RestaurantTable.objects.create(
            number=20,
            capacity=4,
        )
        self.pizza = MenuItem.objects.create(
            name="Margherita Pizza",
            description="Classic tomato and mozzarella pizza",
            price=Decimal("12.50"),
            is_available=True,
        )
        self.pasta = MenuItem.objects.create(
            name="Pasta",
            description="Creamy pasta",
            price=Decimal("9.00"),
            is_available=True,
        )

    def order_payload(self, **overrides):
        payload = {
            "table": self.table.pk,
            "items": [
                {
                    "menu_item": self.pizza.pk,
                    "quantity": 2,
                    "unit_price": "999.99",
                },
                {
                    "menu_item": self.pasta.pk,
                    "quantity": 1,
                },
            ],
        }
        payload.update(overrides)
        return payload

    def test_successful_order_creation_persists_order_items_and_server_prices(self):
        response = self.client.post(
            "/orders/",
            self.order_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderItem.objects.count(), 2)

        order = Order.objects.get()
        self.assertEqual(order.table, self.table)
        self.assertEqual(order.status, Order.Status.PENDING)

        items = list(
            OrderItem.objects.filter(order=order).order_by("menu_item_id")
        )
        self.assertEqual(items[0].menu_item, self.pizza)
        self.assertEqual(items[0].quantity, 2)
        self.assertEqual(items[0].unit_price, Decimal("12.50"))
        self.assertEqual(items[1].menu_item, self.pasta)
        self.assertEqual(items[1].quantity, 1)
        self.assertEqual(items[1].unit_price, Decimal("9.00"))

        self.assertEqual(response.data["table"], self.table.pk)
        self.assertEqual(response.data["status"], Order.Status.PENDING)
        self.assertEqual(len(response.data["items"]), 2)

        response_items = {
            item["menu_item"]: item
            for item in response.data["items"]
        }
        self.assertEqual(
            response_items[self.pizza.pk]["unit_price"],
            "12.50",
        )
        self.assertEqual(
            response_items[self.pasta.pk]["unit_price"],
            "9.00",
        )

    def test_multiple_order_items_belong_to_one_order(self):
        response = self.client.post(
            "/orders/",
            self.order_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        order = Order.objects.get()
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(
            set(order.items.values_list("menu_item_id", flat=True)),
            {self.pizza.pk, self.pasta.pk},
        )

    def test_invalid_table_is_rejected_without_creating_order_items(self):
        response = self.client.post(
            "/orders/",
            self.order_payload(table=999999),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("table", response.data)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderItem.objects.count(), 0)

    def test_invalid_menu_item_is_rejected_without_partial_order(self):
        response = self.client.post(
            "/orders/",
            self.order_payload(
                items=[
                    {
                        "menu_item": self.pizza.pk,
                        "quantity": 1,
                    },
                    {
                        "menu_item": 999999,
                        "quantity": 1,
                    },
                ],
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderItem.objects.count(), 0)

    def test_invalid_quantity_is_rejected(self):
        response = self.client.post(
            "/orders/",
            self.order_payload(
                items=[
                    {
                        "menu_item": self.pizza.pk,
                        "quantity": 0,
                    },
                ],
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("items", response.data)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderItem.objects.count(), 0)

    def test_validation_failure_in_one_item_prevents_any_order_creation(self):
        response = self.client.post(
            "/orders/",
            self.order_payload(
                items=[
                    {
                        "menu_item": self.pizza.pk,
                        "quantity": 2,
                    },
                    {
                        "menu_item": self.pasta.pk,
                        "quantity": 0,
                    },
                ],
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderItem.objects.count(), 0)

    def test_unavailable_menu_item_is_rejected(self):
        self.pasta.is_available = False
        self.pasta.save(update_fields=["is_available"])

        response = self.client.post(
            "/orders/",
            self.order_payload(
                items=[
                    {
                        "menu_item": self.pasta.pk,
                        "quantity": 1,
                    },
                ],
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderItem.objects.count(), 0)

class MenuItemIngredientModelTests(TestCase):
    def setUp(self):
        self.menu_item = MenuItem.objects.create(
            name="Margherita Pizza",
            price=Decimal("12.50"),
        )
        self.second_menu_item = MenuItem.objects.create(
            name="Pasta",
            price=Decimal("9.00"),
        )
        self.tomatoes = InventoryItem.objects.create(
            name="Tomatoes",
            quantity=Decimal("25.50"),
            unit="kg",
            reorder_level=Decimal("5.00"),
        )
        self.cheese = InventoryItem.objects.create(
            name="Cheese",
            quantity=Decimal("10.00"),
            unit="kg",
            reorder_level=Decimal("2.00"),
        )

    def test_menu_item_can_have_one_inventory_requirement(self):
        requirement = MenuItemIngredient.objects.create(
            menu_item=self.menu_item,
            inventory_item=self.tomatoes,
            quantity_required=Decimal("0.15"),
        )

        saved_requirement = MenuItemIngredient.objects.get(pk=requirement.pk)

        self.assertEqual(saved_requirement.menu_item, self.menu_item)
        self.assertEqual(saved_requirement.inventory_item, self.tomatoes)
        self.assertEqual(
            saved_requirement.quantity_required,
            Decimal("0.15"),
        )
        self.assertIn(
            saved_requirement,
            self.menu_item.inventory_requirements.all(),
        )
        self.assertIn(
            saved_requirement,
            self.tomatoes.menu_item_requirements.all(),
        )

    def test_menu_item_can_have_multiple_inventory_requirements(self):
        MenuItemIngredient.objects.create(
            menu_item=self.menu_item,
            inventory_item=self.tomatoes,
            quantity_required=Decimal("0.15"),
        )
        MenuItemIngredient.objects.create(
            menu_item=self.menu_item,
            inventory_item=self.cheese,
            quantity_required=Decimal("0.10"),
        )

        self.assertEqual(self.menu_item.inventory_requirements.count(), 2)
        self.assertEqual(
            set(
                self.menu_item.inventory_requirements.values_list(
                    "inventory_item_id",
                    flat=True,
                )
            ),
            {self.tomatoes.pk, self.cheese.pk},
        )

    def test_inventory_item_can_be_shared_by_multiple_menu_items(self):
        first_requirement = MenuItemIngredient.objects.create(
            menu_item=self.menu_item,
            inventory_item=self.tomatoes,
            quantity_required=Decimal("0.15"),
        )
        second_requirement = MenuItemIngredient.objects.create(
            menu_item=self.second_menu_item,
            inventory_item=self.tomatoes,
            quantity_required=Decimal("0.20"),
        )

        self.assertEqual(first_requirement.inventory_item, self.tomatoes)
        self.assertEqual(second_requirement.inventory_item, self.tomatoes)
        self.assertEqual(
            self.tomatoes.menu_item_requirements.count(),
            2,
        )

    def test_duplicate_menu_item_inventory_mapping_is_rejected(self):
        MenuItemIngredient.objects.create(
            menu_item=self.menu_item,
            inventory_item=self.tomatoes,
            quantity_required=Decimal("0.15"),
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MenuItemIngredient.objects.create(
                    menu_item=self.menu_item,
                    inventory_item=self.tomatoes,
                    quantity_required=Decimal("0.20"),
                )

    def test_zero_quantity_required_is_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MenuItemIngredient.objects.create(
                    menu_item=self.menu_item,
                    inventory_item=self.tomatoes,
                    quantity_required=Decimal("0.00"),
                )

    def test_negative_quantity_required_is_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MenuItemIngredient.objects.create(
                    menu_item=self.menu_item,
                    inventory_item=self.tomatoes,
                    quantity_required=Decimal("-0.10"),
                )

    def test_deleting_menu_item_cascades_to_inventory_requirements(self):
        requirement = MenuItemIngredient.objects.create(
            menu_item=self.menu_item,
            inventory_item=self.tomatoes,
            quantity_required=Decimal("0.15"),
        )

        self.menu_item.delete()

        self.assertFalse(
            MenuItemIngredient.objects.filter(pk=requirement.pk).exists()
        )
        self.assertTrue(
            InventoryItem.objects.filter(pk=self.tomatoes.pk).exists()
        )

    def test_deleting_inventory_item_is_protected(self):
        MenuItemIngredient.objects.create(
            menu_item=self.menu_item,
            inventory_item=self.tomatoes,
            quantity_required=Decimal("0.15"),
        )

        with self.assertRaises(ProtectedError):
            self.tomatoes.delete()

        self.assertTrue(
            InventoryItem.objects.filter(pk=self.tomatoes.pk).exists()
        )

class InventoryDeductionOrderAPITests(APITestCase):
    def setUp(self):
        self.table = RestaurantTable.objects.create(
            number=30,
            capacity=4,
        )
        self.pizza = MenuItem.objects.create(
            name="Pizza",
            price=Decimal("12.50"),
            is_available=True,
        )
        self.burger = MenuItem.objects.create(
            name="Burger",
            price=Decimal("8.50"),
            is_available=True,
        )
        self.tomatoes = InventoryItem.objects.create(
            name="Tomatoes",
            quantity=Decimal("10.00"),
            unit="kg",
            reorder_level=Decimal("2.00"),
        )
        self.cheese = InventoryItem.objects.create(
            name="Cheese",
            quantity=Decimal("5.00"),
            unit="kg",
            reorder_level=Decimal("1.00"),
        )

    def order_payload(self, **overrides):
        payload = {
            "table": self.table.pk,
            "items": [
                {
                    "menu_item": self.pizza.pk,
                    "quantity": 2,
                },
            ],
        }
        payload.update(overrides)
        return payload

    def test_successful_order_deducts_inventory(self):
        MenuItemIngredient.objects.create(
            menu_item=self.pizza,
            inventory_item=self.tomatoes,
            quantity_required=Decimal("0.25"),
        )

        response = self.client.post(
            "/orders/",
            self.order_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderItem.objects.count(), 1)

        self.tomatoes.refresh_from_db()
        self.assertEqual(self.tomatoes.quantity, Decimal("9.50"))

    def test_order_quantity_is_multiplied_by_required_quantity(self):
        MenuItemIngredient.objects.create(
            menu_item=self.pizza,
            inventory_item=self.tomatoes,
            quantity_required=Decimal("0.25"),
        )

        response = self.client.post(
            "/orders/",
            self.order_payload(
                items=[
                    {
                        "menu_item": self.pizza.pk,
                        "quantity": 4,
                    },
                ],
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.tomatoes.refresh_from_db()
        self.assertEqual(self.tomatoes.quantity, Decimal("9.00"))

    def test_multiple_inventory_dependencies_are_deducted(self):
        MenuItemIngredient.objects.create(
            menu_item=self.pizza,
            inventory_item=self.tomatoes,
            quantity_required=Decimal("0.25"),
        )
        MenuItemIngredient.objects.create(
            menu_item=self.pizza,
            inventory_item=self.cheese,
            quantity_required=Decimal("0.10"),
        )

        response = self.client.post(
            "/orders/",
            self.order_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.tomatoes.refresh_from_db()
        self.cheese.refresh_from_db()

        self.assertEqual(self.tomatoes.quantity, Decimal("9.50"))
        self.assertEqual(self.cheese.quantity, Decimal("4.80"))

    def test_shared_inventory_is_aggregated_across_order_items(self):
        MenuItemIngredient.objects.create(
            menu_item=self.pizza,
            inventory_item=self.tomatoes,
            quantity_required=Decimal("0.20"),
        )
        MenuItemIngredient.objects.create(
            menu_item=self.burger,
            inventory_item=self.tomatoes,
            quantity_required=Decimal("0.10"),
        )

        response = self.client.post(
            "/orders/",
            self.order_payload(
                items=[
                    {
                        "menu_item": self.pizza.pk,
                        "quantity": 2,
                    },
                    {
                        "menu_item": self.burger.pk,
                        "quantity": 1,
                    },
                ],
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderItem.objects.count(), 2)

        self.tomatoes.refresh_from_db()
        self.assertEqual(self.tomatoes.quantity, Decimal("9.50"))

    def test_insufficient_stock_rejects_order_without_changes(self):
        self.tomatoes.quantity = Decimal("0.25")
        self.tomatoes.save(update_fields=["quantity"])

        MenuItemIngredient.objects.create(
            menu_item=self.pizza,
            inventory_item=self.tomatoes,
            quantity_required=Decimal("0.50"),
        )

        response = self.client.post(
            "/orders/",
            self.order_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("items", response.data)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderItem.objects.count(), 0)

        self.tomatoes.refresh_from_db()
        self.assertEqual(self.tomatoes.quantity, Decimal("0.25"))

    def test_insufficient_later_requirement_rolls_back_earlier_deduction(self):
        self.tomatoes.quantity = Decimal("1.00")
        self.tomatoes.save(update_fields=["quantity"])

        self.cheese.quantity = Decimal("0.05")
        self.cheese.save(update_fields=["quantity"])

        MenuItemIngredient.objects.create(
            menu_item=self.pizza,
            inventory_item=self.tomatoes,
            quantity_required=Decimal("0.50"),
        )
        MenuItemIngredient.objects.create(
            menu_item=self.pizza,
            inventory_item=self.cheese,
            quantity_required=Decimal("0.10"),
        )

        response = self.client.post(
            "/orders/",
            self.order_payload(
                items=[
                    {
                        "menu_item": self.pizza.pk,
                        "quantity": 1,
                    },
                ],
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderItem.objects.count(), 0)

        self.tomatoes.refresh_from_db()
        self.cheese.refresh_from_db()

        self.assertEqual(self.tomatoes.quantity, Decimal("1.00"))
        self.assertEqual(self.cheese.quantity, Decimal("0.05"))

    def test_menu_item_without_inventory_requirements_preserves_order_creation(self):
        response = self.client.post(
            "/orders/",
            self.order_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderItem.objects.count(), 1)

        self.tomatoes.refresh_from_db()
        self.cheese.refresh_from_db()

        self.assertEqual(self.tomatoes.quantity, Decimal("10.00"))
        self.assertEqual(self.cheese.quantity, Decimal("5.00"))


class InventoryAPITests(APITestCase):
    def setUp(self):
        self.tomatoes = InventoryItem.objects.create(
            name="Tomatoes",
            quantity=Decimal("10.00"),
            unit="kg",
            reorder_level=Decimal("2.00"),
        )
        self.cheese = InventoryItem.objects.create(
            name="Cheese",
            quantity=Decimal("5.00"),
            unit="kg",
            reorder_level=Decimal("1.00"),
        )

    def test_inventory_list_returns_200(self):
        response = self.client.get("/inventory/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_inventory_list_returns_created_records_with_correct_data(self):
        response = self.client.get("/inventory/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        returned_by_id = {
            item["id"]: item
            for item in response.data
        }

        tomatoes = returned_by_id[self.tomatoes.pk]
        self.assertEqual(tomatoes["name"], "Tomatoes")
        self.assertEqual(tomatoes["quantity"], "10.00")
        self.assertEqual(tomatoes["unit"], "kg")
        self.assertEqual(tomatoes["reorder_level"], "2.00")
        self.assertIn("updated_at", tomatoes)

    def test_inventory_patch_updates_quantity(self):
        response = self.client.patch(
            f"/inventory/{self.tomatoes.pk}/",
            {"quantity": "7.50"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.tomatoes.refresh_from_db()
        self.assertEqual(self.tomatoes.quantity, Decimal("7.50"))
        self.assertEqual(response.data["quantity"], "7.50")

    def test_inventory_detail_get_returns_200(self):
        response = self.client.get(f"/inventory/{self.tomatoes.pk}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.tomatoes.pk)
        self.assertEqual(response.data["quantity"], "10.00")

    def test_inventory_detail_put_returns_405(self):
        response = self.client.put(
            f"/inventory/{self.tomatoes.pk}/",
            {"quantity": "7.50"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_inventory_detail_delete_returns_405(self):
        response = self.client.delete(
            f"/inventory/{self.tomatoes.pk}/"
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_inventory_patch_rejects_negative_quantity(self):
        response = self.client.patch(
            f"/inventory/{self.tomatoes.pk}/",
            {"quantity": "-1.00"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.tomatoes.refresh_from_db()
        self.assertEqual(self.tomatoes.quantity, Decimal("10.00"))

    def test_inventory_patch_does_not_modify_another_item(self):
        response = self.client.patch(
            f"/inventory/{self.tomatoes.pk}/",
            {"quantity": "8.25"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.tomatoes.refresh_from_db()
        self.cheese.refresh_from_db()

        self.assertEqual(self.tomatoes.quantity, Decimal("8.25"))
        self.assertEqual(self.cheese.quantity, Decimal("5.00"))

    def test_inventory_patch_returns_404_for_unknown_id(self):
        unknown_id = max(self.tomatoes.pk, self.cheese.pk) + 1000

        response = self.client.patch(
            f"/inventory/{unknown_id}/",
            {"quantity": "3.00"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class InventoryOrderRegressionAPITests(APITestCase):
    def test_order_creation_still_deducts_inventory(self):
        inventory_item = InventoryItem.objects.create(
            name="Tomatoes",
            quantity=Decimal("10.00"),
            unit="kg",
            reorder_level=Decimal("2.00"),
        )
        menu_item = MenuItem.objects.create(
            name="Pizza",
            price=Decimal("12.00"),
        )
        MenuItemIngredient.objects.create(
            menu_item=menu_item,
            inventory_item=inventory_item,
            quantity_required=Decimal("0.50"),
        )

        response = self.client.post(
            "/orders/",
            {
                "items": [
                    {
                        "menu_item": menu_item.pk,
                        "quantity": 2,
                    }
                ]
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        inventory_item.refresh_from_db()
        self.assertEqual(inventory_item.quantity, Decimal("9.00"))
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderItem.objects.count(), 1)
