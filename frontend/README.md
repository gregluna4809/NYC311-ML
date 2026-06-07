# NYC Civic ML Frontend

## Environment

Local development uses `frontend/.env`:

```ini
VITE_API_BASE_URL=http://localhost:8001
```

For production deployments, set:

```ini
VITE_API_BASE_URL=https://nyc311.pulse-forge.com/api
```

In production, the frontend and backend containers run behind the shared external
Caddy reverse proxy on the Docker `edge` network. Do not publish the app
container ports directly to the host; Caddy should route public traffic to the
containers over `edge`.
