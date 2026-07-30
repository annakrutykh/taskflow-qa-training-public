import { useMemo, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { AuthLayout } from './AuthLayout';
import { useFormValidation, type Validator } from '../../hooks/useFormValidation';
import { useAuth } from '../../context/AuthContext';
import { ApiError } from '../../api/client';
import { isValidEmail, passwordStrengthError } from '../../utils/validators';
import '../../styles/forms.css';

interface RegisterValues extends Record<string, string> {
  firstName: string;
  lastName: string;
  email: string;
  password: string;
  confirmPassword: string;
}

const validate: Validator<RegisterValues> = (values) => {
  const errors: Partial<Record<keyof RegisterValues, string>> = {};

  if (!values.firstName.trim()) {
    errors.firstName = 'Введите имя';
  } else if (values.firstName.trim().length > 50) {
    errors.firstName = 'Не длиннее 50 символов';
  }

  if (!values.lastName.trim()) {
    errors.lastName = 'Введите фамилию';
  } else if (values.lastName.trim().length > 50) {
    errors.lastName = 'Не длиннее 50 символов';
  }

  if (!values.email) {
    errors.email = 'Введите email';
  } else if (!isValidEmail(values.email)) {
    errors.email = 'Похоже на невалидный email';
  }

  if (!values.password) {
    errors.password = 'Введите пароль';
  } else {
    const passwordError = passwordStrengthError(values.password);
    if (passwordError) errors.password = passwordError;
  }

  if (!values.confirmPassword) {
    errors.confirmPassword = 'Повторите пароль';
  } else if (values.confirmPassword !== values.password) {
    errors.confirmPassword = 'Пароли не совпадают';
  }

  return errors;
};

function passwordStrength(password: string): { level: 'weak' | 'fair' | 'strong'; label: string } {
  let score = 0;
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (/[0-9]/.test(password) && /[a-zA-Z]/.test(password)) score++;
  if (/[^a-zA-Z0-9]/.test(password)) score++;

  if (score <= 1) return { level: 'weak', label: 'слабый' };
  if (score <= 2) return { level: 'fair', label: 'средний' };
  return { level: 'strong', label: 'сильный' };
}

export function RegisterForm() {
  const { setField, blurField, validateAll, fieldState } = useFormValidation<RegisterValues>({
    initialValues: { firstName: '', lastName: '', email: '', password: '', confirmPassword: '' },
    validate,
  });
  const [showPassword, setShowPassword] = useState(false);
  const [shake, setShake] = useState(false);
  const { register: authRegister } = useAuth();
  const navigate = useNavigate();

  const register = useMutation({
    mutationFn: authRegister,
    onSuccess: () => navigate('/', { replace: true }),
  });

  const firstName = fieldState('firstName');
  const lastName = fieldState('lastName');
  const email = fieldState('email');
  const password = fieldState('password');
  const confirmPassword = fieldState('confirmPassword');
  const strength = useMemo(() => passwordStrength(password.value), [password.value]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!validateAll()) {
      triggerShake();
      return;
    }
    register.mutate(
      {
        firstName: firstName.value.trim(),
        lastName: lastName.value.trim(),
        email: email.value.trim(),
        password: password.value,
      },
      { onError: triggerShake },
    );
  };

  function triggerShake() {
    setShake(true);
    setTimeout(() => setShake(false), 340);
  }

  return (
    <AuthLayout
      eyebrow="QA Training Platform"
      title="Первая ошибка 404 будет твоей."
      subtitle="Регистрация даёт доступ к учебному API, Swagger, и данным для чек-листов и тест-кейсов."
    >
      <form
        className={`auth-form${shake ? ' form--shake' : ''}`}
        onSubmit={handleSubmit}
        noValidate
      >
        <div className="form-header">
          <h2 className="form-header__title">Регистрация</h2>
          <p className="form-header__hint">
            Уже есть аккаунт? <Link to="/login">Войти</Link>
          </p>
        </div>

        {register.isError && (
          <div className="form-banner" role="alert">
            {register.error instanceof ApiError ? register.error.message : 'Что-то пошло не так'}
          </div>
        )}

        <div className={`field${firstName.error ? ' field--invalid' : firstName.isValid ? ' field--valid' : ''}`}>
          <label className="field__label" htmlFor="firstName">
            Имя
          </label>
          <div className="field__input-wrap">
            <input
              id="firstName"
              className="field__input"
              autoComplete="given-name"
              placeholder="Иван"
              value={firstName.value}
              onChange={(e) => setField('firstName', e.target.value)}
              onBlur={() => blurField('firstName')}
              aria-invalid={Boolean(firstName.error)}
            />
          </div>
          {firstName.error && <span className="field__error">{firstName.error}</span>}
        </div>

        <div className={`field${lastName.error ? ' field--invalid' : lastName.isValid ? ' field--valid' : ''}`}>
          <label className="field__label" htmlFor="lastName">
            Фамилия
          </label>
          <div className="field__input-wrap">
            <input
              id="lastName"
              className="field__input"
              autoComplete="family-name"
              placeholder="Иванов"
              value={lastName.value}
              onChange={(e) => setField('lastName', e.target.value)}
              onBlur={() => blurField('lastName')}
              aria-invalid={Boolean(lastName.error)}
            />
          </div>
          {lastName.error && <span className="field__error">{lastName.error}</span>}
        </div>

        <div className={`field${email.error ? ' field--invalid' : email.isValid ? ' field--valid' : ''}`}>
          <label className="field__label" htmlFor="email">
            Email
          </label>
          <div className="field__input-wrap">
            <input
              id="email"
              className="field__input"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              value={email.value}
              onChange={(e) => setField('email', e.target.value)}
              onBlur={() => blurField('email')}
              aria-invalid={Boolean(email.error)}
            />
          </div>
          {email.error && <span className="field__error">{email.error}</span>}
        </div>

        <div className={`field${password.error ? ' field--invalid' : password.isValid ? ' field--valid' : ''}`}>
          <label className="field__label" htmlFor="password">
            <span>Пароль</span>
            {password.value.length > 0 && (
              <span className="field__strength" data-level={strength.level}>
                {strength.label}
              </span>
            )}
          </label>
          <div className="field__input-wrap">
            <input
              id="password"
              className="field__input"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              placeholder="мин. 8 символов, включая A-Z, a-z, 0-9"
              value={password.value}
              onChange={(e) => setField('password', e.target.value)}
              onBlur={() => blurField('password')}
              aria-invalid={Boolean(password.error)}
              style={{ paddingRight: 56 }}
            />
            <button
              type="button"
              className="field__toggle-visibility"
              onClick={() => setShowPassword((v) => !v)}
              tabIndex={-1}
            >
              {showPassword ? 'СКРЫТЬ' : 'ПОКАЗАТЬ'}
            </button>
          </div>
          {password.error && <span className="field__error">{password.error}</span>}
        </div>

        <div
          className={`field${confirmPassword.error ? ' field--invalid' : confirmPassword.isValid ? ' field--valid' : ''}`}
        >
          <label className="field__label" htmlFor="confirmPassword">
            Повторите пароль
          </label>
          <div className="field__input-wrap">
            <input
              id="confirmPassword"
              className="field__input"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              placeholder="••••••••"
              value={confirmPassword.value}
              onChange={(e) => setField('confirmPassword', e.target.value)}
              onBlur={() => blurField('confirmPassword')}
              aria-invalid={Boolean(confirmPassword.error)}
            />
          </div>
          {confirmPassword.error && <span className="field__error">{confirmPassword.error}</span>}
        </div>

        <button
          type="submit"
          className={`form-submit${register.isPending ? ' form-submit--loading' : ''}`}
          disabled={register.isPending}
        >
          Создать аккаунт
        </button>
      </form>
    </AuthLayout>
  );
}
