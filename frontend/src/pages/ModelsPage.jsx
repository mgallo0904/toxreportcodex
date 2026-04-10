import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listModelConfigs, activateModelConfig } from '../api/modelConfigs.js';

/**
 * ModelsPage lists all available models (base and fine‑tuned) and
 * allows the user to activate one for inference.
 */
function ModelsPage() {
  const navigate = useNavigate();
  const [models, setModels] = useState([]);
  const [error, setError] = useState(null);
  const [activating, setActivating] = useState(false);

  useEffect(() => {
    async function fetchData() {
      try {
        const data = await listModelConfigs();
        setModels(data);
      } catch (err) {
        const message = err.response?.data?.detail || err.message;
        setError(message);
      }
    }
    fetchData();
  }, []);

  async function handleActivate(id) {
    setActivating(true);
    try {
      const updated = await activateModelConfig(id);
      setModels((prev) => prev.map((m) => (m.id === id ? updated : { ...m, is_active: false })));
    } catch (err) {
      const message = err.response?.data?.detail || err.message;
      alert(message);
    } finally {
      setActivating(false);
    }
  }

  if (error) {
    return <div style={{ color: 'red' }}>Error: {error}</div>;
  }
  return (
    <div style={{ maxWidth: '800px', margin: '0 auto' }}>
      <h2>Available Models</h2>
      <p>Select a model to activate it for inference. The active model is highlighted.</p>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Name</th>
            <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Tag</th>
            <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Provider</th>
            <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Fine‑tuned</th>
            <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Active</th>
            <th style={{ borderBottom: '1px solid #ccc', textAlign: 'left' }}>Action</th>
          </tr>
        </thead>
        <tbody>
          {models.map((model) => (
            <tr key={model.id} style={{ background: model.is_active ? '#e6f7ff' : 'transparent' }}>
              <td style={{ borderBottom: '1px solid #eee' }}>{model.display_name}</td>
              <td style={{ borderBottom: '1px solid #eee' }}>{model.model_tag}</td>
              <td style={{ borderBottom: '1px solid #eee' }}>{model.provider}</td>
              <td style={{ borderBottom: '1px solid #eee' }}>{model.is_fine_tuned ? 'Yes' : 'No'}</td>
              <td style={{ borderBottom: '1px solid #eee' }}>{model.is_active ? 'Yes' : 'No'}</td>
              <td style={{ borderBottom: '1px solid #eee' }}>
                {!model.is_active && (
                  <button
                    onClick={() => handleActivate(model.id)}
                    disabled={activating}
                    style={{ padding: '.3rem .6rem' }}
                  >
                    Activate
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ marginTop: '1rem' }}>
        <button
          onClick={() => navigate('/')}
          style={{ padding: '.5rem 1rem', background: '#6c757d', color: 'white', border: 'none', borderRadius: '4px' }}
        >
          Back to Home
        </button>
      </div>
    </div>
  );
}

export default ModelsPage;