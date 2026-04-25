"""
FairLens – Bias Detection Engine
Computes fairness metrics on any binary-classification dataset.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix
from typing import Optional
import warnings
warnings.filterwarnings("ignore")


# ── Fairness metric helpers ──────────────────────────────────────────────────

def _rates(y_true, y_pred):
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0   # recall / sensitivity
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    ppv = tp / (tp + fp) if (tp + fp) > 0 else 0.0   # precision
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
    return dict(tpr=tpr, fpr=fpr, ppv=ppv, fnr=fnr,
                tp=int(tp), fp=int(fp), tn=int(tn), fn=int(fn))


def compute_bias_metrics(
    df: pd.DataFrame,
    label_col: str,
    protected_col: str,
    privileged_value,
    unprivileged_value,
    positive_label=1,
) -> dict:
    """
    Compute standard group-fairness metrics between privileged and
    unprivileged groups.

    Returns a dict with all metrics + bias flags + severity scores.
    """
    priv_mask   = df[protected_col] == privileged_value
    unpriv_mask = df[protected_col] == unprivileged_value

    priv_df   = df[priv_mask]
    unpriv_df = df[unpriv_mask]

    if len(priv_df) == 0 or len(unpriv_df) == 0:
        return {"error": "Not enough data in one group"}

    # ── Demographic parity (Statistical parity difference) ──────────────
    priv_pos_rate   = (priv_df[label_col]   == positive_label).mean()
    unpriv_pos_rate = (unpriv_df[label_col] == positive_label).mean()
    spd = float(unpriv_pos_rate - priv_pos_rate)          # negative = unfair to unpriv
    disparate_impact = (
        float(unpriv_pos_rate / priv_pos_rate)
        if priv_pos_rate > 0 else None
    )

    # ── Build a quick model to get predictions ───────────────────────────
    feature_cols = [c for c in df.columns if c != label_col]
    X = df[feature_cols].copy()
    y = (df[label_col] == positive_label).astype(int)

    # Encode categoricals
    enc_map = {}
    for col in X.select_dtypes(include=["object", "category"]).columns:
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col].astype(str))
        enc_map[col] = le

    X = X.fillna(X.median(numeric_only=True))

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s  = scaler.transform(X_test)

    model = LogisticRegression(max_iter=1000, random_state=42)
    model.fit(X_train_s, y_train)
    y_pred_all = model.predict(scaler.transform(X))

    overall_acc = accuracy_score(y, y_pred_all)

    # ── Per-group prediction rates & error rates ─────────────────────────
    priv_idx   = df.index[priv_mask]
    unpriv_idx = df.index[unpriv_mask]

    y_true_priv   = y.loc[priv_idx]
    y_pred_priv   = pd.Series(y_pred_all, index=df.index).loc[priv_idx]
    y_true_unpriv = y.loc[unpriv_idx]
    y_pred_unpriv = pd.Series(y_pred_all, index=df.index).loc[unpriv_idx]

    rates_priv   = _rates(y_true_priv,   y_pred_priv)
    rates_unpriv = _rates(y_true_unpriv, y_pred_unpriv)

    acc_priv   = accuracy_score(y_true_priv,   y_pred_priv)
    acc_unpriv = accuracy_score(y_true_unpriv, y_pred_unpriv)

    # ── Equalized odds difference ─────────────────────────────────────────
    eod_tpr = float(rates_unpriv["tpr"] - rates_priv["tpr"])
    eod_fpr = float(rates_unpriv["fpr"] - rates_priv["fpr"])

    # ── Predictive parity difference ─────────────────────────────────────
    ppd = float(rates_unpriv["ppv"] - rates_priv["ppv"])

    # ── Feature importance & proxy detection ─────────────────────────────
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X, y)
    importances = dict(zip(feature_cols, rf.feature_importances_))

    # Protected col importance
    prot_col_encoded = protected_col  # already in feature_cols if present
    prot_importance = importances.get(prot_col_encoded, 0.0)

    # Proxy detection: correlation with protected column
    proxy_scores = {}
    prot_numeric = X[protected_col] if protected_col in X.columns else None
    if prot_numeric is not None:
        for col in feature_cols:
            if col == protected_col:
                continue
            try:
                corr = abs(np.corrcoef(X[col].values, prot_numeric.values)[0, 1])
                if not np.isnan(corr) and corr > 0.2:
                    proxy_scores[col] = round(float(corr), 3)
            except Exception:
                pass
    proxy_scores = dict(sorted(proxy_scores.items(), key=lambda x: -x[1])[:5])

    # ── Severity scoring ─────────────────────────────────────────────────
    def severity(val, thresholds):
        """thresholds: (low, medium, high) absolute value boundaries"""
        av = abs(val)
        if av <= thresholds[0]:   return "none",   0
        elif av <= thresholds[1]: return "low",    1
        elif av <= thresholds[2]: return "medium", 2
        else:                     return "high",   3

    spd_sev,  spd_score  = severity(spd,     (0.05, 0.10, 0.20))
    eod_sev,  eod_score  = severity(eod_tpr, (0.05, 0.10, 0.20))
    fpr_sev,  fpr_score  = severity(eod_fpr, (0.05, 0.10, 0.20))
    ppd_sev,  ppd_score  = severity(ppd,     (0.05, 0.10, 0.20))
    acc_diff = acc_priv - acc_unpriv
    acc_sev,  acc_score  = severity(acc_diff,(0.02, 0.05, 0.10))

    di_sev = "none"
    di_score = 0
    if disparate_impact is not None:
        if disparate_impact < 0.6:   di_sev, di_score = "high",   3
        elif disparate_impact < 0.7: di_sev, di_score = "medium", 2
        elif disparate_impact < 0.8: di_sev, di_score = "low",    1

    total_score = spd_score + eod_score + fpr_score + ppd_score + acc_score + di_score
    max_score   = 18
    bias_pct    = round(total_score / max_score * 100, 1)

    if bias_pct == 0:     overall_sev = "none"
    elif bias_pct <= 25:  overall_sev = "low"
    elif bias_pct <= 55:  overall_sev = "medium"
    else:                 overall_sev = "high"

    # ── Group statistics ──────────────────────────────────────────────────
    group_stats = {
        str(privileged_value): {
            "count": int(len(priv_df)),
            "positive_rate": round(float(priv_pos_rate), 4),
            "model_accuracy": round(float(acc_priv), 4),
            "true_positive_rate": round(float(rates_priv["tpr"]), 4),
            "false_positive_rate": round(float(rates_priv["fpr"]), 4),
            "precision": round(float(rates_priv["ppv"]), 4),
        },
        str(unprivileged_value): {
            "count": int(len(unpriv_df)),
            "positive_rate": round(float(unpriv_pos_rate), 4),
            "model_accuracy": round(float(acc_unpriv), 4),
            "true_positive_rate": round(float(rates_unpriv["tpr"]), 4),
            "false_positive_rate": round(float(rates_unpriv["fpr"]), 4),
            "precision": round(float(rates_unpriv["ppv"]), 4),
        },
    }

    return {
        "overall": {
            "bias_score": bias_pct,
            "severity": overall_sev,
            "model_accuracy": round(float(overall_acc), 4),
            "total_rows": len(df),
            "protected_attribute": protected_col,
            "privileged_group": str(privileged_value),
            "unprivileged_group": str(unprivileged_value),
        },
        "metrics": {
            "statistical_parity_difference": {
                "value": round(spd, 4),
                "severity": spd_sev,
                "description": "Difference in positive outcome rates between groups",
                "ideal": 0.0,
                "threshold": 0.1,
            },
            "disparate_impact": {
                "value": round(disparate_impact, 4) if disparate_impact else None,
                "severity": di_sev,
                "description": "Ratio of positive outcome rates (unprivileged / privileged)",
                "ideal": 1.0,
                "threshold": 0.8,
            },
            "equalized_odds_difference_tpr": {
                "value": round(eod_tpr, 4),
                "severity": eod_sev,
                "description": "Difference in True Positive Rate (recall) between groups",
                "ideal": 0.0,
                "threshold": 0.1,
            },
            "equalized_odds_difference_fpr": {
                "value": round(eod_fpr, 4),
                "severity": fpr_sev,
                "description": "Difference in False Positive Rate between groups",
                "ideal": 0.0,
                "threshold": 0.1,
            },
            "predictive_parity_difference": {
                "value": round(ppd, 4),
                "severity": ppd_sev,
                "description": "Difference in Precision (PPV) between groups",
                "ideal": 0.0,
                "threshold": 0.1,
            },
            "accuracy_difference": {
                "value": round(float(acc_diff), 4),
                "severity": acc_sev,
                "description": "Difference in model accuracy between groups",
                "ideal": 0.0,
                "threshold": 0.05,
            },
        },
        "group_stats": group_stats,
        "feature_importance": {
            k: round(float(v), 4)
            for k, v in sorted(importances.items(), key=lambda x: -x[1])[:10]
        },
        "proxy_features": proxy_scores,
        "protected_feature_importance": round(float(prot_importance), 4),
    }


def get_fix_recommendations(metrics_result: dict) -> list:
    """Generate actionable fix recommendations based on bias findings."""
    recs = []
    m = metrics_result.get("metrics", {})
    proxies = metrics_result.get("proxy_features", {})
    overall = metrics_result.get("overall", {})

    spd_val = m.get("statistical_parity_difference", {}).get("value", 0)
    spd_sev = m.get("statistical_parity_difference", {}).get("severity", "none")
    di_val  = m.get("disparate_impact",              {}).get("value", 1)
    di_sev  = m.get("disparate_impact",              {}).get("severity", "none")
    eod_sev = m.get("equalized_odds_difference_tpr", {}).get("severity", "none")
    fpr_sev = m.get("equalized_odds_difference_fpr", {}).get("severity", "none")
    acc_sev = m.get("accuracy_difference",           {}).get("severity", "none")
    prot    = overall.get("protected_attribute", "protected attribute")
    unpriv  = overall.get("unprivileged_group", "unprivileged group")

    if spd_sev in ("medium", "high") or di_sev in ("medium", "high"):
        recs.append({
            "id": "reweighting",
            "title": "Apply Reweighting to Training Data",
            "priority": "high",
            "effort": "low",
            "impact": "high",
            "description": (
                f"The '{unpriv}' group receives positive outcomes at a significantly "
                f"lower rate (SPD = {spd_val:.3f}). Reweighting assigns higher importance "
                "to underrepresented positive cases during training, balancing the model's "
                "learning without modifying the original data."
            ),
            "code": (
                "from aif360.algorithms.preprocessing import Reweighing\n"
                "from aif360.datasets import BinaryLabelDataset\n\n"
                "rw = Reweighing(\n"
                f"    unprivileged_groups=[{{'{prot}': {unpriv!r}}}],\n"
                f"    privileged_groups=[{{'{prot}': {overall.get('privileged_group', '')}}}]\n"
                ")\n"
                "dataset_transf = rw.fit_transform(dataset)"
            ),
        })

    if proxies:
        top_proxy = list(proxies.items())[0]
        recs.append({
            "id": "proxy_removal",
            "title": f"Remove or Transform Proxy Features",
            "priority": "high",
            "effort": "medium",
            "impact": "high",
            "description": (
                f"Feature '{top_proxy[0]}' has a high correlation ({top_proxy[1]:.2f}) "
                f"with '{prot}'. Even without using '{prot}' directly, the model learns "
                "its effect through proxy features. Remove or transform these to prevent "
                "indirect discrimination."
            ),
            "code": (
                f"# Remove proxy features\n"
                f"proxy_features = {list(proxies.keys())}\n"
                f"df_clean = df.drop(columns=proxy_features)\n\n"
                f"# Or apply dimensionality reduction\n"
                f"from sklearn.decomposition import PCA\n"
                f"pca = PCA(n_components=0.95)  # keep 95% variance\n"
                f"X_reduced = pca.fit_transform(df_clean)"
            ),
        })

    if eod_sev in ("medium", "high") or fpr_sev in ("medium", "high"):
        recs.append({
            "id": "threshold_opt",
            "title": "Optimize Decision Thresholds Per Group",
            "priority": "medium",
            "effort": "low",
            "impact": "high",
            "description": (
                "Different classification thresholds for each group can equalize error "
                "rates. This post-processing technique doesn't require retraining — "
                "it adjusts the decision boundary after the model is built."
            ),
            "code": (
                "from aif360.algorithms.postprocessing import EqOddsPostprocessing\n\n"
                "eq_odds = EqOddsPostprocessing(\n"
                f"    unprivileged_groups=[{{'{prot}': {unpriv!r}}}],\n"
                f"    privileged_groups=[{{'{prot}': {overall.get('privileged_group', '')}}}]\n"
                ")\n"
                "dataset_pred_transf = eq_odds.fit_predict(\n"
                "    dataset_orig_test, dataset_pred\n"
                ")"
            ),
        })

    if acc_sev in ("medium", "high"):
        recs.append({
            "id": "oversampling",
            "title": "Oversample Underrepresented Group",
            "priority": "medium",
            "effort": "medium",
            "impact": "medium",
            "description": (
                f"The model performs significantly worse for the '{unpriv}' group. "
                "This is often due to insufficient representation in training data. "
                "Synthetic oversampling (SMOTE) generates new examples for the minority "
                "group to improve model fairness."
            ),
            "code": (
                "from imblearn.over_sampling import SMOTE\n\n"
                "smote = SMOTE(random_state=42)\n"
                f"# Filter to unprivileged group first\n"
                f"X_resampled, y_resampled = smote.fit_resample(X_train, y_train)"
            ),
        })

    recs.append({
        "id": "audit_schedule",
        "title": "Implement Continuous Bias Monitoring",
        "priority": "medium",
        "effort": "medium",
        "impact": "high",
        "description": (
            "Bias can increase over time as data distributions shift. Set up automated "
            "fairness metric computation every time the model is retrained or new data "
            "is collected. Alert stakeholders if any metric exceeds defined thresholds."
        ),
        "code": (
            "# Run FairLens audit on every model update\n"
            "from fairlens_engine import compute_bias_metrics\n\n"
            "def audit_on_retrain(df, label_col, protected_col):\n"
            "    result = compute_bias_metrics(df, label_col, protected_col, ...)\n"
            "    if result['overall']['bias_score'] > 30:\n"
            "        alert_team('Bias threshold exceeded!')\n"
            "    return result"
        ),
    })

    return recs
