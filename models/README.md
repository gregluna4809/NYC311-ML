# Models

This directory stores the trained model artifact used by the FastAPI prediction endpoint.

## Current Artifact

```text
enhanced_xgboost_pipeline.joblib
```

The deployed backend loads this Joblib artifact at startup and uses it to serve `/predict` requests.

The selected model is the Enhanced XGBoost model described in the root README.
