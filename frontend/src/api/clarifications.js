import apiClient from './client.js';

/**
 * Fetch clarifications for a session.
 *
 * @param {string} sessionId
 *   Session identifier.
 * @param {string} [status]
 *   Optional status filter (pending, answered, dismissed).  If
 *   provided, only clarifications with the given status are
 *   returned.
 * @returns {Promise<Array>}
 */
export async function getClarifications(sessionId, status) {
  const params = {};
  if (status) params.status_filter = status;
  const response = await apiClient.get(`/api/sessions/${sessionId}/clarifications`, { params });
  return response.data;
}

/**
 * Submit an answer to a clarification.
 *
 * @param {string} clarificationId
 *   Clarification UUID.
 * @param {string} answerText
 *   The answer text.
 * @returns {Promise<Object>}
 */
export async function answerClarification(clarificationId, answerText) {
  const response = await apiClient.post(
    `/api/clarifications/${clarificationId}/answer`,
    { answer_text: answerText },
    { headers: { 'Content-Type': 'application/json' } },
  );
  return response.data;
}

/**
 * Dismiss a clarification as irrelevant.
 *
 * @param {string} clarificationId
 *   Clarification UUID.
 * @returns {Promise<Object>}
 */
export async function dismissClarification(clarificationId) {
  const response = await apiClient.post(`/api/clarifications/${clarificationId}/dismiss`);
  return response.data;
}