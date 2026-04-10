import React, { useEffect, useState } from 'react';
import { listModelConfigs, activateModelConfig } from '../api/modelConfigs.js';

/**
 * ModelSwitcher component renders a dropdown to select the active
 * language model.  The currently active model is highlighted and
 * selecting a different model triggers the activation endpoint.  A
 * callback may be provided via the `onChange` prop to respond to
 * activation events.
 */
function ModelSwitcher({ onChange }) {
  const [models, setModels] = useState([]);
  const [activeId, setActiveId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchModels() {
      try {
        const data = await listModelConfigs();
        setModels(data);
        const active = data.find((m) => m.is_active);
        if (active) setActiveId(active.id);
      } catch (err) {
        const message = err.response?.data?.detail || err.message;
        setError(message);
      }
    }
    fetchModels();
  }, []);

  async function handleChange(e) {
    const newId = e.target.value;
    setLoading(true);
    try {
      await activateModelConfig(newId);
      setActiveId(newId);
      if (onChange) onChange(newId);
    } catch (err) {
      const message = err.response?.data?.detail || err.message;
      alert(message);
    } finally {
      setLoading(false);
    }
  }

  if (error) {
    return <span style={{ color: 'red' }}>Model error: {error}</span>;
  }
  return (
    <div style={{ display: 'inline-block' }}>
      <label style={{ marginRight: '.5rem' }}>Model:</label>
      <select value={activeId} onChange={handleChange} disabled={loading} style={{ padding: '.25rem .5rem' }}>
        {models.map((model) => (
          <option key={model.id} value={model.id}>
            {model.display_name}{model.is_fine_tuned ? ' (FT)' : ''}
          </option>
        ))}
      </select>
    </div>
  );
}

export default ModelSwitcher;