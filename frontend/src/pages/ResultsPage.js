import React, { useState } from 'react';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, Cell
} from 'recharts';
import { downloadReport } from '../utils/api';
import TimeMachine     from './TimeMachine';
import WhatIf          from './WhatIf';
import CaseExplainer   from './CaseExplainer';
import GeminiChat      from './GeminiChat';
import CertificatePage from './Certificate';
import BiasAutopsy     from './BiasAutopsy';
import './ResultsPage.css';

const SEV_COLOR = { none:'#34D399', low:'#FBBF24', medium:'#FB923C', high:'#F87171' };
const SEV_LABEL = { none:'No Bias', low:'Low Bias', medium:'Moderate Bias', high:'High Bias' };

function SevBadge({ sev }) {
  return (
    <span className={`sev-badge sev-bg-${sev}`} style={{ color: SEV_COLOR[sev] }}>
      {SEV_LABEL[sev]}
    </span>
  );
}

function GaugeScore({ score, severity }) {
  const color = SEV_COLOR[severity] || '#4F8EF7';
  const pct   = Math.min(score, 100);
  const r = 60; const cx = 80; const cy = 80;
  const circ = 2 * Math.PI * r;
  const arc  = circ * 0.75;
  const filled = arc * (pct / 100);
  const offset = circ * 0.125;
  return (
    <svg width="160" height="120" viewBox="0 0 160 120">
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(255,255,255,0.06)"
        strokeWidth="12" strokeDasharray={`${arc} ${circ - arc}`}
        strokeDashoffset={-offset} strokeLinecap="round" />
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={color}
        strokeWidth="12" strokeDasharray={`${filled} ${circ - filled}`}
        strokeDashoffset={-offset} strokeLinecap="round"
        style={{ transition: 'stroke-dasharray 1s ease', filter: `drop-shadow(0 0 8px ${color}60)` }} />
      <text x={cx} y={cy - 4} textAnchor="middle" fill={color}
        fontSize="28" fontWeight="800" fontFamily="Syne, sans-serif">{Math.round(pct)}</text>
      <text x={cx} y={cy + 16} textAnchor="middle" fill="#8FA3C8"
        fontSize="11" fontFamily="DM Sans, sans-serif">/ 100</text>
      <text x={cx} y={cy + 34} textAnchor="middle" fill={color}
        fontSize="12" fontWeight="700" fontFamily="DM Sans, sans-serif">
        {(SEV_LABEL[severity] || '').toUpperCase()}
      </text>
    </svg>
  );
}

function MetricBar({ label, value, ideal, severity, description }) {
  const pct = Math.min(Math.abs(value || 0) * 200, 100);
  const col = SEV_COLOR[severity] || '#4F8EF7';
  return (
    <div className="metric-row">
      <div className="metric-top">
        <span className="metric-label">{label}</span>
        <span className="metric-val" style={{ color: col }}>{value !== null ? value.toFixed(4) : 'N/A'}</span>
        <SevBadge sev={severity} />
      </div>
      <div className="metric-bar-bg">
        <div className="metric-bar-fill" style={{ '--w': `${pct}%`, background: col }} />
      </div>
      <div className="metric-desc">{description}</div>
      <div className="metric-ideal">Ideal: {ideal}</div>
    </div>
  );
}

const METRIC_LABELS = {
  statistical_parity_difference:     'Statistical Parity Difference',
  disparate_impact:                  'Disparate Impact Ratio',
  equalized_odds_difference_tpr:     'Equalized Odds (TPR)',
  equalized_odds_difference_fpr:     'Equalized Odds (FPR)',
  predictive_parity_difference:      'Predictive Parity Difference',
  accuracy_difference:               'Accuracy Difference',
};

const ALL_TABS = [
  { id:'overview',    label:'Overview',       icon:'📊', wow: false },
  { id:'metrics',     label:'Metrics',        icon:'📐', wow: false },
  { id:'groups',      label:'Groups',         icon:'👥', wow: false },
  { id:'features',    label:'Features',       icon:'🧬', wow: false },
  { id:'fixes',       label:'Fixes',          icon:'🔧', wow: false },
  { id:'timemachine', label:'Time Machine',   icon:'⏳', wow: true  },
  { id:'whatif',      label:'What-If',        icon:'🧪', wow: true  },
  { id:'cases',       label:'Case Explainer', icon:'🔍', wow: true  },
  { id:'chat',        label:'Ask AI',         icon:'💬', wow: true  },
  { id:'certificate', label:'Certificate',    icon:'🏆', wow: true  },
  { id:'autopsy',     label:'Bias Autopsy',   icon:'🔬', wow: true  },
];

export default function ResultsPage({ result, config, goTo }) {
  const [activeTab, setTab] = useState('overview');
  const [downloading, setDL] = useState(false);

  const analysis = result?.analysis || {};
  const recs     = result?.recommendations || [];
  const overall  = analysis.overall || {};
  const metrics  = analysis.metrics || {};
  const groups   = analysis.group_stats || {};
  const features = analysis.feature_importance || {};
  const proxies  = analysis.proxy_features || {};

  const severity  = overall.severity || 'none';
  const biasScore = overall.bias_score || 0;
  const groupNames = Object.keys(groups);

  const barData = groupNames.map(g => ({
    name: g,
    'Positive Rate':   +(groups[g].positive_rate  * 100).toFixed(1),
    'Accuracy':        +(groups[g].model_accuracy  * 100).toFixed(1),
    'True Pos. Rate':  +(groups[g].true_positive_rate * 100).toFixed(1),
    'False Pos. Rate': +(groups[g].false_positive_rate * 100).toFixed(1),
  }));

  const radarData = Object.entries(METRIC_LABELS).map(([key, label]) => {
    const m    = metrics[key] || {};
    const score = Math.min(Math.abs(m.value || 0) * 500, 100);
    return { metric: label.split(' ').slice(0,3).join(' '), score: +score.toFixed(1) };
  });

  const featureData = Object.entries(features).slice(0,8)
    .map(([k,v]) => ({ name:k, importance: +(v*100).toFixed(2) }));

  const handleDownload = () => {
    setDL(true);
    const a = document.createElement('a');
    a.href = downloadReport(); a.download = 'fairlens_report.pdf'; a.click();
    setTimeout(() => setDL(false), 2000);
  };

  const wowTabs = ALL_TABS.filter(t => t.wow);
  const coreTabs = ALL_TABS.filter(t => !t.wow);

  return (
    <div className="results-page">
      <div className="results-inner">

        {/* Summary bar */}
        <div className="summary-bar fade-up">
          <div className="summary-left">
            <div className="summary-title">
              Bias Audit: <span>{config?.datasetName || 'Dataset'}</span>
            </div>
            <div className="summary-meta">
              Protected: <strong>{overall.protected_attribute}</strong> ·
              Groups: <strong>{overall.privileged_group}</strong> vs <strong>{overall.unprivileged_group}</strong> ·
              Rows: <strong>{(overall.total_rows||0).toLocaleString()}</strong> ·
              Accuracy: <strong>{((overall.model_accuracy||0)*100).toFixed(1)}%</strong>
            </div>
          </div>
          <div className="summary-actions">
            <button className="btn-outline" onClick={() => goTo('analyze')}>← New Audit</button>
            <button className="btn-primary" onClick={handleDownload} disabled={downloading}>
              {downloading ? 'Generating…' : '⬇ PDF Report'}
            </button>
          </div>
        </div>

        {/* Score hero */}
        <div className="score-hero card fade-up">
          <div className="score-gauge"><GaugeScore score={biasScore} severity={severity} /></div>
          <div className="score-detail">
            <h2 className="score-headline" style={{ color: SEV_COLOR[severity] }}>
              {severity === 'none'   && 'No Significant Bias Detected'}
              {severity === 'low'    && 'Low-Level Bias Detected'}
              {severity === 'medium' && 'Moderate Bias — Action Recommended'}
              {severity === 'high'   && 'High Bias — Immediate Action Required'}
            </h2>
            <p className="score-desc">
              {severity === 'none'   && `The model treats "${overall.privileged_group}" and "${overall.unprivileged_group}" with no statistically significant difference.`}
              {severity === 'low'    && `Minor disparities exist between "${overall.privileged_group}" and "${overall.unprivileged_group}". Monitor closely.`}
              {severity === 'medium' && `Meaningful disparities found. Implement recommended fixes before deployment.`}
              {severity === 'high'   && `Severe disparities. Do not deploy without fixes. "${overall.unprivileged_group}" is significantly disadvantaged.`}
            </p>
            <div className="score-quick-stats">
              {[
                { label:'Bias Score',     val:`${Math.round(biasScore)}/100`,  col:SEV_COLOR[severity] },
                { label:'Severity',       val:SEV_LABEL[severity],             col:SEV_COLOR[severity] },
                { label:'Fixes',          val:`${recs.length} found`,          col:'#4F8EF7' },
                { label:'Proxy Features', val:Object.keys(proxies).length,     col:Object.keys(proxies).length>0?'#FB923C':'#34D399' },
              ].map(s => (
                <div key={s.label} className="quick-stat">
                  <span className="qs-val" style={{ color: s.col }}>{s.val}</span>
                  <span className="qs-label">{s.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* WOW feature callout */}
        <div className="wow-banner fade-up">
          <span className="wow-label">✦ WOW Features</span>
          {wowTabs.map(t => (
            <button key={t.id}
              className={`wow-btn ${activeTab === t.id ? 'active' : ''}`}
              onClick={() => setTab(t.id)}>
              {t.icon} {t.label}
            </button>
          ))}
        </div>

        {/* Core tab bar */}
        <div className="tab-bar">
          {coreTabs.map(t => (
            <button key={t.id}
              className={`tab-btn ${activeTab === t.id ? 'active' : ''}`}
              onClick={() => setTab(t.id)}>
              {t.icon} {t.label}
              {t.id === 'fixes' && <span className="tab-badge">{recs.length}</span>}
            </button>
          ))}
        </div>

        {/* ── WOW FEATURE TABS ── */}
        {activeTab === 'timemachine'  && <TimeMachine />}
        {activeTab === 'whatif'       && <WhatIf analysisResult={result} />}
        {activeTab === 'cases'        && <CaseExplainer analysisResult={result} />}
        {activeTab === 'chat'         && <GeminiChat />}
        {activeTab === 'certificate'  && <CertificatePage analysisResult={result} />}
        {activeTab === 'autopsy'       && <BiasAutopsy      analysisResult={result} />}

        {/* ── CORE TABS ── */}

        {activeTab === 'overview' && (
          <div className="tab-content fade-up">
            <div className="charts-row">
              <div className="card chart-card">
                <div className="chart-title">Bias Dimensions Radar</div>
                <div className="chart-sub">Higher = more bias in that dimension</div>
                <ResponsiveContainer width="100%" height={280}>
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="rgba(255,255,255,0.08)" />
                    <PolarAngleAxis dataKey="metric" tick={{ fill:'#8FA3C8', fontSize:11 }} />
                    <PolarRadiusAxis angle={30} domain={[0,100]} tick={{ fill:'#4A5E80', fontSize:9 }} />
                    <Radar name="Bias Score" dataKey="score" stroke="#F87171" fill="#F87171" fillOpacity={0.22} strokeWidth={2} />
                    <Tooltip contentStyle={{ background:'#162040', border:'1px solid rgba(99,142,255,0.2)', borderRadius:8 }} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
              <div className="card chart-card">
                <div className="chart-title">Group Comparison</div>
                <div className="chart-sub">Side-by-side stats (%)</div>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={barData} barGap={4}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="name" tick={{ fill:'#8FA3C8', fontSize:11 }} />
                    <YAxis tick={{ fill:'#8FA3C8', fontSize:10 }} domain={[0,100]} />
                    <Tooltip contentStyle={{ background:'#162040', border:'1px solid rgba(99,142,255,0.2)', borderRadius:8 }} />
                    <Legend wrapperStyle={{ fontSize:12, color:'#8FA3C8' }} />
                    <Bar dataKey="Positive Rate"  fill="#4F8EF7" radius={[4,4,0,0]} />
                    <Bar dataKey="Accuracy"       fill="#34D399" radius={[4,4,0,0]} />
                    <Bar dataKey="True Pos. Rate" fill="#FBBF24" radius={[4,4,0,0]} />
                    <Bar dataKey="False Pos. Rate" fill="#F87171" radius={[4,4,0,0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div className="card" style={{ marginTop:20 }}>
              <div className="chart-title">Top Feature Importances</div>
              <div className="chart-sub">Features the model relies on most (Random Forest)</div>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={featureData} layout="vertical" margin={{ left:20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                  <XAxis type="number" tick={{ fill:'#8FA3C8', fontSize:10 }} />
                  <YAxis dataKey="name" type="category" tick={{ fill:'#8FA3C8', fontSize:11 }} width={120} />
                  <Tooltip contentStyle={{ background:'#162040', border:'1px solid rgba(99,142,255,0.2)', borderRadius:8 }} />
                  <Bar dataKey="importance" radius={[0,4,4,0]}>
                    {featureData.map((entry,i) => (
                      <Cell key={i} fill={Object.keys(proxies).includes(entry.name) ? '#FB923C' : '#4F8EF7'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              {Object.keys(proxies).length > 0 && (
                <div className="proxy-note">🔶 <strong style={{color:'#FB923C'}}>Orange</strong> = proxy features correlated with protected attribute</div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'metrics' && (
          <div className="tab-content fade-up">
            <div className="card">
              <h3 className="card-heading">All Fairness Metrics</h3>
              <p className="card-desc">
                Comparing <strong style={{color:'#4F8EF7'}}>{overall.privileged_group}</strong> vs <strong style={{color:'#FB923C'}}>{overall.unprivileged_group}</strong> across 6 dimensions.
              </p>
              <div className="metrics-list">
                {Object.entries(METRIC_LABELS).map(([key,label]) => {
                  const m = metrics[key] || {};
                  return <MetricBar key={key} label={label} value={m.value}
                    ideal={m.ideal} severity={m.severity||'none'} description={m.description} />;
                })}
              </div>
            </div>
            {Object.keys(proxies).length > 0 && (
              <div className="card" style={{ marginTop:20, borderColor:'rgba(251,146,60,0.3)' }}>
                <h3 className="card-heading" style={{color:'#FB923C'}}>⚠ Proxy Features Detected</h3>
                <p className="card-desc">These features are correlated with <strong>{overall.protected_attribute}</strong> and may enable indirect discrimination.</p>
                <div className="proxy-grid">
                  {Object.entries(proxies).map(([feat,corr]) => (
                    <div key={feat} className="proxy-card">
                      <div className="proxy-feat">{feat}</div>
                      <div className="proxy-corr">Correlation: <strong style={{color:corr>0.5?'#F87171':'#FB923C'}}>{corr.toFixed(3)}</strong></div>
                      <div className="proxy-risk">{corr>0.5?'🔴 High Risk':corr>0.35?'🟠 Medium Risk':'🟡 Low Risk'}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'groups' && (
          <div className="tab-content fade-up">
            <div className="card">
              <h3 className="card-heading">Group-Level Statistics</h3>
              <p className="card-desc">Every performance metric compared side by side.</p>
              <div className="groups-table-wrap">
                <table className="groups-table">
                  <thead>
                    <tr>
                      <th>Metric</th>
                      {groupNames.map(g => (
                        <th key={g}>
                          {g}
                          {g === String(overall.privileged_group) && <span className="priv-tag">privileged</span>}
                          {g === String(overall.unprivileged_group) && <span className="unpriv-tag">unprivileged</span>}
                        </th>
                      ))}
                      <th>Difference</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      ['Sample Size','count',false],
                      ['Positive Outcome Rate','positive_rate',true],
                      ['Model Accuracy','model_accuracy',true],
                      ['True Positive Rate','true_positive_rate',true],
                      ['False Positive Rate','false_positive_rate',true],
                      ['Precision (PPV)','precision',true],
                    ].map(([label,key,isRate]) => {
                      const vals = groupNames.map(g => groups[g]?.[key] ?? null);
                      const [v0,v1] = vals;
                      const diff = (isRate && v0!==null && v1!==null) ? (v1-v0) : null;
                      return (
                        <tr key={key}>
                          <td className="stat-label">{label}</td>
                          {vals.map((v,i) => (
                            <td key={i} className="stat-val">
                              {v===null ? 'N/A' : isRate ? `${(v*100).toFixed(2)}%` : v.toLocaleString()}
                            </td>
                          ))}
                          <td className="stat-diff"
                            style={{color:diff===null?'inherit':Math.abs(diff)>0.05?'#F87171':'#34D399'}}>
                            {diff!==null ? `${diff>0?'+':''}${(diff*100).toFixed(2)}%` : '—'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'features' && (
          <div className="tab-content fade-up">
            <div className="card">
              <h3 className="card-heading">Feature Importance Analysis</h3>
              <p className="card-desc">How much each feature influences the model. Proxy features (correlated with protected attribute) are flagged.</p>
              <div className="feat-list">
                {Object.entries(features).map(([feat,imp],i) => {
                  const isProxy = Object.keys(proxies).includes(feat);
                  return (
                    <div key={feat} className={`feat-row ${isProxy?'is-proxy':''}`}>
                      <div className="feat-rank">{i+1}</div>
                      <div className="feat-info">
                        <div className="feat-name">
                          {feat}
                          {isProxy && <span className="proxy-flag">PROXY</span>}
                          {feat===overall.protected_attribute && <span className="prot-flag">PROTECTED</span>}
                        </div>
                        <div className="feat-bar-bg">
                          <div className="feat-bar-fill"
                            style={{'--fw':`${Math.min(imp*500,100)}%`, background:isProxy?'#FB923C':'#4F8EF7'}} />
                        </div>
                      </div>
                      <div className="feat-pct" style={{color:isProxy?'#FB923C':'#4F8EF7'}}>{(imp*100).toFixed(2)}%</div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'fixes' && (
          <div className="tab-content fade-up">
            <div className="fixes-header">
              <h3>Fix Recommendations</h3>
              <p>{recs.length} actionable steps to reduce bias in this model</p>
            </div>
            {recs.map((rec,i) => (
              <div key={rec.id} className={`rec-card priority-${rec.priority}`}>
                <div className="rec-header">
                  <div className="rec-num">{i+1}</div>
                  <div className="rec-title">{rec.title}</div>
                  <div className="rec-tags">
                    <span className={`rec-tag priority-tag-${rec.priority}`}>{rec.priority?.toUpperCase()} PRIORITY</span>
                    <span className="rec-tag impact-tag">{rec.impact?.toUpperCase()} IMPACT</span>
                    <span className="rec-tag effort-tag">{rec.effort?.toUpperCase()} EFFORT</span>
                  </div>
                </div>
                <p className="rec-desc">{rec.description}</p>
                {rec.code && (
                  <div className="rec-code-wrap">
                    <div className="rec-code-label">Suggested implementation:</div>
                    <pre className="rec-code">{rec.code}</pre>
                  </div>
                )}
              </div>
            ))}
            <div className="download-cta">
              <div>
                <strong>Get the full PDF report</strong>
                <p>Complete audit with all metrics, charts and recommendations.</p>
              </div>
              <button className="btn-primary" onClick={handleDownload} disabled={downloading}>
                {downloading ? 'Generating PDF…' : '⬇ Download PDF Report'}
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
