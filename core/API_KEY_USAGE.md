# API Key Authentication

This document explains how to get and use an API key from web UI.

## Obtaining an API Key

There are several ways to obtain an API key:

1. **Automatic Generation**: API keys are automatically generated when you use the web interface to search for news claims. The system will create an API key for your account if you don't already have one.

2. **User-Created Keys**: You can create your own API keys through the "My API Keys" page. This allows you to create multiple keys for different applications or services.

3. **Admin Creation**: Administrators can create API keys for users through the Django admin interface.

## Using an API Key

To use an API key, include it in the `X-API-Key` header of your requests:

```
X-API-Key: your-api-key
```

Example using curl:
```bash
curl -X POST \
  http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-api-key' \
  -d '{"body": "Your query text here"}'
```

When you use an API key, the system tracks its usage by updating the `last_used_at` timestamp in the database. This provides an audit trail of API key usage and helps identify inactive keys.

## Managing API Keys

### Web Interface

You can manage your API keys through the web interface:

1. **Viewing Keys**: Navigate to the "My API Keys" page to see all your API keys.
2. **Creating Keys**: Click the "Create New API Key" button to generate a new API key.
3. **Deleting Keys**: Click the "Delete" button next to an API key to remove it.

### API Endpoints

You can also manage your API keys programmatically:

#### Listing API Keys

To list all your API keys:

```
GET /api-keys
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

#### Deleting an API Key

To delete an API key:

```
DELETE /api-keys/{api_key_id}
```

Response:
```json
{
  "message": "API key deleted successfully"
}
```

## Security Considerations

- Keep your API keys secure and do not share them with others.
- API keys are stored securely in the database and cannot be retrieved after creation. If you lose your API key, you will need to create a new one.
- API keys do not expire, but they can be deactivated or deleted if needed.
- If you suspect that an API key has been compromised, delete it immediately and create a new one.
