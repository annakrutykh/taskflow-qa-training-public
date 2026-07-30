import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Badge, Button, Modal, SkeletonRows, Table, useToast, type TableColumn } from "../../components";
import { deleteUser, listUsers, updateUserRole, updateUserStatus } from "../../api/users";
import type { User } from "../../api/types";
import { ApiError } from "../../api/client";
import { USER_ROLE_LABEL } from "../../constants/labels";
import "./AdminPage.css";

const PAGE_SIZE = 20;

export function UsersSection({ currentUserId }: { currentUserId?: number }) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [offset, setOffset] = useState(0);
  const [deleteTarget, setDeleteTarget] = useState<User | null>(null);

  const usersQuery = useQuery({
    queryKey: ["admin-users", offset],
    queryFn: () => listUsers(PAGE_SIZE, offset),
  });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ["admin-users"] });
  }

  const roleMutation = useMutation({
    mutationFn: ({ id, role }: { id: number; role: "USER" | "ADMIN" }) => updateUserRole(id, role),
    onSuccess: () => {
      invalidate();
      showToast("Роль обновлена", "success");
    },
    onError: (error) => {
      showToast(error instanceof ApiError ? error.message : "Не удалось изменить роль", "error");
    },
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: number; isActive: boolean }) =>
      updateUserStatus(id, isActive),
    onSuccess: () => {
      invalidate();
      showToast("Статус обновлён", "success");
    },
    onError: (error) => {
      showToast(error instanceof ApiError ? error.message : "Не удалось изменить статус", "error");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteUser(id),
    onSuccess: () => {
      invalidate();
      showToast("Пользователь удалён", "success");
      setDeleteTarget(null);
    },
    onError: (error) => {
      showToast(error instanceof ApiError ? error.message : "Не удалось удалить пользователя", "error");
      setDeleteTarget(null);
    },
  });

  const columns: TableColumn<User>[] = [
    {
      key: "name",
      header: "Пользователь",
      render: (row) => (
        <div className="admin-page__user-cell">
          <span className="admin-page__user-name">
            {row.firstName} {row.lastName}
            {row.id === currentUserId && <span className="admin-page__you-badge">вы</span>}
          </span>
          <span className="admin-page__user-email">{row.email}</span>
        </div>
      ),
    },
    {
      key: "role",
      header: "Роль",
      render: (row) => (
        <select
          className="admin-page__select"
          value={row.role}
          disabled={roleMutation.isPending || row.id === currentUserId}
          onChange={(e) =>
            roleMutation.mutate({ id: row.id, role: e.target.value as "USER" | "ADMIN" })
          }
        >
          <option value="USER">{USER_ROLE_LABEL.USER}</option>
          <option value="ADMIN">{USER_ROLE_LABEL.ADMIN}</option>
        </select>
      ),
      width: "200px",
    },
    {
      key: "status",
      header: "Статус",
      render: (row) => (
        <div className="admin-page__status-cell">
          <Badge variant={row.isActive ? "success" : "neutral"}>
            {row.isActive ? "Активен" : "Деактивирован"}
          </Badge>
          <Button
            size="sm"
            variant="ghost"
            disabled={statusMutation.isPending || row.id === currentUserId}
            onClick={() => statusMutation.mutate({ id: row.id, isActive: !row.isActive })}
          >
            {row.isActive ? "Деактивировать" : "Активировать"}
          </Button>
        </div>
      ),
      width: "220px",
    },
    {
      key: "actions",
      header: "",
      render: (row) => (
        <Button
          size="sm"
          variant="ghost"
          disabled={row.id === currentUserId}
          onClick={() => setDeleteTarget(row)}
        >
          Удалить
        </Button>
      ),
      width: "100px",
    },
  ];

  return (
    <div className="admin-page__section">
      {usersQuery.isLoading ? (
        <SkeletonRows count={4} />
      ) : (
        <>
          <Table
            columns={columns}
            rows={usersQuery.data?.items ?? []}
            getRowKey={(row) => row.id}
          />
          {usersQuery.data && (offset > 0 || usersQuery.data.hasNext) && (
            <div className="admin-page__pagination">
              <Button
                variant="secondary"
                size="sm"
                disabled={offset === 0}
                onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
              >
                Назад
              </Button>
              <span className="admin-page__pagination-info">
                {offset + 1}–{Math.min(offset + PAGE_SIZE, usersQuery.data.total)} из{" "}
                {usersQuery.data.total}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={!usersQuery.data.hasNext}
                onClick={() => setOffset((o) => o + PAGE_SIZE)}
              >
                Вперёд
              </Button>
            </div>
          )}
        </>
      )}

      <Modal
        open={deleteTarget !== null}
        title="Удалить пользователя?"
        onClose={() => setDeleteTarget(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setDeleteTarget(null)}>
              Отмена
            </Button>
            <Button
              variant="danger"
              loading={deleteMutation.isPending}
              onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
            >
              Удалить
            </Button>
          </>
        }
      >
        <p>
          Пользователь «{deleteTarget?.firstName} {deleteTarget?.lastName}» будет помечен как
          удалённый. Если он — последний владелец какого-то проекта, удаление будет отклонено
          (сначала назначьте другого владельца).
        </p>
      </Modal>
    </div>
  );
}
