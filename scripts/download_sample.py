import json
from pathlib import Path

import requests


ENDPOINT = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
PARAMS = {
    "$limit": 5000,
    "$select": "unique_key,created_date,closed_date,agency,complaint_type,borough,status",
}
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "311_sample.json"
TIMEOUT_SECONDS = 120


def main() -> None:
    try:
        response = requests.get(ENDPOINT, params=PARAMS, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        records = response.json()
    except requests.exceptions.RequestException as exc:
        raise SystemExit(f"Download failed: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON response: {exc}") from exc

    if not isinstance(records, list):
        raise SystemExit("Unexpected response format: expected a list of records.")

    with OUTPUT_PATH.open("w", encoding="utf-8") as output_file:
        json.dump(records, output_file, indent=2)

    print(f"Downloaded {len(records)} records to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
