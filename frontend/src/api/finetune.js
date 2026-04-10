import apiClient from './client.js';

/**
 * Start a new fine‑tune job.
 *
 * @param {Object} payload
 *   Contains base_model, session_ids, display_name and optional
 *   hyperparameters.
 * @returns {Promise<Object>}
 */
export async function createFinetuneJob(payload) {
  const response = await apiClient.post('/api/finetune/jobs', payload, {
    headers: { 'Content-Type': 'application/json' },
  });
  return response.data;
}

/**
 * List all fine‑tune jobs.
 *
 * @returns {Promise<Array>}
 */
export async function listFinetuneJobs() {
  const response = await apiClient.get('/api/finetune/jobs');
  return response.data;
}

/**
 * Fetch a single fine‑tune job by ID.
 *
 * @param {string} jobId
 * @returns {Promise<Object>}
 */
export async function getFinetuneJob(jobId) {
  const response = await apiClient.get(`/api/finetune/jobs/${jobId}`);
  return response.data;
}

/**
 * Fetch a summary of available training data.
 *
 * @param {string[]|null} sessionIds Optional list of session IDs to filter by.
 * @returns {Promise<Object>}
 */
export async function getTrainingDataSummary(sessionIds = null) {
  const params = {};
  if (sessionIds && sessionIds.length > 0) {
    // Provide session IDs as repeated query parameters
    params.session_ids = sessionIds;
  }
  const response = await apiClient.get('/api/finetune/training-data', { params });
  return response.data;
}

/**
 * Load a completed fine‑tune adapter as a new model configuration.
 *
 * @param {string} jobId
 * @returns {Promise<Object>}
 */
export async function loadFinetuneAdapter(jobId) {
  const response = await apiClient.post(`/api/finetune/jobs/${jobId}/load`);
  return response.data;
}