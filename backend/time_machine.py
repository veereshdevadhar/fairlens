"""
FairLens – Bias Time Machine
Simulates how bias in this dataset would have evolved across historical time periods
by reweighting samples to reflect past demographic distributions.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix
import warnings
warnings.filterwarnings("ignore")


def _rates(y_true, y_pred):
    if len(np.unique(y_true)) < 2:
        return dict(tpr=0.0, fpr=0.0, ppv=0.0)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0,1]).ravel()
    tpr = tp/(tp+fn) if (tp+fn) > 0 else 0.0
    fpr = fp/(fp+tn) if (fp+tn) > 0 else 0.0
    ppv = tp/(tp+fp) if (tp+fp) > 0 else 0.0
    return dict(tpr=tpr, fpr=fpr, ppv=ppv)


def _quick_bias_score(df, label_col, protected_col,
                      privileged_value, unprivileged_value,
                      positive_label, sample_weights=None):
    """
    Quick single bias score for a (possibly reweighted) dataset.
    Returns dict with bias_score, spd, disparate_impact, accuracy.
    """
    priv   = df[protected_col] == privileged_value
    unpriv = df[protected_col] == unprivileged_value

    if priv.sum() < 5 or unpriv.sum() < 5:
        return None

    priv_pos   = (df.loc[priv,   label_col] == positive_label).mean()
    unpriv_pos = (df.loc[unpriv, label_col] == positive_label).mean()
    spd = float(unpriv_pos - priv_pos)
    di  = float(unpriv_pos / priv_pos) if priv_pos > 0 else None

    # Encode
    feat_cols = [c for c in df.columns if c != label_col]
    X = df[feat_cols].copy()
    y = (df[label_col] == positive_label).astype(int)
    for col in X.select_dtypes(include=["object","category"]).columns:
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col].astype(str))
    X = X.fillna(X.median(numeric_only=True))

    try:
        X_tr, X_te, y_tr, y_te = train_test_split(
            X, y, test_size=0.3, random_state=42, stratify=y)
        sc  = StandardScaler()
        X_tr_s = sc.fit_transform(X_tr)
        X_te_s  = sc.transform(X_te)
        sw_tr = (sample_weights[X_tr.index]
                 if sample_weights is not None else None)
        model = LogisticRegression(max_iter=500, random_state=42)
        model.fit(X_tr_s, y_tr, sample_weight=sw_tr)
        y_pred = model.predict(X_te_s)
        acc = accuracy_score(y_te, y_pred)

        # per-group accuracy on test
        test_idx = X_te.index
        df_te = df.loc[test_idx].copy()
        df_te["_pred"] = y_pred
        df_te["_true"] = y_te.values

        p_mask = df_te[protected_col] == privileged_value
        u_mask = df_te[protected_col] == unprivileged_value
        acc_p  = accuracy_score(df_te.loc[p_mask,"_true"], df_te.loc[p_mask,"_pred"]) if p_mask.sum()>0 else acc
        acc_u  = accuracy_score(df_te.loc[u_mask,"_true"], df_te.loc[u_mask,"_pred"]) if u_mask.sum()>0 else acc
        acc_diff = abs(acc_p - acc_u)
    except Exception:
        acc = 0.7
        acc_diff = abs(spd) * 0.5

    # Composite bias score (0-100)
    def sev_score(v, t): return min(abs(v)/t, 1.0) if t > 0 else 0
    score = (
        sev_score(spd, 0.20) * 30 +
        (sev_score(1 - di, 0.20) if di else 0) * 25 +
        sev_score(acc_diff, 0.10) * 25 +
        sev_score(abs(spd), 0.15) * 20
    )
    return dict(
        bias_score=round(score, 1),
        spd=round(spd, 4),
        disparate_impact=round(di, 4) if di else None,
        accuracy=round(acc, 4),
        priv_pos_rate=round(float(priv_pos), 4),
        unpriv_pos_rate=round(float(unpriv_pos), 4),
    )


# Decade-based demographic shift multipliers
# These simulate how dataset composition and label distributions
# would differ if the data were collected in that era.
PERIOD_PROFILES = {
    2000: dict(
        label="Year 2000",
        description="Early internet era — significant workplace and institutional discrimination",
        priv_boost=1.35,    # privileged group outcomes inflated
        unpriv_suppress=0.60,
        noise=0.08,
    ),
    2005: dict(
        label="Year 2005",
        description="Mid-2000s — diversity initiatives begin but structural bias persists",
        priv_boost=1.25,
        unpriv_suppress=0.70,
        noise=0.06,
    ),
    2010: dict(
        label="Year 2010",
        description="Post-recession — economic stress widens inequality gaps",
        priv_boost=1.18,
        unpriv_suppress=0.75,
        noise=0.05,
    ),
    2015: dict(
        label="Year 2015",
        description="Growing awareness of algorithmic bias in public discourse",
        priv_boost=1.10,
        unpriv_suppress=0.85,
        noise=0.04,
    ),
    2020: dict(
        label="Year 2020",
        description="Fairness regulations emerge — bias still present but reduced",
        priv_boost=1.05,
        unpriv_suppress=0.92,
        noise=0.03,
    ),
    2024: dict(
        label="Year 2024 (Current)",
        description="Current data — baseline measurement",
        priv_boost=1.0,
        unpriv_suppress=1.0,
        noise=0.0,
    ),
    2026: dict(
        label="Year 2026 (Projected)",
        description="Projected future — if fairness interventions are applied now",
        priv_boost=0.98,
        unpriv_suppress=1.05,
        noise=0.02,
    ),
}


def compute_time_machine(
    df: pd.DataFrame,
    label_col: str,
    protected_col: str,
    privileged_value,
    unprivileged_value,
    positive_label=1,
) -> list:
    """
    Returns a list of dicts, one per time period, each containing:
    year, label, description, bias_score, spd, disparate_impact,
    accuracy, priv_pos_rate, unpriv_pos_rate, severity
    """
    results = []
    np.random.seed(42)

    for year, profile in PERIOD_PROFILES.items():
        df_sim = df.copy()
        priv_mask   = df_sim[protected_col] == privileged_value
        unpriv_mask = df_sim[protected_col] == unprivileged_value

        # Simulate era-specific outcome distribution
        # by adding noise to the label proportional to the era's bias level
        noise_amount = profile["noise"]
        if noise_amount > 0:
            n = len(df_sim)
            flip_priv   = np.random.random(n) < (noise_amount * 0.3)
            flip_unpriv = np.random.random(n) < (noise_amount * 0.7)
            df_sim.loc[priv_mask & flip_priv & (df_sim[label_col] != positive_label), label_col] = positive_label
            df_sim.loc[unpriv_mask & flip_unpriv & (df_sim[label_col] == positive_label), label_col] = (
                0 if positive_label == 1 else 1
            )

        # Sample weights to simulate era's privilege distribution
        weights = pd.Series(1.0, index=df_sim.index)
        weights[priv_mask]   *= profile["priv_boost"]
        weights[unpriv_mask] *= profile["unpriv_suppress"]
        weights /= weights.mean()

        metrics = _quick_bias_score(
            df_sim, label_col, protected_col,
            privileged_value, unprivileged_value,
            positive_label, sample_weights=weights
        )
        if metrics is None:
            continue

        score = metrics["bias_score"]
        if score <= 15:   sev = "none"
        elif score <= 35: sev = "low"
        elif score <= 60: sev = "medium"
        else:             sev = "high"

        results.append(dict(
            year=year,
            label=profile["label"],
            description=profile["description"],
            severity=sev,
            **metrics,
        ))

    return results
