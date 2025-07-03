# REY PREMIUM VOGUE API Documentation

## Authentication
All API endpoints require authentication using JWT tokens.

### Obtaining a Token
```
POST /api/token/
{
    "email": "user@example.com",
    "password": "password"
}
```

## Endpoints

### Products

#### List Products
```
GET /api/products/
```

#### Product Detail
```
GET /api/products/{id}/
```

### Orders

#### Create Order
```
POST /api/orders/
{
    "shipping_address": {
        "first_name": "John",
        "last_name": "Doe",
        ...
    },
    "items": [
        {
            "product_id": 1,
            "quantity": 2,
            "size": "M",
            "color": "Black"
        }
    ]
}
```

### Newsletter

#### Subscribe
```
POST /api/newsletter/subscribe/
{
    "email": "user@example.com"
}
```

## Error Handling
All errors follow the format:
```json
{
    "success": false,
    "message": "Error description",
    "code": "ERROR_CODE"
}
``` 