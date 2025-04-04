# API Key Authentication

This document explains how to get and use an API key for the NewsAgent API.

## Obtaining an API Key

There are several ways to obtain an API key:

1. **Automatic Generation**: API keys are automatically generated when you use the web interface to search for news claims. The system will create an API key for your account if you don't already have one.

2. **User-Created Keys**: You can create your own API keys through the "API Keys" page. This allows you to create multiple keys for different applications or services.

3. **Admin Creation**: Administrators can create API keys for users through the Django admin interface.

## Using an API Key

To use an API key, include it in the `X-API-Key` header of your requests:

```
X-API-Key: your-api-key
```

Example using curl:
```bash
curl -X POST \
  http://localhost:8001/query \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-api-key' \
  -d '{"body": "Your query text here"}'
```

When you use an API key, the system tracks its usage by updating the `last_used_at` timestamp in the database. This provides an audit trail of API key usage and helps identify inactive keys.

## Rate Limiting

To ensure fair usage of the API, rate limiting is enforced on the `/query` endpoint:

- **Limit**: 10 requests per minute per API key
- **Reset**: The rate limit window resets 60 seconds after your first request in the current window
- **Headers**: The API includes rate limit information in the response headers:
  - `X-Rate-Limit-Limit`: The maximum number of requests allowed per minute
  - `X-Rate-Limit-Remaining`: The number of requests remaining in the current window

If you exceed the rate limit, the API will return a `429 Too Many Requests` response with the following body:

```json
{
  "detail": "Rate limit exceeded. Try again in X seconds.",
  "rate_limit": {
    "limit": 2,
    "remaining": 0,
    "reset_after_seconds": X
  }
}
```

Where `X` is the number of seconds until the rate limit resets.

Note: This rate limit is currently set to 2 requests per minute for testing purposes and may be adjusted in the future.

## Managing API Keys

### Web Interface

You can manage your API keys through the web interface:

1. **Viewing Keys**: Navigate to the "API Keys" page to see all your API keys.
2. **Creating Keys**: Click the "Create New API Key" button to generate a new API key.
3. **Deleting Keys**: Click the "Delete" button next to an API key to remove it.

**Note**: There is a limit of 3 API keys per user account. If you need to create a new API key but have reached the limit, you must delete an existing key first.

### API Endpoints

You can also manage your API keys programmatically:

#### Creating API Keys

To create a new API key:

```
POST http://localhost:8001/api-keys
```

Request body:
```json
{
  "name": "My New API Key"
}
```

Example using curl:
```bash
curl -X POST \
  http://localhost:8001/api-keys \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-existing-api-key' \
  -d '{"name": "My New API Key"}'
```

Response:
```json
{
  "id": 2,
  "name": "My New API Key",
  "key": "generated-api-key",
  "created_at": "2023-01-03T00:00:00.000Z",
  "last_used_at": null,
  "is_active": true
}
```

Error response (when limit is reached):
```json
{
  "detail": "You can only have a maximum of 3 API keys per account."
}
```

Note: This endpoint requires authentication with an existing API key. You must include your existing API key in the `X-API-Key` header. There is a limit of 3 API keys per user account.

#### Listing API Keys

To list all your API keys:

```
GET http://localhost:8001/api-keys
```

Example using curl:
```bash
curl -X GET \
  http://localhost:8001/api-keys \
  -H 'X-API-Key: your-existing-api-key'
```

Response:
```json
[
  {
    "id": 1,
    "name": "My API Key",
    "key": "your-api-key",
    "created_at": "2023-01-01T00:00:00.000Z",
    "last_used_at": "2023-01-02T00:00:00.000Z",
    "is_active": true
  }
]
```

Note: This endpoint requires authentication with an existing API key.

#### Deleting an API Key

To delete an API key:

```
DELETE http://localhost:8001/api-keys/{api_key_id}
```

Example using curl:
```bash
curl -X DELETE \
  http://localhost:8001/api-keys/<id> \
  -H 'X-API-Key: your-existing-api-key'
```

Response:
```json
{
  "message": "API key deleted successfully"
}
```

Note: This endpoint requires authentication with an existing API key. Replace `{api_key_id}` with the ID of the API key you want to delete.

## Security Considerations

- Keep your API keys secure and do not share them with others.
- API keys are stored securely in the database and cannot be retrieved after creation. If you lose your API key, you will need to create a new one.
- API keys do not expire, but they can be deactivated or deleted if needed.
- If you suspect that an API key has been compromised, delete it immediately and create a new one.
