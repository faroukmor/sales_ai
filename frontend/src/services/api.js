const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!response.ok) {
    let detail = 'The assistant is unavailable.'
    try { detail = (await response.json()).detail || detail } catch { /* non-JSON error */ }
    throw new Error(detail)
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
