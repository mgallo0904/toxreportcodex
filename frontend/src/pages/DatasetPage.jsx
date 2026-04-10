import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getDataset } from '../api/dataset.js';
import { createFinetuneJob } from '../api/finetune.js';

/**
 * DatasetPage displays the confirmed findings dataset for a session and
 * allows the user to initiate a fine‑tune job using this session as
 * training data.
 */
function DatasetPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [dataset, setDataset] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  // Form state for finetune job
  const [baseModel, setBaseModel] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [rank, setRank] = useState('');
  const [alpha, setAlpha] = useState('');
  const [epochs, setEpochs] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    async function fetchData() {
      try {
        const data = await getDataset(sessionId);
        setDataset(data);
      } catch (err) {
        const message = err.response?.data?.detail || err.message;
        setError(message);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [sessionId]);

  async function handleCreateJob(e) {
    e.preventDefault();
    if (!baseModel || !displayName) {
      alert('Please provide a base model and display name.');
      return;
    }
    const payload = {
      base_model: baseModel,
      session_ids: [sessionId],
      display_name: displayName,
    };
    if (rank) payload.lora_rank = parseInt(rank, 10);
    if (alpha) payload.lora_alpha = parseInt(alpha, 10);
    if (epochs) payload.epochs = parseInt(epochs, 10);
    setSubmitting(true);
    try {
      const job = await createFinetuneJob(payload);
      // Redirect to models page after creating job
      // eslint-disable-next-line no-alert
      alert('Fine‑tune job created successfully. It will appear in the models list.');
      navigate('/models');
    } catch (err) {
      const message = err.response?.data?.detail || err.message;
      alert(message);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return <p>Loading…</p>;
  }
  if (error) {
    return <div style={{ color: 'red' }}>Error: {error}</div>;
  }
  return (
    <div style={{ maxWidth: '900px', margin: '0 auto' }}>
      <h2>Training Dataset</h2>
      {dataset.length === 0 ? (
        <p>No confirmed findings available for training.</p>
      ) : (
        <>
          <p>{dataset.length} examples found. The table below lists each example. You can export the dataset by copying the JSON.</p>
          <div style={{ maxHeight: '300px', overflowY: 'auto', border: '1px solid #ddd', padding: '.5rem' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Label</th>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Document</th>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Page</th>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Severity</th>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Category</th>
                  <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Comment</th>
                </tr>
              </thead>
              <tbody>
                {dataset.map((rec) => (
                  <tr key={rec.finding_id}>
                    <td style={{ borderBottom: '1px solid #eee' }}>{rec.finding_label}</td>
                    <td style={{ borderBottom: '1px solid #eee' }}>{rec.document_name}</td>
                    <td style={{ borderBottom: '1px solid #eee' }}>{rec.page_range}</td>
                    <td style={{ borderBottom: '1px solid #eee' }}>{rec.severity}</td>
                    <td style={{ borderBottom: '1px solid #eee' }}>{rec.category}</td>
                    <td style={{ borderBottom: '1px solid #eee' }}>{rec.comment}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      <div style={{ marginTop: '1.5rem' }}>
        <h3>Start Fine‑Tune Job</h3>
        <form onSubmit={handleCreateJob} style={{ maxWidth: '600px' }}>
          <div style={{ marginBottom: '.5rem' }}>
            <label>
              Base model tag:
              <input
                type="text"
                value={baseModel}
                onChange={(e) => setBaseModel(e.target.value)}
                style={{ width: '100%' }}
              />
            </label>
          </div>
          <div style={{ marginBottom: '.5rem' }}>
            <label>
              Model display name:
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                style={{ width: '100%' }}
              />
            </label>
          </div>
          <div style={{ display: 'flex', gap: '.5rem', marginBottom: '.5rem' }}>
            <label style={{ flex: '1 1 30%' }}>
              LoRA rank:
              <input
                type="number"
                value={rank}
                onChange={(e) => setRank(e.target.value)}
                min="1"
                style={{ width: '100%' }}
              />
            </label>
            <label style={{ flex: '1 1 30%' }}>
              LoRA alpha:
              <input
                type="number"
                value={alpha}
                onChange={(e) => setAlpha(e.target.value)}
                min="1"
                style={{ width: '100%' }}
              />
            </label>
            <label style={{ flex: '1 1 30%' }}>
              Epochs:
              <input
                type="number"
                value={epochs}
                onChange={(e) => setEpochs(e.target.value)}
                min="1"
                style={{ width: '100%' }}
              />
            </label>
          </div>
          <button
            type="submit"
            disabled={submitting || dataset.length === 0}
            style={{ padding: '.75rem 1.5rem', background: dataset.length === 0 ? '#aaa' : '#2d9cdb', color: 'white', border: 'none', borderRadius: '4px', cursor: dataset.length === 0 ? 'default' : 'pointer' }}
          >
            Create Fine‑Tune Job
          </button>
        </form>
      </div>
    </div>
  );
}

export default DatasetPage;