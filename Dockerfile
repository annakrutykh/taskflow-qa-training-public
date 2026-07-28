FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt requirements-dev.txt .
# requirements-dev (pytest/ruff/black) — в одном образе с прод-зависимостями.
# Это не "чистый" прод-образ, но это учебный проект без реального деплоя,
# а `docker run ... pytest` без "pip install" на каждый запуск — то, что
# реально сокращает цикл smoke-тестов до целевых 30-60с (docs/TESTING.md);
# отдельный test-образ добавил бы сложность без выгоды здесь.
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY . .
RUN chmod +x entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
