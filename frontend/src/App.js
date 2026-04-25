import React, { useState } from 'react';
import Header from './components/Header';
import LandingPage from './pages/LandingPage';
import AnalyzePage from './pages/AnalyzePage';
import ResultsPage from './pages/ResultsPage';
import './App.css';

export default function App() {
  const [page, setPage]           = useState('landing');
  const [analysisResult, setResult] = useState(null);
  const [analysisConfig, setConfig] = useState(null);

  const goTo = (p) => setPage(p);

  const handleResults = (result, config) => {
    setResult(result);
    setConfig(config);
    setPage('results');
  };

  return (
    <div className="app">
      <Header page={page} goTo={goTo} />
      <main className="main-content">
        {page === 'landing' && <LandingPage goTo={goTo} />}
        {page === 'analyze' && <AnalyzePage onResults={handleResults} />}
        {page === 'results' && analysisResult && (
          <ResultsPage result={analysisResult} config={analysisConfig} goTo={goTo} />
        )}
      </main>
    </div>
  );
}
