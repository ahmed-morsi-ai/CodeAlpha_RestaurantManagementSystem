from decimal import Decimal

from datetime import timedelta

from django.db import transaction
from django.db.models import F
from rest_framework import serializers

from .models import (
    InventoryItem,
    MenuItem,
    MenuItemIngredient,
    Order,
    OrderItem,
    Reservation,
)


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "name",
            "quantity",
            "unit",
            "reorder_level",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "name",
            "unit",
            "reorder_level",
            "updated_at",
        ]

    def validate_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "quantity must be greater than or equal to 0."
            )
        return value


class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = [
            "id",
            "name",
            "description",
            "price",
            "is_available",
            "created_at",
            "updated_at",
        ]


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = [
            "id",
            "table",
            "customer_name",
            "customer_phone",
            "reserved_at",
            "duration_minutes",
            "party_size",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]

    def validate_duration_minutes(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "duration_minutes must be greater than 0."
            )
        return value

    def validate(self, attrs):
        table = attrs["table"]
        reserved_at = attrs["reserved_at"]
        duration_minutes = attrs.get("duration_minutes", 60)
        new_end = reserved_at + timedelta(minutes=duration_minutes)

        active_reservations = Reservation.objects.filter(
            table=table,
        ).exclude(
            status=Reservation.Status.CANCELLED,
        )

        for reservation in active_reservations:
            existing_start = reservation.reserved_at
            existing_end = existing_start + timedelta(
                minutes=reservation.duration_minutes,
            )

            if existing_start < new_end and existing_end > reserved_at:
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            "The table is already reserved for the requested time."
                        ]
                    }
                )

        return attrs


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            "menu_item",
            "quantity",
            "unit_price",
        ]
        read_only_fields = ["unit_price"]

    def validate_menu_item(self, value):
        if not value.is_available:
            raise serializers.ValidationError(
                "This menu item is currently unavailable."
            )
        return value

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "quantity must be greater than 0."
            )
        return value


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "table",
            "status",
            "created_at",
            "updated_at",
            "items",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError(
                "At least one order item is required."
            )
        return value

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        menu_item_ids = {item_data["menu_item"].pk for item_data in items_data}

        inventory_consumption = {}

        requirements = (
            MenuItemIngredient.objects.filter(
                menu_item_id__in=menu_item_ids,
            )
            .select_related("inventory_item")
            .order_by("inventory_item_id")
        )

        for requirement in requirements:
            total_required = (
                Decimal("0")
                + requirement.quantity_required
                * sum(
                    item_data["quantity"]
                    for item_data in items_data
                    if item_data["menu_item"].pk == requirement.menu_item_id
                )
            )

            existing = inventory_consumption.get(requirement.inventory_item_id)
            if existing is None:
                inventory_consumption[requirement.inventory_item_id] = {
                    "inventory_item": requirement.inventory_item,
                    "quantity": total_required,
                }
            else:
                existing["quantity"] += total_required

        with transaction.atomic():
            for inventory_id in sorted(inventory_consumption):
                inventory_data = inventory_consumption[inventory_id]
                inventory_item = inventory_data["inventory_item"]
                required_quantity = inventory_data["quantity"]

                updated = (
                    InventoryItem.objects.filter(
                        pk=inventory_id,
                        quantity__gte=required_quantity,
                    )
                    .update(
                        quantity=F("quantity") - required_quantity,
                    )
                )

                if updated != 1:
                    raise serializers.ValidationError(
                        {
                            "items": [
                                (
                                    "Insufficient inventory for "
                                    f"{inventory_item.name}."
                                )
                            ]
                        }
                    )

            order = Order.objects.create(**validated_data)
            OrderItem.objects.bulk_create(
                [
                    OrderItem(
                        order=order,
                        menu_item=item_data["menu_item"],
                        quantity=item_data["quantity"],
                        unit_price=item_data["menu_item"].price,
                    )
                    for item_data in items_data
                ]
            )

        return order
