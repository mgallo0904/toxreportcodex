import apiClient from './client.js';

/**
 * Create a new review session.
 *
 * @param {Object} data
 *   The session metadata including study_name (optional), study_type,
 *   draft_maturity and priority_notes (optional).
 * @returns {Promise<Object>}
 *   The created session object as returned by the backend.
 */
export async function createSession(data) {
  const response = await apiClient.post('/api/sessions', data, {
    headers: { 'Content-Type': 'application/json' },
  });
  return response.data;
}

/**
 * Retrieve a list of all sessions.
 *
 * @returns {Promise<Array>}
 *   Array of session summary objects.
 */
export async function listSessions() {
  const response = await apiClient.get('/api/sessions');
  return response.data;
}

/**
 * Fetch a single session with its documents.
 *
 * @param {string} sessionId
 *   The UUID of the session to fetch.
 * @returns {Promise<Object>}
 *   A detailed session object including attached documents.
 */
export async function getSession(sessionId) {
  const response = await apiClient.get(`/api/sessions/${sessionId}`);
  return response.data;
}

/**
 * Delete a session and all related data.
 *
 * @param {string} sessionId
 * @returns {Promise<void>}
 */
export async function deleteSession(sessionId) {
  await apiClient.delete(`/api/sessions/${sessionId}`);
}

/**
 * Confirm role assignment and start the mapping phase for a session.
 *
 * @param {string} sessionId
 *   Session identifier.
 * @returns {Promise<Object>}
 *   Response containing job status and job ID.
 */
export async function confirmSession(sessionId) {
  const response = await apiClient.post(`/api/sessions/${sessionId}/confirm`);
  return response.data;
}

/**
 * Retrieve Pass 1 processing status for a session.
 *
 * @param {string} sessionId
 *   Session identifier.
 * @returns {Promise<Object>}
 */
export async function getPass1Status(sessionId) {
  const response = await apiClient.get(`/api/sessions/${sessionId}/pass1/status`);
  return response.data;
}

/**
 * Retrieve the outline of all documents for a session.
 *
 * @param {string} sessionId
 *   Session identifier.
 * @returns {Promise<Object>}
 *   The outline tree object: { documents: [ ... ] }.
 */
export async function getOutline(sessionId) {
  const response = await apiClient.get(`/api/sessions/${sessionId}/outline`);
  return response.data;
}

/**
 * Retrieve all conflicts detected in a session.
 *
 * @param {string} sessionId
 *   Session identifier.
 * @returns {Promise<Array>}
 */
export async function getConflicts(sessionId) {
  const response = await apiClient.get(`/api/sessions/${sessionId}/conflicts`);
  return response.data;
}

/**
 * Retrieve all claims for a session with optional filters.
 * Note: this function accepts a params object which will be serialized
 * into the query string.
 *
 * @param {string} sessionId
 * @param {Object} params
 *   Optional query parameters (document_id, parameter_type).
 */
export async function getClaims(sessionId, params = {}) {
  const response = await apiClient.get(`/api/sessions/${sessionId}/claims`, { params });
  return response.data;
}

/**
 * Begin the deep review (Pass 2) for a session.
 *
 * This request sets the list of selected chunks and schedules the
 * backend job.  The server responds with a status summary.
 *
 * @param {string} sessionId
 *   Session identifier.
 * @param {Array<string>} selectedChunks
 *   Array of chunk UUIDs selected for deep review.
 * @returns {Promise<Object>}
 */
export async function startPass2(sessionId, selectedChunks) {
  const response = await apiClient.post(
    `/api/sessions/${sessionId}/review`,
    selectedChunks,
    {
      headers: { 'Content-Type': 'application/json' },
    },
  );
  return response.data;
}

/**
 * Retrieve Pass 2 processing status for a session.
 *
 * @param {string} sessionId
 *   Session identifier.
 * @returns {Promise<Object>}
 */
export async function getPass2Status(sessionId) {
  const response = await apiClient.get(`/api/sessions/${sessionId}/pass2/status`);
  return response.data;
}