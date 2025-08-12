#!/bin/bash
# Fix permissions for mounted directories and start the application
if [ -d "/app/host-data" ]; then
    echo "Fixing permissions for /app/host-data"
    chown -R 1000:1000 /app/host-data
    chmod -R 755 /app/host-data
fi

# Switch to user 1000 and run the application
exec gosu 1000:1000 python main.py