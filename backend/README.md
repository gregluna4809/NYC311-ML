# NYC Civic ML Backend

The backend is a FastAPI service that exposes NYC 311 analytics, metadata, and machine learning prediction endpoints.

## Implemented Endpoints

### Health

```http
GET /health
```

### Analytics

```http
GET /analytics/categories
GET /analytics/boroughs
GET /analytics/agencies
GET /analytics/top-complaints
GET /analytics/trends/volume
GET /analytics/trends/resolution
```

The trend endpoints provide monthly complaint-volume analytics and monthly average resolution-time analytics from PostgreSQL.

### Metadata

```http
GET /metadata/complaint-types
```

### Prediction

```http
POST /predict
```

The prediction endpoint serves the deployed Enhanced XGBoost model and returns a predicted resolution category with a confidence score.
