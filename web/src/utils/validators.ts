// Регексп из WHATWG HTML living standard (тот же, что браузеры используют
// для <input type="email">) — разумный баланс строгости для клиентской
// UX-подсказки. Не заменяет серверную проверку (EmailStr на бэке),
// только быстрая обратная связь до отправки формы.
export const EMAIL_REGEX =
  /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$/;

export function isValidEmail(email: string): boolean {
  return EMAIL_REGEX.test(email);
}

/** Совпадает с проверкой на бэке (app/schemas.py, Register.password) —
 * держим оба места в синхроне, иначе форма пропустит то, что потом
 * отклонит API (или наоборот, как уже случалось). */
export function passwordStrengthError(password: string): string | null {
  if (password.length < 8) return "Минимум 8 символов";
  if (password.length > 64) return "Не длиннее 64 символов";
  if (!/[a-z]/.test(password)) return "Нужна строчная буква";
  if (!/[A-Z]/.test(password)) return "Нужна заглавная буква";
  if (!/\d/.test(password)) return "Нужна цифра";
  return null;
}
