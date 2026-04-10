import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getPass1Status } from '../api/sessions.js';

/**
 * Pass1ProgressPage displays real‑time progress information about the
 * structural mapping phase.  It polls the backend every 3 seconds to
 * obtain updated counts and log entries.  When mapping is complete
 * (status transitions to `section_selection`), the page shows a
 * summary banner with the number of conflicts detected and a button
 * to proceed to section selection.
 */
function Pass1ProgressPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let timerId;
    async function poll() {
      try {
        const data = await getPass1Status(sessionId);
        setStatus(data);
        if (data.status === 'section_selection') {
          clearInterval(timerId);
        }
      } catch (err) {
        const message = err.response?.data?.detail || err.message;
        setError(message);
        clearInterval(timerId);
      }
    }
    // Initial call and poll every 3 seconds
    poll();
    timerId = setInterval(poll, 3000);
    return () => clearInterval(timerId);
  }, [sessionId]);

  if (error) {
    return <div style={{ color: 'red' }}>Error: {error}</div>;
  }
  if (!status) {
    return <p>Loading…</p>;
  }
  // If mapping complete, show summary
  if (status.status === 'section_selection') {
    return (
      <div style={{ maxWidth: '600px', margin: '0 auto' }}>
        <h2>Mapping Complete</h2>
        <p>
          {status.completed_chunks} of {status.total_chunks} chunks processed.{' '}
          {status.sections_indexed ?? 0} sections indexed, {status.claims_extracted ?? 0} claims extracted, {status.conflicts_found} conflicts detected.
        </p>
        <button
          onClick={() => navigate(`/sessions/${sessionId}/sections`)}
          style={{ padding: '.75rem 1.5rem' }}
        >
          Select Sections for Review
        </button>
      </div>
    );
  }
  // Ongoing mapping
  const percent = status.total_chunks ? status.completed_chunks / status.total_chunks : 0;
  return (
    <div style={{ maxWidth: '700px', margin: '0 auto' }}>
      <h2>Structural Mapping Progress</h2>
      <div style={{ width: '100%', background: '#eee', height: '24px', borderRadius: '4px', overflow: 'hidden', marginBottom: '1rem' }}>
        <div
          style={{
            width: `${(percent * 100).toFixed(1)}%`,
            background: '#2d9cdb',
            height: '100%',
            transition: 'width 0.5s ease',
          }}
        />
      </div>
      <p>
        {status.completed_chunks}/{status.total_chunks} chunks completed
      </p>
      <p>Current: {status.current_document || '—'} {status.current_pages || ''}</p>
      <p>Conflicts detected so far: {status.conflicts_found}</p>
      <div style={{ maxHeight: '200px', overflowY: 'auto', border: '1px solid #ddd', padding: '.5rem', marginTop: '1rem' }}>
        {status.log && status.log.length > 0 ? (
          status.log.map((entry, idx) => (
            <div key={idx} style={{ marginBottom: '.25rem' }}>
              <small>
                {entry.timestamp}: {entry.document} {entry.pages || ''} — {entry.status}
              </small>
            </div>
          ))
        ) : (
          <small>No log entries yet.</small>
        )}
      </div>
    </div>
  );
}

export default Pass1ProgressPage;