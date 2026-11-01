export async function apiRequest(path, options = {}) {
  let response;
  try {
    response = await fetch(path, {
      ...options,
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...options.headers },
    });
  } catch {
    throw new Error('Unable to reach the Founders-Only server. Make sure the backend is running.');
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || 'The request could not be completed.');
  return data;
}
