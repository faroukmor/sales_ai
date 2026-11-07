export function readSessionValue(key) {
  try {
    return window.sessionStorage?.getItem(key) ?? null
  } catch {
    return null
  }
}

export function writeSessionValue(key, value) {
  try {
    window.sessionStorage?.setItem(key, value)
    return true
  } catch {
    return false
  }
}

export function removeSessionValue(key) {
  try {
    window.sessionStorage?.removeItem(key)
  } catch {
    // The conversation still resets in memory when browser storage is unavailable.
  }
}

export function createClientId() {
  try {
    if (typeof globalThis.crypto?.randomUUID === 'function') return globalThis.crypto.randomUUID()
  } catch {
    // Use the non-security fallback below for React list identity only.
  }
  return `local-${Date.now()}-${Math.random().toString(16).slice(2)}`
}
