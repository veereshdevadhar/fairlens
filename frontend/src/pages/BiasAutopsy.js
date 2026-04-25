import React, { useState } from 'react';
import { runAutopsy } from '../utils/api';
import './FeaturePage.css';
import './BiasAutopsy.css';

const SEV_COLOR = { none:'#34D399', low:'#FBBF24', medium:'#FB923C', high:'#F87171' };
const SEV_BG    = { none:'rgba(52,211,153,0.08)', low:'rgba(251,191,36,0.08)', medium:'rgba(251,146,60,0.08)', high:'rgba(248,113,113,0.08)' };
const SEV_LABEL = { none:'Clean', low:'Low', medium:'Medium', high:'High' };

function SeverityPill({ sev }) {
  return (
    <span className="au-pill" style={{ color: SEV_COLOR[sev], background: SEV_BG[sev], border: `1px solid ${SEV_COLOR[sev]}44` }}>
      {SEV_LABEL[sev]}
    </span>
  );
}

function InvestigationCard({ inv, defaultOpen }) {
  const [open, setOpen] = useState(defaultOpen || false);
  const sev = inv.severity || 'none';

  return (
    <div className="au-card" style={{ borderLeftColor: SEV_COLOR[sev] }}>
      <button className="au-card-header" onClick={() => setOpen(o => !o)}>
        <span className="au-card-icon">{inv.icon}</span>
        <span className="au-card-title">{inv.title}</span>
        <SeverityPill sev={sev} />
        <span className="au-card-chevron">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="au-card-body fade-up">
          {/* Verdict */}
          <div className="au-verdict" style={{ background: SEV_BG[sev], borderColor: SEV_COLOR[sev] + '44' }}>
            <span className="au-verdict-icon">{sev === 'high' ? '🔴' : sev === 'medium' ? '🟠' : sev === 'low' ? '🟡' : '🟢'}</span>
            <p className="au-verdict-text">{inv.verdict}</p>
          </div>

          {/* Explanation */}
          {inv.explanation && (
            <p className="au-explanation">{inv.explanation}</p>
          )}

          {/* Investigation-specific content */}
          {inv.title === 'Historical Outcome Bias' && inv.stats && (
            <HistoricalDetail inv={inv} />
          )}
          {inv.title === 'Proxy Chain Analysis' && inv.chains && (
            <ProxyDetail inv={inv} />
          )}
          {inv.title === 'Intersectional Bias Detection' && inv.intersections && (
            <IntersectionalDetail inv={inv} />
          )}
          {inv.title === 'Decision Boundary Audit' && inv.boundary_findings && (
            <BoundaryDetail inv={inv} />
          )}
        </div>
      )}
    </div>
  );
}

function HistoricalDetail({ inv }) {
  const s = inv.stats || {};
  const entries = Object.entries(s).filter(([k]) =>
    !['chi2_statistic','p_value','statistically_significant','outcome_ratio'].includes(k));

  return (
    <div>
      <div className="au-stat-grid">
        {entries.map(([k, v]) => (
          <div key={k} className="au-stat-box">
            <div className="au-stat-val">{typeof v === 'number' ? (k.includes('rate') ? `${(v*100).toFixed(1)}%` : v.toLocaleString()) : String(v)}</div>
            <div className="au-stat-label">{k.replace(/_/g,' ')}</div>
          </div>
        ))}
      </div>
      <div className="au-stat-row">
        <div className="au-stat-chip" style={{ color: SEV_COLOR[s.statistically_significant ? 'high':'none'], background: SEV_BG[s.statistically_significant ? 'high':'none'] }}>
          {s.statistically_significant ? '✕ Statistically Significant (p < 0.05)' : '✓ Not Statistically Significant'}
        </div>
        <div className="au-stat-chip">χ² = {s.chi2_statistic?.toFixed(2)} | p = {s.p_value?.toFixed(4)} | ratio = {s.outcome_ratio?.toFixed(2)}×</div>
      </div>
      {inv.label_distribution && (
        <div className="au-label-dist">
          <div className="au-section-mini-title">Label Distribution per Group</div>
          {Object.entries(inv.label_distribution).map(([group, dist]) => (
            <div key={group} className="au-dist-row">
              <span className="au-dist-group">{group}</span>
              {Object.entries(dist).map(([label, pct]) => (
                <div key={label} className="au-dist-bar-wrap">
                  <span className="au-dist-label">{label}:</span>
                  <div className="au-dist-bg">
                    <div className="au-dist-fill" style={{ width: `${pct*100}%`, background: label === '1' || label === 'True' ? '#34D399' : '#F87171' }} />
                  </div>
                  <span className="au-dist-pct">{(pct*100).toFixed(1)}%</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ProxyDetail({ inv }) {
  return (
    <div>
      {inv.chains && inv.chains.length > 0 && (
        <div>
          <div className="au-section-mini-title">Proxy Chains (Feature → Protected → Outcome)</div>
          {inv.chains.map((c, i) => (
            <div key={i} className="au-chain-row">
              <div className="au-chain-flow">
                <span className="au-chain-node au-node-feat">{c.feature}</span>
                <span className="au-chain-arrow">→<span className="au-chain-corr">{c.corr_with_protected?.toFixed(2)}</span></span>
                <span className="au-chain-node au-node-prot">protected</span>
                <span className="au-chain-arrow">→<span className="au-chain-corr">{c.corr_with_label?.toFixed(2)}</span></span>
                <span className="au-chain-node au-node-out">outcome</span>
                <SeverityPill sev={c.risk} />
              </div>
              <div className="au-chain-desc">{c.chain_description}</div>
            </div>
          ))}
        </div>
      )}
      {inv.multi_hop && inv.multi_hop.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div className="au-section-mini-title">Multi-Hop Correlations (removing one feature is not enough)</div>
          {inv.multi_hop.map((h, i) => (
            <div key={i} className="au-multihop-row">
              <div className="au-chain-flow">
                <span className="au-chain-node au-node-feat">{h.feature_a}</span>
                <span className="au-chain-arrow">↔<span className="au-chain-corr">{h.a_b_corr?.toFixed(2)}</span></span>
                <span className="au-chain-node au-node-feat">{h.feature_b}</span>
              </div>
              <div className="au-chain-desc">{h.description}</div>
            </div>
          ))}
        </div>
      )}
      {(!inv.chains || inv.chains.length === 0) && (
        <div className="au-empty-note">No significant proxy chains detected in this dataset.</div>
      )}
    </div>
  );
}

function IntersectionalDetail({ inv }) {
  const gap = inv.baseline_gap;
  return (
    <div>
      <div className="au-baseline-note">
        Baseline gap between groups: <strong style={{ color: SEV_COLOR[gap > 0.1 ? 'high' : 'low'] }}>{(gap*100).toFixed(1)}%</strong>
        &nbsp;— any subgroup exceeding this is experiencing amplified discrimination.
      </div>
      {inv.intersections && inv.intersections.length > 0 ? (
        <div>
          <div className="au-section-mini-title">Subgroup Analysis ({inv.intersections.length} intersections found)</div>
          <div className="au-intersect-table-wrap">
            <table className="au-intersect-table">
              <thead>
                <tr>
                  <th>Subgroup</th>
                  <th>Value</th>
                  <th>Priv Rate</th>
                  <th>Unpriv Rate</th>
                  <th>Gap</th>
                  <th>vs Baseline</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {inv.intersections.map((s, i) => (
                  <tr key={i} className={s.is_amplified ? 'au-row-amplified' : ''}>
                    <td>{s.column}</td>
                    <td><strong>{s.value}</strong></td>
                    <td>{(s.priv_rate*100).toFixed(1)}%</td>
                    <td>{(s.unpriv_rate*100).toFixed(1)}%</td>
                    <td style={{ color: SEV_COLOR[s.gap > 0.15 ? 'high' : s.gap > 0.08 ? 'medium' : 'low'], fontWeight: 700 }}>
                      {(s.gap*100).toFixed(1)}%
                    </td>
                    <td style={{ color: s.amplification > 0 ? '#F87171' : '#34D399', fontWeight: 600 }}>
                      {s.amplification > 0 ? '+' : ''}{(s.amplification*100).toFixed(1)}pp
                    </td>
                    <td>
                      {s.is_amplified
                        ? <span style={{ color:'#F87171', fontSize:11, fontWeight:700 }}>⚠ AMPLIFIED</span>
                        : <span style={{ color:'#34D399', fontSize:11 }}>Normal</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="au-empty-note">No intersectional subgroups with sufficient sample size found.</div>
      )}
    </div>
  );
}

function BoundaryDetail({ inv }) {
  const gapPct = (inv.approval_prob_gap * 100).toFixed(1);
  const gapCol = Math.abs(inv.approval_prob_gap) > 0.1 ? '#F87171' : '#FBBF24';

  return (
    <div>
      <div className="au-boundary-summary">
        <div className="au-bsumm-box">
          <div className="au-bsumm-val" style={{ color:'#4F8EF7' }}>{(inv.avg_priv_approval*100).toFixed(1)}%</div>
          <div className="au-bsumm-label">Privileged approval probability</div>
        </div>
        <div className="au-bsumm-arrow">→</div>
        <div className="au-bsumm-box">
          <div className="au-bsumm-val" style={{ color:'#FB923C' }}>{(inv.avg_unpriv_approval*100).toFixed(1)}%</div>
          <div className="au-bsumm-label">Unprivileged approval probability</div>
        </div>
        <div className="au-bsumm-gap" style={{ color: gapCol }}>
          {gapPct}pp gap
        </div>
      </div>

      {inv.boundary_findings && inv.boundary_findings.length > 0 ? (
        <div>
          <div className="au-section-mini-title">Numeric Threshold Differences Per Group</div>
          {inv.boundary_findings.map((b, i) => (
            <div key={i} className="au-boundary-row">
              <div className="au-boundary-feat">{b.feature}</div>
              <div className="au-boundary-bars">
                <div className="au-bbar-wrap">
                  <span className="au-bbar-label">Privileged needs ≥</span>
                  <span className="au-bbar-val" style={{ color:'#4F8EF7' }}>{b.priv_threshold?.toFixed(1)}{b.unit}</span>
                </div>
                <div className="au-bbar-wrap">
                  <span className="au-bbar-label">Unprivileged needs ≥</span>
                  <span className="au-bbar-val" style={{ color:'#FB923C' }}>{b.unpriv_threshold?.toFixed(1)}{b.unit}</span>
                </div>
                <div className="au-penalty" style={{ color: b.penalty > 0 ? '#F87171' : '#34D399' }}>
                  {b.penalty > 0 ? '▲' : '▼'} {Math.abs(b.penalty)?.toFixed(1)}{b.unit} penalty for unprivileged group
                </div>
              </div>
              <div className="au-chain-desc">{b.description}</div>
            </div>
          ))}
        </div>
      ) : (
        <div className="au-empty-note">No clear numeric threshold differences detected.</div>
      )}
    </div>
  );
}


export default function BiasAutopsy({ analysisResult }) {
  const [report, setReport]   = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');
  const [started, setStarted] = useState(false);

  const score    = analysisResult?.analysis?.overall?.bias_score || 0;
  const severity = analysisResult?.analysis?.overall?.severity   || 'none';
  const prot     = analysisResult?.analysis?.overall?.protected_attribute || '';
  const priv     = analysisResult?.analysis?.overall?.privileged_group    || '';
  const unpriv   = analysisResult?.analysis?.overall?.unprivileged_group  || '';

  const startAutopsy = async () => {
    setStarted(true);
    setLoading(true);
    setError('');
    try {
      const r = await runAutopsy();
      setReport(r);
    } catch(e) {
      setError(e.response?.data?.detail || 'Autopsy failed. Make sure you ran an analysis first.');
    }
    setLoading(false);
  };

  const SEV_COL = { none:'#34D399', low:'#FBBF24', medium:'#FB923C', high:'#F87171' };

  return (
    <div className="fp-wrap">
      <div className="fp-header">
        <div className="fp-icon">🔬</div>
        <div>
          <h2 className="fp-title">Bias Autopsy</h2>
          <p className="fp-sub">
            Automated root-cause investigation — <em>WHY</em> does this bias exist?
            Four forensic tests find the exact origin, pathway, and tipping point of discrimination.
          </p>
        </div>
      </div>

      {/* Pre-run summary */}
      {!started && (
        <div className="au-intro fade-up">
          <div className="au-intro-score">
            <div className="au-intro-num" style={{ color: SEV_COL[severity] }}>{score.toFixed(0)}</div>
            <div className="au-intro-label">Bias Score</div>
          </div>
          <div className="au-intro-text">
            <p>Your model has a <strong style={{ color: SEV_COL[severity] }}>{severity} severity</strong> bias score
            of {score.toFixed(0)}/100, comparing <strong>{priv}</strong> vs <strong>{unpriv}</strong>
            on the <strong>{prot}</strong> attribute.</p>
            <p>Standard tools tell you <em>that</em> bias exists. Bias Autopsy tells you <em>exactly why</em>.</p>
            <div className="au-investigation-list">
              {[
                { icon:'📜', label:'Historical Outcome Bias', desc:'Was the training data itself already unfair before any model was built?' },
                { icon:'🔗', label:'Proxy Chain Analysis',    desc:'Which features act as indirect proxies? What is the full discrimination pathway?' },
                { icon:'⚡', label:'Intersectional Bias',     desc:'Is the bias worse for specific subgroups that standard metrics hide?' },
                { icon:'📏', label:'Decision Boundary Audit', desc:'What exact numeric score does each group need to get approved?' },
              ].map(({ icon, label, desc }) => (
                <div key={label} className="au-inv-item">
                  <span className="au-inv-icon">{icon}</span>
                  <div>
                    <div className="au-inv-label">{label}</div>
                    <div className="au-inv-desc">{desc}</div>
                  </div>
                </div>
              ))}
            </div>
            <button className="btn-primary au-start-btn" onClick={startAutopsy}>
              🔬 Start Bias Autopsy
            </button>
          </div>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="au-loading">
          <div className="au-loading-spinner" />
          <div className="au-loading-text">
            <h3>Running Forensic Investigation…</h3>
            <div className="au-loading-steps">
              {['Testing historical outcome inequality',
                'Mapping proxy feature chains',
                'Scanning intersectional subgroups',
                'Measuring decision boundaries per group',
                'Synthesising root cause verdict'].map((s, i) => (
                <div key={i} className="au-loading-step" style={{ animationDelay:`${i*0.5}s` }}>
                  <span className="running-dot" />
                  <span>{s}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Error */}
      {error && <div className="fp-error">⚠ {error}</div>}

      {/* Results */}
      {report && !loading && (
        <div className="au-results fade-up">
          {/* Overall verdict banner */}
          <div className="au-verdict-banner" style={{
            background: SEV_BG[report.overall.max_severity],
            borderColor: SEV_COL[report.overall.max_severity] + '55'
          }}>
            <div className="au-vb-left">
              <div className="au-vb-title" style={{ color: SEV_COL[report.overall.max_severity] }}>
                Root Cause Identified
              </div>
              <div className="au-vb-primary">{report.overall.primary_cause}</div>
              <p className="au-vb-narrative"
                dangerouslySetInnerHTML={{ __html: report.overall.narrative }} />
            </div>
            <div className="au-vb-right">
              <div className="au-vb-stat">
                <div className="au-vb-stat-num" style={{ color: SEV_COL[report.overall.max_severity] }}>
                  {report.overall.causes_found}
                </div>
                <div className="au-vb-stat-label">Root Causes Found</div>
              </div>
              <div className="au-sev-row">
                {Object.entries(report.overall.severities).map(([k, s]) => (
                  <div key={k} className="au-sev-chip" style={{ color: SEV_COL[s], background: SEV_BG[s] }}>
                    {k === 'historical' ? '📜' : k === 'proxy_chains' ? '🔗' : k === 'intersectional' ? '⚡' : '📏'}
                    {SEV_LABEL[s]}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Four investigation cards */}
          <div className="au-investigations">
            {Object.values(report.investigations).map((inv, i) => (
              <InvestigationCard key={inv.title} inv={inv}
                defaultOpen={inv.severity === 'high' || inv.severity === 'medium'} />
            ))}
          </div>

          {/* Run again button */}
          <div style={{ textAlign:'center', marginTop:20 }}>
            <button className="btn-ghost" onClick={startAutopsy}>↺ Re-run Autopsy</button>
          </div>
        </div>
      )}
    </div>
  );
}
