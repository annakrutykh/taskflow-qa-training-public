import { useCallback, useState } from 'react';

export type Validator<T> = (values: T) => Partial<Record<keyof T, string>>;

interface UseFormValidationOptions<T> {
  initialValues: T;
  validate: Validator<T>;
}

/**
 * Small, dependency-free form hook — не привязан к auth, используется
 * везде, где нужна валидация полей (Login/Register, создание проекта,
 * добавление участника и т.д.).
 * - Validates on every change once a field has been touched (or on submit).
 * - Exposes per-field error + "valid" state for styling (.field--invalid / .field--valid).
 * - Deliberately does NOT validate on first render, so empty fields don't show red instantly.
 */
export function useFormValidation<T extends Record<string, string>>({
  initialValues,
  validate,
}: UseFormValidationOptions<T>) {
  const [values, setValues] = useState<T>(initialValues);
  const [touched, setTouched] = useState<Partial<Record<keyof T, boolean>>>({});
  const [errors, setErrors] = useState<Partial<Record<keyof T, string>>>({});

  const runValidation = useCallback(
    (next: T) => {
      const nextErrors = validate(next);
      setErrors(nextErrors);
      return nextErrors;
    },
    [validate],
  );

  const setField = useCallback(
    (name: keyof T, value: string) => {
      // Функциональная форма — иначе два setField подряд в одном
      // обработчике (например, предзаполнение формы редактирования)
      // оба читают values из одного и того же устаревшего замыкания,
      // и второй вызов затирает изменение первого.
      setValues((current) => {
        const next = { ...current, [name]: value };
        if (touched[name]) runValidation(next);
        return next;
      });
    },
    [touched, runValidation],
  );

  const blurField = useCallback(
    (name: keyof T) => {
      setTouched((t) => ({ ...t, [name]: true }));
      runValidation(values);
    },
    [values, runValidation],
  );

  /** Call on submit. Marks every field touched and returns whether the form is valid. */
  const validateAll = useCallback(() => {
    const allTouched = Object.keys(values).reduce(
      (acc, key) => ({ ...acc, [key]: true }),
      {} as Partial<Record<keyof T, boolean>>,
    );
    setTouched(allTouched);
    const nextErrors = runValidation(values);
    return Object.keys(nextErrors).length === 0;
  }, [values, runValidation]);

  const fieldState = (name: keyof T) => ({
    value: values[name],
    error: touched[name] ? errors[name] : undefined,
    isValid: touched[name] && !errors[name] && values[name].length > 0,
  });

  return { values, setField, blurField, validateAll, fieldState };
}
