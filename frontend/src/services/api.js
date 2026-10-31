export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/backend'

async function request(path, options = {}, token = null) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      Accept: 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.body && !(options.body instanceof URLSearchParams) && !(options.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    },
  })

  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json')
    ? await response.json()
    : await response.text()

  if (!response.ok) {
    const detail = typeof payload === 'object' && payload !== null
      ? payload.detail || payload.message
      : payload
    const message = typeof detail === 'string'
      ? detail
      : detail && typeof detail === 'object' && detail.message
        ? detail.message
        : detail
          ? JSON.stringify(detail)
          : `Error HTTP ${response.status}`
    throw new Error(message)
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

export function loginWithGoogle(idToken) {
  return request('/users/v1/auth/google', {
    method: 'POST',
    body: JSON.stringify({ id_token: idToken }),
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

export function getCurrentUser(token) {
  return request('/me/', {}, token)
}

export function listProducts(search = '') {
  const query = new URLSearchParams({ limit: '100' })
  if (search) query.set('search', search)
  return request(`/products/?${query.toString()}`)
}

export function listProductSections() {
  return request('/products/sections')
}

export function createProduct(formData, token) {
  return request('/products/', { method: 'POST', body: formData }, token)
}

export function updateProductPrice(productId, price, token) {
  return request(`/products/${productId}/price`, {
    method: 'PATCH',
    body: JSON.stringify({ price }),
  }, token)
}

export function addCartItem(productId, quantity, token) {
  return request('/cart/items', {
    method: 'POST',
    body: JSON.stringify({ product_id: productId, quantity }),
  }, token)
}

export function getCart(token) {
  return request('/cart/', {}, token)
}

export function removeCartItem(productId, token) {
  return request(`/cart/items/${productId}`, { method: 'DELETE' }, token)
}

export function checkoutOrder(data, idempotencyKey, token) {
  return request('/orders/checkout', {
    method: 'POST',
    headers: { 'Idempotency-Key': idempotencyKey },
    body: JSON.stringify(data),
  }, token)
}

export function getMyOrders(token) {
  return request('/orders/me', {}, token)
}

export function updateProductStock(productId, stock, token) {
  return request(`/products/${productId}/stock`, {
    method: 'PATCH',
    body: JSON.stringify({ stock }),
  }, token)
}

export function getPackagingOrders(token, returned = false) {
  return request(returned ? '/orders/packaging/returned' : '/orders/packaging/pending', {}, token)
}

export function markOrderPackaged(orderId, token) {
  return request(`/orders/${orderId}/packaged`, { method: 'POST' }, token)
}

export function getAssignedOrders(token) {
  return request('/orders/courier/assigned', {}, token)
}

export function updateDeliveryStatus(orderId, deliveryStatus, token) {
  return request(`/orders/${orderId}/delivery-status`, {
    method: 'PATCH',
    body: JSON.stringify({ delivery_status: deliveryStatus }),
  }, token)
}

export function confirmCashPayment(orderId, token) {
  return request(`/orders/${orderId}/cash-payment`, {
    method: 'PATCH',
    body: JSON.stringify({ payment_status: 'succeeded' }),
  }, token)
}

export function getReadyForAssignment(token) {
  return request('/orders/ready-for-assignment', {}, token)
}

export function getActiveCouriers(token) {
  return request('/orders/couriers', {}, token)
}

export function assignCourier(orderId, courierId, token) {
  return request(`/orders/${orderId}/assign-courier/${courierId}`, { method: 'POST' }, token)
}
