import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Badge, Button, Modal, SkeletonRows, useToast } from "../../components";
import { createComment, deleteComment, listComments, updateComment } from "../../api/comments";
import type { Comment, Task } from "../../api/types";
import { ApiError } from "../../api/client";
import { TASK_PRIORITY_LABEL, TASK_STATUS_LABEL } from "../../constants/labels";
import "../../styles/forms.css";
import "./TasksSection.css";
import "./TaskDetailModal.css";

interface TaskDetailModalProps {
  task: Task | null;
  onClose: () => void;
  /** Разрешает удалять чужие комментарии (модерация MANAGER+/OWNER/ADMIN).
   * Своя роль в проекте задачи не всегда известна вызывающему (см.
   * MyTasksPage — задачи из разных проектов сразу) — по умолчанию false,
   * автор своих комментарий может удалять всегда. */
  canManage?: boolean;
  currentUserId?: number;
}

export function TaskDetailModal({
  task,
  onClose,
  canManage = false,
  currentUserId,
}: TaskDetailModalProps) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [newCommentText, setNewCommentText] = useState("");
  const [editingCommentId, setEditingCommentId] = useState<number | null>(null);
  const [editingText, setEditingText] = useState("");
  const [armedDeleteId, setArmedDeleteId] = useState<number | null>(null);

  const commentsQuery = useQuery({
    queryKey: ["comments", task?.id],
    queryFn: () => listComments(task!.id, 100, 0),
    enabled: task !== null,
  });

  function invalidateComments() {
    queryClient.invalidateQueries({ queryKey: ["comments", task?.id] });
  }

  // Создание/удаление комментария меняет commentsCount на самой задаче —
  // без этого счётчик рядом с названием в списке (TasksSection/MyTasksPage)
  // не обновится, пока не перезагрузить страницу. Обе таблицы задач сразу
  // на всякий случай — модалка не знает, из какой она открыта.
  function invalidateTaskLists() {
    queryClient.invalidateQueries({ queryKey: ["tasks"] });
    queryClient.invalidateQueries({ queryKey: ["my-tasks"] });
  }

  const createMutation = useMutation({
    mutationFn: () => createComment(task!.id, newCommentText.trim()),
    onSuccess: () => {
      invalidateComments();
      invalidateTaskLists();
      setNewCommentText("");
      showToast("Комментарий добавлен", "success");
    },
    onError: (error) => {
      showToast(
        error instanceof ApiError ? error.message : "Не удалось добавить комментарий",
        "error",
      );
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, text }: { id: number; text: string }) => updateComment(task!.id, id, text),
    onSuccess: () => {
      invalidateComments();
      setEditingCommentId(null);
      showToast("Комментарий обновлён", "success");
    },
    onError: (error) => {
      showToast(
        error instanceof ApiError ? error.message : "Не удалось обновить комментарий",
        "error",
      );
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteComment(task!.id, id),
    onSuccess: () => {
      invalidateComments();
      invalidateTaskLists();
      setArmedDeleteId(null);
      showToast("Комментарий удалён", "success");
    },
    onError: (error) => {
      showToast(
        error instanceof ApiError ? error.message : "Не удалось удалить комментарий",
        "error",
      );
      setArmedDeleteId(null);
    },
  });

  function handleCommentSubmit(e: FormEvent) {
    e.preventDefault();
    if (!newCommentText.trim() || newCommentText.trim().length > 500) return;
    createMutation.mutate();
  }

  function startEdit(comment: Comment) {
    setEditingCommentId(comment.id);
    setEditingText(comment.text);
    setArmedDeleteId(null);
  }

  function submitEdit(id: number) {
    if (!editingText.trim() || editingText.trim().length > 500) return;
    updateMutation.mutate({ id, text: editingText.trim() });
  }

  if (!task) return null;

  return (
    <Modal open={task !== null} title={task.title} onClose={onClose}>
      <div className="task-detail">
        {task.description && <p className="task-detail__description">{task.description}</p>}

        <div className="task-detail__meta">
          <span className="task-detail__meta-label">Приоритет</span>
          <span className="task-detail__meta-value">
            <Badge variant={TASK_PRIORITY_LABEL[task.priority].variant}>
              {TASK_PRIORITY_LABEL[task.priority].label}
            </Badge>
          </span>

          <span className="task-detail__meta-label">Статус</span>
          <span className="task-detail__meta-value">
            <Badge variant={TASK_STATUS_LABEL[task.status].variant}>
              {TASK_STATUS_LABEL[task.status].label}
            </Badge>
          </span>

          <span className="task-detail__meta-label">Исполнитель</span>
          <span className="task-detail__meta-value">
            {task.assigneeId === null
              ? "Не назначен"
              : `${task.assigneeFirstName} ${task.assigneeLastName}`}
          </span>

          {task.labels.length > 0 && (
            <>
              <span className="task-detail__meta-label">Метки</span>
              <span className="task-detail__meta-value">
                <div className="tasks-section__label-chips">
                  {task.labels.map((label) => (
                    <span key={label.id} className="tasks-section__label-chip">
                      {label.name}
                    </span>
                  ))}
                </div>
              </span>
            </>
          )}
        </div>

        <div className="task-detail__comments">
          <span className="task-detail__comments-title">Комментарии</span>

          {commentsQuery.isLoading ? (
            <SkeletonRows count={2} />
          ) : (
            <div className="task-detail__comment-list">
              {(commentsQuery.data?.items.length ?? 0) === 0 ? (
                <span className="tasks-section__label-empty">Пока нет комментариев.</span>
              ) : (
                commentsQuery.data?.items.map((comment) => {
                  const authorName = `${comment.authorFirstName} ${comment.authorLastName}`;
                  const isOwn = comment.authorId === currentUserId;
                  const canDelete = isOwn || canManage;

                  return (
                    <div key={comment.id} className="task-detail__comment">
                      <div className="task-detail__comment-header">
                        <span className="task-detail__comment-author">{authorName}</span>
                        <div className="tasks-section__actions">
                          {isOwn && editingCommentId !== comment.id && (
                            <Button size="sm" variant="ghost" onClick={() => startEdit(comment)}>
                              Изменить
                            </Button>
                          )}
                          {canDelete &&
                            (armedDeleteId === comment.id ? (
                              <>
                                <Button
                                  size="sm"
                                  variant="danger"
                                  loading={deleteMutation.isPending}
                                  onClick={() => deleteMutation.mutate(comment.id)}
                                >
                                  Точно?
                                </Button>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => setArmedDeleteId(null)}
                                >
                                  Отмена
                                </Button>
                              </>
                            ) : (
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => {
                                  setArmedDeleteId(comment.id);
                                  setEditingCommentId(null);
                                }}
                              >
                                Удалить
                              </Button>
                            ))}
                        </div>
                      </div>
                      {editingCommentId === comment.id ? (
                        <div className="task-detail__comment-edit">
                          <textarea
                            className="field__input"
                            rows={2}
                            value={editingText}
                            onChange={(e) => setEditingText(e.target.value)}
                            maxLength={500}
                            autoFocus
                          />
                          <div className="tasks-section__actions">
                            <Button
                              size="sm"
                              loading={updateMutation.isPending}
                              onClick={() => submitEdit(comment.id)}
                            >
                              Сохранить
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => setEditingCommentId(null)}
                            >
                              Отмена
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <p className="task-detail__comment-text">{comment.text}</p>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          )}

          <form onSubmit={handleCommentSubmit} className="task-detail__comment-form">
            <textarea
              className="field__input"
              rows={2}
              placeholder="Написать комментарий…"
              value={newCommentText}
              onChange={(e) => setNewCommentText(e.target.value)}
              maxLength={500}
            />
            <Button
              type="submit"
              size="sm"
              loading={createMutation.isPending}
              disabled={!newCommentText.trim()}
            >
              Отправить
            </Button>
          </form>
        </div>
      </div>
    </Modal>
  );
}
