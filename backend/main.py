"""
FairLens – FastAPI Backend (v2 — all 5 WOW features)
"""
import os

# Load .env file for GEMINI_API_KEY etc.
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
except ImportError:
    _env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(_env_path):
        with open(_env_path) as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith('#') and '=' in _line:
                    _k, _v = _line.split('=', 1)
                    os.environ.setdefault(_k.strip(), _v.strip())

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, List
import pandas as pd
import numpy as np
import io

from bias_engine    import compute_bias_metrics, get_fix_recommendations
from datasets       import DATASETS
from report_gen     import generate_report
from time_machine   import compute_time_machine
from whatif_engine  import run_whatif
from case_explainer import explain_case, get_sample_rows
from gemini_chat    import chat_with_gemini
from certificate    import generate_certificate
from bias_autopsy   import run_bias_autopsy

app = FastAPI(title="FairLens API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_session: dict = {}


def _read_upload(file: UploadFile) -> pd.DataFrame:
    content = file.file.read()
    name = (file.filename or "").lower()
    if name.endswith(".csv"):             return pd.read_csv(io.BytesIO(content))
    elif name.endswith((".xlsx",".xls")): return pd.read_excel(io.BytesIO(content))
    elif name.endswith(".json"):          return pd.read_json(io.BytesIO(content))
    return pd.read_csv(io.BytesIO(content))

def _df_preview(df):
    p = df.head(5).replace({np.nan: None})
    return {
        "columns": list(df.columns),
        "dtypes":  {c: str(t) for c,t in df.dtypes.items()},
        "shape":   list(df.shape),
        "preview": p.to_dict(orient="records"),
        "unique_counts": {c: int(df[c].nunique()) for c in df.columns},
        "null_counts":   {c: int(df[c].isna().sum()) for c in df.columns},
        "numeric_cols":  list(df.select_dtypes(include="number").columns),
        "categorical_cols": list(df.select_dtypes(exclude="number").columns),
    }

def _get_df():
    if "df" not in _session:
        raise HTTPException(400, "No dataset loaded. Run /analyze first.")
    return _session["df"]

def _coerce(df, col, val_str):
    for v in df[col].dropna().unique():
        if str(v).strip() == val_str.strip(): return v
    # Try case-insensitive match as fallback
    for v in df[col].dropna().unique():
        if str(v).strip().lower() == val_str.strip().lower(): return v
    return val_str


# ── Core endpoints ────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "FairLens API v2", "features": [
        "bias_analysis","time_machine","whatif","case_explainer","chat","certificate"]}

@app.get("/health")
def health(): return {"status": "ok"}

@app.get("/datasets")
def list_datasets():
    out = []
    for key, loader in DATASETS.items():
        try:
            _, meta = loader()
            out.append({"id": key, **meta})
        except Exception as e:
            out.append({"id": key, "error": str(e)})
    return out

@app.get("/datasets/{dataset_id}")
def load_dataset(dataset_id: str):
    if dataset_id not in DATASETS:
        raise HTTPException(404, f"Dataset '{dataset_id}' not found")
    df, meta = DATASETS[dataset_id]()
    return {"meta": meta, "preview": _df_preview(df)}

@app.get("/datasets/{dataset_id}/unique-values/{column}")
def get_dataset_unique_values(dataset_id: str, column: str):
    if dataset_id not in DATASETS:
        raise HTTPException(404, f"Dataset '{dataset_id}' not found")
    df, _ = DATASETS[dataset_id]()
    if column not in df.columns:
        raise HTTPException(400, f"Column '{column}' not found")
    unique_vals = [str(v) for v in df[column].dropna().unique().tolist()]
    return {"column": column, "values": unique_vals}

@app.post("/upload")
async def upload_dataset(file: UploadFile = File(...)):
    try: df = _read_upload(file)
    except Exception as e: raise HTTPException(400, f"Parse error: {e}")
    if len(df) < 50: raise HTTPException(400, "Need at least 50 rows")
    _session["uploaded_df"] = df
    return {"filename": file.filename, **_df_preview(df)}

@app.get("/upload/unique-values/{column}")
def get_upload_unique_values(column: str):
    if "uploaded_df" not in _session:
        raise HTTPException(400, "No uploaded dataset found")
    df = _session["uploaded_df"]
    if column not in df.columns:
        raise HTTPException(400, f"Column '{column}' not found")
    unique_vals = df[column].dropna().unique().tolist()
    return {"column": column, "values": unique_vals}

@app.post("/analyze-upload")
async def analyze_uploaded_file(
    label_col: str = Form(...),
    protected_col: str = Form(...),
    privileged_value: str = Form(...),
    unprivileged_value: str = Form(...),
    positive_label: Optional[str] = Form(default=None)
):
    if "uploaded_df" not in _session:
        raise HTTPException(400, "No uploaded dataset found")
    df = _session["uploaded_df"]
    
    # Create request object for reuse
    req = AnalyzeRequest(
        dataset_id=None,
        label_col=label_col,
        protected_col=protected_col,
        privileged_value=privileged_value,
        unprivileged_value=unprivileged_value,
        positive_label=positive_label
    )
    
    # Continue with the rest of the analysis logic
    if req.label_col     not in df.columns: raise HTTPException(400, f"Column '{req.label_col}' not found")
    if req.protected_col not in df.columns: raise HTTPException(400, f"Column '{req.protected_col}' not found")

    priv_val   = _coerce(df, req.protected_col, req.privileged_value)
    unpriv_val = _coerce(df, req.protected_col, req.unprivileged_value)
    
    # Validate that coerced values exist in the dataset
    if priv_val not in df[req.protected_col].values:
        raise HTTPException(400, f"Privileged value '{req.privileged_value}' not found in column '{req.protected_col}'. Available values: {list(df[req.protected_col].unique())}")
    if unpriv_val not in df[req.protected_col].values:
        raise HTTPException(400, f"Unprivileged value '{req.unprivileged_value}' not found in column '{req.protected_col}'. Available values: {list(df[req.protected_col].unique())}")
    
    label_vals = df[req.label_col].dropna().unique()
    pos_label  = req.positive_label
    if pos_label is not None:
        for v in label_vals:
            if str(v) == pos_label: pos_label = v; break
    else:
        pos_label = sorted(label_vals)[-1]

    try:
        result = compute_bias_metrics(df=df, label_col=req.label_col,
            protected_col=req.protected_col, privileged_value=priv_val,
            unprivileged_value=unpriv_val, positive_label=pos_label)
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {e}")
    if "error" in result: raise HTTPException(400, result["error"])

    recs = get_fix_recommendations(result)
    _session.update({"df": df, "label_col": req.label_col,
        "protected_col": req.protected_col, "privileged_value": priv_val,
        "unprivileged_value": unpriv_val, "positive_label": pos_label,
        "dataset_name": "Custom Dataset",
        "metrics_result": result, "recommendations": recs})

    return {"analysis": result, "recommendations": recs,
            "dataset_info": {"rows": len(df), "columns": list(df.columns),
                             "label_col": req.label_col, "protected_col": req.protected_col}}


class AnalyzeRequest(BaseModel):
    dataset_id:         Optional[str] = None
    label_col:          str
    protected_col:      str
    privileged_value:   str
    unprivileged_value: str
    positive_label:     Optional[str] = None

@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    if req.dataset_id:
        if req.dataset_id not in DATASETS: raise HTTPException(404, "Dataset not found")
        df, _ = DATASETS[req.dataset_id]()
    elif "uploaded_df" in _session:
        df = _session["uploaded_df"]
    else:
        raise HTTPException(400, "No dataset provided")

    if req.label_col     not in df.columns: raise HTTPException(400, f"Column '{req.label_col}' not found")
    if req.protected_col not in df.columns: raise HTTPException(400, f"Column '{req.protected_col}' not found")

    priv_val   = _coerce(df, req.protected_col, req.privileged_value)
    unpriv_val = _coerce(df, req.protected_col, req.unprivileged_value)
    
    # Validate that coerced values exist in the dataset
    if priv_val not in df[req.protected_col].values:
        raise HTTPException(400, f"Privileged value '{req.privileged_value}' not found in column '{req.protected_col}'. Available values: {list(df[req.protected_col].unique())}")
    if unpriv_val not in df[req.protected_col].values:
        raise HTTPException(400, f"Unprivileged value '{req.unprivileged_value}' not found in column '{req.protected_col}'. Available values: {list(df[req.protected_col].unique())}")
    
    label_vals = df[req.label_col].dropna().unique()
    pos_label  = req.positive_label
    if pos_label is not None:
        for v in label_vals:
            if str(v) == pos_label: pos_label = v; break
    else:
        pos_label = sorted(label_vals)[-1]

    try:
        result = compute_bias_metrics(df=df, label_col=req.label_col,
            protected_col=req.protected_col, privileged_value=priv_val,
            unprivileged_value=unpriv_val, positive_label=pos_label)
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {e}")
    if "error" in result: raise HTTPException(400, result["error"])

    recs = get_fix_recommendations(result)
    _session.update({"df": df, "label_col": req.label_col,
        "protected_col": req.protected_col, "privileged_value": priv_val,
        "unprivileged_value": unpriv_val, "positive_label": pos_label,
        "dataset_name": req.dataset_id or "Custom Dataset",
        "metrics_result": result, "recommendations": recs})

    return {"analysis": result, "recommendations": recs,
            "dataset_info": {"rows": len(df), "columns": list(df.columns),
                             "label_col": req.label_col, "protected_col": req.protected_col}}

@app.get("/report")
def download_report():
    for k in ["metrics_result","recommendations"]:
        if k not in _session: raise HTTPException(400, "Run /analyze first")
    try:
        pdf = generate_report(_session["dataset_name"], _session["protected_col"],
            str(_session.get("privileged_value","")), str(_session.get("unprivileged_value","")),
            _session["metrics_result"], _session["recommendations"])
    except Exception as e: raise HTTPException(500, str(e))
    return Response(content=pdf, media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="fairlens_report.pdf"'})


# ── Feature 1: Time Machine ───────────────────────────────────────────────────

@app.get("/time-machine")
def time_machine():
    df = _get_df()
    try:
        timeline = compute_time_machine(df=df, label_col=_session["label_col"],
            protected_col=_session["protected_col"],
            privileged_value=_session["privileged_value"],
            unprivileged_value=_session["unprivileged_value"],
            positive_label=_session["positive_label"])
    except Exception as e: raise HTTPException(500, str(e))
    return {"timeline": timeline,
            "protected_col": _session["protected_col"],
            "privileged_group": str(_session["privileged_value"]),
            "unprivileged_group": str(_session["unprivileged_value"])}


# ── Feature 2: What-If Simulator ─────────────────────────────────────────────

class WhatIfRequest(BaseModel):
    remove_features:    Optional[List[str]] = None
    oversample_factor:  Optional[float] = 1.0
    decision_threshold: Optional[float] = 0.5
    reweight:           Optional[bool]  = False
    threshold_priv:     Optional[float] = None
    threshold_unpriv:   Optional[float] = None

@app.post("/whatif")
def what_if(req: WhatIfRequest):
    df = _get_df()
    try:
        result = run_whatif(df=df, label_col=_session["label_col"],
            protected_col=_session["protected_col"],
            privileged_value=_session["privileged_value"],
            unprivileged_value=_session["unprivileged_value"],
            positive_label=_session["positive_label"],
            remove_features=req.remove_features,
            oversample_factor=req.oversample_factor or 1.0,
            decision_threshold=req.decision_threshold or 0.5,
            reweight=req.reweight or False,
            threshold_priv=req.threshold_priv,
            threshold_unpriv=req.threshold_unpriv)
    except Exception as e: raise HTTPException(500, str(e))
    if "error" in result: raise HTTPException(400, result["error"])
    orig = _session["metrics_result"]["overall"].get("bias_score", 0)
    result["original_bias_score"] = orig
    result["improvement"] = round(orig - result.get("bias_score", 0), 1)
    return result


# ── Feature 3: Case Explainer ─────────────────────────────────────────────────

@app.get("/cases")
def list_cases():
    df = _get_df()
    rows = get_sample_rows(df=df, label_col=_session["label_col"],
        protected_col=_session["protected_col"],
        privileged_value=_session["privileged_value"],
        unprivileged_value=_session["unprivileged_value"], n=24)
    return {"cases": rows, "total": len(df)}

@app.get("/cases/{row_index}")
def explain_row(row_index: int):
    df = _get_df()
    try:
        result = explain_case(df=df, label_col=_session["label_col"],
            protected_col=_session["protected_col"],
            privileged_value=_session["privileged_value"],
            unprivileged_value=_session["unprivileged_value"],
            positive_label=_session["positive_label"],
            row_index=row_index)
    except Exception as e: raise HTTPException(500, str(e))
    if "error" in result: raise HTTPException(400, result["error"])
    return result


# ── Feature 4: Gemini Chat ───────────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str
    history:  Optional[list] = None
    api_key:  Optional[str]  = None

@app.post("/chat")
def chat(req: ChatRequest):
    if "metrics_result" not in _session: raise HTTPException(400, "Run /analyze first")
    audit_ctx = {**_session["metrics_result"],
                 "dataset_name": _session.get("dataset_name",""),
                 "recommendations": _session.get("recommendations",[])}
    api_key = req.api_key or os.environ.get("GEMINI_API_KEY","") or _session.get("gemini_api_key","")
    if req.api_key: _session["gemini_api_key"] = req.api_key
    try:
        resp = chat_with_gemini(req.question, audit_ctx, req.history, api_key)
    except Exception as e: raise HTTPException(500, str(e))
    return resp


# ── Feature 5: Certificate ───────────────────────────────────────────────────

class CertRequest(BaseModel):
    organization_name: Optional[str] = "Your Organization"

@app.post("/certificate")
def make_cert(req: CertRequest):
    for k in ["metrics_result","recommendations"]:
        if k not in _session: raise HTTPException(400, "Run /analyze first")
    try:
        html = generate_certificate(
            dataset_name=_session.get("dataset_name","Dataset"),
            protected_col=_session["protected_col"],
            privileged_group=str(_session.get("privileged_value","")),
            unprivileged_group=str(_session.get("unprivileged_value","")),
            metrics_result=_session["metrics_result"],
            recommendations=_session["recommendations"],
            organization_name=req.organization_name or "Your Organization")
    except Exception as e: raise HTTPException(500, str(e))
    return Response(content=html, media_type="text/html")

# ── Feature 6: Bias Autopsy ──────────────────────────────────────────────────

@app.get("/autopsy")
def bias_autopsy():
    """Run full root-cause investigation on the loaded dataset."""
    df = _get_df()
    if "metrics_result" not in _session:
        raise HTTPException(400, "Run /analyze first")
    bias_score = _session["metrics_result"]["overall"].get("bias_score", 0)
    try:
        report = run_bias_autopsy(
            df=df,
            label_col=_session["label_col"],
            protected_col=_session["protected_col"],
            privileged_value=_session["privileged_value"],
            unprivileged_value=_session["unprivileged_value"],
            positive_label=_session["positive_label"],
            overall_bias_score=bias_score,
        )
    except Exception as e:
        raise HTTPException(500, f"Autopsy failed: {e}")
    return report


@app.get("/certificate/download")
def dl_cert(org: str = "Your Organization"):
    for k in ["metrics_result","recommendations"]:
        if k not in _session: raise HTTPException(400, "Run /analyze first")
    try:
        html = generate_certificate(
            dataset_name=_session.get("dataset_name","Dataset"),
            protected_col=_session["protected_col"],
            privileged_group=str(_session.get("privileged_value","")),
            unprivileged_group=str(_session.get("unprivileged_value","")),
            metrics_result=_session["metrics_result"],
            recommendations=_session["recommendations"],
            organization_name=org)
    except Exception as e: raise HTTPException(500, str(e))
    return Response(content=html, media_type="text/html",
        headers={"Content-Disposition": 'attachment; filename="fairlens_certificate.html"'})
