import React, { useEffect } from 'react'
import ReactDOM from 'react-dom/client'
import { AboutPage, GCSS } from '../ai-skill-atlas-explorer.jsx'
import PAPERS_RAW from './papers.json'
import ESTIMATES_RAW from './estimates.json'

// Standalone /about/ page. Reuses the AboutPage component and global CSS from the
// main app; navigation links back to the browse page (which reads ?paper=<key>).
function AboutStandalone() {
  useEffect(() => {
    const styleEl = document.createElement('style')
    styleEl.innerHTML = GCSS
    document.head.appendChild(styleEl)
    return () => { document.head.removeChild(styleEl) }
  }, [])

  const base = import.meta.env.BASE_URL
  return (
    <AboutPage
      nPapers={PAPERS_RAW.length}
      nEstimates={ESTIMATES_RAW.length}
      papers={PAPERS_RAW}
      onBack={() => { window.location.href = base }}
      onSelectPaper={(p) => { window.location.href = `${base}?paper=${p.paper_key}` }}
    />
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AboutStandalone />
  </React.StrictMode>
)
