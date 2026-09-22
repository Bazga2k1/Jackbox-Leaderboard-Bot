# Use a lightweight official Python image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your bot's code into the container
COPY . .

# Expose port 8080 for Render's Web Service health check
EXPOSE 8080

# Command to run the bot
CMD ["python", "-u", "bot.py"]