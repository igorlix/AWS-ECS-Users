FROM python:3.11-slim

# Update the package list and install necessary dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make data loader executable
RUN chmod +x data_loader.py

EXPOSE 9001

# Create startup script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "Starting Authors API..."\n\
\n\
# Wait for database to be ready\n\
echo "Waiting for database to be ready..."\n\
sleep 10\n\
\n\
# Load initial data if needed\n\
if [ "$LOAD_INITIAL_DATA" = "true" ]; then\n\
    echo "Loading initial data from CSV..."\n\
    python data_loader.py --force || echo "Warning: Failed to load initial data"\n\
fi\n\
\n\
# Start the API\n\
echo "Starting FastAPI server..."\n\
exec uvicorn main:app --host 0.0.0.0 --port 9001\n\
' > /app/start.sh && chmod +x /app/start.sh

CMD ["/app/start.sh"]