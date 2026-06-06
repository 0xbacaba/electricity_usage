#!/usr/bin/env bash

API="https://home.server.local/api"

source .env
if [ -z "$TOKEN" ]; then
  echo "Missing API Token (\$TOKEN)"
  exit 1
fi

ENTITY_IDS="sensor.stromzaehler_haus_total_energy_bought_1_8_0,sensor.stromzaehler_pv_total_energy_sold_2_8_0"
START_TIME="2026-05-03T00:00:00+02:00"

ENDPOINT="/history/period/$START_TIME?filter_entity_id=$ENTITY_IDS&minimal_response=true"

ENDPOINT_URL="$API$ENDPOINT"

echo "Fetching $ENDPOINT_URL..."

curl \
  -H "Authorization: Bearer $TOKEN" \
  -s \
  "$ENDPOINT_URL" \
  -o data.json
