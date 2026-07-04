FROM python:3.12-slim
WORKDIR /app
# Install agent deps first
COPY ../agent/requirements.txt agent_requirements.txt
RUN pip install --no-cache-dir -r agent_requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ../agent /app/agent
COPY . .
CMD ["python", "main.py"]
