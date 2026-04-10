import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getFindings, confirmFinding, exportFindings } from '../api/findings.js';

/**
 * FindingsPage presents all findings generated during Pass 2 and
 * allows the user to confirm or reject each one.  Users may also
 * edit certain fields before confirmation.  Once all findings are
 * decided, a message indicates that review is complete.
 */
function FindingsPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [findings, setFindings] = useState([]);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);
  // Local edit state keyed by finding ID
  const [edits, setEdits] = useState({});
  // Filter state for table and export
  const [filters, setFilters] = useState({
    severity: '',
    category: '',
    document_id: '',
    confidence: '',
    confirmed: '',
  });

  // List of documents for filter dropdown (extracted from findings)
  const [documents, setDocuments] = useState([]);

  useEffect(() => {
    async function fetchData() {
      try {
        const data = await getFindings(sessionId, {});
        setFindings(data);
        // Build document list from findings
        const docs = Array.from(new Set(data.map((f) => f.document_id).filter(Boolean)));
        setDocuments(docs);
      } catch (err) {
        const message = err.response?.data?.detail || err.message;
        setError(message);
      }
    }
    fetchData();
  }, [sessionId]);

  async function handleDecision(findingId, confirmFlag) {
    // Build update object: merge edits if present
    const edit = edits[findingId] || {};
    const update = { ...edit, confirm: confirmFlag };
    setBusyId(findingId);
    try {
      const updated = await confirmFinding(findingId, update);
      // Replace finding in list
      setFindings((prev) => prev.map((f) => (f.id === findingId ? updated : f)));
      // Remove edit state
      setEdits((prev) => {
        const n = { ...prev };
        delete n[findingId];
        return n;
      });
    } catch (err) {
      const message = err.response?.data?.detail || err.message;
      alert(message);
    } finally {
      setBusyId(null);
    }
  }

  function handleEditChange(findingId, field, value) {
    setEdits((prev) => {
      const entry = prev[findingId] || {};
      return { ...prev, [findingId]: { ...entry, [field]: value } };
    });
  }

  // Handle filter value change
  function handleFilterChange(name, value) {
    setFilters((prev) => ({ ...prev, [name]: value }));
  }

  // Apply filters to refetch findings
  async function applyFilters() {
    try {
      // Remove empty strings from filters to avoid sending them as params
      const params = {};
      Object.entries(filters).forEach(([k, v]) => {
        if (v) params[k] = v;
      });
      const data = await getFindings(sessionId, params);
      setFindings(data);
      const docs = Array.from(new Set(data.map((f) => f.document_id).filter(Boolean)));
      setDocuments(docs);
    } catch (err) {
      const message = err.response?.data?.detail || err.message;
      setError(message);
    }
  }

  // Export current filtered findings and clarifications
  async function handleExport() {
    try {
      const params = {};
      Object.entries(filters).forEach(([k, v]) => {
        if (v) params[k] = v;
      });
      const blob = await exportFindings(sessionId, params);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `session_${sessionId}_findings.xlsx`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      const message = err.response?.data?.detail || err.message;
      alert(message);
    }
  }

  if (error) {
    return <div style={{ color: 'red' }}>Error: {error}</div>;
  }
  // Sort findings by severity then label for readability
  const severityOrder = { Critical: 0, Moderate: 1, Minor: 2, null: 3, undefined: 3 };
  const sortedFindings = [...findings].sort((a, b) => {
    const sa = severityOrder[a.severity] ?? 3;
    const sb = severityOrder[b.severity] ?? 3;
    if (sa !== sb) return sa - sb;
    return (a.finding_label || '').localeCompare(b.finding_label || '');
  });
  const undecided = sortedFindings.filter((f) => f.confirmed_correct === null || f.confirmed_correct === undefined);
  return (
    <div style={{ maxWidth: '900px', margin: '0 auto' }}>
      <h2>Findings Review</h2>
      {/* Filter controls */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', marginBottom: '1rem', alignItems: 'flex-end' }}>
        <div>
          <label>
            Severity:
            <select value={filters.severity} onChange={(e) => handleFilterChange('severity', e.target.value)}>
              <option value="">All</option>
              <option value="Critical">Critical</option>
              <option value="Moderate">Moderate</option>
              <option value="Minor">Minor</option>
            </select>
          </label>
        </div>
        <div>
          <label>
            Category:
            <input
              type="text"
              value={filters.category}
              onChange={(e) => handleFilterChange('category', e.target.value)}
              placeholder="Any"
            />
          </label>
        </div>
        <div>
          <label>
            Document:
            <select value={filters.document_id} onChange={(e) => handleFilterChange('document_id', e.target.value)}>
              <option value="">All</option>
              {documents.map((docId) => (
                <option key={docId} value={docId}>{docId}</option>
              ))}
            </select>
          </label>
        </div>
        <div>
          <label>
            Confidence:
            <select value={filters.confidence} onChange={(e) => handleFilterChange('confidence', e.target.value)}>
              <option value="">All</option>
              <option value="standard">Standard</option>
              <option value="low">Low</option>
            </select>
          </label>
        </div>
        <div>
          <button onClick={applyFilters} style={{ padding: '.5rem 1rem' }}>Apply Filters</button>
        </div>
        <div style={{ marginLeft: 'auto' }}>
          <button onClick={handleExport} style={{ padding: '.5rem 1rem', background: '#6c757d', color: 'white', border: 'none', borderRadius: '4px' }}>Export to Excel</button>
        </div>
      </div>
      {sortedFindings.length === 0 ? (
        <p>No findings were generated.</p>
      ) : (
        <>
          <p>
            Confirm or reject each finding. Edits to category, comment,
            recommendation or severity will be saved upon confirmation.
          </p>
          {sortedFindings.map((finding) => (
            <div key={finding.id} style={{ border: '1px solid #ddd', borderRadius: '4px', padding: '1rem', marginBottom: '1rem' }}>
              <p style={{ fontWeight: 'bold' }}>
                {finding.finding_label || 'Unlabelled'} — {finding.severity || 'Unclassified'}
              </p>
              <p>
                <strong>{finding.document_name || 'Unknown document'}</strong>{' '}
                {finding.page_range ? `(p. ${finding.page_range})` : ''}
              </p>
              {finding.original_text && (
                <blockquote style={{ fontStyle: 'italic', borderLeft: '4px solid #ccc', margin: '.5rem 0', paddingLeft: '.5rem' }}>
                  {finding.original_text}
                </blockquote>
              )}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
                <div style={{ flex: '1 1 200px' }}>
                  <label>
                    Category:
                    <input
                      type="text"
                      value={edits[finding.id]?.category ?? finding.category ?? ''}
                      onChange={(e) => handleEditChange(finding.id, 'category', e.target.value)}
                      style={{ width: '100%' }}
                    />
                  </label>
                </div>
                <div style={{ flex: '1 1 200px' }}>
                  <label>
                    Severity:
                    <select
                      value={edits[finding.id]?.severity ?? finding.severity ?? ''}
                      onChange={(e) => handleEditChange(finding.id, 'severity', e.target.value)}
                      style={{ width: '100%' }}
                    >
                      <option value="">Select…</option>
                      <option value="Critical">Critical</option>
                      <option value="Moderate">Moderate</option>
                      <option value="Minor">Minor</option>
                    </select>
                  </label>
                </div>
              </div>
              <div style={{ marginTop: '.5rem' }}>
                <label>
                  Comment:
                  <textarea
                    value={edits[finding.id]?.comment ?? finding.comment ?? ''}
                    onChange={(e) => handleEditChange(finding.id, 'comment', e.target.value)}
                    rows={2}
                    style={{ width: '100%' }}
                  />
                </label>
              </div>
              <div style={{ marginTop: '.5rem' }}>
                <label>
                  Recommendation:
                  <textarea
                    value={edits[finding.id]?.recommendation ?? finding.recommendation ?? ''}
                    onChange={(e) => handleEditChange(finding.id, 'recommendation', e.target.value)}
                    rows={2}
                    style={{ width: '100%' }}
                  />
                </label>
              </div>
              <div style={{ marginTop: '.75rem', display: 'flex', gap: '.5rem' }}>
                {finding.confirmed_correct === null || finding.confirmed_correct === undefined ? (
                  <>
                    <button
                      onClick={() => handleDecision(finding.id, true)}
                      disabled={busyId === finding.id}
                      style={{ padding: '.5rem 1rem', background: '#2d9cdb', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                    >
                      Confirm Correct
                    </button>
                    <button
                      onClick={() => handleDecision(finding.id, false)}
                      disabled={busyId === finding.id}
                      style={{ padding: '.5rem 1rem', background: '#b23c17', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                    >
                      Mark Incorrect
                    </button>
                  </>
                ) : (
                  <span>
                    {finding.confirmed_correct ? 'Confirmed' : 'Rejected'} at{' '}
                    {new Date(finding.confirmed_at).toLocaleString()}
                  </span>
                )}
              </div>
            </div>
          ))}
          {undecided.length === 0 ? (
            <div style={{ padding: '1rem', background: '#e6f4ea', borderRadius: '4px' }}>
              <p>All findings have been reviewed. Thank you!</p>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <button
                  onClick={() => navigate(`/sessions/${sessionId}`)}
                  style={{ padding: '.75rem 1.5rem', background: '#6c757d', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                >
                  Back to Session
                </button>
                <button
                  onClick={() => navigate(`/sessions/${sessionId}/dataset`)}
                  style={{ padding: '.75rem 1.5rem', background: '#2d9cdb', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                >
                  View Dataset / Fine‑Tune
                </button>
              </div>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}

export default FindingsPage;