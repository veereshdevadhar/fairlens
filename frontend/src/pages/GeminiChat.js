import React, { useState, useRef, useEffect } from 'react';
import api from '../utils/api';
import './FeaturePage.css';

const SUGGESTED = [
  'How bad is the bias in this dataset?',
  'Explain statistical parity difference in simple words',
  'What are proxy features and why are they dangerous?',
  'Write an email to my board explaining this bias problem',
  'Which fix should I implement first?',
  'Is this bias legally significant?',
  'Explain disparate impact ratio to me like I\'m a lawyer',
  'What would happen if we deployed this model as-is?',
];

function Message({ msg }) {
  const isUser = msg.role === 'user';
  return (
    <div className={`chat-msg ${isUser ? 'chat-user' : 'chat-ai'}`}>
      {!isUser && <div className="chat-ai-icon">⚖</div>}
      <div className={`chat-bubble ${isUser ? 'chat-bubble-user' : 'chat-bubble-ai'}`}>
        {msg.content.split('\n').map((line, i) => (
          <React.Fragment key={i}>
            {line}
            {i < msg.content.split('\n').length - 1 && <br />}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

export default function GeminiChat() {
  const [messages, setMessages] = useState([{
    role: 'ai',
    content: "Hi! I'm FairLens AI — I've just read your full bias audit results. Ask me anything about the findings, what they mean, how to fix them, or ask me to draft an explanation for your team."
  }]);
  const [input, setInput]     = useState('');
  const [loading, setLoading] = useState(false);
  const [apiKey, setApiKey]   = useState('');
  const [showKey, setShowKey] = useState(false);
  const [source, setSource]   = useState('');
  const bottomRef = useRef();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const send = async (text) => {
    const q = text || input.trim();
    if (!q || loading) return;
    setInput('');

    const userMsg = { role: 'user', content: q };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    // Build history for Gemini
    const history = messages.filter(m => m.role !== 'ai' || messages.indexOf(m) > 0)
      .slice(-6)
      .map(m => ({
        role: m.role === 'user' ? 'user' : 'model',
        parts: [{ text: m.content }]
      }));

    try {
      const r = await api.post('/chat', {
        question: q,
        history,
        api_key: apiKey || undefined,
      });
      setMessages(prev => [...prev, { role: 'ai', content: r.data.answer }]);
      setSource(r.data.source);
    } catch(e) {
      setMessages(prev => [...prev, {
        role: 'ai',
        content: 'Sorry, I had trouble answering that. Please try again.'
      }]);
    }
    setLoading(false);
  };

  return (
    <div className="fp-wrap">
      <div className="fp-header">
        <div className="fp-icon">💬</div>
        <div>
          <h2 className="fp-title">Ask AI About Your Audit</h2>
          <p className="fp-sub">
            FairLens AI has read your entire audit report. Ask it anything — from what a metric means 
            to drafting a report for your CEO.
            {source === 'fallback' && <span className="chat-fallback-note"> (Using built-in AI · Add Gemini API key for full AI)</span>}
          </p>
        </div>
      </div>

      {/* Gemini API key input */}
      <div className="chat-key-bar card-sm">
        <span style={{fontSize:12,color:'var(--text2)'}}>🔑 Gemini API Key (optional — enables full AI responses):</span>
        <div style={{display:'flex',gap:8,flex:1,marginLeft:12}}>
          <input type={showKey?'text':'password'} placeholder="AIza... (get free at aistudio.google.com)"
            value={apiKey} onChange={e=>setApiKey(e.target.value)}
            style={{flex:1,fontSize:12,padding:'6px 10px'}} />
          <button className="btn-ghost" style={{padding:'6px 10px',fontSize:12}}
            onClick={()=>setShowKey(s=>!s)}>{showKey?'Hide':'Show'}</button>
        </div>
      </div>

      {/* Suggested questions */}
      <div className="chat-suggestions">
        {SUGGESTED.map(s => (
          <button key={s} className="chat-chip" onClick={() => send(s)}>{s}</button>
        ))}
      </div>

      {/* Chat window */}
      <div className="chat-window card">
        {messages.map((m, i) => <Message key={i} msg={m} />)}
        {loading && (
          <div className="chat-msg chat-ai">
            <div className="chat-ai-icon">⚖</div>
            <div className="chat-bubble chat-bubble-ai chat-typing">
              <span/><span/><span/>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="chat-input-row">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
          placeholder="Ask anything about your bias audit…"
          disabled={loading}
        />
        <button className="btn-primary" onClick={() => send()} disabled={loading || !input.trim()}>
          {loading ? <span className="btn-spinner"/> : 'Send →'}
        </button>
      </div>
    </div>
  );
}
