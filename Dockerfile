# Use an official Python runtime as the base image
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Copy app code
COPY . /app

# Copy the secrets.toml to the correct location
RUN mkdir -p /root/.streamlit
COPY secrets.toml /root/.streamlit/secrets.toml

# Copy requirement file and install others
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 8501 for the Streamlit app
EXPOSE 8501

# Command to run the Streamlit app
CMD ["streamlit", "run", "reorder-app.py", "--server.port=8501", "--server.address=0.0.0.0"]
