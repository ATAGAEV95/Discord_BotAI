FROM python:3.13-slim
RUN pip install --upgrade pip
ENV PYTHONUNBUFFERED=1
WORKDIR /python-app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENTRYPOINT ["python", "main.py"]