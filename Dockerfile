# Use the official Python image from the Docker Hub
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Upgrade pip and install Flask, Selenium, and Requests
RUN pip install --upgrade pip && \
    pip install Flask Selenium requests

# Copy the rest of the application code into the container
COPY . .

# Expose the port the app runs on
EXPOSE 5000

# Define environment variable
ENV FLASK_ENV=production

# Run the application
CMD ["python", "app.py"]
