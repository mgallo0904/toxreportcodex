import React from 'react';

/**
 * SectionTree renders a hierarchical outline of document sections as a
 * collapsible tree with checkboxes.  Each node corresponds to a
 * document section (and therefore to a single chunk).  Users can
 * expand or collapse each node and select or deselect individual
 * sections for deep review.  Conflict‑flagged sections are
 * highlighted.
 *
 * Props:
 * - node: the SectionNode object describing a section and its
 *   children.  The object includes id, chunk_id, header, page and
 *   children list.
 * - selectedIds: a Set of chunk_id strings indicating which
 *   sections are currently selected.
 * - conflictIds: a Set of chunk_id strings flagged by conflict
 *   detection.  These nodes will be highlighted in the UI.
 * - expandedIds: a Set of section id strings indicating which
 *   nodes are expanded.  Top‑level nodes should be expanded by
 *   default.
 * - onToggle: callback invoked when a checkbox is clicked.  It
 *   receives the chunk_id and the new boolean selected state.
 * - onExpand: callback invoked when the expand/collapse icon is
 *   clicked.  It receives the section id to toggle expansion.
 * - level: optional depth to indent child nodes.  Root nodes use
 *   level=0.
 */
function SectionTree({ node, selectedIds, conflictIds, expandedIds, onToggle, onExpand, level = 0 }) {
  const isExpanded = expandedIds.has(node.id);
  const isSelected = selectedIds.has(node.chunk_id);
  const isConflict = conflictIds.has(node.chunk_id);

  // Indentation for nested levels
  const indent = 16 * level;

  return (
    <div>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: '4px 0',
          backgroundColor: isConflict ? '#fff4e5' : 'transparent',
        }}
      >
        {/* Indent marker */}
        <div style={{ width: indent }} />
        {/* Expand/collapse toggle */}
        {node.children && node.children.length > 0 ? (
          <button
            onClick={() => onExpand(node.id)}
            style={{
              marginRight: 4,
              border: 'none',
              background: 'transparent',
              cursor: 'pointer',
              fontSize: '0.8rem',
              lineHeight: 1,
            }}
            aria-label={isExpanded ? 'Collapse' : 'Expand'}
          >
            {isExpanded ? '▾' : '▸'}
          </button>
        ) : (
          <span style={{ width: 14, display: 'inline-block' }} />
        )}
        {/* Checkbox */}
        <input
          type="checkbox"
          checked={isSelected}
          onChange={(e) => onToggle(node.chunk_id, e.target.checked)}
          style={{ marginRight: 6 }}
        />
        {/* Header text and page number */}
        <span style={{ fontWeight: node.level === 1 ? 'bold' : 'normal' }}>
          {node.header}
          {node.page ? ` (p${node.page})` : ''}
        </span>
      </div>
      {/* Render children when expanded */}
      {isExpanded && node.children && node.children.length > 0 && (
        <div>
          {node.children.map((child) => (
            <SectionTree
              key={child.id}
              node={child}
              selectedIds={selectedIds}
              conflictIds={conflictIds}
              expandedIds={expandedIds}
              onToggle={onToggle}
              onExpand={onExpand}
              level={level + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default SectionTree;