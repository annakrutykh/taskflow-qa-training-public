from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.models import (
    Comment,
    Label,
    Project,
    ProjectMember,
    ProjectRole,
    Task,
    User,
    UserRole,
)

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def seed_database(db: Session):
    """
    Заполняет БД начальными данными.
    Если пользователи уже существуют — ничего не делает.
    """

    if db.query(User).first():
        return

    # ---------- Пользователи ----------

    admin = User(
        email="admin@example.com",
        password_hash=pwd.hash("Admin123!"),
        first_name="System",
        last_name="Administrator",
        role=UserRole.ADMIN,
        is_active=True,
    )

    user1 = User(
        email="ivan@example.com",
        password_hash=pwd.hash("User123!"),
        first_name="Иван",
        last_name="Иванов",
        role=UserRole.USER,
        is_active=True,
    )

    user2 = User(
        email="anna@example.com",
        password_hash=pwd.hash("User123!"),
        first_name="Анна",
        last_name="Петрова",
        role=UserRole.USER,
        is_active=True,
    )

    user3 = User(
        email="alex@example.com",
        password_hash=pwd.hash("User123!"),
        first_name="Алексей",
        last_name="Сидоров",
        role=UserRole.USER,
        is_active=True,
    )

    user4 = User(
        email="kate@example.com",
        password_hash=pwd.hash("User123!"),
        first_name="Екатерина",
        last_name="Орлова",
        role=UserRole.USER,
        is_active=True,
    )

    user5 = User(
        email="dmitry@example.com",
        password_hash=pwd.hash("User123!"),
        first_name="Дмитрий",
        last_name="Соколов",
        role=UserRole.USER,
        is_active=True,
    )

    # намеренно неактивен — для проверки сценария деактивации/логина
    user6 = User(
        email="olga@example.com",
        password_hash=pwd.hash("User123!"),
        first_name="Ольга",
        last_name="Смирнова",
        role=UserRole.USER,
        is_active=False,
    )

    db.add_all([admin, user1, user2, user3, user4, user5, user6])
    db.commit()

    users = db.query(User).all()

    # ---------- Проекты ----------

    project1 = Project(
        name="TaskFlow Backend",
        description="Разработка backend сервиса",
        owner_id=users[0].id,
    )

    project2 = Project(
        name="Mobile Banking",
        description="Мобильное банковское приложение",
        owner_id=users[1].id,
    )

    project3 = Project(
        name="CRM System",
        description="CRM для отдела продаж",
        owner_id=users[2].id,
    )

    project4 = Project(
        name="Online Store",
        description="Интернет-магазин",
        owner_id=users[3].id,
    )

    db.add_all([project1, project2, project3, project4])
    db.commit()

    projects = db.query(Project).all()

    # ---------- Участники проектов ----------
    # Владелец каждого проекта — участник с ролью OWNER (тот же инвариант,
    # что и в POST /projects). Плюс демонстрация всех трёх ролей и доступа
    # исполнителя без членства (task3/task4/task6 — assignee не участник).

    memberships = [
        ProjectMember(
            project_id=project1.id, user_id=users[0].id, role=ProjectRole.OWNER
        ),
        ProjectMember(
            project_id=project2.id, user_id=users[1].id, role=ProjectRole.OWNER
        ),
        ProjectMember(
            project_id=project3.id, user_id=users[2].id, role=ProjectRole.OWNER
        ),
        ProjectMember(
            project_id=project4.id, user_id=users[3].id, role=ProjectRole.OWNER
        ),
        ProjectMember(
            project_id=project1.id, user_id=users[1].id, role=ProjectRole.MANAGER
        ),
        ProjectMember(
            project_id=project1.id, user_id=users[2].id, role=ProjectRole.VIEWER
        ),
        ProjectMember(
            project_id=project2.id, user_id=users[4].id, role=ProjectRole.VIEWER
        ),
    ]

    db.add_all(memberships)
    db.commit()

    # ---------- Метки ----------

    labels = [
        Label(name="backend"),
        Label(name="frontend"),
        Label(name="mobile"),
        Label(name="bug"),
        Label(name="feature"),
        Label(name="urgent"),
    ]

    db.add_all(labels)
    db.commit()

    labels = db.query(Label).all()

    # ---------- Задачи ----------
    # Намеренно покрывает все статусы (TODO/IN_PROGRESS/DONE), все
    # приоритеты (LOW/MEDIUM/HIGH), задачи без исполнителя и без рейтинга.

    task1 = Task(
        project_id=projects[0].id,
        assignee_id=users[1].id,
        title="Создать регистрацию",
        description="Добавить регистрацию пользователей",
        priority="HIGH",
        status="TODO",
        rating=5,
    )

    task2 = Task(
        project_id=projects[0].id,
        assignee_id=users[2].id,
        title="JWT авторизация",
        description="Реализовать вход по JWT",
        priority="HIGH",
        status="IN_PROGRESS",
        rating=4,
    )

    task3 = Task(
        project_id=projects[1].id,
        assignee_id=users[3].id,
        title="Push-уведомления",
        description="Настроить Firebase",
        priority="MEDIUM",
        status="DONE",
        rating=5,
    )

    task4 = Task(
        project_id=projects[2].id,
        assignee_id=users[4].id,
        title="Импорт клиентов",
        description="Добавить импорт базы клиентов",
        priority="LOW",
        status="TODO",
        rating=3,
    )

    task5 = Task(
        project_id=projects[0].id,
        assignee_id=None,
        title="Настроить CI",
        description="Прогон линтера и тестов на пуш",
        priority="LOW",
        status="TODO",
        rating=None,
    )

    task6 = Task(
        project_id=projects[1].id,
        assignee_id=users[5].id,
        title="Двухфакторная аутентификация",
        description="Добавить 2FA для входа в приложение",
        priority="MEDIUM",
        status="IN_PROGRESS",
        rating=None,
    )

    task7 = Task(
        project_id=projects[3].id,
        assignee_id=users[3].id,
        title="Корзина покупок",
        description="Реализовать сохранение корзины между сессиями",
        priority="HIGH",
        status="DONE",
        rating=4,
    )

    db.add_all([task1, task2, task3, task4, task5, task6, task7])
    db.commit()

    tasks = db.query(Task).all()

    # ---------- Комментарии ----------

    comments = [
        Comment(
            task_id=tasks[0].id,
            author_id=users[0].id,
            text="Начинаем разработку.",
        ),
        Comment(
            task_id=tasks[0].id,
            author_id=users[1].id,
            text="Работа уже ведётся.",
        ),
        Comment(
            task_id=tasks[1].id,
            author_id=users[2].id,
            text="JWT реализован.",
        ),
        Comment(
            task_id=tasks[5].id,
            author_id=users[5].id,
            text="Нужно выбрать провайдера OTP.",
        ),
        Comment(
            task_id=tasks[6].id,
            author_id=users[3].id,
            text="Готово, покрыто тестами.",
        ),
    ]

    db.add_all(comments)

    # ---------- Метки задач ----------

    task1.labels.extend([labels[0], labels[4]])
    task2.labels.extend([labels[0], labels[5]])
    task3.labels.extend([labels[2]])
    task4.labels.extend([labels[3]])
    task6.labels.extend([labels[0], labels[2]])
    task7.labels.extend([labels[1], labels[4]])

    db.commit()
