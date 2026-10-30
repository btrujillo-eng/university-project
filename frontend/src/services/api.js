const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/backend'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      Accept: 'application/json',
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    },
  })

  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json')
    ? await response.json()
    : await response.text()

  if (!response.ok) {
    const message = typeof payload === 'object' && payload !== null
      ? payload.detail || payload.message
      : payload
    throw new Error(message || `Error HTTP ${response.status}`)
  }

  return payload
}

export function registerUser(form) {
  return request('/register/user/', {
    method: 'POST',
    body: JSON.stringify({
      first_name: form.first_name.trim(),
      middle_name: form.middle_name.trim() || null,
      first_surname: form.first_surname.trim(),
      middle_surname: form.middle_surname.trim() || null,
      contact_info: { email: form.email.trim() },
      password: form.password,
    }),
  })
}

export function loginUser(email, password) {
  const body = new URLSearchParams({ username: email.trim(), password })
  return request('/users/v1/auth/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
}

export function requestRestoreCode(email) {
  return request('/users/v1/auth/password/restore-code', {
    method: 'POST',
    body: JSON.stringify({ email: email.trim() }),
  })
}

export function verifyRestoreCode(email, restore_code) {
  return request('/users/v1/auth/password/verify', {
    method: 'POST',
    body: JSON.stringify({ email: email.trim(), restore_code }),
  })
}

export function resetPassword(email, restore_code, new_password) {
  return request('/users/v1/auth/password/reset', {
    method: 'POST',
    body: JSON.stringify({ email: email.trim(), restore_code, new_password }),
  })
}
