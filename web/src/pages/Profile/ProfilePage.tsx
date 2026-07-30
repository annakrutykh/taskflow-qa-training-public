import { type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button, Card, useToast } from "../../components";
import { updateProfile } from "../../api/auth";
import { ApiError } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { useFormValidation, type Validator } from "../../hooks/useFormValidation";
import { USER_ROLE_LABEL } from "../../constants/labels";
import "../../styles/forms.css";
import "./ProfilePage.css";

interface ProfileValues extends Record<string, string> {
  firstName: string;
  lastName: string;
}

const validateProfile: Validator<ProfileValues> = (values) => {
  const errors: Partial<Record<keyof ProfileValues, string>> = {};
  if (!values.firstName.trim()) errors.firstName = "Введите имя";
  else if (values.firstName.trim().length > 50) errors.firstName = "Не длиннее 50 символов";
  if (!values.lastName.trim()) errors.lastName = "Введите фамилию";
  else if (values.lastName.trim().length > 50) errors.lastName = "Не длиннее 50 символов";
  return errors;
};

export function ProfilePage() {
  const { user, updateUser } = useAuth();
  const { showToast } = useToast();

  const { setField, blurField, validateAll, fieldState, values } = useFormValidation<ProfileValues>({
    initialValues: { firstName: user?.firstName ?? "", lastName: user?.lastName ?? "" },
    validate: validateProfile,
  });
  const firstName = fieldState("firstName");
  const lastName = fieldState("lastName");

  const mutation = useMutation({
    mutationFn: () =>
      updateProfile({ firstName: values.firstName.trim(), lastName: values.lastName.trim() }),
    onSuccess: (updated) => {
      updateUser(updated);
      showToast("Профиль обновлён", "success");
    },
    onError: (error) => {
      showToast(error instanceof ApiError ? error.message : "Не удалось обновить профиль", "error");
    },
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!validateAll()) return;
    mutation.mutate();
  }

  if (!user) return null;

  return (
    <div className="profile-page">
      <h1 className="profile-page__title">Профиль</h1>
      <Card>
        <form onSubmit={handleSubmit} noValidate>
          {mutation.isError && (
            <div className="form-banner" role="alert">
              {mutation.error instanceof ApiError ? mutation.error.message : "Что-то пошло не так"}
            </div>
          )}
          <div className="field">
            <label className="field__label" htmlFor="profile-email">
              Email
            </label>
            <div className="field__input-wrap">
              <input id="profile-email" className="field__input" value={user.email} disabled />
            </div>
            <span className="field__hint">Email нельзя изменить.</span>
          </div>
          <div className={`field${firstName.error ? " field--invalid" : ""}`}>
            <label className="field__label" htmlFor="profile-first-name">
              Имя
            </label>
            <div className="field__input-wrap">
              <input
                id="profile-first-name"
                className="field__input"
                value={firstName.value}
                onChange={(e) => setField("firstName", e.target.value)}
                onBlur={() => blurField("firstName")}
              />
            </div>
            {firstName.error && <span className="field__error">{firstName.error}</span>}
          </div>
          <div className={`field${lastName.error ? " field--invalid" : ""}`}>
            <label className="field__label" htmlFor="profile-last-name">
              Фамилия
            </label>
            <div className="field__input-wrap">
              <input
                id="profile-last-name"
                className="field__input"
                value={lastName.value}
                onChange={(e) => setField("lastName", e.target.value)}
                onBlur={() => blurField("lastName")}
              />
            </div>
            {lastName.error && <span className="field__error">{lastName.error}</span>}
          </div>
          <div className="field">
            <label className="field__label" htmlFor="profile-role">
              Роль
            </label>
            <div className="field__input-wrap">
              <input
                id="profile-role"
                className="field__input"
                value={USER_ROLE_LABEL[user.role]}
                disabled
              />
            </div>
          </div>
          <Button type="submit" loading={mutation.isPending}>
            Сохранить
          </Button>
        </form>
      </Card>
    </div>
  );
}
