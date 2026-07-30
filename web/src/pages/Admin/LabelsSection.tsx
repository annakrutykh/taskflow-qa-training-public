import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, useToast } from "../../components";
import { createLabel, deleteLabel, listLabels } from "../../api/labels";
import { ApiError } from "../../api/client";
import "../../styles/forms.css";
import "./AdminPage.css";

export function LabelsSection() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [name, setName] = useState("");
  const [armedDeleteId, setArmedDeleteId] = useState<number | null>(null);

  const labelsQuery = useQuery({
    queryKey: ["labels"],
    queryFn: () => listLabels(100, 0),
  });

  const createMutation = useMutation({
    mutationFn: () => createLabel(name.trim()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["labels"] });
      setName("");
      showToast("Метка создана", "success");
    },
    onError: (error) => {
      showToast(error instanceof ApiError ? error.message : "Не удалось создать метку", "error");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteLabel(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["labels"] });
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      queryClient.invalidateQueries({ queryKey: ["my-tasks"] });
      setArmedDeleteId(null);
      showToast("Метка удалена", "success");
    },
    onError: (error) => {
      showToast(error instanceof ApiError ? error.message : "Не удалось удалить метку", "error");
      setArmedDeleteId(null);
    },
  });

  function handleCreateSubmit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim() || name.trim().length > 30) return;
    createMutation.mutate();
  }

  return (
    <div className="admin-page__section">
      <form onSubmit={handleCreateSubmit} noValidate className="admin-page__label-create">
        <div className="field__input-wrap">
          <input
            className="field__input"
            placeholder="Название метки"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={30}
          />
        </div>
        <Button type="submit" size="sm" loading={createMutation.isPending} disabled={!name.trim()}>
          Добавить
        </Button>
      </form>
      {createMutation.isError && (
        <div className="form-banner" role="alert">
          {createMutation.error instanceof ApiError
            ? createMutation.error.message
            : "Что-то пошло не так"}
        </div>
      )}

      <div className="admin-page__label-list">
        {labelsQuery.isLoading ? (
          <span className="admin-page__empty-hint">Загрузка…</span>
        ) : (labelsQuery.data?.items.length ?? 0) === 0 ? (
          <span className="admin-page__empty-hint">Меток пока нет.</span>
        ) : (
          labelsQuery.data?.items.map((label) => (
            <div key={label.id} className="admin-page__label-row">
              <span className="admin-page__label-chip">{label.name}</span>
              {armedDeleteId === label.id ? (
                <div className="admin-page__row-actions">
                  <Button
                    size="sm"
                    variant="danger"
                    loading={deleteMutation.isPending}
                    onClick={() => deleteMutation.mutate(label.id)}
                  >
                    Точно удалить?
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setArmedDeleteId(null)}>
                    Отмена
                  </Button>
                </div>
              ) : (
                <Button size="sm" variant="ghost" onClick={() => setArmedDeleteId(label.id)}>
                  Удалить
                </Button>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
