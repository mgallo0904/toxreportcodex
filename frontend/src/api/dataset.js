import apiClient from './client.js';

/**
 * Retrieve the fine‑tuning dataset for a session.
 *
 * The dataset consists of records for each confirmed finding.  See
 * backend/services/dataset_builder.py for details.
 *
 * @param {string} sessionId
 * @returns {Promise<Array>}
 */
export async function getDataset(sessionId) {
  const response = await apiClient.get(`/api/sessions/${sessionId}/dataset`);
  return response.data;
}