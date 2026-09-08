from datetime import timedelta

from rest_framework import serializers

from .models import MenuItem, Reservation


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
