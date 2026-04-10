import axios from 'axios';

/**
 * Centralised Axios instance for all HTTP requests to the backend API.
 *
 * The base URL is provided by the Vite environment variable
 * `VITE_API_BASE_URL`. See `render.yaml` for deployment configuration.
 */
// The central Axios client used throughout the frontend.  Note that
// no default Content‑Type header is set here; this allows us to
// correctly send both JSON and multipart form data.  Individual
// requests can override headers as needed (for example when
// uploading files).  The base URL is configured via the Vite
// environment variable `VITE_API_BASE_URL` or falls back to
// localhost during development.
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
});

export default apiClient;