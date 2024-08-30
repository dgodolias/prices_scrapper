# Use the official Python image from the Docker Hub
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install necessary packages including Chrome and WebDriver
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    gnupg2 \
    libgconf-2-4 \
    libxss1 \
    chromium \
    chromium-driver

# Upgrade pip and install Flask, Selenium, Requests, and Gunicorn
RUN pip install --upgrade pip && \
    pip install Flask Selenium requests gunicorn

# Copy the rest of the application code into the container
COPY . .

# Expose the port the app runs on
EXPOSE 5000

# Define environment variable
ENV FLASK_ENV=production

# Run the application with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
