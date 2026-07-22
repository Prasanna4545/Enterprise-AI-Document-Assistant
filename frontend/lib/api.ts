export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1').replace(/\/$/, '');

export async function parseJsonResponse(res: Response) {
  const contentType = res.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) {
    const text = await res.text();
    throw new Error(`Backend returned non-JSON response (${res.status}): ${text.slice(0, 100)}`);
  }
  return await res.json();
}

export async function fetchWithAuth(url: string, options: RequestInit = {}) {
  let token = localStorage.getItem('access_token');

  const headers = new Headers(options.headers || {});
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const endpoint = url.startsWith('http') ? url : `${API_BASE_URL}${url.startsWith('/') ? '' : '/'}${url}`;

  let response = await fetch(endpoint, {
    ...options,
    headers,
  });

  // Handle token refresh if 401
  if (response.status === 401 && !url.includes('/auth/login') && !url.includes('/auth/refresh')) {
    const refreshToken = localStorage.getItem('refresh_token');
    if (refreshToken) {
      try {
        const refreshRes = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (refreshRes.ok) {
          const data = await parseJsonResponse(refreshRes);
          localStorage.setItem('access_token', data.access_token);
          localStorage.setItem('refresh_token', data.refresh_token);

          // Retry original request with new token
          headers.set('Authorization', `Bearer ${data.access_token}`);
          response = await fetch(endpoint, {
            ...options,
            headers,
          });
        } else {
          // Token refresh failed -> Logout
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      } catch (err) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
      }
    }
  }

  return response;
}
