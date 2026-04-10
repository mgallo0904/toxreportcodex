import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getTrainingDataSummary,
  createFinetuneJob,
  listFinetuneJobs,
  loadFinetuneAdapter,
} from '../api/finetune.js';

/**
 * FinetunePage provides a management interface for fine‑tuning models.
 *
 * It displays a summary of available training data (number of confirmed findings
 * by severity and which sessions are included), allows the user to select
 * which sessions to include in a new job, specify hyperparameters, and
 * launch a fine‑tune job.  A list of past jobs with status indicators is
 * shown below, and completed jobs can be registered as model configurations.
 */
function FinetunePage() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [loadingSummary, setLoadingSummary] = useState(true);
  const [jobs, setJobs] = useState([]);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [selectedSessionIds, setSelectedSessionIds] = useState([]);
  // Form fields
  const [baseModel, setBaseModel] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [rank, setRank] = useState('');
  const [alpha, setAlpha] = useState('');
  const [epochs, setEpochs] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [loadingAction, setLoadingAction] = useState(false);

  // Load training summary on mount
  useEffect(() => {
    async function fetchSummary() {
      setLoadingSummary(true);
      try {
        const data = await getTrainingDataSummary();
        setSummary(data);
        // Default to including all sessions with training data
        if (data.sessions_included) {
          const ids = data.sessions_included.map((s) => s.id);
          setSelectedSessionIds(ids);
        }
      } catch (err) {
        // eslint-disable-next-line no-console
        console.error(err);
        setSummary(null);
      } finally {
        setLoadingSummary(false);
      }
    }
    fetchSummary();
  }, []);

  // Load jobs on mount and after actions
  async function fetchJobs() {
    setLoadingJobs(true);
    try {
      const list = await listFinetuneJobs();
      setJobs(list);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error(err);
      setJobs([]);
    } finally {
      setLoadingJobs(false);
    }
  }

  useEffect(() => {
    fetchJobs();
  }, []);

  // Toggle selection of a session ID
  function handleSessionToggle(id) {
    setSelectedSessionIds((prev) => {
      if (prev.includes(id)) {
        return prev.filter((sid) => sid !== id);
      }
      return [...prev, id];
    });
  }

  async function handleCreateJob(e) {
    e.preventDefault();
    if (!baseModel || !displayName) {
      // eslint-disable-next-line no-alert
      alert('Please provide a base model tag and display name.');
      return;
    }
    if (selectedSessionIds.length === 0) {
      // eslint-disable-next-line no-alert
      alert('Please select at least one session for training.');
      return;
    }
    const payload = {
      base_model: baseModel,
      display_name: displayName,
      session_ids: selectedSessionIds,
    };
    if (rank) payload.lora_rank = parseInt(rank, 10);
    if (alpha) payload.lora_alpha = parseInt(alpha, 10);
    if (epochs) payload.epochs = parseInt(epochs, 10);
    setSubmitting(true);
    try {
      const job = await createFinetuneJob(payload);
      // eslint-disable-next-line no-alert
      alert('Fine‑tune job started successfully.');
      // Refresh job list and reset form
      fetchJobs();
      setBaseModel('');
      setDisplayName('');
      setRank('');
      setAlpha('');
      setEpochs('');
    } catch (err) {
      const message = err.response?.data?.detail || err.message;
      // eslint-disable-next-line no-alert
      alert(message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleLoadAdapter(jobId) {
    setLoadingAction(true);
    try {
      const config = await loadFinetuneAdapter(jobId);
      // eslint-disable-next-line no-alert
      alert('Model loaded and registered successfully. You can activate it from the Models page.');
      // Refresh job list to update statuses (if changed)
      fetchJobs();
    } catch (err) {
      const message = err.response?.data?.detail || err.message;
      // eslint-disable-next-line no-alert
      alert(message);
    } finally {
      setLoadingAction(false);
    }
  }

  if (loadingSummary) {
    return <p>Loading training data…</p>;
  }
  if (!summary) {
    return <div style={{ color: 'red' }}>Unable to load training summary.</div>;
  }

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
      <h2>Fine‑Tune Management</h2>
      <p>This page shows available training data and lets you start fine‑tune jobs.</p>
      {/* Training summary */}
      <div style={{ border: '1px solid #ddd', padding: '1rem', marginBottom: '1rem' }}>
        <h3>Training Data Summary</h3>
        {summary.example_count === 0 ? (
          <p>No confirmed findings are available across sessions. Ensure findings are confirmed before training.</p>
        ) : (
          <>
            <p>
              Total examples: <strong>{summary.example_count}</strong> (Critical: {summary.critical_count}, Moderate: {summary.moderate_count}, Minor: {summary.minor_count})
            </p>
            <p>Sessions included:</p>
            <ul style={{ listStyle: 'none', paddingLeft: 0 }}>
              {summary.sessions_included.map((s) => (
                <li key={s.id} style={{ marginBottom: '.25rem' }}>
                  <label>
                    <input
                      type="checkbox"
                      checked={selectedSessionIds.includes(s.id)}
                      onChange={() => handleSessionToggle(s.id)}
                      style={{ marginRight: '.5rem' }}
                    />
                    {s.study_name} (confirmed: {s.confirmed_count})
                  </label>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
      {/* Job creation form */}
      <div style={{ border: '1px solid #ddd', padding: '1rem', marginBottom: '1rem' }}>
        <h3>Start a New Fine‑Tune Job</h3>
        <form onSubmit={handleCreateJob} style={{ maxWidth: '700px' }}>
          <div style={{ display: 'flex', gap: '.5rem', flexWrap: 'wrap' }}>
            <label style={{ flex: '1 1 45%' }}>
              Base model tag:
              <input
                type="text"
                value={baseModel}
                onChange={(e) => setBaseModel(e.target.value)}
                style={{ width: '100%' }}
              />
            </label>
            <label style={{ flex: '1 1 45%' }}>
              Model display name:
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                style={{ width: '100%' }}
              />
            </label>
          </div>
          <div style={{ display: 'flex', gap: '.5rem', flexWrap: 'wrap', marginTop: '.5rem' }}>
            <label style={{ flex: '1 1 30%' }}>
              LoRA rank:
              <input
                type="number"
                value={rank}
                min="1"
                onChange={(e) => setRank(e.target.value)}
                style={{ width: '100%' }}
              />
            </label>
            <label style={{ flex: '1 1 30%' }}>
              LoRA alpha:
              <input
                type="number"
                value={alpha}
                min="1"
                onChange={(e) => setAlpha(e.target.value)}
                style={{ width: '100%' }}
              />
            </label>
            <label style={{ flex: '1 1 30%' }}>
              Epochs:
              <input
                type="number"
                value={epochs}
                min="1"
                onChange={(e) => setEpochs(e.target.value)}
                style={{ width: '100%' }}
              />
            </label>
          </div>
          <div style={{ marginTop: '1rem' }}>
            <button
              type="submit"
              disabled={submitting || summary.example_count < 50 || selectedSessionIds.length === 0}
              style={{ padding: '.6rem 1.2rem', background: summary.example_count < 50 ? '#aaa' : '#2d9cdb', color: 'white', border: 'none', borderRadius: '4px', cursor: summary.example_count < 50 ? 'default' : 'pointer' }}
            >
              Start Fine‑Tune Job
            </button>
            {summary.example_count < 50 && (
              <span style={{ marginLeft: '.5rem', color: '#d9534f' }}>
                At least 50 examples are required to start a job.
              </span>
            )}
          </div>
        </form>
      </div>
      {/* Jobs list */}
      <div style={{ border: '1px solid #ddd', padding: '1rem' }}>
        <h3>Past Fine‑Tune Jobs</h3>
        {loadingJobs ? (
          <p>Loading jobs…</p>
        ) : jobs.length === 0 ? (
          <p>No fine‑tune jobs have been created yet.</p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Name</th>
                <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Base Model</th>
                <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Sessions</th>
                <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Examples</th>
                <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Status</th>
                <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.id} style={{ borderBottom: '1px solid #eee' }}>
                  <td>{job.display_name || `(Unnamed) ${job.id.slice(0, 8)}`}</td>
                  <td>{job.base_model}</td>
                  <td>{job.training_session_ids ? job.training_session_ids.length : '-'}</td>
                  <td>{job.training_example_count ?? '-'}</td>
                  <td>{job.status}</td>
                  <td>
                    {job.status === 'complete' && job.adapter_path && job.ollama_model_tag ? (
                      <button
                        onClick={() => handleLoadAdapter(job.id)}
                        disabled={loadingAction}
                        style={{ padding: '.3rem .6rem' }}
                      >
                        Load Model
                      </button>
                    ) : (
                      <span style={{ color: '#888' }}>—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <div style={{ marginTop: '1rem' }}>
        <button
          onClick={() => navigate('/models')}
          style={{ padding: '.5rem 1rem', background: '#6c757d', color: 'white', border: 'none', borderRadius: '4px' }}
        >
          Go to Models
        </button>
      </div>
    </div>
  );
}

export default FinetunePage;