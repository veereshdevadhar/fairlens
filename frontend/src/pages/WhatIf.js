import React, { useState, useEffect, useCallback } from 'react';
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from 'recharts';
import api from '../utils/api';
import './FeaturePage.css';

const SEV_COLOR = { none:'#34D399', low:'#FBBF24', medium:'#FB923C', high:'#F87171' };

function ScoreDiff({ original, current }) {
  const diff = original - current;
  const improved = diff > 0;
  return (
    <div className="score-diff-wrap">
      <div className="score-diff-box original">
        <div className="sd-label">Original</div>
        <div className="sd-score" style={{color:'#F87171'}}>{original?.toFixed(1)}</div>
      </div>
      <div className="sd-arrow">{improved ? '→' : '→'}</div>
      <div className="score-diff-box current" style={{borderColor: improved ? '#34D399' : '#F87171'}}>
        <div className="sd-label">After Fix</div>
        <div className="sd-score" style={{color: improved ? '#34D399' : '#F87171'}}>{current?.toFixed(1)}</div>
      </div>
      <div className={`sd-change ${improved ? 'sd-positive' : 'sd-negative'}`}>
        {improved ? `▼ ${diff.toFixed(1)} improved` : `▲ ${Math.abs(diff).toFixed(1)} worsened`}
      </div>
    </div>
  );
}

export default function WhatIfSimulator({ analysisResult }) {
  const features     = Object.keys(analysisResult?.analysis?.feature_importance || {});
  const [controls, setControls] = useState({
    removeFeatures:    [],
    oversample:        1.0,
    threshold:         0.5,
    reweight:          false,
    threshPriv:        0.5,
    threshUnpriv:      0.5,
    splitThreshold:    false,
  });
  const [result, setResult]   = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');
  const [autoRun, setAutoRun] = useState(false);

  const originalScore = analysisResult?.analysis?.overall?.bias_score || 0;

  const runSim = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const payload = {
        remove_features:    controls.removeFeatures.length ? controls.removeFeatures : null,
        oversample_factor:  controls.oversample,
        decision_threshold: controls.splitThreshold ? 0.5 : controls.threshold,
        reweight:           controls.reweight,
        threshold_priv:     controls.splitThreshold ? controls.threshPriv  : null,
        threshold_unpriv:   controls.splitThreshold ? controls.threshUnpriv : null,
      };
      const r = await api.post('/whatif', payload);
      setResult(r.data);
    } catch(e) {
      setError(e.response?.data?.detail || 'Simulation failed');
    }
    setLoading(false);
  }, [controls]);

  useEffect(() => { if (autoRun) runSim(); }, [controls, autoRun, runSim]);

  const toggleFeature = (f) =>
    setControls(c => ({...c,
      removeFeatures: c.removeFeatures.includes(f)
        ? c.removeFeatures.filter(x=>x!==f)
        : [...c.removeFeatures, f]
    }));

  const radarData = result ? Object.entries(result.metrics||{}).map(([k,v]) => ({
    metric: k.replace(/_/g,' ').split(' ').slice(0,3).join(' '),
    score:  Math.min(Math.abs(v.value||0)*500,100)
  })) : [];

  return (
    <div className="fp-wrap">
      <div className="fp-header">
        <div className="fp-icon">🧪</div>
        <div>
          <h2 className="fp-title">What-If Simulator</h2>
          <p className="fp-sub">Apply fairness interventions and see the bias score update in real-time. Experiment without touching the real model.</p>
        </div>
      </div>

      <div className="wi-layout">
        {/* Controls */}
        <div className="wi-controls card">
          <div className="wi-ctrl-title">Interventions</div>

          {/* Reweighting */}
          <div className="wi-section">
            <div className="wi-section-label">
              <label className="wi-toggle-row">
                <span>Apply Reweighting</span>
                <div className="toggle-wrap">
                  <input type="checkbox" checked={controls.reweight}
                    onChange={e => setControls(c=>({...c, reweight:e.target.checked}))} />
                  <span className="toggle-slider" />
                </div>
              </label>
            </div>
            <p className="wi-hint">Increases importance of underrepresented positive cases during training.</p>
          </div>

          {/* Remove features */}
          <div className="wi-section">
            <div className="wi-section-label">Remove Features (Proxy Removal)</div>
            <p className="wi-hint">Select features to exclude from the model.</p>
            <div className="wi-feat-grid">
              {features.slice(0,10).map(f => (
                <button key={f}
                  className={`wi-feat-btn ${controls.removeFeatures.includes(f) ? 'active' : ''}`}
                  onClick={() => toggleFeature(f)}>
                  {controls.removeFeatures.includes(f) ? '✕ ' : ''}{f}
                </button>
              ))}
            </div>
          </div>

          {/* Oversample */}
          <div className="wi-section">
            <div className="wi-section-label">Oversample Unprivileged Group: {controls.oversample.toFixed(1)}×</div>
            <input type="range" min="1" max="3" step="0.1"
              value={controls.oversample}
              onChange={e => setControls(c=>({...c, oversample: parseFloat(e.target.value)}))} />
            <p className="wi-hint">1.0 = no change · 2.0 = double the unprivileged group samples</p>
          </div>

          {/* Threshold */}
          <div className="wi-section">
            <div className="wi-section-label">
              <label className="wi-toggle-row">
                <span>Split Thresholds by Group</span>
                <div className="toggle-wrap">
                  <input type="checkbox" checked={controls.splitThreshold}
                    onChange={e => setControls(c=>({...c, splitThreshold:e.target.checked}))} />
                  <span className="toggle-slider" />
                </div>
              </label>
            </div>
            {!controls.splitThreshold ? (
              <>
                <div className="wi-section-label" style={{marginTop:8}}>Decision Threshold: {controls.threshold.toFixed(2)}</div>
                <input type="range" min="0.1" max="0.9" step="0.01"
                  value={controls.threshold}
                  onChange={e => setControls(c=>({...c, threshold: parseFloat(e.target.value)}))} />
              </>
            ) : (
              <>
                <div className="wi-section-label" style={{marginTop:8}}>Privileged threshold: {controls.threshPriv.toFixed(2)}</div>
                <input type="range" min="0.1" max="0.9" step="0.01"
                  value={controls.threshPriv}
                  onChange={e => setControls(c=>({...c, threshPriv: parseFloat(e.target.value)}))} />
                <div className="wi-section-label" style={{marginTop:8}}>Unprivileged threshold: {controls.threshUnpriv.toFixed(2)}</div>
                <input type="range" min="0.1" max="0.9" step="0.01"
                  value={controls.threshUnpriv}
                  onChange={e => setControls(c=>({...c, threshUnpriv: parseFloat(e.target.value)}))} />
                <p className="wi-hint">Lower threshold for unprivileged group = more approvals for them.</p>
              </>
            )}
          </div>

          <div className="wi-actions">
            <button className="btn-primary" onClick={runSim} disabled={loading}>
              {loading ? <><span className="btn-spinner"/>Running…</> : '▶ Run Simulation'}
            </button>
            <label className="wi-toggle-row" style={{fontSize:12,color:'var(--text2)'}}>
              <input type="checkbox" checked={autoRun}
                onChange={e => setAutoRun(e.target.checked)}
                style={{width:'auto',marginRight:6}} />
              Auto-run on change
            </label>
          </div>
          {error && <div className="fp-error" style={{marginTop:8}}>⚠ {error}</div>}
        </div>

        {/* Results */}
        <div className="wi-results">
          {!result && !loading && (
            <div className="wi-empty">
              <div style={{fontSize:48,marginBottom:12}}>🎛</div>
              <p>Adjust the controls and click <strong>Run Simulation</strong> to see how each intervention affects bias.</p>
            </div>
          )}
          {loading && (
            <div className="fp-loading"><div className="spinner"/><span>Running simulation…</span></div>
          )}
          {result && !loading && (
            <div className="fade-up">
              <ScoreDiff original={originalScore} current={result.bias_score} />

              <div className="wi-metric-grid">
                {Object.entries(result.metrics||{}).map(([k,v]) => (
                  <div key={k} className="wi-metric-card card-sm">
                    <div className="wi-m-name">{k.replace(/_/g,' ')}</div>
                    <div className="wi-m-val" style={{color: SEV_COLOR[v.severity]||'#4F8EF7'}}>
                      {v.value?.toFixed(4)}
                    </div>
                    <span className={`sev-badge sev-bg-${v.severity}`} style={{color:SEV_COLOR[v.severity]}}>
                      {v.severity}
                    </span>
                  </div>
                ))}
              </div>

              {radarData.length > 0 && (
                <div className="card" style={{marginTop:16}}>
                  <div className="chart-label">Bias Dimensions After Intervention</div>
                  <ResponsiveContainer width="100%" height={240}>
                    <RadarChart data={radarData}>
                      <PolarGrid stroke="rgba(255,255,255,0.08)" />
                      <PolarAngleAxis dataKey="metric" tick={{fill:'#8FA3C8',fontSize:10}} />
                      <PolarRadiusAxis angle={30} domain={[0,100]} tick={{fill:'#4A5E80',fontSize:9}} />
                      <Radar dataKey="score" stroke="#34D399" fill="#34D399" fillOpacity={0.18} strokeWidth={2} />
                      <Tooltip contentStyle={{background:'#162040',border:'1px solid rgba(99,142,255,0.2)',borderRadius:8}} />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              )}

              {result.interventions_applied?.length > 0 && (
                <div className="wi-applied">
                  <div className="wi-applied-title">Interventions applied:</div>
                  {result.interventions_applied.map((i,idx) => (
                    <div key={idx} className="wi-applied-item">✓ {i}</div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="fp-note">
        💡 <strong>Try this:</strong> Enable reweighting + lower the unprivileged threshold to 0.4 — 
        this often reduces bias significantly while keeping accuracy high.
      </div>
    </div>
  );
}
