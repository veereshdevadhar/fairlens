import React, { useState, useEffect } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Area, AreaChart
} from 'recharts';
import api from '../utils/api';
import './FeaturePage.css';

const SEV_COLOR = { none:'#34D399', low:'#FBBF24', medium:'#FB923C', high:'#F87171' };

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  return (
    <div style={{background:'#162040',border:'1px solid rgba(99,142,255,0.2)',borderRadius:10,padding:'12px 16px',maxWidth:260}}>
      <div style={{fontFamily:'Syne,sans-serif',fontWeight:700,fontSize:14,color:'#E8EEFF',marginBottom:6}}>{d?.label}</div>
      <div style={{fontSize:13,color:SEV_COLOR[d?.severity]||'#4F8EF7',fontWeight:700,marginBottom:4}}>
        Bias Score: {d?.bias_score?.toFixed(1)}/100
      </div>
      <div style={{fontSize:12,color:'#8FA3C8',lineHeight:1.5}}>{d?.description}</div>
      <div style={{marginTop:8,fontSize:11,color:'#4A5E80'}}>{d?.label}</div>
    </div>
  );
};

export default function TimeMachine() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    api.get('/time-machine')
      .then(r => { setData(r.data); setSelected(r.data.timeline?.find(t=>t.year===2024)); })
      .catch(e => setError(e.response?.data?.detail || 'Load failed. Run an analysis first.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="fp-loading"><div className="spinner"/><span>Simulating time periods…</span></div>;
  if (error)   return <div className="fp-error">⚠ {error}</div>;
  if (!data)   return null;

  const { timeline, protected_col, privileged_group, unprivileged_group } = data;

  return (
    <div className="fp-wrap">
      <div className="fp-header">
        <div className="fp-icon">⏳</div>
        <div>
          <h2 className="fp-title">Bias Time Machine</h2>
          <p className="fp-sub">
            How would this model's bias have looked if trained on data from different eras?
            Simulating <strong>{privileged_group}</strong> vs <strong>{unprivileged_group}</strong> across time.
          </p>
        </div>
      </div>

      {/* Main chart */}
      <div className="card tm-chart-card">
        <div className="chart-label">Bias Score Across Time Periods</div>
        <ResponsiveContainer width="100%" height={320}>
          <AreaChart data={timeline} margin={{top:10,right:20,bottom:0,left:0}}>
            <defs>
              <linearGradient id="tmGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#F87171" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#F87171" stopOpacity={0.0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="year" tick={{fill:'#8FA3C8',fontSize:12}} />
            <YAxis domain={[0,100]} tick={{fill:'#8FA3C8',fontSize:11}} />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine y={30} stroke="#34D399" strokeDasharray="4 4" label={{value:'Low',fill:'#34D399',fontSize:10}} />
            <ReferenceLine y={60} stroke="#FB923C" strokeDasharray="4 4" label={{value:'Medium',fill:'#FB923C',fontSize:10}} />
            <Area type="monotone" dataKey="bias_score" stroke="#F87171" strokeWidth={3}
              fill="url(#tmGrad)" dot={(p) => (
                <circle key={p.cx} cx={p.cx} cy={p.cy} r={6}
                  fill={SEV_COLOR[p.payload?.severity]||'#4F8EF7'}
                  stroke="#060B1A" strokeWidth={2}
                  style={{cursor:'pointer'}}
                  onClick={() => setSelected(p.payload)} />
              )} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Timeline cards */}
      <div className="tm-cards">
        {timeline.map(t => (
          <button key={t.year}
            className={`tm-card ${selected?.year === t.year ? 'tm-card-sel' : ''}`}
            style={{'--sc': SEV_COLOR[t.severity]}}
            onClick={() => setSelected(t)}>
            <div className="tm-year">{t.year}</div>
            <div className="tm-score" style={{color: SEV_COLOR[t.severity]}}>{t.bias_score?.toFixed(0)}</div>
            <div className="tm-sev">{t.severity}</div>
          </button>
        ))}
      </div>

      {/* Selected detail */}
      {selected && (
        <div className="card tm-detail fade-up" style={{borderColor: SEV_COLOR[selected.severity]+'44'}}>
          <div className="tm-detail-header">
            <span className="tm-detail-year">{selected.label}</span>
            <span className="tm-detail-score" style={{color: SEV_COLOR[selected.severity]}}>
              Bias Score: {selected.bias_score?.toFixed(1)}/100
            </span>
          </div>
          <p className="tm-detail-desc">{selected.description}</p>
          <div className="tm-detail-stats">
            {[
              ['Statistical Parity Diff', selected.spd?.toFixed(4)],
              ['Disparate Impact', selected.disparate_impact?.toFixed(4)],
              [`${privileged_group} Positive Rate`, (selected.priv_pos_rate*100)?.toFixed(1)+'%'],
              [`${unprivileged_group} Positive Rate`, (selected.unpriv_pos_rate*100)?.toFixed(1)+'%'],
              ['Model Accuracy', (selected.accuracy*100)?.toFixed(1)+'%'],
            ].map(([k,v]) => (
              <div key={k} className="tm-stat">
                <span className="tm-stat-label">{k}</span>
                <span className="tm-stat-val">{v}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="fp-note">
        💡 <strong>What this shows:</strong> If your model were trained on data from earlier eras — when discrimination 
        was more prevalent in outcomes — it would have learned even more biased patterns. 
        This demonstrates why <em>when</em> data was collected matters as much as what data was collected.
      </div>
    </div>
  );
}
