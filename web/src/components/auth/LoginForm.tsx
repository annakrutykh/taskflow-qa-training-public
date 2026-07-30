import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { AuthLayout } from './AuthLayout';
import { useFormValidation, type Validator } from '../../hooks/useFormValidation';
import { useAuth } from '../../context/AuthContext';
import { ApiError } from '../../api/client';
import { isValidEmail } from '../../utils/validators';
import '../../styles/forms.css';

interface LoginValues extends Record<string, string> {
  email: string;
  password: string;
}

const validate: Validator<LoginValues> = (values) => {
  const errors: Partial<Record<keyof LoginValues, string>> = {};

  if (!values.email) {
    errors.email = 'Введите email';
  } else if (!isValidEmail(values.email)) {
    errors.email = 'Похоже на невалидный email';
  }

  if (!values.password) {
    errors.password = 'Введите пароль';
  }

  return errors;
};

export function LoginForm() {
  const { setField, blurField, validateAll, fieldState } = useFormValidation<LoginValues>({
    initialValues: { email: '', password: '' },
    validate,
  });
  const [showPassword, setShowPassword] = useState(false);
  const [shake, setShake] = useState(false);
  const { login: authLogin } = useAuth();
  const navigate = useNavigate();

  const login = useMutation({
    mutationFn: authLogin,
    onSuccess: () => navigate('/', { replace: true }),
  });

  const email = fieldState('email');
  const password = fieldState('password');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!validateAll()) {
      triggerShake();
      return;
    }
    login.mutate(
      { email: email.value, password: password.value },
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
      title="Учись тестировать так, как в бою."
      subtitle="Реальный backend, реальные баги, реальные ревью. Без песочницы — сразу рабочая среда."
    >
      <form
        className={`auth-form${shake ? ' form--shake' : ''}`}
        onSubmit={handleSubmit}
        noValidate
      >
        <div className="form-header">
          <h2 className="form-header__title">Вход</h2>
          <p className="form-header__hint">
            Нет аккаунта? <Link to="/register">Зарегистрироваться</Link>
          </p>
        </div>

        {login.isError && (
          <div className="form-banner" role="alert">
            {login.error instanceof ApiError ? login.error.message : 'Что-то пошло не так'}
          </div>
        )}

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
              aria-describedby={email.error ? 'email-error' : undefined}
            />
          </div>
          {email.error && (
            <span className="field__error" id="email-error">
              {email.error}
            </span>
          )}
        </div>

        <div className={`field${password.error ? ' field--invalid' : password.isValid ? ' field--valid' : ''}`}>
          <label className="field__label" htmlFor="password">
            Пароль
          </label>
          <div className="field__input-wrap">
            <input
              id="password"
              className="field__input"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              placeholder="••••••••"
              value={password.value}
              onChange={(e) => setField('password', e.target.value)}
              onBlur={() => blurField('password')}
              aria-invalid={Boolean(password.error)}
              aria-describedby={password.error ? 'password-error' : undefined}
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
          {password.error && (
            <span className="field__error" id="password-error">
              {password.error}
            </span>
          )}
        </div>

        <button
          type="submit"
          className={`form-submit${login.isPending ? ' form-submit--loading' : ''}`}
          disabled={login.isPending}
        >
          Войти
        </button>
      </form>
    </AuthLayout>
  );
}
