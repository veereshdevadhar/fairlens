import React, { useState, useEffect, useRef } from 'react';
import {
  BASE,
  fetchDatasets,
  loadDataset,
  runAnalysis,
} from '../utils/api';
import './AnalyzePage.css';

const STEP_LABELS = ['Choose Dataset', 'Configure Audit', 'Running Analysis'];

export default function AnalyzePage({ onResults }) {
  const [step, setStep]           = useState(0);
  const [datasets, setDatasets]   = useState([]);
  const [selected, setSelected]   = useState(null);   // built-in id
  const [uploadedFile, setUploaded] = useState(null); // { name, columns, unique_counts }
  const [preview, setPreview]     = useState(null);
  const [config, setConfig]       = useState({
    label_col: '', protected_col: '', privileged_value: '', unprivileged_value: '', positive_label: ''
  });
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState('');
  const [dragOver, setDragOver]   = useState(false);
  const [columnValues, setColumnValues] = useState({}); // col -> [values] fetched from backend
  const fileRef = useRef();

  useEffect(() => {
    fetchDatasets()
      .then(d => setDatasets(d))
      .catch(() => setError('Could not connect to backend. Is the server running?'));
  }, []);

  /* ── Helpers ── */
  const colOptions = preview ? preview.columns : [];
  const uniqueFor  = (col) => col ? Object.keys(preview?.unique_counts_per_col?.[col] || {}) : [];

  // Fetch full unique values for a column from backend (not just 5-row preview)
  const fetchColumnValues = async (col, datasetId, isUpload) => {
    if (!col) return;
    const cacheKey = (datasetId || 'upload') + '__' + col;
    if (columnValues[cacheKey]) return;
    try {
      let url;
      if (datasetId) {
        url = `${BASE}/datasets/${datasetId}/unique-values/${encodeURIComponent(col)}`;
      } else if (isUpload) {
        url = `${BASE}/upload/unique-values/${encodeURIComponent(col)}`;
      } else {
        return;
      }
      const res = await fetch(url);
      if (!res.ok) return;
      const data = await res.json();
      if (data.values) {
        setColumnValues(prev => ({ ...prev, [cacheKey]: data.values.map(String) }));
      }
    } catch (e) {
      // silently fallback to preview rows
    }
  };

  // Get distinct values for a given column - use fetched full values or preview fallback
  const uniqueValues = (col) => {
    if (!col) return [];
    const cacheKey = (selected || 'upload') + '__' + col;
    if (columnValues[cacheKey]) return columnValues[cacheKey];
    // Fallback: gather from preview rows only
    if (!preview) return [];
    const vals = [...new Set((preview.preview || []).map(r => String(r[col])).filter(v => v && v !== 'null' && v !== 'undefined'))];
    return vals.slice(0, 30);
  };

  /* ── Select built-in dataset ── */
  const selectBuiltin = async (id) => {
    setError('');
    setLoading(true);
    setSelected(id);
    setUploaded(null);
    try {
      const data = await loadDataset(id);
      setPreview(data.preview);
      const meta = data.meta;
      setConfig({
        label_col:          meta.label_col,
        protected_col:      meta.default_protected,
        privileged_value:   meta.default_privileged,
        unprivileged_value: meta.default_unprivileged,
        positive_label:     String(meta.label_positive),
        dataset_id:         id,
      });
      // Pre-fetch full unique values for the default columns so dropdowns are populated
      await Promise.all([
        fetch(`${BASE}/datasets/${id}/unique-values/${encodeURIComponent(meta.label_col)}`)
          .then(r => r.json()).then(d => {
            if (d.values) setColumnValues(prev => ({ ...prev, [id + '__' + meta.label_col]: d.values.map(String) }));
          }).catch(() => {}),
        fetch(`${BASE}/datasets/${id}/unique-values/${encodeURIComponent(meta.default_protected)}`)
          .then(r => r.json()).then(d => {
            if (d.values) setColumnValues(prev => ({ ...prev, [id + '__' + meta.default_protected]: d.values.map(String) }));
          }).catch(() => {}),
      ]);
      setStep(1);
    } catch (e) {
      setError('Failed to load dataset: ' + (e.response?.data?.detail || e.message));
    }
    setLoading(false);
  };

  /* ── Upload custom file ── */
  const handleFile = async (file) => {
    if (!file) return;
    setError('');
    setLoading(true);
    setSelected(null);
    const form = new FormData();
    form.append('file', file);
    try {
      const res = await fetch(`${BASE}/upload`, { method: 'POST', body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Upload failed');
      setPreview(data);
      setUploaded({ name: file.name, ...data });
      setConfig({ label_col: '', protected_col: '', privileged_value: '', unprivileged_value: '', positive_label: '', dataset_id: null });
      setStep(1);
    } catch (e) {
      setError('Upload failed: ' + e.message);
    }
    setLoading(false);
  };

  /* ── Run analysis ── */
  const handleRun = async () => {
    if (!config.label_col || !config.protected_col || !config.privileged_value || !config.unprivileged_value) {
      setError('Please fill in all required fields.'); return;
    }
    if (config.privileged_value === config.unprivileged_value) {
      setError('Privileged and unprivileged values must be different.'); return;
    }
    setError('');
    setStep(2);
    setLoading(true);
    try {
      const payload = { ...config };
      if (!payload.dataset_id) delete payload.dataset_id;
      const result = await runAnalysis(payload);
      onResults(result, { ...config, datasetName: selected || (uploadedFile?.name || 'Custom') });
    } catch (e) {
      setError('Analysis failed: ' + (e.response?.data?.detail || e.message));
      setStep(1);
    }
    setLoading(false);
  };

  const selMeta = datasets.find(d => d.id === selected);

  /* ── Render ── */
  return (
    <div className="analyze-page">
      <div className="analyze-inner">
        {/* Step indicator */}
        <div className="steps">
          {STEP_LABELS.map((label, i) => (
            <div key={i} className={`step-item ${i === step ? 'active' : ''} ${i < step ? 'done' : ''}`}>
              <div className="step-dot">{i < step ? '✓' : i + 1}</div>
              <span>{label}</span>
            </div>
          ))}
        </div>

        {error && <div className="error-banner">⚠ {error}</div>}

        {/* STEP 0 – Choose dataset */}
        {step === 0 && (
          <div className="fade-up">
            <h2 className="page-title">Choose Your Dataset</h2>
            <p className="page-sub">Pick a real benchmark dataset or upload your own.</p>

            <h3 className="section-label">Built-in Benchmark Datasets</h3>
            {loading && <div className="loading-row"><div className="spinner" /><span>Loading datasets…</span></div>}
            <div className="dataset-grid">
              {datasets.map(d => (
                <button key={d.id} className={`dataset-card ${selected === d.id ? 'sel' : ''}`}
                  onClick={() => selectBuiltin(d.id)} disabled={loading}>
                  <div className="ds-header">
                    <span className="ds-name">{d.name}</span>
                    <span className="ds-badge">{(d.rows||0).toLocaleString()} rows</span>
                  </div>
                  <p className="ds-desc">{d.description}</p>
                  <div className="ds-tags">
                    {(d.protected_options||[]).map(p => (
                      <span key={p.col} className="ds-tag">{p.col}</span>
                    ))}
                  </div>
                  <div className="ds-source">Source: {d.source}</div>
                </button>
              ))}
            </div>

            <h3 className="section-label" style={{marginTop:36}}>Or Upload Your Own</h3>
            <div
              className={`dropzone ${dragOver ? 'drag-over' : ''}`}
              onDragOver={e => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={e => { e.preventDefault(); setDragOver(false); handleFile(e.dataTransfer.files[0]); }}
              onClick={() => fileRef.current.click()}>
              <input ref={fileRef} type="file" accept=".csv,.xlsx,.xls,.json"
                style={{display:'none'}} onChange={e => handleFile(e.target.files[0])} />
              <div className="dropzone-icon">📂</div>
              <div className="dropzone-text">Drop CSV, Excel or JSON here</div>
              <div className="dropzone-sub">or click to browse · min 50 rows</div>
            </div>
          </div>
        )}

        {/* STEP 1 – Configure */}
        {step === 1 && (
          <div className="fade-up">
            <h2 className="page-title">Configure the Audit</h2>
            <p className="page-sub">
              {selMeta ? `Dataset: ${selMeta.name} · ${(selMeta.rows||0).toLocaleString()} rows`
                       : `File: ${uploadedFile?.name || 'Uploaded dataset'}`}
            </p>

            {/* Preview table */}
            {preview && (
              <div className="preview-wrap">
                <div className="preview-label">Data Preview (first 5 rows)</div>
                <div className="preview-scroll">
                  <table className="preview-table">
                    <thead>
                      <tr>{(preview.columns||[]).map(c => <th key={c}>{c}</th>)}</tr>
                    </thead>
                    <tbody>
                      {(preview.preview||[]).map((row, i) => (
                        <tr key={i}>{(preview.columns||[]).map(c => <td key={c}>{String(row[c] ?? '')}</td>)}</tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            <div className="config-grid">
              <div className="field">
                <label>Label Column (what to predict) *</label>
                <select value={config.label_col}
                  onChange={e => {
                    const col = e.target.value;
                    setConfig(c => ({ ...c, label_col: col }));
                    fetchColumnValues(col, selected, !!uploadedFile);
                  }}>
                  <option value="">Select column…</option>
                  {colOptions.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>

              <div className="field">
                <label>Positive Label Value *</label>
                <select value={config.positive_label}
                  onChange={e => setConfig(c => ({ ...c, positive_label: e.target.value }))}>
                  <option value="">Select value…</option>
                  {uniqueValues(config.label_col).map(v => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>

              <div className="field">
                <label>Protected Attribute *</label>
                <select value={config.protected_col}
                  onChange={e => {
                    const col = e.target.value;
                    setConfig(c => ({
                      ...c, protected_col: col,
                      privileged_value: '', unprivileged_value: ''
                    }));
                    fetchColumnValues(col, selected, !!uploadedFile);
                  }}>
                  <option value="">Select column…</option>
                  {colOptions.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>

              <div className="field" />

              <div className="field">
                <label>Privileged Group Value *</label>
                <select value={config.privileged_value}
                  onChange={e => setConfig(c => ({ ...c, privileged_value: e.target.value }))}>
                  <option value="">Select value…</option>
                  {uniqueValues(config.protected_col).map(v => <option key={v} value={v}>{v}</option>)}
                </select>
                <span className="field-hint">The group historically treated better (e.g. "Male", "White")</span>
              </div>

              <div className="field">
                <label>Unprivileged Group Value *</label>
                <select value={config.unprivileged_value}
                  onChange={e => setConfig(c => ({ ...c, unprivileged_value: e.target.value }))}>
                  <option value="">Select value…</option>
                  {uniqueValues(config.protected_col)
                    .filter(v => v !== config.privileged_value)
                    .map(v => <option key={v} value={v}>{v}</option>)}
                </select>
                <span className="field-hint">The group potentially disadvantaged (e.g. "Female", "Black")</span>
              </div>
            </div>

            <div className="config-actions">
              <button className="btn-ghost" onClick={() => { setStep(0); setError(''); }}>← Back</button>
              <button className="btn-primary run-btn" onClick={handleRun}
                disabled={!config.label_col || !config.protected_col || !config.privileged_value || !config.unprivileged_value}>
                Run Bias Audit →
              </button>
            </div>
          </div>
        )}

        {/* STEP 2 – Running */}
        {step === 2 && (
          <div className="running-screen fade-up">
            <div className="running-spinner" />
            <h2>Running Bias Analysis…</h2>
            <p>Training model · computing fairness metrics · detecting proxy features</p>
            <div className="running-steps">
              {['Loading dataset', 'Encoding features', 'Training classifier',
                'Computing group statistics', 'Calculating fairness metrics',
                'Detecting proxy features', 'Generating recommendations'].map((s, i) => (
                <div key={i} className="running-step" style={{ animationDelay: `${i * 0.4}s` }}>
                  <span className="running-dot" />
                  <span>{s}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
