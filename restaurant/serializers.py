from datetime import timedelta

from django.db import transaction
from rest_framework import serializers

from .models import MenuItem, Order, OrderItem, Reservation


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

        with transaction.atomic():
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
