import React, { useState } from 'react';
import api from '../utils/api';
import './FeaturePage.css';

export default function CertificatePage({ analysisResult }) {
  const [orgName, setOrgName]   = useState('');
  const [preview, setPreview]   = useState('');
  const [loading, setLoading]   = useState(false);
  const [generated, setGenerated] = useState(false);
  const [error, setError]       = useState('');

  const overall  = analysisResult?.analysis?.overall || {};
  const severity = overall.severity || 'high';
  const score    = overall.bias_score || 0;

  const SEV_COL = { none:'#34D399', low:'#FBBF24', medium:'#FB923C', high:'#F87171' };
  const SEV_MSG = {
    none:   '✓ This model qualifies for a FairLens Fairness Certificate.',
    low:    '⚡ This model can receive a conditional certificate with noted findings.',
    medium: '⚠ Certificate issued with warnings. Fixes are strongly recommended.',
    high:   '✕ This model does not qualify for certification without fixes.',
  };

  const generate = async () => {
    setLoading(true); setError('');
    try {
      const r = await api.post('/certificate', { organization_name: orgName || 'Your Organization' });
      setPreview(r.data);
      setGenerated(true);
    } catch(e) {
      setError(e.response?.data?.detail || 'Certificate generation failed.');
    }
    setLoading(false);
  };

  const download = () => {
    const blob = new Blob([preview], { type: 'text/html' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url; a.download = 'fairlens_certificate.html';
    a.click(); URL.revokeObjectURL(url);
  };

  return (
    <div className="fp-wrap">
      <div className="fp-header">
        <div className="fp-icon">🏆</div>
        <div>
          <h2 className="fp-title">Fairness Certificate</h2>
          <p className="fp-sub">
            Generate a signed, timestamped HTML certificate summarising your full audit.
            Share it publicly, attach it to a submission, or present it to regulators.
          </p>
        </div>
      </div>

      {/* Eligibility card */}
      <div className={`cert-eligibility card sev-bg-${severity}`}
        style={{borderColor: SEV_COL[severity]}}>
        <div className="cert-el-score" style={{color: SEV_COL[severity]}}>{score.toFixed(0)}/100</div>
        <div className="cert-el-msg" style={{color: SEV_COL[severity]}}>{SEV_MSG[severity]}</div>
      </div>

      {/* Org name */}
      <div className="card cert-form">
        <label>Organisation / Team Name (appears on certificate)</label>
        <input value={orgName} onChange={e=>setOrgName(e.target.value)}
          placeholder="e.g. Google Solution Challenge 2026 Team" />
        <div style={{display:'flex',gap:12,marginTop:16,alignItems:'center'}}>
          <button className="btn-primary" onClick={generate} disabled={loading}>
            {loading ? <><span className="btn-spinner"/>Generating…</> : '🏆 Generate Certificate'}
          </button>
          {generated && (
            <button className="btn-outline" onClick={download}>⬇ Download HTML</button>
          )}
        </div>
        {error && <div className="fp-error" style={{marginTop:10}}>⚠ {error}</div>}
      </div>

      {/* Certificate preview */}
      {generated && preview && (
        <div className="cert-preview-wrap fade-up">
          <div className="cert-preview-label">
            Certificate Preview
            <button className="btn-ghost" style={{fontSize:12,padding:'4px 10px'}} onClick={download}>
              ⬇ Download
            </button>
          </div>
          <div className="cert-preview-frame">
            <iframe
              srcDoc={preview}
              title="Fairness Certificate Preview"
              style={{width:'100%',height:'820px',border:'none',borderRadius:'12px'}}
            />
          </div>
          <div className="cert-share-note">
            💡 <strong>This is a standalone HTML file.</strong> You can open it in any browser,
            attach it to your hackathon submission, print it as PDF (Ctrl+P), 
            or host it on any website. Each certificate has a unique ID for verification.
          </div>
        </div>
      )}
    </div>
  );
}
