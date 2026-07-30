import { useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  EmptyState,
  Modal,
  Skeleton,
  SkeletonRows,
  Table,
  useToast,
  type TableColumn,
} from "../../components";
import { createProject, listMembers, listProjects } from "../../api/projects";
import type { Project, ProjectRole } from "../../api/types";
import { ApiError } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { useFormValidation, type Validator } from "../../hooks/useFormValidation";
import { ROLE_LABEL, STATUS_LABEL } from "../../constants/labels";
import "../../styles/forms.css";
import "./ProjectsList.css";

const PAGE_SIZE = 20;

interface CreateValues extends Record<string, string> {
  name: string;
  description: string;
}

const validate: Validator<CreateValues> = (values) => {
  const errors: Partial<Record<keyof CreateValues, string>> = {};

  if (!values.name.trim()) {
    errors.name = "Введите название";
  } else if (values.name.trim().length > 100) {
    errors.name = "Не длиннее 100 символов";
  }

  if (values.description.length > 1000) {
    errors.description = "Не длиннее 1000 символов";
  }

  return errors;
};

export function ProjectsList() {
  const [offset, setOffset] = useState(0);
  const [modalOpen, setModalOpen] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const { user } = useAuth();
  const isAdmin = user?.role === "ADMIN";

  const { data, isLoading, isError } = useQuery({
    queryKey: ["projects", offset],
    queryFn: () => listProjects(PAGE_SIZE, offset),
  });

  // ProjectResponse не отдаёт роль текущего пользователя — приходится
  // подтягивать участников по каждому проекту отдельно. ADMIN видит все
  // проекты не через членство, ему тут смысла нет (роль всегда ADMIN).
  const roleQueries = useQueries({
    queries: (data?.items ?? []).map((project) => ({
      queryKey: ["project-members", project.id, "mine"],
      queryFn: () => listMembers(project.id, 100, 0),
      enabled: !isAdmin,
    })),
  });
  const myRoleByProject = useMemo(() => {
    const map = new Map<number, ProjectRole>();
    (data?.items ?? []).forEach((project, index) => {
      const mine = roleQueries[index]?.data?.items.find((m) => m.userId === user?.id);
      if (mine) map.set(project.id, mine.role);
    });
    return map;
  }, [data, roleQueries, user]);

  const { setField, blurField, validateAll, fieldState, values } = useFormValidation<CreateValues>({
    initialValues: { name: "", description: "" },
    validate,
  });
  const name = fieldState("name");
  const description = fieldState("description");

  const create = useMutation({
    mutationFn: () => createProject({ name: values.name.trim(), description: values.description.trim() || undefined }),
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setModalOpen(false);
      showToast("Проект создан", "success");
      navigate(`/projects/${project.id}`);
    },
  });

  function handleCreateSubmit(event: FormEvent) {
    event.preventDefault();
    if (!validateAll()) return;
    create.mutate();
  }

  const columns: TableColumn<Project>[] = [
    {
      key: "name",
      header: "Название",
      render: (row) => (
        <span
          className="projects-page__name-link"
          onClick={() => navigate(`/projects/${row.id}`)}
        >
          {row.name}
        </span>
      ),
    },
    {
      key: "description",
      header: "Описание",
      render: (row) => (
        <span className="projects-page__description">{row.description || "—"}</span>
      ),
    },
    {
      key: "status",
      header: "Статус",
      render: (row) => (
        <Badge variant={STATUS_LABEL[row.status].variant}>{STATUS_LABEL[row.status].label}</Badge>
      ),
      width: "140px",
    },
    {
      key: "role",
      header: "Моя роль",
      render: (row) => {
        if (isAdmin) return <Badge variant="accent">Администратор</Badge>;
        const role = myRoleByProject.get(row.id);
        return role ? (
          <Badge variant="accent">{ROLE_LABEL[role]}</Badge>
        ) : (
          <Skeleton width="90px" height="1.1rem" />
        );
      },
      width: "160px",
    },
  ];

  return (
    <div className="projects-page">
      <div className="projects-page__header">
        <div className="projects-page__title">
          <h1>Проекты</h1>
          <span className="projects-page__subtitle">
            {isAdmin ? "Все проекты" : "Проекты, в которых вы участвуете"}
            {data ? ` — ${data.total}` : ""}
          </span>
        </div>
        <Button onClick={() => setModalOpen(true)}>Создать проект</Button>
      </div>

      {isError && (
        <div className="projects-page__banner" role="alert">
          Не удалось загрузить проекты. Попробуйте обновить страницу.
        </div>
      )}

      {isLoading ? (
        <SkeletonRows count={5} height="3rem" />
      ) : (
        <>
          {data && data.items.length > 0 ? (
            <Table
              columns={columns}
              rows={data.items}
              getRowKey={(row) => row.id}
              onRowClick={(row) => navigate(`/projects/${row.id}`)}
            />
          ) : (
            <EmptyState
              icon="📁"
              title="Пока нет проектов"
              description="Создайте первый проект, чтобы начать заводить задачи."
            />
          )}
          {/* Не завязано на items.length — иначе пустая страница при
              offset>0 оставила бы без кнопок "Назад"/"Вперёд". */}
          {data && (offset > 0 || data.hasNext) && (
            <div className="projects-page__pagination">
              <Button
                variant="secondary"
                size="sm"
                disabled={offset === 0}
                onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
              >
                Назад
              </Button>
              <span className="projects-page__pagination-info">
                {offset + 1}–{Math.min(offset + PAGE_SIZE, data.total)} из {data.total}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={!data.hasNext}
                onClick={() => setOffset((o) => o + PAGE_SIZE)}
              >
                Вперёд
              </Button>
            </div>
          )}
        </>
      )}

      <Modal
        open={modalOpen}
        title="Новый проект"
        onClose={() => setModalOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setModalOpen(false)}>
              Отмена
            </Button>
            <Button
              type="submit"
              form="create-project-form"
              loading={create.isPending}
            >
              Создать
            </Button>
          </>
        }
      >
        <form id="create-project-form" onSubmit={handleCreateSubmit} noValidate>
          {create.isError && (
            <div className="form-banner" role="alert">
              {create.error instanceof ApiError ? create.error.message : "Что-то пошло не так"}
            </div>
          )}
          <div className={`field${name.error ? " field--invalid" : name.isValid ? " field--valid" : ""}`}>
            <label className="field__label" htmlFor="project-name">
              Название
            </label>
            <div className="field__input-wrap">
              <input
                id="project-name"
                className="field__input"
                placeholder="Например, Redesign"
                value={name.value}
                onChange={(e) => setField("name", e.target.value)}
                onBlur={() => blurField("name")}
                aria-invalid={Boolean(name.error)}
              />
            </div>
            {name.error && <span className="field__error">{name.error}</span>}
          </div>
          <div
            className={`field${description.error ? " field--invalid" : description.isValid ? " field--valid" : ""}`}
          >
            <label className="field__label" htmlFor="project-description">
              Описание
            </label>
            <div className="field__input-wrap">
              <input
                id="project-description"
                className="field__input"
                placeholder="Необязательно"
                value={description.value}
                onChange={(e) => setField("description", e.target.value)}
                onBlur={() => blurField("description")}
                aria-invalid={Boolean(description.error)}
              />
            </div>
            {description.error && <span className="field__error">{description.error}</span>}
          </div>
        </form>
      </Modal>
    </div>
  );
}
