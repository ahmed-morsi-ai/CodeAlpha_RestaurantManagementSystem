# Restaurant Management System

A Django and Django REST Framework backend for restaurant operations, developed as part of the CodeAlpha Backend Development Task 3 internship project.

## Overview

This project provides a backend API for core restaurant operations:

- menu items
- restaurant tables
- reservations
- order creation and processing
- inventory management

The API exposes menu, reservation, order, and inventory operations. Order creation integrates menu-to-inventory requirements through `MenuItemIngredient`, so successful orders automatically deduct the required inventory quantities.

Inventory deduction and order creation are handled transactionally. If an order cannot be fulfilled because of insufficient inventory, the operation is rejected without leaving a partial order or partial inventory deduction.

This is an internship/assignment implementation for CodeAlpha Task 3, not a production deployment.

## Features

- Menu read/list API
- Restaurant table reservations
- Same-table reservation conflict handling
- Order creation and processing
- Inventory item modeling
- Menu-to-inventory ingredient requirements
- Automatic inventory deduction during order creation
- Inventory read/update API
- Automated tests

## Tech Stack

- Python 3.13.13
- Django 6.1.1
- Django REST Framework 3.18.1
- SQLite

Dependencies are pinned in `requirements.txt`.

## Architecture

The project is organized around a Django project (`config`) and a restaurant application (`restaurant`).

- `config/` — project-level Django configuration and root URLs
- `restaurant/models.py` — domain models and relationships
- `restaurant/serializers.py` — API serialization and validation
- `restaurant/views.py` — DRF API views
- `restaurant/urls.py` — application API routes
- `restaurant/tests.py` — model and API tests
- `restaurant/migrations/` — database schema migrations
- `manage.py` — Django management entry point
## Core Domain

### `MenuItem`

Represents a menu item with name, description, price, availability, and timestamps.

### `RestaurantTable`

Represents a restaurant table with a unique number, capacity, and active/inactive state.

### `Reservation`

Represents a table reservation with customer details, reservation time, duration, party size, and status. It references `RestaurantTable`.

### `Order`

Represents an order with an optional table, server-controlled status, and timestamps.

### `OrderItem`

Represents a menu item within an order with quantity and server-derived unit price. It references both `Order` and `MenuItem`.

### `InventoryItem`

Represents stock with a unique name, quantity, unit, reorder level, and update timestamp.

### `MenuItemIngredient`

Connects a `MenuItem` to an `InventoryItem` and records `quantity_required` for one unit of that menu item.

`MenuItemIngredient` enforces a unique menu-item/inventory-item mapping and requires a positive required quantity.

## API Reference

| Method | Endpoint | Purpose | Success | Validation / failure behavior |
|---|---|---|---|---|
| GET | `/menu/` | List menu items | `200 OK` | Read-only menu listing |
| POST | `/reservations/` | Create reservation | `201 Created` | Rejects overlapping active reservations, invalid tables, and non-positive duration |
| POST | `/orders/` | Create order with nested items | `201 Created` | Rejects empty orders, invalid references, unavailable items, non-positive quantities, and insufficient inventory |
| GET | `/inventory/` | List inventory items | `200 OK` | Returns current inventory |
| GET | `/inventory/<id>/` | Retrieve inventory item | `200 OK` | Unknown IDs return `404 Not Found` |
| PATCH | `/inventory/<id>/` | Update inventory quantity | `200 OK` | Negative quantity is rejected; unknown IDs return `404 Not Found` |

The inventory detail endpoint currently exposes:

```text
GET, PATCH, HEAD, OPTIONS
```

`PUT` and `DELETE` are not exposed and return `405 Method Not Allowed`.

## Example Requests and Responses

The numeric IDs below are illustrative only.

### Create a Reservation

`POST /reservations/`

```json
{
  "table": 1,
  "customer_name": "Ahmed",
  "customer_phone": "01000000000",
  "reserved_at": "2026-09-10T18:00:00Z",
  "duration_minutes": 60,
  "party_size": 2
}
```

### Create an Order

`POST /orders/`

```json
{
  "table": 1,
  "items": [
    {
      "menu_item": 1,
      "quantity": 2
    }
  ]
}
```

`unit_price` and `status` are server-controlled.

Example response:

```json
{
  "id": 1,
  "table": 1,
  "status": "pending",
  "created_at": "2026-09-10T18:05:00Z",
  "updated_at": "2026-09-10T18:05:00Z",
  "items": [
    {
      "menu_item": 1,
      "quantity": 2,
      "unit_price": "12.50"
    }
  ]
}
```

### List Inventory

`GET /inventory/`

```json
[
  {
    "id": 1,
    "name": "Tomatoes",
    "quantity": "10.00",
    "unit": "kg",
    "reorder_level": "2.00",
    "updated_at": "2026-09-10T17:00:00Z"
  }
]
```

### Update Inventory

`PATCH /inventory/1/`

```json
{
  "quantity": "7.50"
}
```

## Inventory / Order Flow

1. The client submits menu item IDs and quantities.
2. The server resolves the menu items and uses their server-side prices.
3. `MenuItemIngredient` defines required inventory consumption.
4. Required consumption is calculated as order quantity × `quantity_required`.
5. Consumption is aggregated by `InventoryItem`.
6. Inventory is conditionally deducted only when enough stock exists.
7. Insufficient inventory rejects the order.
8. Inventory deduction, `Order` creation, and `OrderItem` creation are wrapped in a database transaction.

SQLite is used for this assignment and should not be represented as production-grade high-contention inventory concurrency infrastructure.

## Validation / Business Rules

### Menu

- Unavailable menu items cannot be ordered.
- Order item prices are server-controlled.

### Reservations

- Same-table overlapping active reservations are rejected.
- Different tables may be reserved concurrently.
- Cancelled reservations do not block new reservations.
- Exact end/start boundaries are allowed.
- Non-positive duration is rejected.
- Invalid table references are rejected.

### Orders

- Empty orders are rejected.
- Invalid table or menu item references are rejected.
- Unavailable menu items are rejected.
- Non-positive quantities are rejected.
- Order status is server-controlled.
- Insufficient inventory rejects the order without partial state.

### Inventory

- Inventory can be listed.
- Inventory quantity can be updated through `PATCH`.
- Negative quantity is rejected.
- Unknown inventory IDs return `404 Not Found`.
- `PUT` and `DELETE` are not exposed by the inventory detail API.

## Setup

```bash
git clone https://github.com/ahmed-morsi-ai/CodeAlpha_RestaurantManagementSystem.git
cd CodeAlpha_RestaurantManagementSystem

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

The project uses SQLite and the Django development server.

## Testing

```bash
python manage.py check
python manage.py test restaurant
python manage.py test
python manage.py makemigrations --check --dry-run
```

Current verified baseline:

- 55/55 tests passing
- Django system check: clean
- Migration drift: none

No code coverage percentage is reported because coverage was not measured.

## Project Structure

```text
CodeAlpha_RestaurantManagementSystem/
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── restaurant/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── tests.py
│   ├── urls.py
│   ├── views.py
│   └── migrations/
├── .gitignore
├── manage.py
└── requirements.txt
```

## Known Development Limitations

- SQLite is used for the assignment and is not presented as production-grade high-contention inventory infrastructure.
- Current Django settings are development-oriented.
- Authentication and authorization are not implemented.
- Payment, notifications, reporting, dashboards, and frontend functionality are outside the current scope.
- No production deployment configuration is included.

## CodeAlpha Context

This repository implements **CodeAlpha Backend Development Task 3 — Restaurant Management System**.

It is an internship/assignment project and does not make claims about certification, employment, ranking, or production deployment.

## License

No license file is currently included in the repository.
