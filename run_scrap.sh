#!/bin/bash
# Random delay 0-2400s (~40 min) para evitar patrón predecible
DELAY=$((RANDOM % 2400))
echo "[$(date)] Waiting ${DELAY}s before scraping..."
sleep $DELAY

export JOBSCRAP_DSN="dbname=jobscrap user=jobscrap password=jobscrap_local host=localhost"

cd /var/www/jobscrap.alvar3z.nl
.venv/bin/python main.py >> scrap.log 2>&1
echo "[$(date)] Done"
