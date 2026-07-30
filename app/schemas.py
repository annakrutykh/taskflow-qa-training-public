from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(StrEnum):
    USER = "USER"
    ADMIN = "ADMIN"


class TaskStatus(StrEnum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"


class TaskPriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ProjectRole(StrEnum):
    OWNER = "OWNER"
    MANAGER = "MANAGER"
    VIEWER = "VIEWER"


class ProjectStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class Register(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)
    firstName: str = Field(min_length=1, max_length=50)
    lastName: str = Field(min_length=1, max_length=50)


class Login(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    firstName: str | None = Field(None, min_length=1, max_length=50)
    lastName: str | None = Field(None, min_length=1, max_length=50)


class UserRoleUpdate(BaseModel):
    role: UserRole


class UserStatusUpdate(BaseModel):
    is_active: bool = Field(alias="isActive")


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(None, max_length=1000)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    status: ProjectStatus | None = None


class ProjectMemberCreate(BaseModel):
    userId: int
    role: ProjectRole = ProjectRole.VIEWER


class ProjectMemberRoleUpdate(BaseModel):
    role: ProjectRole


class TaskCreate(BaseModel):
    projectId: int
    title: str = Field(min_length=1, max_length=100)
    description: str | None = Field(None, max_length=1000)
    priority: TaskPriority = TaskPriority.MEDIUM
    assigneeId: int | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
    )
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assignee_id: int | None = Field(default=None, alias="assigneeId")


class CommentCreate(BaseModel):
    text: str = Field(
        min_length=1,
        max_length=500,
    )


class CommentUpdate(BaseModel):
    text: str = Field(
        min_length=1,
        max_length=500,
    )


class LabelCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=30,
    )


# =========================
# Response models
# =========================

# Поле — snake_case (совпадает с атрибутом ORM-объекта, из которого модель
# заполняется через from_attributes), alias — camelCase (то, что реально
# уходит в JSON, т.к. FastAPI сериализует response_model с
# response_model_by_alias=True по умолчанию). populate_by_name=True
# дополнительно разрешает валидацию по имени поля — нужно там, где ответ
# строится из обычного dict, а не из ORM-объекта.


class UserResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id: int
    email: EmailStr
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    role: UserRole
    is_active: bool = Field(alias="isActive")


class UserSearchResult(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id: int
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    email: EmailStr


class TokenResponse(BaseModel):
    accessToken: str
    tokenType: str


class ProjectResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id: int
    name: str
    description: str | None = None
    status: ProjectStatus
    owner_id: int = Field(alias="ownerId")


class ProjectMemberResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    user_id: int = Field(alias="userId")
    role: ProjectRole
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")


class LabelResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id: int
    name: str


class TaskResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id: int
    project_id: int = Field(alias="projectId")
    assignee_id: int | None = Field(default=None, alias="assigneeId")
    assignee_first_name: str | None = Field(default=None, alias="assigneeFirstName")
    assignee_last_name: str | None = Field(default=None, alias="assigneeLastName")

    title: str
    description: str | None = None
    status: TaskStatus
    priority: TaskPriority
    labels: list[LabelResponse] = []
    comments_count: int = Field(default=0, alias="commentsCount")


class CommentResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id: int
    task_id: int = Field(alias="taskId")
    author_id: int = Field(alias="authorId")
    author_first_name: str = Field(alias="authorFirstName")
    author_last_name: str = Field(alias="authorLastName")
    text: str


class Page[T](BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[T]
    total: int
    limit: int
    offset: int
    has_next: bool = Field(alias="hasNext")
