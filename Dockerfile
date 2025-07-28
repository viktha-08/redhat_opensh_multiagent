# Step 1: Use the official Red Hat Python 3.9 UBI image as a base
#FROM registry.access.redhat.com/ubi9/python-39:1-117.1684741281
FROM python:3.11-slim

# Step 2: Set the working directory inside the container
WORKDIR /app

# Step 3: Copy the requirements file and install dependencies
COPY requirements.txt .


RUN pip install --no-cache-dir -r requirements.txt

# Step 4: Copy the rest of the application code
COPY . .


EXPOSE 8080
# Step 6: Command to run the application using gunicorn
# The user is already set by the base image
CMD ["python", "app.py"]