import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ResponsiveContainer } from 'recharts';
import api from '../utils/api';
import './FeaturePage.css';

export default function CaseExplainer({ analysisResult }) {
  const [cases, setCases]       = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail]     = useState(null);
  const [loading, setLoading]   = useState(true);
  const [detailLoading, setDL]  = useState(false);
  const [error, setError]       = useState('');

  const priv   = analysisResult?.analysis?.overall?.privileged_group   || '';
  const unpriv = analysisResult?.analysis?.overall?.unprivileged_group || '';
  const prot   = analysisResult?.analysis?.overall?.protected_attribute || '';

  useEffect(() => {
    api.get('/cases')
      .then(r => setCases(r.data.cases || []))
      .catch(e => setError(e.response?.data?.detail || 'Load failed. Run an analysis first.'))
      .finally(() => setLoading(false));
  }, []);

  const selectCase = async (c) => {
    setSelected(c);
    setDetail(null);
    setDL(true);
    try {
      const r = await api.get(`/cases/${c.index}`);
      setDetail(r.data);
    } catch(e) {
      setError(e.response?.data?.detail || 'Could not load case details.');
    }
    setDL(false);
  };

  const contribData = (detail?.feature_contributions || [])
    .slice(0,8)
    .map(c => ({name: c.feature, value: c.contribution, magnitude: c.magnitude}));

  const cf = detail?.counterfactual;
  const pred = detail?.prediction;
  const group = detail?.group_context;

  if (loading) return <div className="fp-loading"><div className="spinner"/><span>Loading cases…</span></div>;

  return (
    <div className="fp-wrap">
      <div className="fp-header">
        <div className="fp-icon">🔍</div>
        <div>
          <h2 className="fp-title">Individual Case Explainer</h2>
          <p className="fp-sub">
            Select any person from the dataset to see exactly why the AI approved or rejected them — 
            and whether someone from the other group with identical qualifications would get a different outcome.
          </p>
        </div>
      </div>
      {error && <div className="fp-error">⚠ {error}</div>}

      <div className="ce-layout">
        {/* Case list */}
        <div className="ce-list card">
          <div className="ce-list-title">Select a Case</div>
          <div className="ce-groups">
            <div className="ce-group-label" style={{color:'#4F8EF7'}}>Privileged: {priv}</div>
            {cases.filter(c=>c.protected_value===String(priv)).map(c => (
              <CaseRow key={c.index} c={c} sel={selected?.index===c.index} onClick={()=>selectCase(c)}
                prot={prot} priv={priv} unpriv={unpriv} />
            ))}
            <div className="ce-group-label" style={{color:'#FB923C',marginTop:12}}>Unprivileged: {unpriv}</div>
            {cases.filter(c=>c.protected_value===String(unpriv)).map(c => (
              <CaseRow key={c.index} c={c} sel={selected?.index===c.index} onClick={()=>selectCase(c)}
                prot={prot} priv={priv} unpriv={unpriv} />
            ))}
          </div>
        </div>

        {/* Detail panel */}
        <div className="ce-detail">
          {!selected && (
            <div className="wi-empty">
              <div style={{fontSize:48,marginBottom:12}}>👆</div>
              <p>Select a person from the list to see a full explanation of the AI's decision.</p>
            </div>
          )}
          {detailLoading && <div className="fp-loading"><div className="spinner"/><span>Analysing case…</span></div>}

          {detail && !detailLoading && (
            <div className="fade-up">
              {/* Decision verdict */}
              <div className={`ce-verdict ${pred?.predicted===1 ? 'ce-approved' : 'ce-rejected'}`}>
                <div className="ce-verdict-icon">{pred?.predicted===1 ? '✓' : '✕'}</div>
                <div>
                  <div className="ce-verdict-title">{pred?.predicted_label}</div>
                  <div className="ce-verdict-conf">Confidence: {(pred?.confidence*100)?.toFixed(1)}%</div>
                </div>
                <div className="ce-verdict-correct">
                  {pred?.correct ? '✓ Correct' : '✕ Incorrect prediction'}
                </div>
              </div>

              {/* Counterfactual — the WOW moment */}
              <div className={`ce-counter card ${cf?.outcome_would_change ? 'ce-counter-unfair' : 'ce-counter-fair'}`}>
                <div className="ce-counter-title">
                  {cf?.outcome_would_change ? '⚠ UNFAIR: Outcome changes with group' : '✓ CONSISTENT: Outcome stays the same'}
                </div>
                <p className="ce-counter-desc">
                  <strong>What if this exact person belonged to the {cf?.other_group} group</strong> — 
                  same age, education, income, everything — only their {prot} is different?
                </p>
                <div className="ce-counter-compare">
                  <div className="ce-counter-box" style={{borderColor: pred?.predicted===1?'#34D399':'#F87171'}}>
                    <div className="ccb-group">{group?.this_person_group}</div>
                    <div className="ccb-outcome" style={{color:pred?.predicted===1?'#34D399':'#F87171'}}>
                      {pred?.predicted_label}
                    </div>
                    <div className="ccb-prob">Prob: {(pred?.probability_positive*100)?.toFixed(1)}%</div>
                  </div>
                  <div className="ce-vs">→</div>
                  <div className="ce-counter-box" style={{borderColor: cf?.other_pred===1?'#34D399':'#F87171'}}>
                    <div className="ccb-group">{cf?.other_group}</div>
                    <div className="ccb-outcome" style={{color:cf?.other_pred===1?'#34D399':'#F87171'}}>
                      {cf?.other_pred_label}
                    </div>
                    <div className="ccb-prob">Prob: {(cf?.other_prob_positive*100)?.toFixed(1)}%</div>
                  </div>
                </div>
                <div className="ce-fairness-impact" style={{
                  color: cf?.outcome_would_change ? '#F87171' : '#34D399'}}>
                  {cf?.fairness_impact}
                </div>
              </div>

              {/* Feature contributions */}
              <div className="card" style={{marginTop:16}}>
                <div className="chart-label">Why this decision? (Feature contributions)</div>
                <div style={{fontSize:12,color:'var(--text3)',marginBottom:12}}>
                  Positive bars pushed toward approval. Negative bars pushed toward rejection.
                </div>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={contribData} layout="vertical" margin={{left:20}}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                    <XAxis type="number" tick={{fill:'#8FA3C8',fontSize:10}} />
                    <YAxis dataKey="name" type="category" tick={{fill:'#8FA3C8',fontSize:11}} width={110} />
                    <Tooltip contentStyle={{background:'#162040',border:'1px solid rgba(99,142,255,0.2)',borderRadius:8}}
                      formatter={(v)=>[v?.toFixed(4),'Contribution']} />
                    <Bar dataKey="value" radius={[0,4,4,0]}>
                      {contribData.map((e,i) => (
                        <Cell key={i} fill={e.value>=0?'#34D399':'#F87171'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Group context */}
              <div className="card ce-context" style={{marginTop:16}}>
                <div className="chart-label">Group Context</div>
                <div className="ce-context-grid">
                  {[
                    ['This person\'s group', group?.this_person_group, group?.is_privileged?'#4F8EF7':'#FB923C'],
                    [`${priv} positive rate`, `${(group?.data_positive_rate_privileged*100)?.toFixed(1)}%`, '#4F8EF7'],
                    [`${unpriv} positive rate`, `${(group?.data_positive_rate_unprivileged*100)?.toFixed(1)}%`, '#FB923C'],
                    ['Gap', `${((group?.data_positive_rate_privileged - group?.data_positive_rate_unprivileged)*100)?.toFixed(1)}%`, '#F87171'],
                  ].map(([k,v,c]) => (
                    <div key={k} className="ce-ctx-item">
                      <div className="ce-ctx-val" style={{color:c}}>{v}</div>
                      <div className="ce-ctx-label">{k}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function CaseRow({ c, sel, onClick, prot, priv }) {
  const isPriv = c.protected_value === String(priv);
  return (
    <button className={`ce-case-row ${sel ? 'sel' : ''}`} onClick={onClick}>
      <span className="ce-case-idx">#{c.index}</span>
      <span className="ce-case-group" style={{color:isPriv?'#4F8EF7':'#FB923C'}}>
        {c.protected_value}
      </span>
      <span className="ce-case-label">Label: {c.label_value}</span>
    </button>
  );
}
