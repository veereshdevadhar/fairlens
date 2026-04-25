import React from 'react';
import './LandingPage.css';

const REAL_CASES = [
  { icon: '⚖️', domain: 'Criminal Justice', system: 'COMPAS Algorithm',
    fact: '2× more likely to falsely flag Black defendants as high-risk', color: '#F87171' },
  { icon: '💼', domain: 'Hiring', system: 'Amazon Recruiting AI',
    fact: 'Penalised resumes mentioning "women\'s" — scrapped in 2018', color: '#FB923C' },
  { icon: '🏥', domain: 'Healthcare', system: 'Patient Risk Algorithm',
    fact: 'Black patients needed to be sicker to receive same care', color: '#FBBF24' },
  { icon: '📸', domain: 'Facial Recognition', system: 'Commercial Systems',
    fact: '35% error rate on dark-skinned women vs <1% for white men', color: '#A78BFA' },
  { icon: '🏦', domain: 'Banking', system: 'Apple Card Credit AI',
    fact: 'Women given 10× lower credit limits than men with same finances', color: '#34D399' },
];

const HOW_STEPS = [
  { num: '01', title: 'Upload or select dataset', desc: 'Use our real benchmark datasets or upload your own CSV/Excel file.' },
  { num: '02', title: 'Configure the audit', desc: 'Choose the label column, the protected attribute, and the groups to compare.' },
  { num: '03', title: 'Get instant bias report', desc: 'FairLens computes 6 fairness metrics and flags bias with clear severity scores.' },
  { num: '04', title: 'Fix it with AI guidance', desc: 'Get step-by-step fix recommendations and downloadable PDF audit reports.' },
];

export default function LandingPage({ goTo }) {
  return (
    <div className="landing">
      {/* Hero */}
      <section className="hero">
        <div className="hero-badge">Google Solution Challenge 2026</div>
        <h1 className="hero-title">
          Find and Fix<br />
          <span>Hidden Bias</span> in AI
        </h1>
        <p className="hero-sub">
          FairLens audits your datasets and models for racial, gender, and age discrimination
          — before your AI harms real people.
        </p>
        <div className="hero-actions">
          <button className="btn-primary" onClick={() => goTo('analyze')}>
            Start Free Audit →
          </button>
          <button className="btn-outline" onClick={() => goTo('analyze')}>
            Try with COMPAS Dataset
          </button>
        </div>
        <div className="hero-stats">
          {[
            ['72%', 'of companies use AI in hiring'],
            ['35%', 'facial recognition error — dark-skinned women'],
            ['0%', 'of AI systems publish fairness audits'],
          ].map(([n, l]) => (
            <div className="hero-stat" key={n}>
              <span className="hero-stat-num">{n}</span>
              <span className="hero-stat-label">{l}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Real cases */}
      <section className="section cases-section">
        <div className="section-inner">
          <h2 className="section-title">Real-World AI Bias Cases</h2>
          <p className="section-sub">These are documented real systems that caused measurable harm.</p>
          <div className="cases-grid">
            {REAL_CASES.map(c => (
              <div className="case-card" key={c.domain} style={{ '--accent-col': c.color }}>
                <div className="case-icon">{c.icon}</div>
                <div className="case-domain">{c.domain}</div>
                <div className="case-system">{c.system}</div>
                <div className="case-fact">"{c.fact}"</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="section how-section">
        <div className="section-inner">
          <h2 className="section-title">How FairLens Works</h2>
          <div className="how-grid">
            {HOW_STEPS.map((s, i) => (
              <div className="how-step" key={s.num}
                   style={{ animationDelay: `${i * 0.1}s` }}>
                <div className="how-num">{s.num}</div>
                <div className="how-title">{s.title}</div>
                <div className="how-desc">{s.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Metrics explainer */}
      <section className="section metrics-section">
        <div className="section-inner">
          <h2 className="section-title">6 Fairness Metrics Computed</h2>
          <div className="metrics-grid">
            {[
              { name: 'Statistical Parity Difference', desc: 'Are positive outcomes equally distributed across groups?', ideal: '= 0' },
              { name: 'Disparate Impact Ratio', desc: 'How many times more likely is the privileged group to get a positive outcome?', ideal: '≥ 0.8' },
              { name: 'Equalized Odds (TPR)', desc: 'Is the true positive rate equal across groups?', ideal: '= 0' },
              { name: 'Equalized Odds (FPR)', desc: 'Are false positive rates equal across groups?', ideal: '= 0' },
              { name: 'Predictive Parity', desc: 'Is the precision (PPV) equal across groups?', ideal: '= 0' },
              { name: 'Accuracy Difference', desc: 'Is the model equally accurate for all groups?', ideal: '= 0' },
            ].map(m => (
              <div className="metric-card" key={m.name}>
                <div className="metric-name">{m.name}</div>
                <div className="metric-desc">{m.desc}</div>
                <div className="metric-ideal">Ideal: <strong>{m.ideal}</strong></div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="cta-section">
        <h2>Ready to audit your AI?</h2>
        <p>Upload your dataset and get a full bias report in under 30 seconds.</p>
        <button className="btn-primary large" onClick={() => goTo('analyze')}>
          Launch Audit Tool →
        </button>
      </section>
    </div>
  );
}
