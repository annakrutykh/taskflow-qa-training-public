import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Card,
  Modal,
  SkeletonRows,
  Table,
  useToast,
  type TableColumn,
} from "../../components";
import {
  addMember,
  deleteProject,
  getProject,
  listMembers,
  removeMember,
  updateMemberRole,
  updateProject,
} from "../../api/projects";
import { searchUsers } from "../../api/users";
import type { ProjectMember, ProjectRole, ProjectStatus, UserSearchResult } from "../../api/types";
import { ApiError } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { useFormValidation, type Validator } from "../../hooks/useFormValidation";
import { ROLE_LABEL, STATUS_LABEL } from "../../constants/labels";
import { TasksSection } from "./TasksSection";
import "../../styles/forms.css";
import "./ProjectDetail.css";

const ROLE_ORDER: Record<ProjectRole, number> = { ADMIN: 0, OWNER: 1, MANAGER: 2, VIEWER: 3 };

interface EditValues extends Record<string, string> {
  name: string;
  description: string;
  status: string;
}

const validateEdit: Validator<EditValues> = (values) => {
  const errors: Partial<Record<keyof EditValues, string>> = {};
  if (!values.name.trim()) errors.name = "Введите название";
  else if (values.name.trim().length > 100) errors.name = "Не длиннее 100 символов";
  if (values.description.length > 1000) errors.description = "Не длиннее 1000 символов";
  return errors;
};

type ConfirmTarget =
  | { kind: "delete-project" }
  | { kind: "remove-member"; userId: number };

export function ProjectDetail() {
  const { id } = useParams();
  const projectId = Number(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { user } = useAuth();

  const [editOpen, setEditOpen] = useState(false);
  const [addMemberOpen, setAddMemberOpen] = useState(false);
  const [newMemberRole, setNewMemberRole] = useState<ProjectRole>("VIEWER");
  const [confirmTarget, setConfirmTarget] = useState<ConfirmTarget | null>(null);

  const projectQuery = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => getProject(projectId),
  });

  const membersQuery = useQuery({
    queryKey: ["project-members", projectId],
    queryFn: () => listMembers(projectId, 100, 0),
  });

  const myRole: ProjectRole | "ADMIN" | undefined =
    user?.role === "ADMIN"
      ? "ADMIN"
      : membersQuery.data?.items.find((m) => m.userId === user?.id)?.role;
  const canManage = myRole === "ADMIN" || myRole === "OWNER" || myRole === "MANAGER";
  const canManageMembers = myRole === "ADMIN" || myRole === "OWNER";

  const [memberSearch, setMemberSearch] = useState("");
  const [debouncedMemberSearch, setDebouncedMemberSearch] = useState("");
  const [selectedUser, setSelectedUser] = useState<UserSearchResult | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedMemberSearch(memberSearch.trim()), 250);
    return () => clearTimeout(timer);
  }, [memberSearch]);

  // GET /users/search доступен любому авторизованному (в отличие от
  // полного GET /users, который ADMIN-only) — этого достаточно, чтобы
  // найти коллегу по имени/email при добавлении в проект.
  const userSearchQuery = useQuery({
    queryKey: ["users-search", debouncedMemberSearch],
    queryFn: () => searchUsers(debouncedMemberSearch),
    enabled: addMemberOpen && debouncedMemberSearch.length > 0,
  });
  const currentMemberIds = useMemo(
    () => new Set((membersQuery.data?.items ?? []).map((m) => m.userId)),
    [membersQuery.data],
  );
  // Владелец(-цы) всегда первыми — это тот, с кем чаще всего нужно
  // связаться/сверить права, не должен теряться среди наблюдателей.
  const sortedMembers = useMemo(
    () => [...(membersQuery.data?.items ?? [])].sort((a, b) => ROLE_ORDER[a.role] - ROLE_ORDER[b.role]),
    [membersQuery.data],
  );
  // Уже добавленных в проект не показываем — клик по ним всё равно
  // упрётся в 409 MEMBER_ALREADY_EXISTS.
  const filteredDirectory = useMemo(
    () => (userSearchQuery.data ?? []).filter((u) => !currentMemberIds.has(u.id)),
    [userSearchQuery.data, currentMemberIds],
  );

  const edit = useFormValidation<EditValues>({
    initialValues: {
      name: projectQuery.data?.name ?? "",
      description: projectQuery.data?.description ?? "",
      status: projectQuery.data?.status ?? "ACTIVE",
    },
    validate: validateEdit,
  });
  const editName = edit.fieldState("name");
  const editDescription = edit.fieldState("description");

  const updateMutation = useMutation({
    mutationFn: () =>
      updateProject(projectId, {
        name: edit.values.name.trim(),
        description: edit.values.description.trim() || undefined,
        status: edit.values.status as ProjectStatus,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setEditOpen(false);
      showToast("Проект обновлён", "success");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteProject(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      showToast("Проект удалён", "success");
      navigate("/", { replace: true });
    },
    onError: (error) => {
      showToast(error instanceof ApiError ? error.message : "Не удалось удалить проект", "error");
      setConfirmTarget(null);
    },
  });

  const addMemberMutation = useMutation({
    mutationFn: (userId: number) => addMember(projectId, userId, newMemberRole),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-members", projectId] });
      showToast("Участник добавлен", "success");
    },
    onError: (error) => {
      showToast(error instanceof ApiError ? error.message : "Не удалось добавить участника", "error");
    },
  });

  const roleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: number; role: ProjectRole }) =>
      updateMemberRole(projectId, userId, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-members", projectId] });
      showToast("Роль обновлена", "success");
    },
    onError: (error) => {
      showToast(error instanceof ApiError ? error.message : "Не удалось изменить роль", "error");
    },
  });

  const removeMemberMutation = useMutation({
    mutationFn: (userId: number) => removeMember(projectId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-members", projectId] });
      showToast("Участник удалён", "success");
      setConfirmTarget(null);
    },
    onError: (error) => {
      showToast(error instanceof ApiError ? error.message : "Не удалось удалить участника", "error");
      setConfirmTarget(null);
    },
  });

  function openEdit() {
    if (!projectQuery.data) return;
    edit.setField("name", projectQuery.data.name);
    edit.setField("description", projectQuery.data.description ?? "");
    edit.setField("status", projectQuery.data.status);
    setEditOpen(true);
  }

  function handleEditSubmit(e: FormEvent) {
    e.preventDefault();
    if (!edit.validateAll()) return;
    updateMutation.mutate();
  }

  function handlePickUser(pickedUser: UserSearchResult) {
    setSelectedUser(pickedUser);
    setMemberSearch("");
    setNewMemberRole(pickedUser.role === "ADMIN" ? "ADMIN" : "VIEWER");
  }

  function handleConfirmAddSelected() {
    if (!selectedUser) return;
    addMemberMutation.mutate(selectedUser.id, {
      onSuccess: () => closeAddMemberModal(),
    });
  }

  function closeAddMemberModal() {
    setAddMemberOpen(false);
    setNewMemberRole("VIEWER");
    setMemberSearch("");
    setSelectedUser(null);
  }

  const memberColumns: TableColumn<ProjectMember>[] = [
    {
      key: "userId",
      header: "Пользователь",
      render: (row) => (
        <>
          {row.firstName} {row.lastName}
          {row.userId === user?.id && <span className="member-you-badge">вы</span>}
        </>
      ),
    },
    {
      key: "role",
      header: "Роль",
      render: (row) =>
        // Роль ADMIN (глобальный админ, добавленный в проект) — не
        // редактируется: у него и так полный доступ, менять нечего.
        canManageMembers && row.role !== "ADMIN" ? (
          <select
            className="project-detail__role-select"
            value={row.role}
            disabled={roleMutation.isPending}
            onChange={(e) =>
              roleMutation.mutate({ userId: row.userId, role: e.target.value as ProjectRole })
            }
          >
            <option value="OWNER">Владелец</option>
            <option value="MANAGER">Менеджер</option>
            <option value="VIEWER">Наблюдатель</option>
          </select>
        ) : (
          <Badge variant="accent">{ROLE_LABEL[row.role]}</Badge>
        ),
      width: "200px",
    },
    ...(canManageMembers
      ? [
          {
            key: "actions",
            header: "",
            render: (row: ProjectMember) => (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setConfirmTarget({ kind: "remove-member", userId: row.userId })}
              >
                Удалить
              </Button>
            ),
            width: "100px",
          },
        ]
      : []),
  ];

  if (projectQuery.isLoading) {
    return (
      <div className="project-detail">
        <SkeletonRows count={4} height="2.5rem" />
      </div>
    );
  }

  if (projectQuery.isError || !projectQuery.data) {
    const notFound = projectQuery.error instanceof ApiError && projectQuery.error.status === 404;
    return (
      <div className="project-detail">
        <div className="project-detail__banner" role="alert">
          {notFound ? "Проект не найден или у вас нет к нему доступа." : "Не удалось загрузить проект."}
        </div>
        <Link className="project-detail__back" to="/">
          ← Ко всем проектам
        </Link>
      </div>
    );
  }

  const project = projectQuery.data;

  return (
    <div className="project-detail">
      <Link className="project-detail__back" to="/">
        ← Ко всем проектам
      </Link>

      <div className="project-detail__header">
        <div>
          <div className="project-detail__title">
            <h1>{project.name}</h1>
            <Badge variant={STATUS_LABEL[project.status].variant}>
              {STATUS_LABEL[project.status].label}
            </Badge>
          </div>
          {project.description && (
            <p className="project-detail__description">{project.description}</p>
          )}
        </div>
        {!membersQuery.isLoading && canManage && (
          <div className="project-detail__actions">
            <Button variant="secondary" size="sm" onClick={openEdit}>
              Редактировать
            </Button>
            {(myRole === "ADMIN" || myRole === "OWNER") && (
              <Button
                variant="danger"
                size="sm"
                onClick={() => setConfirmTarget({ kind: "delete-project" })}
              >
                Удалить
              </Button>
            )}
          </div>
        )}
      </div>

      <div className="project-detail__section">
        <div className="project-detail__section-header">
          <span className="project-detail__section-title">Участники</span>
          {canManageMembers && (
            <Button size="sm" onClick={() => setAddMemberOpen(true)}>
              Добавить участника
            </Button>
          )}
        </div>
        {membersQuery.isLoading ? (
          <Card>
            <SkeletonRows count={3} />
          </Card>
        ) : (
          <Table columns={memberColumns} rows={sortedMembers} getRowKey={(row) => row.userId} />
        )}
      </div>

      <TasksSection projectId={projectId} canManage={canManage} currentUserId={user?.id} />

      {/* Редактирование проекта */}
      <Modal
        open={editOpen}
        title="Редактировать проект"
        onClose={() => setEditOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setEditOpen(false)}>
              Отмена
            </Button>
            <Button type="submit" form="edit-project-form" loading={updateMutation.isPending}>
              Сохранить
            </Button>
          </>
        }
      >
        <form id="edit-project-form" onSubmit={handleEditSubmit} noValidate>
          {updateMutation.isError && (
            <div className="form-banner" role="alert">
              {updateMutation.error instanceof ApiError ? updateMutation.error.message : "Что-то пошло не так"}
            </div>
          )}
          <div className={`field${editName.error ? " field--invalid" : ""}`}>
            <label className="field__label" htmlFor="edit-name">
              Название
            </label>
            <div className="field__input-wrap">
              <input
                id="edit-name"
                className="field__input"
                value={editName.value}
                onChange={(e) => edit.setField("name", e.target.value)}
                onBlur={() => edit.blurField("name")}
              />
            </div>
            {editName.error && <span className="field__error">{editName.error}</span>}
          </div>
          <div className={`field${editDescription.error ? " field--invalid" : ""}`}>
            <label className="field__label" htmlFor="edit-description">
              Описание
            </label>
            <div className="field__input-wrap">
              <input
                id="edit-description"
                className="field__input"
                value={editDescription.value}
                onChange={(e) => edit.setField("description", e.target.value)}
                onBlur={() => edit.blurField("description")}
              />
            </div>
            {editDescription.error && <span className="field__error">{editDescription.error}</span>}
          </div>
          <div className="field">
            <label className="field__label" htmlFor="edit-status">
              Статус
            </label>
            <div className="field__input-wrap">
              <select
                id="edit-status"
                className="field__input"
                value={edit.values.status}
                onChange={(e) => edit.setField("status", e.target.value)}
              >
                <option value="ACTIVE">Активен</option>
                <option value="ARCHIVED">В архиве</option>
              </select>
            </div>
          </div>
        </form>
      </Modal>

      {/* Добавление участника */}
      <Modal
        open={addMemberOpen}
        title="Добавить участника"
        onClose={closeAddMemberModal}
        footer={
          <>
            <Button variant="secondary" onClick={closeAddMemberModal}>
              Отмена
            </Button>
            <Button
              onClick={handleConfirmAddSelected}
              disabled={!selectedUser}
              loading={addMemberMutation.isPending}
            >
              Добавить
            </Button>
          </>
        }
      >
        <div className="field">
          <label className="field__label" htmlFor="member-role">
            Роль для новых участников
          </label>
          {selectedUser?.role === "ADMIN" ? (
            <>
              <div className="field__input-wrap">
                <input className="field__input" value="Администратор" disabled readOnly />
              </div>
              <span className="field__hint">
                {selectedUser.firstName} {selectedUser.lastName} — администратор платформы, роль
                в проекте всегда «Администратор».
              </span>
            </>
          ) : (
            <div className="field__input-wrap">
              <select
                id="member-role"
                className="field__input"
                value={newMemberRole}
                onChange={(e) => setNewMemberRole(e.target.value as ProjectRole)}
              >
                <option value="VIEWER">Наблюдатель</option>
                <option value="MANAGER">Менеджер</option>
                <option value="OWNER">Владелец</option>
              </select>
            </div>
          )}
        </div>

        <div className="field">
          <label className="field__label" htmlFor="member-search">
            Пользователь
          </label>
          {selectedUser ? (
            <div className="member-picker__selected">
              <div>
                <span className="member-picker__name">
                  {selectedUser.firstName} {selectedUser.lastName}
                </span>
                <span className="member-picker__email">{selectedUser.email}</span>
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  setSelectedUser(null);
                  setNewMemberRole("VIEWER");
                }}
              >
                Изменить
              </Button>
            </div>
          ) : (
            <>
              <div className="field__input-wrap">
                <input
                  id="member-search"
                  className="field__input"
                  placeholder="Поиск по имени или email"
                  value={memberSearch}
                  onChange={(e) => setMemberSearch(e.target.value)}
                  autoFocus
                />
              </div>
              <div className="member-picker">
                {memberSearch.trim().length === 0 ? (
                  <div className="member-picker__empty">Начните вводить имя или email</div>
                ) : filteredDirectory.length === 0 ? (
                  <div className="member-picker__empty">
                    {userSearchQuery.isFetching ? "Ищем…" : "Никого не найдено"}
                  </div>
                ) : (
                  filteredDirectory.map((u) => (
                    <button
                      key={u.id}
                      type="button"
                      className="member-picker__item"
                      onClick={() => handlePickUser(u)}
                    >
                      <span className="member-picker__name">
                        {u.firstName} {u.lastName}
                      </span>
                      <span className="member-picker__email">{u.email}</span>
                    </button>
                  ))
                )}
              </div>
            </>
          )}
        </div>
      </Modal>

      {/* Подтверждение удаления */}
      <Modal
        open={confirmTarget !== null}
        title={confirmTarget?.kind === "delete-project" ? "Удалить проект?" : "Удалить участника?"}
        onClose={() => setConfirmTarget(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmTarget(null)}>
              Отмена
            </Button>
            <Button
              variant="danger"
              loading={deleteMutation.isPending || removeMemberMutation.isPending}
              onClick={() => {
                if (confirmTarget?.kind === "delete-project") deleteMutation.mutate();
                else if (confirmTarget?.kind === "remove-member") removeMemberMutation.mutate(confirmTarget.userId);
              }}
            >
              Удалить
            </Button>
          </>
        }
      >
        <p>
          {confirmTarget?.kind === "delete-project"
            ? "Проект и все его задачи будут помечены как удалённые. Это действие можно отменить только через прямой доступ к БД."
            : "Участник потеряет доступ к проекту."}
        </p>
      </Modal>
    </div>
  );
}
