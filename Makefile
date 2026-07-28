# Тестовая стратегия — три уровня, подробности в docs/TESTING.md.
# make smoke        — после каждого небольшого изменения (~10с)
# make integration  — перед пушем/PR (~40с)
# make regression   — перед релизом/после крупных изменений (~40с, включает e2e)

NETWORK := taskflow-main_default
IMAGE := taskflow-main-api

DOCKER_RUN := docker run --rm -v "$(CURDIR):/app" -w /app --network $(NETWORK) \
	-e DATABASE_URL=postgresql://taskflow:taskflow@db:5432/taskflow \
	-e REDIS_URL=redis://redis:6379/0 \
	-e ELASTICSEARCH_ENABLED=false \
	$(IMAGE)

.PHONY: help test-services lint smoke integration regression test-down

help:
	@echo "make lint         — ruff + black --check"
	@echo "make smoke        — быстрый набор ~49 тестов (~10с) — после каждого изменения"
	@echo "make integration  — unit + integration, без e2e (~40с) — перед пушем/PR"
	@echo "make regression   — весь набор, включая e2e (~40с) — перед релизом"
	@echo "make test-down    — остановить тестовые db/redis"
	@echo "Подробности и время выполнения — docs/TESTING.md"

# db/redis нужны для любого варианта тестов, кроме tests/unit в изоляции.
# Elasticsearch тестам не нужен (ELASTICSEARCH_ENABLED=false) — см.
# tests/conftest.py и docs/TESTING.md.
test-services:
	@docker compose up -d db redis
	@docker compose build api -q

lint: test-services
	$(DOCKER_RUN) sh -c "ruff check app tests && black --check app tests"

smoke: test-services
	$(DOCKER_RUN) sh -c "pytest -m smoke -q"

integration: test-services
	$(DOCKER_RUN) sh -c "pytest tests/unit tests/integration -q"

regression: test-services
	$(DOCKER_RUN) sh -c "pytest -q"

test-down:
	docker compose stop db redis
