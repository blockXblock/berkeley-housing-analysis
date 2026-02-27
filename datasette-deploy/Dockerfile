FROM python:3.12-slim

WORKDIR /app

# Copy files
COPY berkeley_housing_map.db .
COPY metadata.json .
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8080

# Run datasette
CMD ["datasette", "serve", "berkeley_housing_map.db", "--metadata", "metadata.json", "--host", "0.0.0.0", "--port", "8080", "--cors"]
