# Architecture

## Overview

NYC311-ML is a full-stack analytics and machine learning application built using real NYC Open Data.

The project starts by downloading NYC 311 service request data, cleaning and processing it, storing it in PostgreSQL, and then exposing analytics and machine learning predictions through a FastAPI backend and React frontend.

The goal was not just to train a model, but to build a complete application around the data.

---

## How the System Works

```text
NYC Open Data
       ↓
Python ETL
       ↓
Data Cleaning
       ↓
PostgreSQL
       ↓
FastAPI
       ↓
React Dashboard
       ↓
XGBoost Predictions
```

The application follows a fairly straightforward workflow.

Data is downloaded from NYC Open Data and processed through a series of Python scripts. After cleaning and feature engineering, the records are loaded into PostgreSQL.

The FastAPI backend reads from PostgreSQL and exposes analytics endpoints that the React frontend consumes.

Machine learning predictions are generated using a trained XGBoost model that is loaded when the API starts.

---

## Data Pipeline

The project begins with raw NYC 311 service request data.

Several processing steps are applied:

* Download data from NYC Open Data
* Profile the dataset
* Identify missing values and outliers
* Calculate resolution times
* Create resolution categories
* Generate machine learning features

The cleaned dataset is then loaded into PostgreSQL.

This allows both SQL analysis and machine learning workflows to use the same source of truth.

---

## Database Layer

PostgreSQL serves as the application's primary datastore.

The database stores:

* Complaint information
* Agencies
* Boroughs
* Resolution times
* Resolution categories

Using PostgreSQL made it possible to perform analytics directly in SQL while also providing data to the API layer.

---

## API Layer

The backend is built with FastAPI.

It provides endpoints for:

* Health checks
* Analytics
* Metadata
* Machine learning predictions

The API acts as the bridge between PostgreSQL and the frontend.

Rather than allowing the frontend to communicate directly with the database, all requests pass through the API.

---

## Frontend

The frontend is built using React, TypeScript, and Vite.

It provides:

* Analytics dashboard
* Charts
* Summary statistics
* Prediction interface

All displayed data comes from the FastAPI backend.

No analytics are hardcoded into the UI.

---

## Machine Learning

The project uses several machine learning models to predict complaint resolution categories.

Models evaluated:

* Logistic Regression
* XGBoost
* Enhanced XGBoost

The Enhanced XGBoost model achieved the best performance and was selected for deployment.

The trained model is saved using Joblib and loaded by FastAPI during startup.

Predictions are served through the `/predict` endpoint.

---

## Deployment

The application is containerized using Docker.

The deployment stack includes:

* Frontend container
* Backend container
* PostgreSQL container

Docker Compose is used to run the complete application locally and provides a straightforward path to cloud deployment.

---

## Future Improvements

There are several directions this project could grow:

* Automated data refresh jobs
* Geospatial analysis and mapping
* Time-series forecasting
* Managed cloud deployment
* User authentication
* Additional machine learning features

The current version focuses on demonstrating the complete analytics workflow from raw data to deployed prediction service.
