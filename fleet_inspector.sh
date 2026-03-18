#!/bin/bash

# Fleet Inspector - Server Status Checker
# Updates /root/HEARTBEAT.md with current fleet status
# Uses SSH port check (port 22) instead of ping

HEARTBEAT_FILE="/root/HEARTBEAT.md"
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")

# Function to check server status via SSH port
check_server() {
    local name=$1
    local host=$2

    if nc -zv -w 2 "$host" 22 2>&1 | grep -q "succeeded"; then
        echo "$name: UP"
    else
        echo "$name: DOWN"
    fi
}

# Generate heartbeat report
cat << 'EOF' > "$HEARTBEAT_FILE"
# 100-App Factory Fleet Status
Last Updated: TIMESTAMP

## Server Status
EOF

# Replace timestamp placeholder
sed -i "s/TIMESTAMP/$TIMESTAMP/" "$HEARTBEAT_FILE"

check_server "TheController" "localhost" >> "$HEARTBEAT_FILE"
check_server "Moonbot2" "165.245.132.82" >> "$HEARTBEAT_FILE"
check_server "Factory Floor" "165.245.134.252" >> "$HEARTBEAT_FILE"
check_server "Klume-Dev-Server" "165.245.128.251" >> "$HEARTBEAT_FILE"

echo "✅ Fleet status updated at $TIMESTAMP"
