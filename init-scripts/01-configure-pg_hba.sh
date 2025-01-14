#!/bin/bash

# Check if the pg_hba.conf already has the line
PG_HBA_FILE="/var/lib/postgresql/data/pg_hba.conf"
if ! grep -q "host all all 0.0.0.0/0 md5" "$PG_HBA_FILE"; then
  echo "host all all 0.0.0.0/0 md5" >> "$PG_HBA_FILE"
fi

# Ensure PostgreSQL listens on all addresses
POSTGRESQL_CONF="/var/lib/postgresql/data/postgresql.conf"
if ! grep -q "listen_addresses" "$POSTGRESQL_CONF"; then
  echo "listen_addresses = '*'" >> "$POSTGRESQL_CONF"
fi