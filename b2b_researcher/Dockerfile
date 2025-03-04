FROM python:3.11-slim

WORKDIR /app

# Copy requirements files first for better caching
COPY requirements.txt .
COPY agent-api/requirements.txt agent-api-requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt -r agent-api-requirements.txt

# Copy the project files
COPY . .

# Create b2b_researcher package structure
RUN mkdir -p /app/b2b_researcher
RUN cp -r /app/src/* /app/b2b_researcher/
RUN touch /app/b2b_researcher/__init__.py

# Install the main package
RUN pip install -e .

# Set the correct working directory for the API
WORKDIR /app/agent-api

# Install the API package
RUN pip install -e .

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "agent_api.main:app", "--host", "0.0.0.0", "--port", "8000"]