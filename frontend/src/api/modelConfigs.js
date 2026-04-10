import apiClient from './client.js';

/**
 * Retrieve all model configurations.
 *
 * @returns {Promise<Array>}
 */
export async function listModelConfigs() {
  const response = await apiClient.get('/api/model-configs');
  return response.data;
}

/**
 * Activate a model configuration by ID.
 *
 * @param {string} modelId
 * @returns {Promise<Object>}
 */
export async function activateModelConfig(modelId) {
  const response = await apiClient.post(`/api/model-configs/${modelId}/activate`);
  return response.data;
}