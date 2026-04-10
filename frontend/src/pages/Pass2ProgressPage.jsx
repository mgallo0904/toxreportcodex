import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getPass2Status } from '../api/sessions.js';

/**
 * Pass2ProgressPage shows real‑time progress of the deep review phase.
 *
 * It polls the backend every few seconds for updated status
 * information.  While the review is running it displays a progress
 * bar, current document and page range, pending clarification count
 * and severity counts.  Once all chunks are processed, it shows a
 * summary with counts of critical, moderate and minor findings and
 * provides links to clarifications (if any remain) and findings
 * review.
 */
function Pass2ProgressPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let timerId;
    async function poll() {
      try {
        const data = await getPass2Status(sessionId);
        setStatus(data);
        // Stop polling if complete
        if (data.status === 'complete') {
          clearInterval(timerId);
        }
      } catch (err) {
        const message = err.response?.data?.detail || err.message;
        setError(message);
        clearInterval(timerId);
      }
    }
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
  const total = status.total_selected || 0;
  const completed = status.completed_selected || 0;
  const percent = total ? completed / total : 0;
  // When complete, show summary and navigation options
  if (status.status === 'complete') {
    return (
      <div style={{ maxWidth: '600px', margin: '0 auto' }}>
        <h2>Deep Review Complete</h2>
        <p>
          {completed} of {total} sections processed.
        </p>
        <p>
          Findings: <strong>{status.critical_count}</strong> critical,{' '}
          <strong>{status.moderate_count}</strong> moderate,{' '}
          <strong>{status.minor_count}</strong> minor.
        </p>
        {status.pending_clarifications > 0 ? (
          <div style={{ marginBottom: '1rem', color: '#b23c17' }}>
            There are still {status.pending_clarifications} pending clarifications. Please answer or
            dismiss them before finalizing findings.
            <br />
            <button
              onClick={() => navigate(`/sessions/${sessionId}/clarifications`)}
              style={{ marginTop: '.5rem', padding: '.5rem 1rem' }}
            >
              Answer Clarifications
            </button>
          </div>
        ) : null}
        <button
          onClick={() => navigate(`/sessions/${sessionId}/findings`)}
          style={{ padding: '.75rem 1.5rem', background: '#2d9cdb', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          Review Findings
        </button>
      </div>
    );
  }
  // Otherwise show ongoing progress
  return (
    <div style={{ maxWidth: '700px', margin: '0 auto' }}>
      <h2>Deep Review Progress</h2>
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
        {completed}/{total} sections reviewed
      </p>
      <p>
        Current: {status.current_document || '—'} {status.current_pages ? `(p. ${status.current_pages})` : ''}
      </p>
      <p>
        Pending clarifications: {status.pending_clarifications || 0}{' '}
        {status.pending_clarifications > 0 && (
          <button
            onClick={() => navigate(`/sessions/${sessionId}/clarifications`)}
            style={{ marginLeft: '.5rem', padding: '.25rem .5rem', fontSize: '.8rem' }}
          >
            View
          </button>
        )}
      </p>
      <p>
        Findings so far: <strong>{status.critical_count}</strong> critical,{' '}
        <strong>{status.moderate_count}</strong> moderate,{' '}
        <strong>{status.minor_count}</strong> minor.
      </p>
      <div style={{ maxHeight: '200px', overflowY: 'auto', border: '1px solid #ddd', padding: '.5rem', marginTop: '1rem' }}>
        {status.log && status.log.length > 0 ? (
          status.log.map((entry, idx) => (
            <div key={idx} style={{ marginBottom: '.25rem' }}>
              <small>
                {entry.timestamp}: {entry.document} {entry.pages ? `(p. ${entry.pages})` : ''} — {entry.status}
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

export default Pass2ProgressPage;