# ⚖ FairLens — AI Bias Detection & Fairness Auditing Platform
### Google Solution Challenge 2026 · Build with AI · Theme: Unbiased AI Decision

FairLens detects, measures, explains and fixes AI bias — with 6 unique WOW features
that go far beyond any other bias tool.

---

## 📁 Project Structure

```
fairlens/
├── backend/
│   ├── main.py            ← FastAPI — all endpoints
│   ├── bias_engine.py     ← 6 fairness metrics engine
│   ├── datasets.py        ← Real datasets (Adult Census, COMPAS, German Credit)
│   ├── report_gen.py      ← PDF audit report
│   ├── time_machine.py    ← Feature 1: Bias Time Machine
│   ├── whatif_engine.py   ← Feature 2: What-If Simulator
│   ├── case_explainer.py  ← Feature 3: Individual Case Explainer
│   ├── gemini_chat.py     ← Feature 4: Gemini AI Chat
│   ├── certificate.py     ← Feature 5: Fairness Certificate
│   ├── bias_autopsy.py    ← Feature 6: Bias Autopsy
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.js
│   │   ├── pages/
│   │   │   ├── LandingPage.js/css
│   │   │   ├── AnalyzePage.js/css
│   │   │   ├── ResultsPage.js/css    ← Core dashboard
│   │   │   ├── TimeMachine.js        ← WOW Feature 1
│   │   │   ├── WhatIf.js             ← WOW Feature 2
│   │   │   ├── CaseExplainer.js      ← WOW Feature 3
│   │   │   ├── GeminiChat.js         ← WOW Feature 4
│   │   │   ├── Certificate.js        ← WOW Feature 5
│   │   │   ├── BiasAutopsy.js          ← WOW Feature 6
│   │   │   └── FeaturePage.css
│   │   └── utils/api.js
│   └── package.json
├── start_backend.sh
├── start_frontend.sh
└── README.md
```

---

## ⚡ Quick Start — 2 Terminals

### Prerequisites
| Tool    | Version | Install |
|---------|---------|---------|
| Python  | 3.9+    | https://python.org |
| Node.js | 16+     | https://nodejs.org |

---

### Terminal 1 — Backend

**Windows:**
```powershell
cd fairlens\backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Mac/Linux:**
```bash
cd fairlens/backend
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Or using startup scripts:**
```bash
# Mac/Linux
cd fairlens
chmod +x start_backend.sh
./start_backend.sh

# Windows (PowerShell)
cd fairlens\backend
python start_backend.py
```

Wait for: `Uvicorn running on http://0.0.0.0:8000`

---

### Terminal 2 — Frontend

**Windows:**
```powershell
cd fairlens\frontend
npm install
npm start
```

**Mac/Linux:**
```bash
cd fairlens/frontend
npm install
npm start
```

**Or using startup scripts:**
```bash
# Mac/Linux
cd fairlens
chmod +x start_frontend.sh
./start_frontend.sh

# Windows (PowerShell)
cd fairlens\frontend
npm start
```

Wait for: `Compiled successfully! Local: http://localhost:3000`

---

### Open the App
**http://localhost:3000**

---

## 🌟 The 6 WOW Features

### 1. ⏳ Bias Time Machine
See how this model's bias would have looked across different historical eras (2000→2026).
Animated line chart showing bias score evolution. Click any era for details.

### 2. 🧪 What-If Simulator
Apply fairness interventions (reweighting, feature removal, threshold adjustment,
oversampling) with sliders and toggles. Bias score updates instantly.
Compare before/after with radar charts.

### 3. 🔍 Individual Case Explainer
Select any person from the dataset. See:
- Why the AI approved or rejected them (feature contributions bar chart)
- **Counterfactual: what if they belonged to the other group?**  
  "Same person, different gender → different outcome" — the most powerful bias demo possible.

### 4. 💬 Ask AI About Your Audit (Gemini)
Context-aware AI assistant that has read your full audit results.
Ask questions in plain English. Works with or without Gemini API key.
**To enable full AI responses:** get a free key at https://aistudio.google.com

### 5. 🏆 Fairness Certificate
Generate a signed, timestamped, self-contained HTML certificate
with unique ID. Download and share — open in any browser, print as PDF,
attach to submissions or show to regulators.

### 6. 🧬 Bias Autopsy
Root-cause investigation engine with 4 deep analyses:
- **Historical Outcome Bias** - Was training data already unfair?
- **Proxy Chain Analysis** - Full feature→feature→protected→outcome chains
- **Intersectional Bias** - Bias in specific subgroups (e.g., "unprivileged + young")
- **Decision Boundary Audit** - Exact numeric tipping points per group

Identifies WHY bias exists and provides specific remediation paths.

---

## 🔑 Gemini API Key (optional)

Feature 4 (Ask AI) works out of the box with smart built-in responses.
For full Gemini AI responses:

1. Get a free API key: https://aistudio.google.com/app/apikey
2. Either:
   - Enter it in the app's chat interface (Key input field)
   - Or set environment variable before starting backend:
     ```bash
     # Mac/Linux
     export GEMINI_API_KEY="your-key-here"
     ./start_backend.sh
     
     # Windows (PowerShell)
     $env:GEMINI_API_KEY="your-key-here"
     python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
     ```

---

## 📊 Built-in Datasets

| Dataset | Source | Rows | Protected Attribute |
|---------|--------|------|---------------------|
| Adult Census Income | UCI / US Census 1994 | 5,000 | sex, race |
| COMPAS Recidivism | ProPublica 2016 | 4,000 | race |
| German Credit | UCI | 1,000 | sex, age |

All datasets are **real, publicly available** data used in published academic research.
Synthetic fallback activates automatically if URLs are unreachable.

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/datasets` | GET | List built-in datasets |
| `/datasets/{id}` | GET | Load dataset with preview |
| `/upload` | POST | Upload custom CSV/Excel/JSON |
| `/analyze` | POST | Run full bias analysis |
| `/report` | GET | Download PDF audit report |
| `/time-machine` | GET | **[WOW 1]** Historical bias timeline |
| `/whatif` | POST | **[WOW 2]** Intervention simulator |
| `/cases` | GET | **[WOW 3]** Sample rows for browser |
| `/cases/{idx}` | GET | **[WOW 3]** Explain one case |
| `/chat` | POST | **[WOW 4]** Gemini AI chat |
| `/certificate` | POST | **[WOW 5]** Generate HTML certificate |
| `/autopsy` | GET | **[WOW 6]** Root-cause bias investigation |
| `/docs` | GET | Interactive API docs (Swagger) |

---

## 🛠 Tech Stack

**Backend:** FastAPI · scikit-learn · AIF360 · pandas · numpy · ReportLab · Uvicorn  
**Frontend:** React 18 · Recharts · Google Fonts (Syne + DM Sans) · Axios  
**AI:** Google Gemini 1.5 Flash (with smart fallback)  
**Datasets:** Real UCI + ProPublica public data

---

## 🐛 Troubleshooting

**"Could not connect to backend"**
```bash
curl http://localhost:8000/
# Should return: {"message":"FairLens API v2 running",...}
```

**pip install fails**
```bash
# Mac/Linux
pip3 install -r requirements.txt --user

# Windows
pip install -r requirements.txt --user
```

**npm install fails**
```bash
npm cache clean --force && npm install
```

**Dataset loads slowly** — first load fetches from UCI/ProPublica URLs.
Subsequent runs use synthetic fallback instantly if URLs fail.

---


