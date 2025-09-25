# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container
COPY . .

# Command to run your Flask application
# Gunicorn is a production-ready web server for Python.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
