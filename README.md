# dimepi
Converting a Sound Leisure Dime Box controller to a Raspberry Pi powered Sonos controller

## Track admin frontend

The Docker Compose stack includes a small admin UI for editing the SQLite track database used by the main app.

- `dimepi-api` exposes CRUD endpoints for the `tracks` table and mounts the shared `database` volume at `/var/lib/dimepi`.
- `dimepi-frontend` serves the React app on port `8080` and proxies `/api` requests to `dimepi-api`.

Run the stack and open `http://localhost:8080`:

```sh
docker compose up --build
```

The API is also exposed directly on `http://localhost:8000` for debugging.
