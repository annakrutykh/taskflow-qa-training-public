
# API_SPEC.md — целевая спецификация TaskFlow API

> Главный источник истины по контракту, ролям, кодам ошибок и схеме БД (CLAUDE.md, раздел 3).
> При расхождении фактического поведения API и этого документа прав документ — расхождение
> является дефектом и оформляется багрепортом (см. `docs/STUDENT_BUG_REPORTING.md`).
>
> Версия: v1 (соответствует состоянию на начало спринта S0, 2026-07-28).

---

## 1. Общие сведения

- Base URL: `http://localhost:8000`
- Префикс всех ручек: `/api/v1`, задаётся один раз через `APIRouter(prefix="/api/v1/...")`,
  без дублирования в декораторах эндпоинтов (CLAUDE.md, раздел 6).
- Swagger UI: `/docs`, OpenAPI-схема: `/openapi.json`.
- Формат тела запроса/ответа — JSON, `Content-Type: application/json`.

## 2. Аутентификация

- JWT, алгоритм `HS256`, секрет — `JWT_SECRET` из `.env`.
- Заголовок: `Authorization: Bearer <accessToken>`.
- `accessToken` выдаётся `POST /auth/login`, срок жизни — 8 часов, claim `sub` = `id` пользователя.
- Роль и статус (`is_active`) пользователя **не кэшируются в токене** — проверяются в БД на каждый
  запрос чтобы деактивация или смена роли действовали мгновенно, без необходимости
  перевыпускать токен.

### Правило разделения 401 / 403 / 404

| Ситуация | Код |
|---|---|
| Заголовок `Authorization` отсутствует | `401` |
| Токен невалиден, просрочен или подпись не совпадает | `401` |
| Пользователь по токену деактивирован (`is_active=false`) | `401` |
| Токен валиден, пользователь активен, но роли/владения недостаточно | `403` |
| Ресурс существует, но текущий пользователь не является его участником/владельцем | `404` (не `403` — чтобы не раскрывать факт существования ресурса чужому пользователю) |
| Ресурс не существует | `404` |

> Разделение 404 (не участник/не найдено) и 403 (участник, но роль недостаточна) введено
> вместе с `project_members`.

## 3. Ролевая модель

### Глобальные роли (`users.role`)

| Роль | Описание |
|---|---|
| `USER` | Обычный пользователь. Новый пользователь после `POST /auth/register` получает эту роль |
| `ADMIN` | Полный доступ к управлению пользователями и метками, полный доступ ко всем проектам и задачам, обходит проверку членства в `project_members` |

### Проектные роли (`project_members.role`)

| Роль | Права |
|---|---|
| `VIEWER` | Просмотр проекта, задач, участников. Комментирование |
| `MANAGER` | + полный CRUD задач, привязка меток |
| `OWNER` | + удаление проекта, управление составом участников и их ролями |

Владелец проекта (`projects.owner_id`) всегда имеет строку в `project_members` с ролью `OWNER` —
создаётся автоматически при `POST /projects`. У каждого проекта минимум один `OWNER` — это
инвариант, поддерживаемый на уровне API (`LAST_PROJECT_OWNER`, `409`).

### Доступ исполнителя (`Task.assignee_id`)

Пользователь, назначенный на задачу, но не являющийся участником её проекта, получает урезанный
доступ: просмотр задачи, смена `status`, комментирование — без прав на `title`/`description`/
`priority`/`rating`, удаление или управление метками. Не требует членства в проекте.

### Разрешение доступа к задаче (`app/permissions/projects.py`)

| Кто | Уровень доступа |
|---|---|
| `ADMIN` | Полный (как `MANAGER`) |
| Участник проекта, роль `OWNER`/`MANAGER` | Полный (`MANAGER`) |
| Участник проекта, роль `VIEWER` | Просмотр + комментарии |
| Исполнитель (`assignee_id`), не участник | Просмотр + `status` + комментарии |
| Ни то, ни другое | `404` (не раскрываем существование задачи) |

Модуль `app/permissions/` — единая точка правды для всех проверок доступа (CLAUDE.md, раздел 5).
Роутеры не дублируют эту логику.

### Soft delete 

`users`, `projects`, `tasks`, `comments` не удаляются физически — проставляется `deleted_at`.
Удалённая запись неотличима снаружи от несуществующей: `404` везде, где применимо. Удаление проекта
каскадно помечает его задачи и их комментарии. `email` пользователя освобождается для повторной
регистрации после удаления (частичный уникальный индекс `WHERE deleted_at IS NULL`). `labels` вне
scope soft delete — удаляются физически, каскад на `task_labels` через `ON DELETE CASCADE`.

## 4. Общие конвенции

| Правило | Значение |
|---|---|
| Именование полей | camelCase в запросах/ответах, snake_case в коде и БД |
| Списки | обёртка `{ "items": [...], "total": N, "limit": N, "offset": N, "hasNext": bool }` — реализовано в S2 (`Page[T]` в `app/schemas.py`) |
| Даты | ISO 8601, UTC, суффикс `Z` |
| Enum | строки в верхнем регистре (`TODO`, `HIGH`, `ADMIN`, ...) |
| Сортировка списков | всегда вторичный ключ `id ASC` для стабильности пагинации — реализовано в S2 |
| `201 Created` | обязателен заголовок `Location` с URL созданного ресурса |
| Пагинация | `limit` (1–100, по умолчанию 20), `offset` (≥0, по умолчанию 0) |

## 5. Формат ошибок

Единый формат тела ошибки (реализовано в S1, глобальным обработчиком исключений):

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Человекочитаемое описание",
    "details": null,
    "correlationId": "b3c1e2d4-...",
    "timestamp": "2026-07-28T12:56:40Z"
  }
}
```

`correlationId` совпадает со значением заголовка ответа `X-Request-ID`.

### Реестр `error.code`

| Код | HTTP статус | Когда |
|---|---|---|
| `VALIDATION_ERROR` | 422 | Ошибка валидации тела/параметров запроса |
| `UNAUTHORIZED` | 401 | Отсутствует, невалиден токен, либо пользователь деактивирован |
| `FORBIDDEN` | 403 | Недостаточно прав при валидном токене |
| `NOT_FOUND` | 404 | Ресурс не найден или пользователь не является его участником |
| `EMAIL_ALREADY_EXISTS` | 409 | Регистрация с уже существующим email |
| `INVALID_CREDENTIALS` | 401 | Неверный email/пароль на `/auth/login` |
| `LABEL_ALREADY_EXISTS` | 409 | Метка с таким именем уже существует |
| `UNKNOWN_SORT_FIELD` | 400 | Неизвестное значение параметра `sort` в `GET /tasks` |
| `MEMBER_ALREADY_EXISTS` | 409 | Пользователь уже участник проекта |
| `LAST_PROJECT_OWNER` | 409 | Попытка удалить/разжаловать последнего `OWNER` проекта |
| `TOO_MANY_REQUESTS` | 429 | Превышен лимит запросов на `/auth/login`/`/auth/register` |
| `INTERNAL_ERROR` | 500 | Необработанное исключение |

Новый код ошибки не вводится без добавления записи сюда (CLAUDE.md, раздел 6).

## 6. Ресурсы

### 6.1 Auth

| Метод | Путь | Авторизация | Успех | Ошибки |
|---|---|---|---|---|
| POST | `/auth/register` | нет | `201`, `Location: /api/v1/users/{id}` | `409 EMAIL_ALREADY_EXISTS`, `422 VALIDATION_ERROR`, `429 TOO_MANY_REQUESTS` |
| POST | `/auth/login` | нет | `200`, `{accessToken, tokenType}` | `401 INVALID_CREDENTIALS`, `422 VALIDATION_ERROR`, `429 TOO_MANY_REQUESTS` |
| POST | `/auth/logout` | любой авторизованный | `204` | `401` |

`POST /auth/register` body: `email, password (8–64), firstName (1–50), lastName (1–50)`.
Новый пользователь получает роль `USER`, `isActive=true`.

`POST /auth/login` body: `email, password`.

`POST /auth/logout` — отзывает текущий `accessToken` немедленно (через блэклист
в Redis с TTL до конца исходного срока действия токена, `jti`-claim). Тело не
требуется, токен берётся из заголовка `Authorization`.

#### Rate limiting

`POST /auth/login` и `POST /auth/register` ограничены по количеству запросов с
одного client IP (fixed window, реализация — `app/core/rate_limit.py`, счётчики
в Redis):

| Ручка | Лимит по умолчанию | Переменные окружения |
|---|---|---|
| `/auth/login` | 5 запросов / 60 секунд | `RATE_LIMIT_LOGIN_MAX_ATTEMPTS`, `RATE_LIMIT_LOGIN_WINDOW_SECONDS` |
| `/auth/register` | 10 запросов / 60 секунд | `RATE_LIMIT_REGISTER_MAX_ATTEMPTS`, `RATE_LIMIT_REGISTER_WINDOW_SECONDS` |

При превышении — `429 TOO_MANY_REQUESTS` с заголовком `Retry-After` (секунды до
сброса окна). Fail-open: если Redis недоступен, ограничение не применяется —
доступность входа важнее защиты от перебора.

### 6.2 Users

| Метод | Путь | Авторизация | Успех | Ошибки |
|---|---|---|---|---|
| GET | `/users/me` | любой авторизованный | `200 UserResponse` | `401` |
| PATCH | `/users/me` | любой авторизованный | `200 UserResponse` | `401`, `422` |
| GET | `/users` | `ADMIN` | `200`, список (пагинация) | `401`, `403` |
| GET | `/users/{id}` | `ADMIN` | `200 UserResponse` | `401`, `403`, `404` |
| PATCH | `/users/{id}/role` | `ADMIN` | `200 UserResponse` | `401`, `403`, `404`, `422` |
| PATCH | `/users/{id}/status` | `ADMIN` | `200 UserResponse` | `401`, `403`, `404`, `422` |
| DELETE | `/users/{id}` | `ADMIN` | `204`, soft delete | `401`, `403`, `404`, `409 LAST_PROJECT_OWNER` (последний `OWNER` проекта) |

`UserResponse`: `id, email, firstName, lastName, role, isActive`.

### 6.3 Projects

| Метод | Путь | Авторизация | Успех | Ошибки |
|---|---|---|---|---|
| POST | `/projects` | любой авторизованный | `201`, `Location: /api/v1/projects/{id}` — создатель становится `OWNER` | `401`, `422` |
| GET | `/projects` | любой авторизованный | `200`, проекты пользователя-участника (все — для `ADMIN`) | `401` |
| GET | `/projects/{id}` | участник любой роли или `ADMIN` | `200 ProjectResponse` | `401`, `404` |
| PATCH | `/projects/{id}` | `MANAGER+` или `ADMIN` | `200`, `name`/`description`/`status` | `401`, `403`, `404`, `422` |
| DELETE | `/projects/{id}` | `OWNER` или `ADMIN` | `204`, soft delete, каскад на задачи/комментарии | `401`, `403` (участник, но роль ниже `OWNER`), `404` (не участник/не найден) |
| POST | `/projects/{id}/members` | `OWNER` или `ADMIN` | `201`, `Location: .../members/{userId}` | `401`, `403`, `404` (проект/пользователь), `409 MEMBER_ALREADY_EXISTS` |
| GET | `/projects/{id}/members` | любой участник или `ADMIN` | `200`, список участников | `401`, `404` |
| PATCH | `/projects/{id}/members/{userId}` | `OWNER` или `ADMIN` | `200` | `401`, `403`, `404`, `409 LAST_PROJECT_OWNER` |
| DELETE | `/projects/{id}/members/{userId}` | `OWNER` или `ADMIN` | `204` | `401`, `403`, `404`, `409 LAST_PROJECT_OWNER` |

`ProjectCreate`: `name (1–100), description (опционально, ≤1000)`.
`ProjectUpdate`: любое подмножество `name (1–100), description (≤1000), status (ACTIVE|ARCHIVED)`.
`ProjectResponse`: `id, name, description, status, ownerId`.
`ProjectMemberCreate`: `userId, role (OWNER|MANAGER|VIEWER, default VIEWER)`.
`ProjectMemberResponse`: `userId, role`.

### 6.4 Tasks

| Метод | Путь | Авторизация | Успех | Ошибки |
|---|---|---|---|---|
| POST | `/tasks` | участник проекта `MANAGER+` или `ADMIN` | `201`, `Location: /api/v1/tasks/{id}` | `401`, `403`, `404` (проект/`assigneeId` не найден), `422` |
| GET | `/tasks` | любой авторизованный | `200`, задачи из проектов-участника + назначенные напрямую (все — для `ADMIN`) | `401`, `400 UNKNOWN_SORT_FIELD` |
| GET | `/tasks/{id}` | участник любой роли, исполнитель или `ADMIN` | `200 TaskResponse` | `401`, `404` |
| PATCH | `/tasks/{id}` | `MANAGER+`: любые поля. Исполнитель без членства: только `status` | `200 TaskResponse` | `401`, `403` (недостаточно прав на конкретное поле), `404`, `422` |
| DELETE | `/tasks/{id}` | участник `MANAGER+` или `ADMIN` | `204`, soft delete, каскад на комментарии | `401`, `403`, `404` |

Параметры `GET /tasks`: `limit, offset, status, priority, assigneeId, projectId, search, sort, order`.
`sort` ∈ `{createdAt, priority, rating, title, status}`, `order` ∈ `{asc, desc}`.

`TaskCreate`: `projectId, title (1–100), description (≤1000), priority (LOW|MEDIUM|HIGH, default MEDIUM), rating (1–5, опционально), assigneeId (опционально, должен существовать)`.
`TaskUpdate`: любое подмножество `title, description, status (TODO|IN_PROGRESS|DONE), priority, rating` — доступное подмножество зависит от роли вызывающего (см. выше).
`TaskResponse`: `id, projectId, assigneeId, title, description, status, priority, rating, labels: LabelResponse[]`.

### 6.5 Comments

| Метод | Путь | Авторизация | Успех | Ошибки |
|---|---|---|---|---|
| POST | `/tasks/{taskId}/comments` | доступ к задаче (участник любой роли, исполнитель, `ADMIN`) | `201` | `401`, `404`, `422` |
| GET | `/tasks/{taskId}/comments` | доступ к задаче | `200`, список | `401`, `404` |
| PATCH | `/tasks/{taskId}/comments/{id}` | только автор комментария | `200` | `401`, `403`, `404`, `422` |
| DELETE | `/tasks/{taskId}/comments/{id}` | автор либо участник `MANAGER+`/`ADMIN` (модерация) | `204`, soft delete | `401`, `403`, `404` |

`CommentCreate`/`CommentUpdate`: `text (1–500)`. Автор определяется по токену.
`CommentResponse`: `id, taskId, authorId, text`.

### 6.6 Labels

| Метод | Путь | Авторизация | Успех | Ошибки |
|---|---|---|---|---|
| POST | `/labels` | `ADMIN` | `201` | `401`, `403`, `409 LABEL_ALREADY_EXISTS`, `422` |
| GET | `/labels` | любой авторизованный | `200`, список | `401` |
| DELETE | `/labels/{id}` | `ADMIN` | `204`, физическое удаление, каскад на `task_labels` | `401`, `403`, `404` |
| POST | `/tasks/{taskId}/labels/{labelId}` | участник проекта `MANAGER+` или `ADMIN` | `204` | `401`, `403`, `404` |
| DELETE | `/tasks/{taskId}/labels/{labelId}` | участник проекта `MANAGER+` или `ADMIN` | `204`, идемпотентно | `401`, `403`, `404` (задача не найдена) |

`LabelCreate`: `name (1–30, уникально)`.
`LabelResponse`: `id, name`.

### 6.7 Admin

| Метод | Путь | Авторизация | Успех | Ошибки |
|---|---|---|---|---|
| POST | `/admin/reset` | `ADMIN` | `204`, полная очистка БД + повторный `seed_database()` | `401`, `403` |

Необратимо. `TRUNCATE ... RESTART IDENTITY CASCADE` по всем таблицам, включая `audit_log` — сбрасывает
и автоинкрементные ID, чтобы после сброса состояние совпадало со свежим `docker compose up`.

## 7. Схема БД

| Таблица | Ключевые поля | Ограничения |
|---|---|---|
| `users` | `id, email, password_hash, first_name, last_name, role, is_active, created_at, updated_at, deleted_at` | `role` — enum `USER/ADMIN`; `email` уникален только среди активных строк (частичный индекс `WHERE deleted_at IS NULL`) |
| `projects` | `id, name, description, status, owner_id → users.id, created_at, deleted_at` | FK `owner_id` |
| `project_members` | `project_id → projects.id (cascade), user_id → users.id (cascade), role, created_at` | составной PK `(project_id, user_id)`, индекс на `user_id`. `role` — enum `OWNER/MANAGER/VIEWER` |
| `tasks` | `id, project_id → projects.id (cascade), assignee_id → users.id, title, description, status, priority, rating, created_at, deleted_at` | `CHECK (rating between 1 and 5)` |
| `comments` | `id, task_id → tasks.id (cascade), author_id → users.id, text, created_at, deleted_at` | FK на `tasks`, `users` |
| `labels` | `id, name (unique)` | вне scope soft delete — удаляется физически |
| `task_labels` | `task_id → tasks.id (cascade), label_id → labels.id (cascade)` | составной PK, many-to-many `tasks` ↔ `labels` |
| `audit_log` | `id, user_id → users.id (nullable), action, entity_type, entity_id, details (JSON), created_at` | индексы на `user_id`, `action`. Не подлежит soft delete — неизменяемый лог |

Индексы на все внешние ключи и поля фильтрации/сортировки (`tasks.status`, `tasks.priority`,
`tasks.project_id`, `tasks.assignee_id`) — обязательны по правилу раздела 9 CLAUDE.md; добавляются
миграциями Alembic по мере перехода на них (спринт S0/S2).

`deleted_at IS NULL` — обязательное условие во всех выборках `users`/`projects`/`tasks`/`comments` по
первичному ключу и в списках; `Session.get()` для этих моделей не используется в бизнес-коде —
только `app.core.db_utils.get_active()`.

## 8. Тестирование

`tests/unit/` (без БД, permissions/errors), `tests/integration/` (реальный PostgreSQL — `db` из
`docker-compose.yml`, без testcontainers по причинам DooD-сети в этом окружении, см. `tests/conftest.py`),
`tests/e2e/` (полный пользовательский сценарий).

Три уровня прогона — smoke/integration/regression, что входит и сколько занимает —
`docs/TESTING.md` (команды `make smoke`/`make integration`/`make regression`).
Elasticsearch тестам не нужен (`ELASTICSEARCH_ENABLED=false` по умолчанию в
тестовом окружении).

`postman/TaskFlow.postman_collection.json` — ручное/обучающее тестирование всех ручек.

## 9. Связанные документы

- `API_DOCUMENTATION.md` — документация по API для студентов, описывает поведение «как есть» на момент
  последнего завершённого спринта.
- `docs/STUDENT_BUG_REPORTING.md` — как искать расхождения с этим документом и оформлять багрепорт.
- `docs/STUDENT_GIT_WORKFLOW.md` — рекомендуемый процесс работы с git в рамках курса.
- `docs/STUDENT_LOG_ANALYSIS.md` — работа с логами через Kibana и с Redis через redis-cli (необязательные инструменты).
