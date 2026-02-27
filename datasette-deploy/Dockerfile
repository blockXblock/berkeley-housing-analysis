FROM python:3.12-slim

WORKDIR /app

# Copy files
COPY berkeley_housing_map.db .
COPY berkeley_address_centric.db .
COPY metadata.json .
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8080

# Run datasette with both databases
CMD ["datasette", "serve", "berkeley_housing_map.db", "berkeley_address_centric.db", "--metadata", "metadata.json", "--host", "0.0.0.0", "--port", "8080", "--cors"]
