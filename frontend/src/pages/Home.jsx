import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { listSessions, deleteSession } from '../api/sessions.js';

/**
 * Home page showing history of review sessions.
 *
 * Displays a table listing all sessions with their basic metadata
 * (study name, type, maturity, status, creation date).  Each row
 * includes a "Resume" button that navigates to the correct screen
 * based on the session's status and a "Delete" button that removes
 * the session from the database and storage.
 */
function Home() {
  const [sessions, setSessions] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    async function fetchSessions() {
      try {
        const data = await listSessions();
        setSessions(data);
      } catch (err) {
        const message = err.response?.data?.detail || err.message;
        setError(message);
      } finally {
        setLoading(false);
      }
    }
    fetchSessions();
  }, []);

  function resumePathForStatus(session) {
    switch (session.status) {
      case 'uploading':
      case 'roles_assigned':
        return `/sessions/${session.id}/assign-roles`;
      case 'mapping':
        return `/sessions/${session.id}/pass1`;
      case 'section_selection':
        return `/sessions/${session.id}/sections`;
      case 'reviewing':
        return `/sessions/${session.id}/pass2`;
      case 'complete':
        return `/sessions/${session.id}/findings`;
      default:
        return `/sessions/${session.id}/assign-roles`;
    }
  }

  async function handleDelete(sessionId) {
    const confirmed = window.confirm('Are you sure you want to delete this session? This cannot be undone.');
    if (!confirmed) return;
    try {
      await deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
    } catch (err) {
      const message = err.response?.data?.detail || err.message;
      alert(message);
    }
  }

  if (loading) {
    return <div>Loading sessions…</div>;
  }
  if (error) {
    return <div style={{ color: 'red' }}>Error: {error}</div>;
  }
  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
      <h1>Session History</h1>
      <p>
        Manage your existing review sessions. You can resume unfinished reviews
        or delete sessions you no longer need.
      </p>
      <div style={{ marginBottom: '1rem' }}>
        <Link to="/sessions/new" style={{ padding: '.5rem 1rem', background: '#2d9cdb', color: 'white', borderRadius: '4px', textDecoration: 'none' }}>
          New Session
        </Link>
      </div>
      {sessions.length === 0 ? (
        <p>No sessions found. Click "New Session" to start a review.</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', padding: '.5rem', borderBottom: '1px solid #ddd' }}>Study Name</th>
              <th style={{ textAlign: 'left', padding: '.5rem', borderBottom: '1px solid #ddd' }}>Type</th>
              <th style={{ textAlign: 'left', padding: '.5rem', borderBottom: '1px solid #ddd' }}>Maturity</th>
              <th style={{ textAlign: 'left', padding: '.5rem', borderBottom: '1px solid #ddd' }}>Status</th>
              <th style={{ textAlign: 'left', padding: '.5rem', borderBottom: '1px solid #ddd' }}>Created</th>
              <th style={{ textAlign: 'left', padding: '.5rem', borderBottom: '1px solid #ddd' }}>Updated</th>
              <th style={{ padding: '.5rem', borderBottom: '1px solid #ddd' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((session) => (
              <tr key={session.id}>
                <td style={{ padding: '.5rem', borderBottom: '1px solid #f0f0f0' }}>{session.study_name || 'Untitled'}</td>
                <td style={{ padding: '.5rem', borderBottom: '1px solid #f0f0f0' }}>{session.study_type}</td>
                <td style={{ padding: '.5rem', borderBottom: '1px solid #f0f0f0' }}>{session.draft_maturity}</td>
                <td style={{ padding: '.5rem', borderBottom: '1px solid #f0f0f0' }}>{session.status}</td>
                <td style={{ padding: '.5rem', borderBottom: '1px solid #f0f0f0' }}>{new Date(session.created_at).toLocaleString()}</td>
                <td style={{ padding: '.5rem', borderBottom: '1px solid #f0f0f0' }}>{new Date(session.updated_at).toLocaleString()}</td>
                <td style={{ padding: '.5rem', borderBottom: '1px solid #f0f0f0', whiteSpace: 'nowrap' }}>
                  <button
                    onClick={() => navigate(resumePathForStatus(session))}
                    style={{ marginRight: '.5rem', padding: '.25rem .75rem', background: '#2d9cdb', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                  >
                    Resume
                  </button>
                  <button
                    onClick={() => handleDelete(session.id)}
                    style={{ padding: '.25rem .75rem', background: '#b23c17', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default Home;