# NYC Civic ML Frontend

The frontend is a React, TypeScript, and Vite dashboard for NYC311-ML.

It displays:

* Summary statistics for complaints, resolution categories, boroughs, and agencies
* Resolution category, borough, agency, and top complaint-type charts
* Historical trend visualizations using Recharts
* Monthly sampled complaint-volume trends
* Monthly average resolution-time trends
* Machine learning model performance comparisons
* A prediction form backed by the FastAPI `/predict` endpoint

All dashboard data is loaded from the FastAPI backend. Analytics and trend data are not hardcoded in the frontend.

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
