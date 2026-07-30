import { useEffect, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  EmptyState,
  Modal,
  SkeletonRows,
  Table,
  useToast,
  type TableColumn,
} from "../../components";
import { createTask, deleteTask, listTasks, updateTask } from "../../api/tasks";
import { attachLabel, detachLabel, listLabels } from "../../api/labels";
import { searchUsers } from "../../api/users";
import type { Task, TaskPriority, TaskStatus } from "../../api/types";
import { ApiError } from "../../api/client";
import { useFormValidation, type Validator } from "../../hooks/useFormValidation";
import { TASK_PRIORITY_LABEL, TASK_STATUS_LABEL } from "../../constants/labels";
import { TaskDetailModal } from "./TaskDetailModal";
import "../../styles/forms.css";
import "./TasksSection.css";

const PAGE_SIZE = 20;

interface TaskFormValues extends Record<string, string> {
  title: string;
  description: string;
  priority: string;
}

interface SelectedAssignee {
  id: number;
  firstName: string;
  lastName: string;
}

const validateTask: Validator<TaskFormValues> = (values) => {
  const errors: Partial<Record<keyof TaskFormValues, string>> = {};
  if (!values.title.trim()) errors.title = "Введите название";
  else if (values.title.trim().length > 100) errors.title = "Не длиннее 100 символов";
  if (values.description.length > 1000) errors.description = "Не длиннее 1000 символов";
  return errors;
};

const EMPTY_TASK_FORM: TaskFormValues = {
  title: "",
  description: "",
  priority: "MEDIUM",
};

interface TasksSectionProps {
  projectId: number;
  canManage: boolean;
  currentUserId?: number;
}

export function TasksSection({ projectId, canManage, currentUserId }: TasksSectionProps) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const [offset, setOffset] = useState(0);
  const [statusFilter, setStatusFilter] = useState<TaskStatus | "">("");
  const [priorityFilter, setPriorityFilter] = useState<TaskPriority | "">("");
  const [titleSearch, setTitleSearch] = useState("");
  const [debouncedTitleSearch, setDebouncedTitleSearch] = useState("");
  const [taskModalOpen, setTaskModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Task | null>(null);
  const [selectedLabelIds, setSelectedLabelIds] = useState<Set<number>>(new Set());
  const [viewingTask, setViewingTask] = useState<Task | null>(null);
  const [assigneeSearch, setAssigneeSearch] = useState("");
  const [debouncedAssigneeSearch, setDebouncedAssigneeSearch] = useState("");
  const [selectedAssignee, setSelectedAssignee] = useState<SelectedAssignee | null>(null);

  const tasksQuery = useQuery({
    queryKey: ["tasks", projectId, offset, statusFilter, priorityFilter, debouncedTitleSearch],
    queryFn: () =>
      listTasks({
        projectId,
        limit: PAGE_SIZE,
        offset,
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
        search: debouncedTitleSearch || undefined,
      }),
  });

  // limit=100 — меток на всю учебную площадку немного, полноценная
  // пагинация пикеру не нужна.
  const labelsQuery = useQuery({
    queryKey: ["labels"],
    queryFn: () => listLabels(100, 0),
  });

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedAssigneeSearch(assigneeSearch.trim()), 250);
    return () => clearTimeout(timer);
  }, [assigneeSearch]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedTitleSearch(titleSearch.trim());
      setOffset(0);
    }, 250);
    return () => clearTimeout(timer);
  }, [titleSearch]);

  // Исполнителем может стать любой пользователь, не только участник
  // проекта (см. "Доступ исполнителя" в docs/API_SPEC.md) — поэтому поиск
  // по всем пользователям (GET /users/search), а не выбор из members.
  // Включая ADMIN — иногда платформенный админ и правда должен быть
  // исполнителем конкретной задачи.
  const assigneeSearchQuery = useQuery({
    queryKey: ["users-search-assignee", debouncedAssigneeSearch],
    queryFn: () => searchUsers(debouncedAssigneeSearch),
    enabled: taskModalOpen && debouncedAssigneeSearch.length > 0,
  });

  const taskForm = useFormValidation<TaskFormValues>({
    initialValues: EMPTY_TASK_FORM,
    validate: validateTask,
  });
  const titleField = taskForm.fieldState("title");
  const descriptionField = taskForm.fieldState("description");

  // Инвалидируем и ["my-tasks"] тоже — иначе создание/правка/статус/удаление
  // задачи здесь не отразится в «Мои задачи» без ручного reload (тот же
  // класс бага, что был со счётчиком комментариев — см. TaskDetailModal).
  function invalidateTasks() {
    queryClient.invalidateQueries({ queryKey: ["tasks", projectId] });
    queryClient.invalidateQueries({ queryKey: ["my-tasks"] });
  }

  function toggleLabel(id: number) {
    setSelectedLabelIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  const createTaskMutation = useMutation({
    mutationFn: async () => {
      const task = await createTask({
        projectId,
        title: taskForm.values.title.trim(),
        description: taskForm.values.description.trim() || undefined,
        priority: taskForm.values.priority as TaskPriority,
        assigneeId: selectedAssignee?.id,
      });
      await Promise.all([...selectedLabelIds].map((labelId) => attachLabel(task.id, labelId)));
      return task;
    },
    onSuccess: () => {
      invalidateTasks();
      closeTaskModal();
      showToast("Задача создана", "success");
    },
    onError: (error) => {
      showToast(error instanceof ApiError ? error.message : "Не удалось создать задачу", "error");
    },
  });

  const updateTaskMutation = useMutation({
    mutationFn: async () => {
      const task = await updateTask(editingTask!.id, {
        title: taskForm.values.title.trim(),
        description: taskForm.values.description.trim() || undefined,
        priority: taskForm.values.priority as TaskPriority,
        assigneeId: selectedAssignee?.id ?? null,
      });

      const existingLabelIds = new Set(editingTask!.labels.map((l) => l.id));
      const toAttach = [...selectedLabelIds].filter((id) => !existingLabelIds.has(id));
      const toDetach = [...existingLabelIds].filter((id) => !selectedLabelIds.has(id));
      await Promise.all([
        ...toAttach.map((labelId) => attachLabel(task.id, labelId)),
        ...toDetach.map((labelId) => detachLabel(task.id, labelId)),
      ]);

      return task;
    },
    onSuccess: () => {
      invalidateTasks();
      closeTaskModal();
      showToast("Задача обновлена", "success");
    },
    onError: (error) => {
      showToast(error instanceof ApiError ? error.message : "Не удалось обновить задачу", "error");
    },
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: TaskStatus }) => updateTask(id, { status }),
    onSuccess: () => {
      invalidateTasks();
      showToast("Статус обновлён", "success");
    },
    onError: (error) => {
      showToast(error instanceof ApiError ? error.message : "Не удалось изменить статус", "error");
    },
  });

  const deleteTaskMutation = useMutation({
    mutationFn: (id: number) => deleteTask(id),
    onSuccess: () => {
      invalidateTasks();
      showToast("Задача удалена", "success");
      setDeleteTarget(null);
    },
    onError: (error) => {
      showToast(error instanceof ApiError ? error.message : "Не удалось удалить задачу", "error");
      setDeleteTarget(null);
    },
  });

  function openCreateModal() {
    setEditingTask(null);
    taskForm.setField("title", "");
    taskForm.setField("description", "");
    taskForm.setField("priority", "MEDIUM");
    setSelectedAssignee(null);
    setAssigneeSearch("");
    setSelectedLabelIds(new Set());
    setTaskModalOpen(true);
  }

  function openEditModal(task: Task) {
    setEditingTask(task);
    taskForm.setField("title", task.title);
    taskForm.setField("description", task.description ?? "");
    taskForm.setField("priority", task.priority);
    setSelectedAssignee(
      task.assigneeId !== null && task.assigneeFirstName && task.assigneeLastName
        ? { id: task.assigneeId, firstName: task.assigneeFirstName, lastName: task.assigneeLastName }
        : null,
    );
    setAssigneeSearch("");
    setSelectedLabelIds(new Set(task.labels.map((l) => l.id)));
    setTaskModalOpen(true);
  }

  function closeTaskModal() {
    setTaskModalOpen(false);
    setEditingTask(null);
  }

  function handleTaskSubmit(e: FormEvent) {
    e.preventDefault();
    if (!taskForm.validateAll()) return;
    if (editingTask) updateTaskMutation.mutate();
    else createTaskMutation.mutate();
  }

  const columns: TableColumn<Task>[] = [
    {
      key: "title",
      header: "Задача",
      render: (row) => (
        <div className="tasks-section__title-cell">
          <div className="tasks-section__title-row">
            <span
              className="tasks-section__title tasks-section__title--link"
              onClick={() => setViewingTask(row)}
            >
              {row.title}
            </span>
            {row.commentsCount > 0 && (
              <span
                className="tasks-section__comments-badge"
                title={`Комментариев: ${row.commentsCount}`}
              >
                💬 {row.commentsCount}
              </span>
            )}
          </div>
          {row.description && (
            <span className="tasks-section__task-description">{row.description}</span>
          )}
          {row.labels.length > 0 && (
            <div className="tasks-section__label-chips">
              {row.labels.map((label) => (
                <span key={label.id} className="tasks-section__label-chip">
                  {label.name}
                </span>
              ))}
            </div>
          )}
        </div>
      ),
    },
    {
      key: "priority",
      header: "Приоритет",
      render: (row) => (
        <Badge variant={TASK_PRIORITY_LABEL[row.priority].variant}>
          {TASK_PRIORITY_LABEL[row.priority].label}
        </Badge>
      ),
      width: "140px",
    },
    {
      key: "status",
      header: "Статус",
      render: (row) =>
        canManage || row.assigneeId === currentUserId ? (
          <select
            className="project-detail__role-select"
            value={row.status}
            disabled={statusMutation.isPending}
            onChange={(e) =>
              statusMutation.mutate({ id: row.id, status: e.target.value as TaskStatus })
            }
          >
            <option value="TODO">К выполнению</option>
            <option value="IN_PROGRESS">В работе</option>
            <option value="DONE">Готово</option>
          </select>
        ) : (
          <Badge variant={TASK_STATUS_LABEL[row.status].variant}>
            {TASK_STATUS_LABEL[row.status].label}
          </Badge>
        ),
      width: "180px",
    },
    {
      key: "assignee",
      header: "Исполнитель",
      render: (row) =>
        row.assigneeId === null ? (
          <span className="tasks-section__unassigned">—</span>
        ) : (
          `${row.assigneeFirstName} ${row.assigneeLastName}`
        ),
      width: "180px",
    },
    ...(canManage
      ? [
          {
            key: "actions",
            header: "",
            render: (row: Task) => (
              <div className="tasks-section__actions">
                <Button size="sm" variant="ghost" onClick={() => openEditModal(row)}>
                  Изменить
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setDeleteTarget(row)}>
                  Удалить
                </Button>
              </div>
            ),
            width: "160px",
          },
        ]
      : []),
  ];

  return (
    <div className="project-detail__section">
      <div className="project-detail__section-header">
        <span className="project-detail__section-title">Задачи</span>
        {canManage && <Button size="sm" onClick={openCreateModal}>Создать задачу</Button>}
      </div>

      <div className="tasks-section__filters">
        <input
          className="tasks-section__search-input"
          type="text"
          placeholder="Поиск по названию…"
          value={titleSearch}
          onChange={(e) => setTitleSearch(e.target.value)}
        />
        <select
          className="project-detail__role-select"
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value as TaskStatus | "");
            setOffset(0);
          }}
        >
          <option value="">Все статусы</option>
          <option value="TODO">К выполнению</option>
          <option value="IN_PROGRESS">В работе</option>
          <option value="DONE">Готово</option>
        </select>
        <select
          className="project-detail__role-select"
          value={priorityFilter}
          onChange={(e) => {
            setPriorityFilter(e.target.value as TaskPriority | "");
            setOffset(0);
          }}
        >
          <option value="">Все приоритеты</option>
          <option value="LOW">Низкий</option>
          <option value="MEDIUM">Средний</option>
          <option value="HIGH">Высокий</option>
        </select>
      </div>

      {tasksQuery.isLoading ? (
        <SkeletonRows count={3} />
      ) : (
        <>
          {tasksQuery.data && tasksQuery.data.items.length > 0 ? (
            <Table columns={columns} rows={tasksQuery.data.items} getRowKey={(row) => row.id} />
          ) : (
            <EmptyState
              icon="✅"
              title={
                statusFilter || priorityFilter || debouncedTitleSearch
                  ? "Нет задач по фильтру"
                  : "Пока нет задач"
              }
              description={
                canManage && !statusFilter && !priorityFilter && !debouncedTitleSearch
                  ? "Создайте первую задачу для этого проекта."
                  : undefined
              }
            />
          )}
          {/* Не завязано на items.length — иначе на пустой странице
              offset>0 (например, последнюю задачу страницы удалили)
              пропадали бы и кнопки "Назад"/"Вперёд", застревая без reload. */}
          {tasksQuery.data && (offset > 0 || tasksQuery.data.hasNext) && (
            <div className="tasks-section__pagination">
              <Button
                variant="secondary"
                size="sm"
                disabled={offset === 0}
                onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
              >
                Назад
              </Button>
              <span className="tasks-section__pagination-info">
                {offset + 1}–{Math.min(offset + PAGE_SIZE, tasksQuery.data.total)} из{" "}
                {tasksQuery.data.total}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={!tasksQuery.data.hasNext}
                onClick={() => setOffset((o) => o + PAGE_SIZE)}
              >
                Вперёд
              </Button>
            </div>
          )}
        </>
      )}

      {/* Создание/редактирование задачи */}
      <Modal
        open={taskModalOpen}
        title={editingTask ? "Изменить задачу" : "Новая задача"}
        onClose={closeTaskModal}
        footer={
          <>
            <Button variant="secondary" onClick={closeTaskModal}>
              Отмена
            </Button>
            <Button
              type="submit"
              form="task-form"
              loading={createTaskMutation.isPending || updateTaskMutation.isPending}
            >
              {editingTask ? "Сохранить" : "Создать"}
            </Button>
          </>
        }
      >
        <form id="task-form" onSubmit={handleTaskSubmit} noValidate>
          {(() => {
            const activeError = createTaskMutation.error ?? updateTaskMutation.error;
            if (!activeError) return null;
            return (
              <div className="form-banner" role="alert">
                {activeError instanceof ApiError ? activeError.message : "Что-то пошло не так"}
              </div>
            );
          })()}
          <div className={`field${titleField.error ? " field--invalid" : ""}`}>
            <label className="field__label" htmlFor="task-title">
              Название
            </label>
            <div className="field__input-wrap">
              <input
                id="task-title"
                className="field__input"
                value={titleField.value}
                onChange={(e) => taskForm.setField("title", e.target.value)}
                onBlur={() => taskForm.blurField("title")}
                maxLength={100}
                autoFocus
              />
            </div>
            {titleField.error && <span className="field__error">{titleField.error}</span>}
          </div>
          <div className={`field${descriptionField.error ? " field--invalid" : ""}`}>
            <label className="field__label" htmlFor="task-description">
              Описание
            </label>
            <div className="field__input-wrap">
              <input
                id="task-description"
                className="field__input"
                value={descriptionField.value}
                onChange={(e) => taskForm.setField("description", e.target.value)}
                onBlur={() => taskForm.blurField("description")}
                maxLength={1000}
              />
            </div>
            {descriptionField.error && (
              <span className="field__error">{descriptionField.error}</span>
            )}
          </div>
          <div className="field">
            <label className="field__label" htmlFor="task-priority">
              Приоритет
            </label>
            <div className="field__input-wrap">
              <select
                id="task-priority"
                className="field__input"
                value={taskForm.values.priority}
                onChange={(e) => taskForm.setField("priority", e.target.value)}
              >
                <option value="LOW">Низкий</option>
                <option value="MEDIUM">Средний</option>
                <option value="HIGH">Высокий</option>
              </select>
            </div>
          </div>
          <div className="field">
            <label className="field__label" htmlFor="task-assignee-search">
              Исполнитель
            </label>
            {selectedAssignee ? (
              <div className="member-picker__selected">
                <span className="member-picker__name">
                  {selectedAssignee.firstName} {selectedAssignee.lastName}
                </span>
                <Button size="sm" variant="ghost" onClick={() => setSelectedAssignee(null)}>
                  Изменить
                </Button>
              </div>
            ) : (
              <>
                <div className="field__input-wrap">
                  <input
                    id="task-assignee-search"
                    className="field__input"
                    placeholder="Поиск по имени или email — необязательно"
                    value={assigneeSearch}
                    onChange={(e) => setAssigneeSearch(e.target.value)}
                  />
                </div>
                {assigneeSearch.trim().length > 0 && (
                  <div className="member-picker">
                    {(assigneeSearchQuery.data?.length ?? 0) === 0 ? (
                      <div className="member-picker__empty">
                        {assigneeSearchQuery.isFetching ? "Ищем…" : "Никого не найдено"}
                      </div>
                    ) : (
                      assigneeSearchQuery.data?.map((u) => (
                        <button
                          key={u.id}
                          type="button"
                          className="member-picker__item"
                          onClick={() => {
                            setSelectedAssignee({ id: u.id, firstName: u.firstName, lastName: u.lastName });
                            setAssigneeSearch("");
                          }}
                        >
                          <span className="member-picker__name">
                            {u.firstName} {u.lastName}
                          </span>
                          <span className="member-picker__email">{u.email}</span>
                        </button>
                      ))
                    )}
                  </div>
                )}
              </>
            )}
          </div>
          <div className="field">
            <label className="field__label">Метки</label>
            <div className="tasks-section__label-picker">
              {(labelsQuery.data?.items.length ?? 0) === 0 ? (
                <span className="tasks-section__label-empty">
                  Меток пока нет — создать можно в разделе «Админ».
                </span>
              ) : (
                labelsQuery.data?.items.map((label) => (
                  <button
                    key={label.id}
                    type="button"
                    className={`tasks-section__label-chip tasks-section__label-chip--toggle${
                      selectedLabelIds.has(label.id) ? " tasks-section__label-chip--active" : ""
                    }`}
                    onClick={() => toggleLabel(label.id)}
                  >
                    {label.name}
                  </button>
                ))
              )}
            </div>
          </div>
        </form>
      </Modal>

      {/* Подтверждение удаления */}
      <Modal
        open={deleteTarget !== null}
        title="Удалить задачу?"
        onClose={() => setDeleteTarget(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setDeleteTarget(null)}>
              Отмена
            </Button>
            <Button
              variant="danger"
              loading={deleteTaskMutation.isPending}
              onClick={() => deleteTarget && deleteTaskMutation.mutate(deleteTarget.id)}
            >
              Удалить
            </Button>
          </>
        }
      >
        <p>Задача «{deleteTarget?.title}» и её комментарии будут помечены как удалённые.</p>
      </Modal>

      <TaskDetailModal
        task={viewingTask}
        onClose={() => setViewingTask(null)}
        canManage={canManage}
        currentUserId={currentUserId}
      />
    </div>
  );
}
