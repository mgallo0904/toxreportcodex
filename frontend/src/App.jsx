import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import UploadPage from './pages/UploadPage.jsx';
import RoleAssignmentPage from './pages/RoleAssignmentPage.jsx';
import Pass1ProgressPage from './pages/Pass1ProgressPage.jsx';
import SectionSelectionPage from './pages/SectionSelectionPage.jsx';
import Pass2ProgressPage from './pages/Pass2ProgressPage.jsx';
import ClarificationsPage from './pages/ClarificationsPage.jsx';
import FindingsPage from './pages/FindingsPage.jsx';
import DatasetPage from './pages/DatasetPage.jsx';
import ModelsPage from './pages/ModelsPage.jsx';
import FinetunePage from './pages/FinetunePage.jsx';
import Home from './pages/Home.jsx';
import ModelSwitcher from './components/ModelSwitcher.jsx';

/**
 * The root component of the React application.  In Phase 2 the
 * application now includes additional pages for uploading documents
 * and assigning roles.  The navigation bar provides access to these
 * pages.
 */
function App() {
  return (
    <div style={{ padding: '1rem' }}>
      <nav style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <Link to="/" style={{ marginRight: '1rem' }}>Home</Link>
        <Link to="/sessions/new" style={{ marginRight: '1rem' }}>New Session</Link>
        <Link to="/models" style={{ marginRight: '1rem' }}>Models</Link>
        <Link to="/finetune" style={{ marginRight: '1rem' }}>Fine‑Tune</Link>
        {/* Model switcher aligned to the right */}
        <div style={{ marginLeft: 'auto' }}>
          <ModelSwitcher />
        </div>
      </nav>
      <Routes>
        <Route path="/" element={<Home />} />
        {/* Upload new session */}
        <Route path="/sessions/new" element={<UploadPage />} />
        {/* Role assignment */}
        <Route path="/sessions/:sessionId/assign-roles" element={<RoleAssignmentPage />} />
        {/* Pass 1 progress */}
        <Route path="/sessions/:sessionId/pass1" element={<Pass1ProgressPage />} />
        {/* Section selection for Pass 2 */}
        <Route path="/sessions/:sessionId/sections" element={<SectionSelectionPage />} />
        {/* Pass 2 progress */}
        <Route path="/sessions/:sessionId/pass2" element={<Pass2ProgressPage />} />
        {/* Clarifications handling */}
        <Route path="/sessions/:sessionId/clarifications" element={<ClarificationsPage />} />
        {/* Findings review */}
        <Route path="/sessions/:sessionId/findings" element={<FindingsPage />} />
        {/* Training dataset export and job creation */}
        <Route path="/sessions/:sessionId/dataset" element={<DatasetPage />} />
        {/* Model configurations */}
        <Route path="/models" element={<ModelsPage />} />
        {/* Fine‑tune management */}
        <Route path="/finetune" element={<FinetunePage />} />
      </Routes>
    </div>
  );
}

export default App;