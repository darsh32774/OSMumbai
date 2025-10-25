# Use the official Python image as a base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV APP_HOME /app

# Create and set the working directory
WORKDIR $APP_HOME

# Install dependencies (requests, uvicorn, fastapi, psycopg2, google-genai, python-dotenv, tabulate)
COPY requirements.txt .
# Install PostgreSQL client libraries needed for psycopg2
RUN apt-get update && apt-get install -y libpq-dev && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on. Render will handle the public port mapping.
EXPOSE 8000

# Command to run the application using Uvicorn. 
# Render automatically sets the PORT environment variable, so we use it here.
CMD ["uvicorn", "main_app_server:app", "--host", "0.0.0.0", "--port", "8000"]
