# syntax=docker/dockerfile:1

# Start from the official Python 3.12 slim image
FROM python:3.12-slim

# Install the project with FastAPI extras
WORKDIR /app

# Copy only the necessary files to leverage Docker layer caching
COPY pyproject.toml README.md ./
COPY leropa ./leropa

# Install dependencies and the package itself with FastAPI extras
RUN pip install --no-cache-dir .[fastapi]

# Expose the port the app runs on
EXPOSE 8000

# Run the FastAPI application with uvicorn
CMD ["uvicorn", "leropa.web:app", "--host", "0.0.0.0", "--port", "8000"]
