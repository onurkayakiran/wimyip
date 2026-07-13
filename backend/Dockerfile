FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Celery/uvicorn root olarak calismasin diye ayri, ayricaliksiz bir kullanici.
# /app'in sahipligini de appuser'a veriyoruz - aksi halde celery beat kendi
# zamanlama durumunu (celerybeat-schedule) buraya yazamaz ve surekli
# "Permission denied" ile coker (bu, root=appuser gecisinde yasandi).
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
