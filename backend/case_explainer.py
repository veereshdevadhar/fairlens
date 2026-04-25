"""
FairLens – Individual Case Explainer
Shows why a specific person was approved/rejected, which features
contributed how much, and whether a person from the other group
with identical qualifications would have gotten a different outcome.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings("ignore")


def explain_case(
    df: pd.DataFrame,
    label_col: str,
    protected_col: str,
    privileged_value,
    unprivileged_value,
    positive_label,
    row_index: int,
) -> dict:
    """
    Explain the model's decision for a specific row.
    Returns feature contributions, counterfactual, and fairness impact.
    """
    if row_index < 0 or row_index >= len(df):
        return {"error": f"Row index {row_index} out of range (0–{len(df)-1})"}

    feat_cols = [c for c in df.columns if c != label_col]
    X_raw = df[feat_cols].copy()
    y     = (df[label_col] == positive_label).astype(int)

    # Encode
    encoders = {}
    for col in X_raw.select_dtypes(include=["object","category"]).columns:
        le = LabelEncoder()
        X_raw[col] = le.fit_transform(X_raw[col].astype(str))
        encoders[col] = le
    X_raw = X_raw.fillna(X_raw.median(numeric_only=True))

    X_tr, X_te, y_tr, y_te = train_test_split(
        X_raw, y, test_size=0.3, random_state=42, stratify=y)

    sc = StandardScaler()
    X_tr_s = sc.fit_transform(X_tr)
    model  = LogisticRegression(max_iter=600, random_state=42)
    model.fit(X_tr_s, y_tr)

    # Get prediction for target row
    x_row     = X_raw.iloc[row_index:row_index+1]
    x_row_s   = sc.transform(x_row)
    proba     = model.predict_proba(x_row_s)[0]
    pred      = int(model.predict(x_row_s)[0])
    confidence = float(proba[1]) if pred == 1 else float(proba[0])

    # Actual label
    actual_label = int(df[label_col].iloc[row_index] == positive_label)
    correct = (pred == actual_label)

    # ── Feature contributions (LIME-style manual approximation) ──────────
    # Use logistic regression coefficients × standardized feature values
    coef = model.coef_[0]
    x_std = x_row_s[0]
    contributions_raw = coef * x_std

    # Map back to original feature names
    feature_names = feat_cols
    contributions = []
    for i, fname in enumerate(feature_names):
        orig_val = df[fname].iloc[row_index]
        contrib  = float(contributions_raw[i])
        contributions.append(dict(
            feature=fname,
            value=str(orig_val),
            contribution=round(contrib, 4),
            direction="positive" if contrib > 0 else "negative",
            magnitude=round(abs(contrib), 4),
        ))

    contributions.sort(key=lambda x: -x["magnitude"])
    top_contributions = contributions[:10]

    # ── Counterfactual: flip protected attribute ──────────────────────────
    group_val = df[protected_col].iloc[row_index]
    is_priv   = (group_val == privileged_value)

    x_counter = X_raw.iloc[row_index].copy()
    counter_group = unprivileged_value if is_priv else privileged_value

    if protected_col in feature_names:
        prot_idx = feature_names.index(protected_col)
        if protected_col in encoders:
            try:
                encoded_counter = encoders[protected_col].transform([str(counter_group)])[0]
                x_counter.iloc[prot_idx] = encoded_counter
            except Exception:
                pass

    x_counter_s = sc.transform(x_counter.values.reshape(1, -1))
    counter_proba   = model.predict_proba(x_counter_s)[0]
    counter_pred    = int(model.predict(x_counter_s)[0])
    counter_prob_pos = float(counter_proba[1])

    # Outcome change?
    outcome_changed = (counter_pred != pred)
    prob_diff       = round(float(proba[1]) - counter_prob_pos, 4)

    # ── Group context ─────────────────────────────────────────────────────
    priv_mask   = df[protected_col] == privileged_value
    unpriv_mask = df[protected_col] == unprivileged_value
    priv_pos_rate   = float((df.loc[priv_mask,   label_col] == positive_label).mean())
    unpriv_pos_rate = float((df.loc[unpriv_mask, label_col] == positive_label).mean())

    # Model's group-level approval rates
    x_all_s = sc.transform(X_raw)
    all_pred = model.predict(x_all_s)
    all_pred_s = pd.Series(all_pred, index=df.index)
    model_priv_rate   = float(all_pred_s[priv_mask].mean())
    model_unpriv_rate = float(all_pred_s[unpriv_mask].mean())

    # Row info
    row_data = {str(k): str(v) for k, v in df.iloc[row_index].items()}

    return dict(
        row_index=row_index,
        row_data=row_data,
        prediction=dict(
            predicted=pred,
            predicted_label="Approved / Positive" if pred == 1 else "Rejected / Negative",
            confidence=round(confidence, 4),
            probability_positive=round(float(proba[1]), 4),
            actual_label=actual_label,
            actual_label_text="Positive (Approved)" if actual_label == 1 else "Negative (Rejected)",
            correct=correct,
        ),
        group_context=dict(
            this_person_group=str(group_val),
            is_privileged=bool(is_priv),
            protected_attribute=protected_col,
            data_positive_rate_privileged=round(priv_pos_rate, 4),
            data_positive_rate_unprivileged=round(unpriv_pos_rate, 4),
            model_approval_rate_privileged=round(model_priv_rate, 4),
            model_approval_rate_unprivileged=round(model_unpriv_rate, 4),
        ),
        feature_contributions=top_contributions,
        counterfactual=dict(
            what_if="If this person belonged to the other group with everything else identical:",
            other_group=str(counter_group),
            other_pred=counter_pred,
            other_pred_label="Approved / Positive" if counter_pred == 1 else "Rejected / Negative",
            other_prob_positive=round(counter_prob_pos, 4),
            outcome_would_change=outcome_changed,
            probability_difference=prob_diff,
            fairness_impact=(
                "UNFAIR: Same person, different group → different outcome" if outcome_changed
                else "CONSISTENT: Same outcome regardless of group membership"
            ),
        ),
    )


def get_sample_rows(
    df: pd.DataFrame,
    label_col: str,
    protected_col: str,
    privileged_value,
    unprivileged_value,
    n: int = 20,
) -> list:
    """Return a sample of rows for the UI case browser."""
    indices = []
    for mask in [
        df[protected_col] == privileged_value,
        df[protected_col] == unprivileged_value,
    ]:
        sub = df[mask].head(n // 2)
        indices.extend(sub.index.tolist())

    rows = []
    for idx in indices[:n]:
        row = df.iloc[idx]
        rows.append(dict(
            index=int(idx),
            protected_value=str(row[protected_col]),
            label_value=str(row[label_col]),
            preview={str(k): str(v) for k, v in row.items()},
        ))
    return rows
