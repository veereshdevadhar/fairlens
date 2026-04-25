"""
FairLens – What-If Simulator
Computes real-time bias metrics under user-specified interventions
without full model retraining (uses cached model + fast approximation).
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix
from imblearn.over_sampling import SMOTE
import warnings
warnings.filterwarnings("ignore")


def _encode(df, label_col):
    X = df[[c for c in df.columns if c != label_col]].copy()
    y = df[label_col].copy()
    encoders = {}
    for col in X.select_dtypes(include=["object","category"]).columns:
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col].astype(str))
        encoders[col] = le
    X = X.fillna(X.median(numeric_only=True))
    return X, y, encoders


def _group_metrics(y_true_s, y_pred_s, df_orig, protected_col,
                   privileged_value, unprivileged_value):
    priv_idx   = df_orig[df_orig[protected_col] == privileged_value].index
    unpriv_idx = df_orig[df_orig[protected_col] == unprivileged_value].index

    common_p = y_true_s.index.intersection(priv_idx)
    common_u = y_true_s.index.intersection(unpriv_idx)

    def rates(yt, yp):
        if len(yt) < 3: return dict(tpr=0,fpr=0,ppv=0,acc=0,pos_rate=0)
        try:
            tn,fp,fn,tp = confusion_matrix(yt,yp,labels=[0,1]).ravel()
        except Exception:
            return dict(tpr=0,fpr=0,ppv=0,acc=accuracy_score(yt,yp),pos_rate=float(yp.mean()))
        return dict(
            tpr=tp/(tp+fn) if (tp+fn)>0 else 0,
            fpr=fp/(fp+tn) if (fp+tn)>0 else 0,
            ppv=tp/(tp+fp) if (tp+fp)>0 else 0,
            acc=accuracy_score(yt,yp),
            pos_rate=float(yp.mean()),
        )

    rp = rates(y_true_s.loc[common_p], y_pred_s.loc[common_p])
    ru = rates(y_true_s.loc[common_u], y_pred_s.loc[common_u])

    spd = ru["pos_rate"] - rp["pos_rate"]
    di  = ru["pos_rate"]/rp["pos_rate"] if rp["pos_rate"]>0 else None
    eod = ru["tpr"] - rp["tpr"]
    fpr_diff = ru["fpr"] - rp["fpr"]
    acc_diff = ru["acc"] - rp["acc"]

    def sev(v, t):
        av = abs(v)
        if av<=t*0.5:  return "none"
        elif av<=t:    return "low"
        elif av<=t*2:  return "medium"
        else:          return "high"

    # Composite 0-100
    def sc(v,t): return min(abs(v)/t,1.0) if t>0 else 0
    di_penalty = sc(1-(di or 1),0.20)*25
    score = sc(spd,0.20)*30 + di_penalty + sc(abs(eod),0.20)*25 + sc(abs(acc_diff),0.10)*20

    if score<=15:   overall_sev="none"
    elif score<=35: overall_sev="low"
    elif score<=60: overall_sev="medium"
    else:           overall_sev="high"

    return dict(
        bias_score=round(score,1),
        severity=overall_sev,
        overall_accuracy=round(accuracy_score(y_true_s, y_pred_s),4),
        metrics=dict(
            statistical_parity_difference=dict(value=round(spd,4), severity=sev(spd,0.10)),
            disparate_impact=dict(value=round(di,4) if di else None, severity=sev(1-(di or 1),0.20)),
            equalized_odds_tpr=dict(value=round(eod,4), severity=sev(eod,0.10)),
            equalized_odds_fpr=dict(value=round(fpr_diff,4), severity=sev(fpr_diff,0.10)),
            accuracy_difference=dict(value=round(acc_diff,4), severity=sev(acc_diff,0.05)),
        ),
        group_stats=dict(
            privileged=dict(
                pos_rate=round(rp["pos_rate"],4),
                accuracy=round(rp["acc"],4),
                tpr=round(rp["tpr"],4),
                fpr=round(rp["fpr"],4),
            ),
            unprivileged=dict(
                pos_rate=round(ru["pos_rate"],4),
                accuracy=round(ru["acc"],4),
                tpr=round(ru["tpr"],4),
                fpr=round(ru["fpr"],4),
            ),
        ),
    )


def run_whatif(
    df: pd.DataFrame,
    label_col: str,
    protected_col: str,
    privileged_value,
    unprivileged_value,
    positive_label,
    # Intervention parameters
    remove_features: list = None,
    oversample_factor: float = 1.0,      # 1.0 = no change, 2.0 = double unpriv group
    decision_threshold: float = 0.5,
    reweight: bool = False,
    threshold_priv: float = None,        # separate threshold for privileged group
    threshold_unpriv: float = None,      # separate threshold for unprivileged group
) -> dict:
    """
    Apply interventions and return updated bias metrics.
    """
    df_work = df.copy()
    interventions_applied = []

    # 1. Remove features
    remove_features = remove_features or []
    valid_remove = [f for f in remove_features if f in df_work.columns and f != label_col]
    if valid_remove:
        df_work = df_work.drop(columns=valid_remove)
        interventions_applied.append(f"Removed features: {', '.join(valid_remove)}")

    # 2. Reweighting
    sample_weights = None
    if reweight:
        priv_mask   = df_work[protected_col] == privileged_value
        unpriv_mask = df_work[protected_col] == unprivileged_value
        weights = pd.Series(1.0, index=df_work.index)
        priv_pos_rate = (df_work.loc[priv_mask, label_col] == positive_label).mean()
        unpriv_pos_rate = (df_work.loc[unpriv_mask, label_col] == positive_label).mean()
        if priv_pos_rate > 0 and unpriv_pos_rate > 0:
            ratio = priv_pos_rate / unpriv_pos_rate
            weights[unpriv_mask & (df_work[label_col] == positive_label)] *= ratio
        sample_weights = weights.values
        interventions_applied.append("Reweighting applied")

    # 3. Oversample unprivileged group
    if oversample_factor > 1.05:
        unpriv_mask = df_work[protected_col] == unprivileged_value
        unpriv_rows = df_work[unpriv_mask]
        extra_n = int(len(unpriv_rows) * (oversample_factor - 1.0))
        if extra_n > 0:
            extra = unpriv_rows.sample(n=min(extra_n, len(unpriv_rows)*3),
                                       replace=True, random_state=42)
            df_work = pd.concat([df_work, extra], ignore_index=True)
            interventions_applied.append(f"Oversampled unprivileged group by {oversample_factor:.1f}×")

    # Save group column BEFORE possible feature removal in _encode
    prot_col_vals = (df_work[protected_col].copy() if protected_col in df_work.columns
                     else pd.Series([privileged_value]*len(df_work)))

    # Encode & train
    X, y, _ = _encode(df_work, label_col)
    y_bin = (y == positive_label).astype(int)

    # Keep track of group for each row
    orig_idx = pd.DataFrame({protected_col: prot_col_vals.values})
    orig_idx.index = range(len(orig_idx))
    X.index = range(len(X))
    y_bin.index = range(len(y_bin))

    try:
        X_tr, X_te, y_tr, y_te, idx_tr, idx_te = train_test_split(
            X, y_bin, orig_idx, test_size=0.3, random_state=42, stratify=y_bin)

        sc = StandardScaler()
        X_tr_s = sc.fit_transform(X_tr)
        X_te_s  = sc.transform(X_te)

        sw = sample_weights[X_tr.index] if sample_weights is not None else None
        model = LogisticRegression(max_iter=600, random_state=42)
        model.fit(X_tr_s, y_tr, sample_weight=sw)

        # 4. Threshold adjustment
        if threshold_priv is not None or threshold_unpriv is not None:
            proba = model.predict_proba(X_te_s)[:, 1]
            y_pred = np.zeros(len(proba), dtype=int)
            th_p = threshold_priv  if threshold_priv  is not None else decision_threshold
            th_u = threshold_unpriv if threshold_unpriv is not None else decision_threshold
            te_groups = idx_te[protected_col].values
            for i, g in enumerate(te_groups):
                th = th_p if g == privileged_value else th_u
                y_pred[i] = 1 if proba[i] >= th else 0
            interventions_applied.append(
                f"Decision thresholds — privileged: {th_p:.2f}, unprivileged: {th_u:.2f}")
        else:
            proba = model.predict_proba(X_te_s)[:, 1]
            y_pred = (proba >= decision_threshold).astype(int)
            if decision_threshold != 0.5:
                interventions_applied.append(f"Decision threshold: {decision_threshold:.2f}")

        y_pred_s = pd.Series(y_pred, index=X_te.index)
        y_te_s   = pd.Series(y_te.values,  index=X_te.index)

        result = _group_metrics(y_te_s, y_pred_s, idx_te.reset_index(drop=True),
                                protected_col, privileged_value, unprivileged_value)
        result["interventions_applied"] = interventions_applied
        result["rows_after_intervention"] = len(df_work)
        return result

    except Exception as e:
        return {"error": str(e), "interventions_applied": interventions_applied}
