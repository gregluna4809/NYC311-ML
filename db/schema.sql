CREATE TABLE raw_311_requests (
    unique_key BIGINT PRIMARY KEY,
    created_date TIMESTAMP,
    closed_date TIMESTAMP,
    agency VARCHAR(50),
    agency_name VARCHAR(255),
    complaint_type VARCHAR(255),
    descriptor TEXT,
    location_type VARCHAR(255),
    incident_zip VARCHAR(10),
    borough VARCHAR(50),
    latitude NUMERIC(10,6),
    longitude NUMERIC(10,6),
    status VARCHAR(50),
    resolution_description TEXT,
    raw_json JSONB,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_raw_311_requests_created_date
    ON raw_311_requests (created_date);

CREATE INDEX idx_raw_311_requests_complaint_type
    ON raw_311_requests (complaint_type);

CREATE INDEX idx_raw_311_requests_borough
    ON raw_311_requests (borough);

CREATE INDEX idx_raw_311_requests_agency
    ON raw_311_requests (agency);

CREATE INDEX idx_raw_311_requests_incident_zip
    ON raw_311_requests (incident_zip);

CREATE INDEX idx_raw_311_requests_status
    ON raw_311_requests (status);
