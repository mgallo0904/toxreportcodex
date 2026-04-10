import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getOutline, getConflicts, startPass2 } from '../api/sessions.js';
import SectionTree from '../components/SectionTree.jsx';

/**
 * SectionSelectionPage allows the user to choose which sections (chunks)
 * should be passed to the deep review (Pass 2) stage.  It fetches the
 * document outline and conflict list from the backend, applies
 * default selection heuristics, and displays a collapsible tree for
 * manual adjustment.  A summary shows how many sections are selected
 * and an estimate of API calls required.  Once the user is
 * satisfied, they may proceed to Pass 2 (in Phase 4) via a button.
 */
function SectionSelectionPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [documents, setDocuments] = useState([]);
  const [conflictIds, setConflictIds] = useState(new Set());
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [expandedIds, setExpandedIds] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch outline and conflicts on mount
  useEffect(() => {
    async function fetchData() {
      try {
        const outlineData = await getOutline(sessionId);
        const conflictsData = await getConflicts(sessionId);
        // Compute conflict chunk IDs
        const conflictSet = new Set();
        conflictsData.forEach((conf) => {
          if (conf.chunk_id_a) conflictSet.add(conf.chunk_id_a);
          if (conf.chunk_id_b) conflictSet.add(conf.chunk_id_b);
        });
        setConflictIds(conflictSet);
        // Build default selection and expansion sets
        const defaultSelected = new Set();
        const defaultExpanded = new Set();
        // Helper to process each section recursively
        function traverseSections(doc, sections) {
          sections.forEach((sec) => {
            // Expand all top-level nodes by default
            if (sec.level === 1) {
              defaultExpanded.add(sec.id);
            }
            // Default selection heuristics
            const headerLower = (sec.header || '').toLowerCase();
            const isConflict = conflictSet.has(sec.chunk_id);
            if (isConflict) {
              defaultSelected.add(sec.chunk_id);
            } else {
              // Primary Report: select typical review sections
              if (doc.role && doc.role.toLowerCase().includes('primary')) {
                const keywords = ['method', 'result', 'conclusion', 'summary', 'deviation'];
                if (keywords.some((kw) => headerLower.includes(kw))) {
                  defaultSelected.add(sec.chunk_id);
                }
              }
              // Raw Data Appendix: leave unchecked by default
              // (handled implicitly by not adding)
            }
            if (sec.children && sec.children.length > 0) {
              traverseSections(doc, sec.children);
            }
          });
        }
        // Iterate through documents
        outlineData.documents.forEach((doc) => {
          traverseSections(doc, doc.sections);
        });
        setDocuments(outlineData.documents);
        setSelectedIds(defaultSelected);
        setExpandedIds(defaultExpanded);
      } catch (err) {
        const message = err.response?.data?.detail || err.message;
        setError(message);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [sessionId]);

  const handleToggle = useCallback((chunkId, checked) => {
    setSelectedIds((prev) => {
      const newSet = new Set(prev);
      if (checked) {
        newSet.add(chunkId);
      } else {
        newSet.delete(chunkId);
      }
      return newSet;
    });
  }, []);

  const handleExpand = useCallback((sectionId) => {
    setExpandedIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(sectionId)) {
        newSet.delete(sectionId);
      } else {
        newSet.add(sectionId);
      }
      return newSet;
    });
  }, []);

  if (loading) {
    return <p>Loading…</p>;
  }
  if (error) {
    return <div style={{ color: 'red' }}>Error: {error}</div>;
  }

  // Count selected sections
  const selectedCount = selectedIds.size;

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto' }}>
      <h2>Select Sections for Deep Review</h2>
      <p>
        Choose which sections you want the AI to analyse in depth. Conflicts have
        been pre‑selected and highlighted. The more sections you select, the
        longer the review will take.
      </p>
      {documents.map((doc) => (
        <div key={doc.id} style={{ border: '1px solid #ddd', borderRadius: '4px', marginBottom: '1rem', padding: '.5rem' }}>
          <h3 style={{ margin: '0 0 .5rem 0' }}>{doc.filename} {doc.role ? `— ${doc.role}` : ''}</h3>
          {doc.sections.map((sec) => (
            <SectionTree
              key={sec.id}
              node={sec}
              selectedIds={selectedIds}
              conflictIds={conflictIds}
              expandedIds={expandedIds}
              onToggle={handleToggle}
              onExpand={handleExpand}
            />
          ))}
        </div>
      ))}
      <div style={{ marginTop: '1rem' }}>
        <p><strong>{selectedCount}</strong> sections selected = approx. <strong>{selectedCount}</strong> API calls</p>
        <button
          onClick={async () => {
            // Gather selected chunk IDs and start Pass 2
            const ids = Array.from(selectedIds);
            try {
              await startPass2(sessionId, ids);
              navigate(`/sessions/${sessionId}/pass2`);
            } catch (err) {
              const message = err.response?.data?.detail || err.message;
              // eslint-disable-next-line no-alert
              alert(message);
            }
          }}
          style={{ padding: '.75rem 1.5rem', background: '#2d9cdb', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          Start Deep Review
        </button>
      </div>
    </div>
  );
}

export default SectionSelectionPage;