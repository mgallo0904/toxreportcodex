import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createSession } from '../api/sessions.js';
import { uploadDocuments } from '../api/documents.js';

/**
 * UploadPage allows users to initiate a new review session and upload
 * study documents.  The form collects basic study metadata and
 * accepts multiple files.  After creating the session and uploading
 * documents, the user is redirected to the role assignment page.
 */
function UploadPage() {
  const navigate = useNavigate();
  // Form state
  const [studyName, setStudyName] = useState('');
  const [studyType, setStudyType] = useState('GLP');
  const [draftMaturity, setDraftMaturity] = useState('Early Draft');
  const [priorityNotes, setPriorityNotes] = useState('');
  const [files, setFiles] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    setFiles(e.target.files);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!files || files.length === 0) {
      setError('Please select at least one file.');
      return;
    }
    setSubmitting(true);
    try {
      // Create session with provided metadata
      const payload = {
        study_name: studyName || null,
        study_type: studyType,
        draft_maturity: draftMaturity,
        priority_notes: priorityNotes || null,
      };
      const session = await createSession(payload);
      // Upload documents
      await uploadDocuments(session.id, files);
      // Redirect to role assignment page
      navigate(`/sessions/${session.id}/assign-roles`);
    } catch (err) {
      // Attempt to extract error message
      const message = err.response?.data?.detail || err.message;
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: '600px', margin: '0 auto' }}>
      <h2>Create New Session & Upload Documents</h2>
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '1rem' }}>
          <label htmlFor="studyName" style={{ display: 'block', marginBottom: '.25rem' }}>
            Study Name (optional)
          </label>
          <input
            id="studyName"
            type="text"
            value={studyName}
            onChange={(e) => setStudyName(e.target.value)}
            style={{ width: '100%', padding: '.5rem' }}
          />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label htmlFor="studyType" style={{ display: 'block', marginBottom: '.25rem' }}>
            Study Type
          </label>
          <select
            id="studyType"
            value={studyType}
            onChange={(e) => setStudyType(e.target.value)}
            style={{ width: '100%', padding: '.5rem' }}
          >
            <option value="GLP">GLP</option>
            <option value="Non-GLP">Non-GLP</option>
          </select>
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label htmlFor="draftMaturity" style={{ display: 'block', marginBottom: '.25rem' }}>
            Draft Maturity
          </label>
          <select
            id="draftMaturity"
            value={draftMaturity}
            onChange={(e) => setDraftMaturity(e.target.value)}
            style={{ width: '100%', padding: '.5rem' }}
          >
            <option value="Early Draft">Early Draft</option>
            <option value="Near-Final">Near-Final</option>
            <option value="Final">Final</option>
          </select>
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label htmlFor="priorityNotes" style={{ display: 'block', marginBottom: '.25rem' }}>
            Priority Notes (optional)
          </label>
          <textarea
            id="priorityNotes"
            value={priorityNotes}
            onChange={(e) => setPriorityNotes(e.target.value)}
            rows={3}
            style={{ width: '100%', padding: '.5rem' }}
          />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label htmlFor="files" style={{ display: 'block', marginBottom: '.25rem' }}>
            Select Files (PDF, DOCX, XLSX)
          </label>
          <input
            id="files"
            type="file"
            accept=".pdf,.docx,.xlsx"
            multiple
            onChange={handleFileChange}
          />
        </div>
        {error && <p style={{ color: 'red', marginBottom: '1rem' }}>{error}</p>}
        <button type="submit" disabled={submitting} style={{ padding: '.75rem 1.5rem' }}>
          {submitting ? 'Uploading…' : 'Create Session & Upload'}
        </button>
      </form>
    </div>
  );
}

export default UploadPage;