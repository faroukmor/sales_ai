const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

function errorMessage(status, payload) {
  const detail = payload?.detail
  if (typeof detail === 'string' && detail) return detail
  if (Array.isArray(detail) && detail.length) {
    return detail.map((item) => item?.msg || String(item)).join(' · ')
  }
  if (status >= 500) return `Server error (HTTP ${status}). Check the API logs: docker compose logs api`
  return `Request failed (HTTP ${status}).`
}

async function request(path, options = {}) {
  // Headers must be merged AFTER spreading the other options. Spreading `...options` last
  // would replace the whole headers object and silently drop Content-Type: application/json
  // on every write request (the API then answers 422).
  const { headers, ...rest } = options
  let response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      credentials: 'include',
      ...rest,
      headers: { 'Content-Type': 'application/json', ...headers },
    })
  } catch {
    throw new Error('Cannot reach the server. Check that the API container is running.')
  }
  if (response.status === 204) return null
  if (!response.ok) {
    let payload = null
    try { payload = await response.json() } catch { /* non-JSON error */ }
    throw new Error(errorMessage(response.status, payload))
  }
  return response.json()
}

let csrfToken = ''
export function setCsrfToken(value) { csrfToken = value || '' }
function write(path, options = {}) { return request(path, { ...options, headers: { 'X-CSRF-Token': csrfToken, ...options.headers } }) }

export const storeApi = {
  products(params = {}) { return request(`/api/products?${new URLSearchParams(Object.entries(params).filter(([, v]) => v !== '' && v != null))}`) },
  product(id) { return request(`/api/products/${id}`) },
  categories() { return request('/api/categories') },
  promotions() { return request('/api/promotions') },
  me() { return request('/api/auth/me') },
  register(data) { return request('/api/auth/register', { method: 'POST', body: JSON.stringify(data) }) },
  login(data) { return request('/api/auth/login', { method: 'POST', body: JSON.stringify(data) }) },
  logout() { return write('/api/auth/logout', { method: 'POST' }) },
  cart() { return request('/api/cart') },
  addCart(product_id, quantity = 1) { return write('/api/cart/items', { method: 'POST', body: JSON.stringify({ product_id, quantity }) }) },
  updateCart(id, quantity) { return write(`/api/cart/items/${id}`, { method: 'PATCH', body: JSON.stringify({ quantity }) }) },
  removeCart(id) { return write(`/api/cart/items/${id}`, { method: 'DELETE' }) },
  checkout(data) { return write('/api/orders/demo', { method: 'POST', body: JSON.stringify(data) }) },
  orders() { return request('/api/orders/me') },
  adminMe() { return request('/api/admin/me') },
  adminProducts(params = {}) { return request(`/api/admin/products?${new URLSearchParams(Object.entries(params).filter(([, v]) => v !== '' && v != null))}`) },
  createAdminProduct(data) { return write('/api/admin/products', { method: 'POST', body: JSON.stringify(data) }) },
  updateAdminProduct(id, data) { return write(`/api/admin/products/${id}`, { method: 'PATCH', body: JSON.stringify(data) }) },
  deleteAdminProduct(id) { return write(`/api/admin/products/${id}`, { method: 'DELETE' }) },
}

export const chatApi = {
  send(message, sessionId) {
    return request('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ message, session_id: sessionId || null }),
    })
  },
  health() { return request('/health') },
}
