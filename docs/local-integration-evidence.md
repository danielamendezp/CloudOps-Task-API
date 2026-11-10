# Local HTTP integration evidence

Executed: 2026-11-10T14:53:38.826359+00:00

Environment: Python + temporary SQLite database. No AWS deployment, Docker execution or external website check.

## Manually registered real-world asset

```json
{
  "id": "c3455821-2e81-4042-80d0-097b1bb81481",
  "kind": "asset",
  "created_at": "2026-11-10T14:53:38.893256+00:00",
  "name": "Dani WebWorks public website",
  "service": "Website",
  "project": "Dani WebWorks",
  "reference": "https://daniwebworks.com",
  "environment": "personal-business"
}
```

## Completed application verification

```json
{
  "id": "dcf8f32d-6769-4595-8797-60deb6b57d11",
  "kind": "task",
  "created_at": "2026-11-10T14:53:38.895700+00:00",
  "title": "Verify asset inventory survives a local process restart",
  "status": "done",
  "priority": "medium",
  "asset_id": "c3455821-2e81-4042-80d0-097b1bb81481",
  "updated_at": "2026-11-10T14:53:39.005549+00:00"
}
```

PASS: health, asset registration, linked task creation, list pagination, status updates, persistence across process restart.

The website availability task remains OPEN. No availability or security inspection of the website was performed.

This temporary test database was removed after verification. Run try_real_asset.ps1 against your running instance to keep your own records.
