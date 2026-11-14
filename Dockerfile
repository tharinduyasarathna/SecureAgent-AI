
FROM python:3.12-slim

WORKDIR /code

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/code

# Install all Python dependencies from root requirements.txt
COPY requirements.txt /code/requirements.txt

RUN python -m pip install --no-cache-dir -r requirements.txt

# Copy the application using the original project structure
COPY apps /code/apps

# Create a non-root user
RUN useradd --create-home appuser

USER appuser

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
