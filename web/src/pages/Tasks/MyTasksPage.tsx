import { useEffect, useMemo, useState } from "react";
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  EmptyState,
  SkeletonRows,
  Table,
  useToast,
  type TableColumn,
} from "../../components";
import { listTasks, updateTask } from "../../api/tasks";
import { listMembers, listProjects } from "../../api/projects";
import type { ProjectRole, Task, TaskPriority, TaskStatus } from "../../api/types";
import { ApiError } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { TASK_PRIORITY_LABEL } from "../../constants/labels";
import { TaskDetailModal } from "../Projects/TaskDetailModal";
import "../Projects/TasksSection.css";
import "./MyTasksPage.css";

const PAGE_SIZE = 20;
const MANAGE_ROLES: ProjectRole[] = ["OWNER", "MANAGER"];

export function MyTasksPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "ADMIN";
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const [offset, setOffset] = useState(0);
  const [statusFilter, setStatusFilter] = useState<TaskStatus | "">("");
  const [priorityFilter, setPriorityFilter] = useState<TaskPriority | "">("");
  const [titleSearch, setTitleSearch] = useState("");
  const [debouncedTitleSearch, setDebouncedTitleSearch] = useState("");
  const [viewingTask, setViewingTask] = useState<Task | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedTitleSearch(titleSearch.trim());
      setOffset(0);
    }, 250);
    return () => clearTimeout(timer);
  }, [titleSearch]);

  const tasksQuery = useQuery({
    queryKey: ["my-tasks", user?.id, offset, statusFilter, priorityFilter, debouncedTitleSearch],
    queryFn: () =>
      listTasks({
        assigneeId: user!.id,
        limit: PAGE_SIZE,
        offset,
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
        search: debouncedTitleSearch || undefined,
      }),
    enabled: user !== null,
  });

  // Резолвим свою роль в проекте каждой задачи тем же приёмом, что и
  // ProjectsList ("Моя роль") — нужно для права МОДЕРИРОВАТЬ чужие
  // комментарии (MANAGER+/OWNER/ADMIN), а не для статуса: раз список уже
  // отфильтрован по assigneeId=я, право менять статус есть всегда как у
  // исполнителя — но модерация чужих комментариев исполнителю сама по
  // себе не положена, только реальная роль в проекте.
  const projectsQuery = useQuery({
    queryKey: ["projects-for-my-tasks"],
    queryFn: () => listProjects(100, 0),
    enabled: !isAdmin,
  });
  const memberQueries = useQueries({
    queries: (projectsQuery.data?.items ?? []).map((project) => ({
      queryKey: ["project-members", project.id, "mine"],
      queryFn: () => listMembers(project.id, 100, 0),
      enabled: !isAdmin,
    })),
  });
  const myRoleByProject = useMemo(() => {
    const map = new Map<number, ProjectRole>();
    (projectsQuery.data?.items ?? []).forEach((project, index) => {
      const mine = memberQueries[index]?.data?.items.find((m) => m.userId === user?.id);
      if (mine) map.set(project.id, mine.role);
    });
    return map;
  }, [projectsQuery.data, memberQueries, user]);

  function canModerateComments(task: Task): boolean {
    if (isAdmin) return true;
    const role = myRoleByProject.get(task.projectId);
    return role !== undefined && MANAGE_ROLES.includes(role);
  }

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: TaskStatus }) => updateTask(id, { status }),
    onSuccess: () => {
      // И ["tasks"] тоже — иначе смена статуса здесь не отразится в
      // TasksSection на странице проекта без ручного reload.
      queryClient.invalidateQueries({ queryKey: ["my-tasks"] });
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      showToast("Статус обновлён", "success");
    },
    onError: (error) => {
      showToast(error instanceof ApiError ? error.message : "Не удалось изменить статус", "error");
    },
  });

  const columns: TableColumn<Task>[] = [
    {
      key: "project",
      header: "Проект",
      render: (row) => row.projectName,
      width: "180px",
    },
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
      // Список и так отфильтрован по assigneeId=я — статус своей задачи
      // может менять любой исполнитель, без проверки роли в проекте.
      render: (row) => (
        <select
          className="my-tasks-page__select"
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
      ),
      width: "180px",
    },
  ];

  return (
    <div className="my-tasks-page">
      <div className="my-tasks-page__header">
        <h1>Мои задачи</h1>
        <span className="my-tasks-page__subtitle">
          Задачи, назначенные лично на вас{tasksQuery.data ? ` — ${tasksQuery.data.total}` : ""}
        </span>
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
          className="my-tasks-page__select"
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
          className="my-tasks-page__select"
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
        <SkeletonRows count={4} />
      ) : (
        <>
          {tasksQuery.data && tasksQuery.data.items.length > 0 ? (
            <Table columns={columns} rows={tasksQuery.data.items} getRowKey={(row) => row.id} />
          ) : (
            <EmptyState
              icon="🗂️"
              title={
                statusFilter || priorityFilter || debouncedTitleSearch
                  ? "Нет задач по фильтру"
                  : "Задач пока нет"
              }
              description="Задачи появятся здесь, как только вас назначат исполнителем."
            />
          )}
          {/* Не завязано на items.length — иначе пустая страница при
              offset>0 оставила бы без кнопок "Назад"/"Вперёд". */}
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

      <TaskDetailModal
        task={viewingTask}
        onClose={() => setViewingTask(null)}
        canManage={viewingTask ? canModerateComments(viewingTask) : false}
        currentUserId={user?.id}
      />
    </div>
  );
}
