import enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class UserRole(enum.StrEnum):
    USER = "USER"
    ADMIN = "ADMIN"


class ProjectRole(enum.StrEnum):
    OWNER = "OWNER"
    MANAGER = "MANAGER"
    VIEWER = "VIEWER"


task_labels = Table(
    "task_labels",
    Base.metadata,
    Column(
        "task_id",
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "label_id",
        ForeignKey("labels.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Index("ix_task_labels_label_id", "label_id"),
)


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        Index(
            "ix_users_email_active_unique",
            "email",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id = Column(Integer, primary_key=True)

    # Не unique=True: уникальность только среди активных строк (см.
    # ix_users_email_active_unique ниже) — email освобождается после
    # soft delete (ADR-08).
    email = Column(String(255), nullable=False)

    password_hash = Column(String(255), nullable=False)

    first_name = Column(String(50), nullable=False)

    last_name = Column(String(50), nullable=False)

    role = Column(
        Enum(UserRole),
        default=UserRole.USER,
        nullable=False,
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    deleted_at = Column(DateTime(timezone=True), nullable=True)


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)

    name = Column(String(100), nullable=False)

    description = Column(String(1000))

    status = Column(
        String(20),
        default="ACTIVE",
        nullable=False,
    )

    owner_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    owner = relationship("User")
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    deleted_at = Column(DateTime(timezone=True), nullable=True)

    tasks = relationship(
        "Task",
        cascade="all, delete-orphan",
    )

    members = relationship(
        "ProjectMember",
        cascade="all, delete-orphan",
    )


class ProjectMember(Base):
    __tablename__ = "project_members"

    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    # lazy="joined" — участников проекта всегда показывают с именем
    # (ProjectMemberResponse), joined избегает N+1 при листинге.
    user = relationship("User", lazy="joined")

    role = Column(
        Enum(ProjectRole),
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    @property
    def first_name(self) -> str:
        return self.user.first_name

    @property
    def last_name(self) -> str:
        return self.user.last_name


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)

    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    assignee_id = Column(
        Integer,
        ForeignKey("users.id"),
        index=True,
    )

    title = Column(
        String(100),
        nullable=False,
    )

    description = Column(
        String(1000),
    )

    status = Column(
        String(20),
        default="TODO",
        nullable=False,
        index=True,
    )

    priority = Column(
        String(10),
        default="MEDIUM",
        nullable=False,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    deleted_at = Column(DateTime(timezone=True), nullable=True)

    comments = relationship(
        "Comment",
        cascade="all, delete-orphan",
    )

    labels = relationship(
        "Label",
        secondary=task_labels,
    )


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True)

    task_id = Column(
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    author_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    text = Column(
        String(500),
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    deleted_at = Column(DateTime(timezone=True), nullable=True)


class Label(Base):
    __tablename__ = "labels"

    id = Column(Integer, primary_key=True)

    name = Column(
        String(30),
        unique=True,
        nullable=False,
    )


class AuditLog(Base):
    """Журнал мутирующих действий (кто/что/когда). Не подлежит soft
    delete — исторический, неизменяемый лог."""

    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    action = Column(String(50), nullable=False, index=True)

    entity_type = Column(String(50), nullable=False)

    entity_id = Column(Integer, nullable=False)

    details = Column(JSON, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
