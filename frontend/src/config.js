export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';
export const MEDIA_BASE_URL = import.meta.env.VITE_MEDIA_BASE_URL || '';
export const DEV_MODE = String(import.meta.env.VITE_DEV_MODE).toLowerCase() === 'true';
export const DEV_AUTH_ENDPOINT =
  import.meta.env.VITE_DEV_AUTH_ENDPOINT || '/v1/dev/auth/{tg_user_id}';
export const TELEGRAM_BOT_USERNAME = import.meta.env.VITE_TELEGRAM_BOT_USERNAME || '';

export function resolveApiPath(path) {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }

  if (API_BASE_URL !== '/' && path.startsWith(`${API_BASE_URL.replace(/\/$/, '')}/`)) {
    return path;
  }

  return `${API_BASE_URL.replace(/\/$/, '')}${path}`;
}

export function resolveMediaUrl(filePath) {
  if (!filePath) {
    return '';
  }

  if (/^https?:\/\//i.test(filePath)) {
    return filePath;
  }

  const normalizedPath = filePath.startsWith('/') ? filePath : `/${filePath}`;
  if (normalizedPath.startsWith('/media/')) {
    return normalizedPath;
  }

  if (!MEDIA_BASE_URL) {
    return normalizedPath;
  }

  const normalizedBase = MEDIA_BASE_URL.replace(/\/$/, '');
  return `${normalizedBase}${normalizedPath}`;
}
