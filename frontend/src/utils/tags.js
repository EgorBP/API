export function parseCsv(value) {
  return String(value || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

export function uniqueTags(value) {
  return [...new Set(parseCsv(value))];
}
