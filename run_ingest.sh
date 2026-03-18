#!/bin/bash
# Navigate to the project directory
cd /mnt/volume_nyc3_01/agents/ssh_armorer/

# Load environment variables
source .env

# Run the ingestion script
python3 ingest_memory.py >> /var/log/factory_ingest.log 2>&1