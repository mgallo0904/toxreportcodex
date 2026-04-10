import apiClient from './client.js';

/**
 * Upload one or more documents to a session.
 *
 * Each file is appended under the "files" key in a multipart form
 * data payload.  The backend will create Document records and
 * immediately process the files.
 *
 * @param {string} sessionId
 *   UUID of the session.
 * @param {FileList|Array<File>} files
 *   List of File objects selected by the user.
 * @returns {Promise<Array>}
 *   Array of created document objects including chunk counts.
 */
export async function uploadDocuments(sessionId, files) {
  const formData = new FormData();
  Array.from(files).forEach((file) => {
    formData.append('files', file);
  });
  const response = await apiClient.post(`/api/sessions/${sessionId}/documents`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

/**
 * Retrieve all documents for a given session.
 *
 * @param {string} sessionId
 *   UUID of the session.
 * @returns {Promise<Array>}
 *   Array of document objects.
 */
export async function listDocuments(sessionId) {
  const response = await apiClient.get(`/api/sessions/${sessionId}/documents`);
  return response.data;
}

/**
 * Update a document's assigned role or label.
 *
 * @param {string} sessionId
 *   UUID of the session.
 * @param {string} documentId
 *   UUID of the document.
 * @param {Object} data
 *   Object containing assigned_role and/or role_label keys.
 * @returns {Promise<Object>}
 *   Updated document object.
 */
export async function updateDocument(sessionId, documentId, data) {
  const response = await apiClient.patch(
    `/api/sessions/${sessionId}/documents/${documentId}`,
    data,
    {
      headers: { 'Content-Type': 'application/json' },
    },
  );
  return response.data;
}

/**
 * Delete a document from a session.
 *
 * @param {string} sessionId
 *   UUID of the session.
 * @param {string} documentId
 *   UUID of the document.
 * @returns {Promise<Object>}
 *   Response object indicating deletion.
 */
export async function deleteDocument(sessionId, documentId) {
  const response = await apiClient.delete(`/api/sessions/${sessionId}/documents/${documentId}`);
  return response.data;
}