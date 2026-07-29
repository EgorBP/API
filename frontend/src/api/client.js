import { DEV_AUTH_ENDPOINT, resolveApiPath } from '../config.js';

const TOKENS_KEY = 'auth_tokens';

// --- Работа с локальным хранилищем токенов ---
export function getStoredTokens() {
  try {
    const raw = localStorage.getItem(TOKENS_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setStoredTokens(tokens) {
  if (tokens) {
    localStorage.setItem(TOKENS_KEY, JSON.stringify(tokens));
  } else {
    localStorage.removeItem(TOKENS_KEY);
  }
  // Уведомляем хуки/компоненты об изменении токена
  window.dispatchEvent(new CustomEvent('auth:tokens-changed', { detail: tokens }));
}

export function clearStoredTokens() {
  setStoredTokens(null);
}

export class ApiError extends Error {
  constructor(message, status, payload) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
  }
}

function appendQuery(url, query = {}) {
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return;
    }

    const values = Array.isArray(value) ? value : [value];
    values.forEach((item) => {
      if (item !== undefined && item !== null && item !== '') {
        url.searchParams.append(key, String(item));
      }
    });
  });
}

async function parseResponse(response) {
  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return response.json();
  }

  return response.text();
}

// --- Защита от параллельных запросов на Refresh ---
let isRefreshing = false;
let refreshSubscribers = [];

function subscribeTokenRefresh(callback) {
  refreshSubscribers.push(callback);
}

function onRefreshed(newToken) {
  refreshSubscribers.forEach((callback) => callback(newToken));
  refreshSubscribers = [];
}

function onRefreshFailed(error) {
  refreshSubscribers.forEach((callback) => callback(null, error));
  refreshSubscribers = [];
}

async function request(path, options = {}) {
  const { token, query, headers, body, _isRetry, ...rest } = options;
  
  // Авто-подстановка токена из хранилища, если он не передан явно
  const storedTokens = getStoredTokens();
  const effectiveToken = token || storedTokens?.access_token;

  const url = new URL(resolveApiPath(path), window.location.origin);
  appendQuery(url, query);

  const requestHeaders = new Headers(headers);
  if (effectiveToken) {
    requestHeaders.set('Authorization', `Bearer ${effectiveToken}`);
  }
  if (body && !(body instanceof FormData) && !requestHeaders.has('Content-Type')) {
    requestHeaders.set('Content-Type', 'application/json');
  }

  const response = await fetch(url, {
    ...rest,
    headers: requestHeaders,
    body: body && !(body instanceof FormData) ? JSON.stringify(body) : body,
  });

  const payload = await parseResponse(response);

  if (!response.ok) {
    const isAuthEndpoint =
      path.includes('/auth/refresh') ||
      path.includes('/auth/telegram') ||
      path.includes('/auth/dev');

    // Перехват 401 ошибки для авто-ревалидации токена
    if (response.status === 401 && !_isRetry && !isAuthEndpoint) {
      const refreshToken = storedTokens?.refresh_token;

      if (refreshToken) {
        if (!isRefreshing) {
          isRefreshing = true;

          try {
            // Вызываем метод рефреша
            const newTokens = await api.auth.refresh(refreshToken);
            setStoredTokens(newTokens);
            isRefreshing = false;
            onRefreshed(newTokens.access_token);
          } catch (refreshErr) {
            isRefreshing = false;
            clearStoredTokens();
            onRefreshFailed(refreshErr);

            const detail = Array.isArray(payload?.detail)
              ? payload.detail.map((item) => item.msg).join('; ')
              : payload?.detail || payload?.message || response.statusText;
            throw new ApiError(detail || 'Сессия истекла. Войдите заново.', response.status, payload);
          }
        }

        // Если рефреш уже выполняется — ждем его завершения и повторяем текущий запрос
        return new Promise((resolve, reject) => {
          subscribeTokenRefresh((newToken, err) => {
            if (err || !newToken) {
              const detail = Array.isArray(payload?.detail)
                ? payload.detail.map((item) => item.msg).join('; ')
                : payload?.detail || payload?.message || response.statusText;
              reject(new ApiError(detail || 'API request failed', response.status, payload));
            } else {
              // Повторяем запрос с новым токеном
              resolve(request(path, { ...options, token: newToken, _isRetry: true }));
            }
          });
        });
      } else {
        clearStoredTokens();
      }
    }

    const detail = Array.isArray(payload?.detail)
      ? payload.detail.map((item) => item.msg).join('; ')
      : payload?.detail || payload?.message || response.statusText;
    throw new ApiError(detail || 'API request failed', response.status, payload);
  }

  return payload;
}

function makeUploadForm(file, tags) {
  const form = new FormData();
  tags.forEach((tag) => form.append('tags', tag));
  form.append('file', file);
  return form;
}

export const api = {
  auth: {
    telegram: async (payload) => {
      const res = await request('/v1/web/auth/telegram', {
        method: 'POST',
        body: payload,
      });
      if (res?.access_token) setStoredTokens(res);
      return res;
    },
    devLogin: async (tgUserId) => {
      const path = DEV_AUTH_ENDPOINT.replace('{tg_user_id}', encodeURIComponent(tgUserId));
      const res = await request(path, { method: 'POST' });
      if (res?.access_token) setStoredTokens(res);
      return res;
    },
    refresh: (refreshToken) =>
      request('/v1/web/auth/refresh', {
        method: 'POST',
        body: { refresh_token: refreshToken },
      }),
    logout: async (token) => {
      try {
        await request('/v1/web/auth/logout', { method: 'POST', token });
      } finally {
        clearStoredTokens();
      }
    },
  },
  web: {
    me: (token) => request('/v1/web/users/me', { token }),
    deleteMe: (token) => request('/v1/web/users/me', { method: 'DELETE', token }),
    count: (token) => request('/v1/web/users/me/gifs/count', { token }),
    tags: (token) => request('/v1/web/users/me/tags/all', { token }),
    gifs: (token, query) => request('/v1/web/users/me/gifs', { token, query }),
    deleteGifs: (token, gifIds) =>
      request('/v1/web/users/me/gifs', {
        method: 'DELETE',
        token,
        query: { gif_ids: gifIds },
      }),
    upload: (token, file, tags) =>
      request('/v1/web/users/me/gifs/new', {
        method: 'POST',
        token,
        body: makeUploadForm(file, tags),
      }),
    updateTags: (token, gifId, tags) =>
      request(`/v1/web/users/me/gifs/${gifId}/tags`, {
        method: 'PUT',
        token,
        body: tags,
      }),
  },
  public: {
    searchGifs: (query) => request('/v1/gifs', { query }),
    popularGifs: () => request('/v1/gifs/popular'),
    popularTagsForGif: (gifId, limit) =>
      request(`/v1/gifs/${gifId}/popular/tags`, { query: { limit } }),
    popularTags: () => request('/v1/tags/popular'),
  },
};
