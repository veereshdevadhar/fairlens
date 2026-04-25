import React from 'react';
import './Header.css';

export default function Header({ page, goTo }) {
  return (
    <header className="header">
      <div className="header-inner">
        <button className="logo" onClick={() => goTo('landing')}>
          <span className="logo-icon">⚖</span>
          <span className="logo-text">Fair<span>Lens</span></span>
        </button>
        <nav className="nav">
          <button
            className={`nav-btn ${page === 'landing' ? 'active' : ''}`}
            onClick={() => goTo('landing')}>
            Home
          </button>
          <button
            className={`nav-btn ${page === 'analyze' ? 'active' : ''}`}
            onClick={() => goTo('analyze')}>
            Analyze
          </button>
          {page === 'results' && (
            <button className="nav-btn active">Results</button>
          )}
        </nav>
        <button className="cta-btn" onClick={() => goTo('analyze')}>
          Run Audit →
        </button>
      </div>
    </header>
  );
}
