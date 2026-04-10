import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getClarifications, answerClarification, dismissClarification } from '../api/clarifications.js';

/**
 * ClarificationsPage allows the user to view and respond to
 * clarification questions generated during Pass 2.
 *
 * The page displays all pending clarifications for the session.  For
 * each question, the user may either provide a textual answer or
 * dismiss the question.  Once answered or dismissed, the
 * clarification disappears from the list.  When no pending
 * clarifications remain, the page offers a button to return to the
 * progress or findings view.
 */
function ClarificationsPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [clarifications, setClarifications] = useState([]);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  // Local state for answer inputs keyed by clarification ID
  const [answers, setAnswers] = useState({});

  // Fetch pending clarifications on mount
  useEffect(() => {
    async function fetchData() {
      try {
        const data = await getClarifications(sessionId, 'pending');
        setClarifications(data);
      } catch (err) {
        const message = err.response?.data?.detail || err.message;
        setError(message);
      }
    }
    fetchData();
  }, [sessionId]);

  async function handleAnswer(id) {
    const text = answers[id];
    if (!text || text.trim() === '') {
      alert('Please enter an answer.');
      return;
    }
    setBusy(true);
    try {
      await answerClarification(id, text);
      // Remove answered clarification from list
      setClarifications((prev) => prev.filter((c) => c.id !== id));
      // Remove answer state
      setAnswers((prev) => {
        const newAnswers = { ...prev };
        delete newAnswers[id];
        return newAnswers;
      });
    } catch (err) {
      const message = err.response?.data?.detail || err.message;
      alert(message);
    } finally {
      setBusy(false);
    }
  }

  async function handleDismiss(id) {
    if (!window.confirm('Are you sure you want to dismiss this clarification?')) {
      return;
    }
    setBusy(true);
    try {
      await dismissClarification(id);
      setClarifications((prev) => prev.filter((c) => c.id !== id));
    } catch (err) {
      const message = err.response?.data?.detail || err.message;
      alert(message);
    } finally {
      setBusy(false);
    }
  }

  if (error) {
    return <div style={{ color: 'red' }}>Error: {error}</div>;
  }
  // When no pending clarifications
  if (clarifications.length === 0) {
    return (
      <div style={{ maxWidth: '600px', margin: '0 auto' }}>
        <h2>No Pending Clarifications</h2>
        <p>All clarifications have been resolved. You may return to the review.</p>
        <button
          onClick={() => navigate(`/sessions/${sessionId}/pass2`)}
          style={{ padding: '.75rem 1.5rem', background: '#2d9cdb', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          Back to Progress
        </button>
      </div>
    );
  }
  return (
    <div style={{ maxWidth: '800px', margin: '0 auto' }}>
      <h2>Clarifications</h2>
      <p>Please answer or dismiss each question to continue the review.</p>
      {clarifications.map((clar) => (
        <div key={clar.id} style={{ border: '1px solid #ddd', borderRadius: '4px', padding: '1rem', marginBottom: '1rem' }}>
          <p>
            <strong>{clar.document_name || 'Unknown document'}</strong>{' '}
            {clar.page_range ? `(p. ${clar.page_range})` : ''}
          </p>
          <p style={{ marginTop: '.25rem' }}>{clar.question_text}</p>
          <textarea
            value={answers[clar.id] || ''}
            onChange={(e) => setAnswers({ ...answers, [clar.id]: e.target.value })}
            placeholder="Type your answer here…"
            rows={3}
            style={{ width: '100%', marginTop: '.5rem' }}
          />
          <div style={{ marginTop: '.5rem' }}>
            <button
              onClick={() => handleAnswer(clar.id)}
              disabled={busy}
              style={{ padding: '.5rem 1rem', marginRight: '.5rem', background: '#2d9cdb', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
            >
              Submit Answer
            </button>
            <button
              onClick={() => handleDismiss(clar.id)}
              disabled={busy}
              style={{ padding: '.5rem 1rem', background: '#b23c17', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
            >
              Dismiss
            </button>
          </div>
        </div>
      ))}
      <div style={{ marginTop: '1rem' }}>
        <button
          onClick={() => navigate(`/sessions/${sessionId}/pass2`)}
          style={{ padding: '.75rem 1.5rem', background: '#6c757d', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          Back to Progress
        </button>
      </div>
    </div>
  );
}

export default ClarificationsPage;