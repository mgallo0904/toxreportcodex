import apiClient from './client.js';

/**
 * Fetch findings for a session.
 *
 * Query parameters may be supplied to filter by severity,
 * confidence or confirmation state.  See backend documentation
 * for accepted values.
 *
 * @param {string} sessionId
 * @param {Object} params
 *   Optional query parameters.
 * @returns {Promise<Array>}
 */
export async function getFindings(sessionId, params = {}) {
  const response = await apiClient.get(`/api/sessions/${sessionId}/findings`, { params });
  return response.data;
}

/**
 * Retrieve a single finding by its ID.
 *
 * @param {string} findingId
 * @returns {Promise<Object>}
 */
export async function getFinding(findingId) {
  const response = await apiClient.get(`/api/findings/${findingId}`);
  return response.data;
}

/**
 * Confirm or reject a finding.
 *
 * The update object should include a `confirm` boolean and may
 * optionally override other fields (category, comment,
 * recommendation, severity) before confirmation.  See
 * backend/schemas/finding.py for details.
 *
 * @param {string} findingId
 * @param {Object} update
 * @returns {Promise<Object>}
 */
export async function confirmFinding(findingId, update) {
  const response = await apiClient.post(
    `/api/findings/${findingId}/confirm`,
    update,
    { headers: { 'Content-Type': 'application/json' } },
  );
  return response.data;
}

/**
 * Export findings and clarifications for a session as an Excel file.
 *
 * Accepts optional query parameters for filtering.  The backend
 * returns a binary Excel file.  This function sets responseType
 * to 'blob' so that Axios returns a Blob which can be converted
 * to a download link.
 *
 * @param {string} sessionId
 * @param {Object} params
 *   Optional filters: severity, category, document_id, confidence, confirmed.
 * @returns {Promise<Blob>}
 */
export async function exportFindings(sessionId, params = {}) {
  const response = await apiClient.get(
    `/api/sessions/${sessionId}/findings/export`,
    {
      params,
      responseType: 'blob',
    },
  );
  return response.data;
}