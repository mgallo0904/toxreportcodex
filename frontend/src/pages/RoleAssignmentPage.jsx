import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { listDocuments, updateDocument } from '../api/documents.js';
import { confirmSession } from '../api/sessions.js';

/**
 * RoleAssignmentPage allows users to assign roles to each uploaded
 * document within a session.  The roles correspond to the type of
 * material represented in the document (e.g. Test Article, Control
 * Article, Reference Standard).  Users can also provide an optional
 * descriptive label.  After saving, the user can proceed to the next
 * step in the review process.
 */
function RoleAssignmentPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [docs, setDocs] = useState([]);
  const [assignments, setAssignments] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    // Fetch documents for the session on mount
    async function fetchDocs() {
      setLoading(true);
      try {
        const data = await listDocuments(sessionId);
        setDocs(data);
        // Initialise assignments from existing document values
        const initial = {};
        data.forEach((doc) => {
          initial[doc.id] = {
            assigned_role: doc.assigned_role || '',
            role_label: doc.role_label || '',
          };
        });
        setAssignments(initial);
      } catch (err) {
        const message = err.response?.data?.detail || err.message;
        setError(message);
      } finally {
        setLoading(false);
      }
    }
    fetchDocs();
  }, [sessionId]);

  const handleRoleChange = (docId, value) => {
    setAssignments((prev) => ({
      ...prev,
      [docId]: {
        ...prev[docId],
        assigned_role: value,
      },
    }));
  };

  const handleLabelChange = (docId, value) => {
    setAssignments((prev) => ({
      ...prev,
      [docId]: {
        ...prev[docId],
        role_label: value,
      },
    }));
  };

  // Persist assignments to the backend
  const saveAssignments = async () => {
    for (const doc of docs) {
      const values = assignments[doc.id];
      await updateDocument(sessionId, doc.id, values);
    }
    const refreshed = await listDocuments(sessionId);
    setDocs(refreshed);
  };

  // Determine if all documents have a role assigned
  const allAssigned = docs.length > 0 && docs.every((doc) => {
    const values = assignments[doc.id] || {};
    return values.assigned_role && values.assigned_role !== '';
  });

  const handleConfirm = async () => {
    setError(null);
    setSaving(true);
    try {
      // Save assignments first
      await saveAssignments();
      // Confirm session and start mapping
      await confirmSession(sessionId);
      // Navigate to Pass 1 progress page
      navigate(`/sessions/${sessionId}/pass1`);
    } catch (err) {
      const message = err.response?.data?.detail || err.message;
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <p>Loading documents…</p>;
  }

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto' }}>
      <h2>Assign Roles</h2>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {docs.length === 0 ? (
        <p>No documents found for this session.</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '.5rem' }}>Filename</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '.5rem' }}>Format</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '.5rem' }}>Total Pages</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '.5rem' }}>Total Chunks</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '.5rem' }}>Role</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: '.5rem' }}>Label (optional)</th>
            </tr>
          </thead>
          <tbody>
            {docs.map((doc) => (
              <tr key={doc.id}>
                <td style={{ padding: '.5rem', borderBottom: '1px solid #f0f0f0' }}>{doc.original_filename}</td>
                <td style={{ padding: '.5rem', borderBottom: '1px solid #f0f0f0' }}>{doc.format}</td>
                <td style={{ padding: '.5rem', borderBottom: '1px solid #f0f0f0' }}>{
                  doc.total_pages != null ? doc.total_pages : '—'
                }</td>
                <td style={{ padding: '.5rem', borderBottom: '1px solid #f0f0f0' }}>{
                  doc.total_chunks != null ? doc.total_chunks : '—'
                }</td>
                <td style={{ padding: '.5rem', borderBottom: '1px solid #f0f0f0' }}>
                  <select
                    value={assignments[doc.id]?.assigned_role || ''}
                    onChange={(e) => handleRoleChange(doc.id, e.target.value)}
                    style={{ width: '100%', padding: '.25rem' }}
                  >
                    <option value="">Select a role</option>
                    <option value="Primary Report (Final)">Primary Report (Final)</option>
                    <option value="Primary Report (Draft)">Primary Report (Draft)</option>
                    <option value="Study Protocol">Study Protocol</option>
                    <option value="Protocol Amendment">Protocol Amendment</option>
                    <option value="Bioanalytical/PK Sub-report">Bioanalytical/PK Sub-report</option>
                    <option value="Histopathology Sub-report">Histopathology Sub-report</option>
                    <option value="Raw Data Appendix">Raw Data Appendix</option>
                    <option value="Other">Other</option>
                  </select>
                </td>
                <td style={{ padding: '.5rem', borderBottom: '1px solid #f0f0f0' }}>
                  {assignments[doc.id]?.assigned_role === 'Other' ? (
                    <input
                      type="text"
                      value={assignments[doc.id]?.role_label || ''}
                      onChange={(e) => handleLabelChange(doc.id, e.target.value)}
                      placeholder="Enter role description"
                      style={{ width: '100%', padding: '.25rem' }}
                    />
                  ) : (
                    <span style={{ color: '#888' }}>—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div style={{ marginTop: '1rem' }}>
        <button
          onClick={handleConfirm}
          disabled={saving || !allAssigned}
          style={{ padding: '.75rem 1.5rem' }}
        >
          {saving ? 'Confirming…' : 'Confirm and Start Mapping'}
        </button>
      </div>
    </div>
  );
}

export default RoleAssignmentPage;