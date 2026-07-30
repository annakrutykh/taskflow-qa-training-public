import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button, useToast } from "../../components";
import { resetDatabase } from "../../api/admin";
import { ApiError } from "../../api/client";
import "./AdminPage.css";

export function MaintenanceSection() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [armed, setArmed] = useState(false);

  const resetMutation = useMutation({
    mutationFn: () => resetDatabase(),
    onSuccess: () => {
      queryClient.clear();
      setArmed(false);
      showToast("База данных сброшена и заново засеяна", "success");
    },
    onError: (error) => {
      showToast(error instanceof ApiError ? error.message : "Не удалось сбросить БД", "error");
      setArmed(false);
    },
  });

  return (
    <div className="admin-page__section">
      <div className="admin-page__maintenance-card">
        <div>
          <p className="admin-page__maintenance-title">Сбросить базу данных</p>
          <p className="admin-page__maintenance-description">
            Полностью очищает все данные (проекты, задачи, пользователей, метки) и заново
            заполняет их из seed.py. Необратимо — весь мусор от ручного тестирования и накопленные
            изменения будут потеряны.
          </p>
        </div>
        {armed ? (
          <div className="admin-page__row-actions">
            <Button variant="danger" loading={resetMutation.isPending} onClick={() => resetMutation.mutate()}>
              Точно сбросить всё?
            </Button>
            <Button variant="ghost" onClick={() => setArmed(false)}>
              Отмена
            </Button>
          </div>
        ) : (
          <Button variant="danger" onClick={() => setArmed(true)}>
            Сбросить БД
          </Button>
        )}
      </div>
    </div>
  );
}
