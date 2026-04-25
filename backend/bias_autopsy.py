"""
FairLens – Bias Autopsy Engine
Automated root-cause investigation: WHY does this specific bias exist?

Four investigations:
  1. Historical Outcome Bias   – was the training data itself already unfair?
  2. Proxy Chain Analysis      – full feature→feature→protected→outcome chains
  3. Intersectional Bias       – bias that only appears at group intersections
  4. Decision Boundary Audit   – exact numeric tipping points per group
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from itertools import combinations
import warnings
warnings.filterwarnings("ignore")


# ── Shared helpers ────────────────────────────────────────────────────────────

def _encode_df(df, label_col):
    """Encode all categoricals, return X (encoded), y (binary series), encoders."""
    X = df[[c for c in df.columns if c != label_col]].copy()
    y = df[label_col].copy()
    encoders = {}
    for col in X.select_dtypes(include=["object", "category"]).columns:
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col].astype(str))
        encoders[col] = le
    X = X.fillna(X.median(numeric_only=True))
    return X, y, encoders


def _train_model(X, y_bin):
    """Train logistic regression, return (model, scaler, X_te, y_te, y_pred)."""
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y_bin, test_size=0.3, random_state=42, stratify=y_bin)
    sc = StandardScaler()
    model = LogisticRegression(max_iter=600, random_state=42)
    model.fit(sc.fit_transform(X_tr), y_tr)
    y_pred = model.predict(sc.transform(X_te))
    return model, sc, X_te, y_te, y_pred


def _corr(a, b):
    try:
        c = float(np.corrcoef(a.values, b.values)[0, 1])
        return 0.0 if np.isnan(c) else abs(c)
    except Exception:
        return 0.0


# ══════════════════════════════════════════════════════════════════════════════
# INVESTIGATION 1 – Historical Outcome Bias
# ══════════════════════════════════════════════════════════════════════════════

def _investigate_historical(df, label_col, protected_col,
                             privileged_value, unprivileged_value,
                             positive_label):
    """
    Tests whether the raw label distribution in the data is itself biased —
    before any model is applied.
    """
    priv_mask   = df[protected_col] == privileged_value
    unpriv_mask = df[protected_col] == unprivileged_value

    priv_pos   = float((df.loc[priv_mask,   label_col] == positive_label).mean())
    unpriv_pos = float((df.loc[unpriv_mask, label_col] == positive_label).mean())

    priv_n   = int(priv_mask.sum())
    unpriv_n = int(unpriv_mask.sum())
    total    = priv_n + unpriv_n

    ratio = priv_pos / unpriv_pos if unpriv_pos > 0 else float("inf")
    abs_gap = abs(priv_pos - unpriv_pos)

    # Chi-square test for independence
    from scipy.stats import chi2_contingency
    priv_pos_n   = int((df.loc[priv_mask,   label_col] == positive_label).sum())
    unpriv_pos_n = int((df.loc[unpriv_mask, label_col] == positive_label).sum())
    contingency  = [[priv_pos_n, priv_n - priv_pos_n],
                    [unpriv_pos_n, unpriv_n - unpriv_pos_n]]
    chi2, p_value, _, _ = chi2_contingency(contingency)
    statistically_significant = bool(p_value < 0.05)

    if abs_gap <= 0.03:
        severity = "none"
        verdict  = "The training data labels are approximately equal between groups. Historical outcome bias is NOT the primary cause."
    elif abs_gap <= 0.08:
        severity = "low"
        verdict  = f"Mild historical inequality exists: '{privileged_value}' has a {priv_pos*100:.1f}% positive rate vs {unpriv_pos*100:.1f}% for '{unprivileged_value}'. This contributes modestly to model bias."
    elif abs_gap <= 0.18:
        severity = "medium"
        verdict  = f"Clear historical inequality: '{privileged_value}' achieves positive outcomes {ratio:.1f}× more often than '{unprivileged_value}' in the raw data. The model learned this as ground truth."
    else:
        severity = "high"
        verdict  = f"STRONG historical bias confirmed: '{privileged_value}' has a {priv_pos*100:.1f}% positive rate vs only {unpriv_pos*100:.1f}% for '{unprivileged_value}' — a {ratio:.1f}× gap. This is the dominant root cause of model bias."

    label_dist = {}
    for gname, mask in [(str(privileged_value), priv_mask),
                        (str(unprivileged_value), unpriv_mask)]:
        vc = df.loc[mask, label_col].value_counts(normalize=True)
        label_dist[gname] = {str(k): round(float(v), 4) for k, v in vc.items()}

    return {
        "title": "Historical Outcome Bias",
        "icon": "📜",
        "severity": severity,
        "verdict": verdict,
        "stats": {
            f"{privileged_value}_positive_rate":   round(priv_pos, 4),
            f"{unprivileged_value}_positive_rate": round(unpriv_pos, 4),
            f"{privileged_value}_sample_size":     priv_n,
            f"{unprivileged_value}_sample_size":   unpriv_n,
            "outcome_ratio":                       round(ratio, 3),
            "absolute_gap":                        round(abs_gap, 4),
            "chi2_statistic":                      round(chi2, 3),
            "p_value":                             round(p_value, 6),
            "statistically_significant":           statistically_significant,
        },
        "label_distribution": label_dist,
        "explanation": (
            f"We tested whether the positive outcome rate is statistically different "
            f"between '{privileged_value}' ({priv_pos*100:.1f}%) and '{unprivileged_value}' "
            f"({unpriv_pos*100:.1f}%) using a chi-square test (χ²={chi2:.2f}, p={p_value:.4f}). "
            f"{'The difference IS statistically significant' if statistically_significant else 'The difference is NOT statistically significant'} "
            f"at the 5% level. "
            f"{'This means the data itself encodes historical discrimination that the model learned to replicate.' if statistically_significant and abs_gap > 0.05 else 'This is not the primary bias source.'}"
        ),
    }


# ══════════════════════════════════════════════════════════════════════════════
# INVESTIGATION 2 – Proxy Chain Analysis
# ══════════════════════════════════════════════════════════════════════════════

def _investigate_proxy_chains(df, label_col, protected_col,
                               privileged_value, unprivileged_value,
                               positive_label):
    """
    Finds the full discrimination pathway: which features act as proxies,
    and how they chain together to reach the protected attribute.
    """
    X, y_raw, encoders = _encode_df(df, label_col)
    y_bin = (y_raw == positive_label).astype(int)

    feature_cols = [c for c in X.columns if c != protected_col]
    prot_encoded = X[protected_col] if protected_col in X.columns else None

    # Correlation of every feature with protected attribute
    proxy_corrs = {}
    if prot_encoded is not None:
        for col in feature_cols:
            c = _corr(X[col], prot_encoded)
            if c > 0.15:
                proxy_corrs[col] = round(c, 4)
    proxy_corrs = dict(sorted(proxy_corrs.items(), key=lambda x: -x[1]))

    # Correlation of every feature with label
    label_corrs = {}
    for col in feature_cols:
        c = _corr(X[col], y_bin)
        if c > 0.05:
            label_corrs[col] = round(c, 4)

    # Build proxy chains: feature → protected → label
    chains = []
    for feat, prot_corr in list(proxy_corrs.items())[:8]:
        label_corr = label_corrs.get(feat, 0.0)
        if label_corr > 0.05:
            chain_strength = round(prot_corr * label_corr, 4)
            risk = "high" if prot_corr > 0.5 else ("medium" if prot_corr > 0.3 else "low")
            chains.append({
                "feature":            feat,
                "corr_with_protected": prot_corr,
                "corr_with_label":    label_corr,
                "chain_strength":     chain_strength,
                "risk":               risk,
                "chain_description": (
                    f"'{feat}' → '{protected_col}' → '{label_col}': "
                    f"This feature correlates {prot_corr:.2f} with {protected_col} "
                    f"and {label_corr:.2f} with the outcome, creating an indirect "
                    f"discrimination pathway with strength {chain_strength:.3f}."
                ),
            })

    chains.sort(key=lambda x: -x["chain_strength"])

    # Multi-hop chains: feature_A → feature_B → protected
    multi_hop = []
    top_proxies = list(proxy_corrs.keys())[:5]
    for f1, f2 in combinations(feature_cols[:12], 2):
        if f1 in top_proxies or f2 in top_proxies:
            c12  = _corr(X[f1], X[f2])
            c1p  = proxy_corrs.get(f1, 0)
            c2p  = proxy_corrs.get(f2, 0)
            if c12 > 0.3 and (c1p > 0.2 or c2p > 0.2):
                multi_hop.append({
                    "feature_a":    f1,
                    "feature_b":    f2,
                    "a_b_corr":     round(c12, 3),
                    "a_prot_corr":  round(c1p, 3),
                    "b_prot_corr":  round(c2p, 3),
                    "description": (
                        f"'{f1}' and '{f2}' are correlated ({c12:.2f}), "
                        f"and both correlate with '{protected_col}' "
                        f"({c1p:.2f} and {c2p:.2f}). "
                        f"Removing one may not be enough — the other still carries the signal."
                    ),
                })
    multi_hop.sort(key=lambda x: -(x["a_b_corr"] * max(x["a_prot_corr"], x["b_prot_corr"])))

    top_chain = chains[0] if chains else None
    if not chains:
        severity = "none"
        verdict  = "No significant proxy chains detected. The model does not appear to use indirect pathways to reach the protected attribute."
    elif top_chain["risk"] == "high":
        severity = "high"
        verdict  = (f"CRITICAL PROXY CHAIN: '{top_chain['feature']}' is a strong proxy "
                    f"(r={top_chain['corr_with_protected']:.2f}) for '{protected_col}'. "
                    f"Even if you remove '{protected_col}' from the model, discrimination "
                    f"will persist through this feature.")
    elif top_chain["risk"] == "medium":
        severity = "medium"
        verdict  = (f"Moderate proxy chains found. '{top_chain['feature']}' "
                    f"(r={top_chain['corr_with_protected']:.2f} with {protected_col}) "
                    f"enables indirect discrimination.")
    else:
        severity = "low"
        verdict  = f"Weak proxy chains detected. Low indirect discrimination risk through feature correlations."

    return {
        "title":       "Proxy Chain Analysis",
        "icon":        "🔗",
        "severity":    severity,
        "verdict":     verdict,
        "chains":      chains[:6],
        "multi_hop":   multi_hop[:4],
        "top_proxies": list(proxy_corrs.items())[:8],
        "explanation": (
            f"We computed Pearson correlations between every feature and "
            f"(a) the protected attribute '{protected_col}' and "
            f"(b) the outcome label '{label_col}'. "
            f"Features appearing in both lists create indirect discrimination pathways. "
            f"Found {len(chains)} proxy chains and {len(multi_hop)} multi-hop correlations."
        ),
    }


# ══════════════════════════════════════════════════════════════════════════════
# INVESTIGATION 3 – Intersectional Bias
# ══════════════════════════════════════════════════════════════════════════════

def _investigate_intersectional(df, label_col, protected_col,
                                  privileged_value, unprivileged_value,
                                  positive_label):
    """
    Finds bias that only emerges at the intersection of multiple characteristics.
    E.g. bias against Black women that wouldn't show up checking race or gender alone.
    """
    # Find candidate intersecting columns (categorical, low-cardinality)
    candidate_cols = []
    for col in df.columns:
        if col in (label_col, protected_col):
            continue
        n_unique = df[col].nunique()
        if 2 <= n_unique <= 8:
            candidate_cols.append(col)

    # Baseline group rates
    priv_mask   = df[protected_col] == privileged_value
    unpriv_mask = df[protected_col] == unprivileged_value
    baseline_priv   = float((df.loc[priv_mask,   label_col] == positive_label).mean())
    baseline_unpriv = float((df.loc[unpriv_mask, label_col] == positive_label).mean())
    baseline_gap    = abs(baseline_priv - baseline_unpriv)

    intersections = []
    for col in candidate_cols[:6]:
        col_vals = df[col].dropna().unique()
        for val in col_vals:
            sub_mask = df[col] == val
            sub_priv   = df[priv_mask   & sub_mask]
            sub_unpriv = df[unpriv_mask & sub_mask]
            if len(sub_priv) < 15 or len(sub_unpriv) < 15:
                continue
            sub_priv_rate   = float((sub_priv[label_col]   == positive_label).mean())
            sub_unpriv_rate = float((sub_unpriv[label_col] == positive_label).mean())
            sub_gap         = abs(sub_priv_rate - sub_unpriv_rate)
            gap_amplification = sub_gap - baseline_gap

            if sub_gap > 0.05:
                intersections.append({
                    "column":          col,
                    "value":           str(val),
                    "group":           f"{protected_col}={unprivileged_value} & {col}={val}",
                    "priv_rate":       round(sub_priv_rate,   4),
                    "unpriv_rate":     round(sub_unpriv_rate, 4),
                    "gap":             round(sub_gap, 4),
                    "baseline_gap":    round(baseline_gap, 4),
                    "amplification":   round(gap_amplification, 4),
                    "priv_n":          len(sub_priv),
                    "unpriv_n":        len(sub_unpriv),
                    "is_amplified":    bool(gap_amplification > 0.05),
                    "description": (
                        f"When {col}='{val}': '{privileged_value}' rate={sub_priv_rate*100:.1f}% "
                        f"vs '{unprivileged_value}' rate={sub_unpriv_rate*100:.1f}% "
                        f"(gap={sub_gap*100:.1f}%). "
                        + (f"⚠ This is {gap_amplification*100:.1f}pp WORSE than the baseline gap — "
                           f"intersectional discrimination detected."
                           if gap_amplification > 0.05 else
                           f"Gap is similar to baseline.")
                    ),
                })

    intersections.sort(key=lambda x: -x["gap"])
    amplified = [i for i in intersections if i["is_amplified"]]

    if not intersections:
        severity = "none"
        verdict  = "No intersectional bias detected. Bias affects both groups uniformly across all sub-segments."
    elif not amplified:
        severity = "low"
        verdict  = f"Bias is relatively uniform across subgroups. No strong intersectional amplification found."
    elif max(i["amplification"] for i in amplified) > 0.15:
        severity = "high"
        worst    = max(amplified, key=lambda x: x["amplification"])
        verdict  = (f"INTERSECTIONAL BIAS CONFIRMED: The subgroup "
                    f"'{worst['group']}' experiences {worst['gap']*100:.1f}% gap — "
                    f"{worst['amplification']*100:.1f} percentage points WORSE than the baseline. "
                    f"Standard metrics hide this — only intersectional analysis reveals it.")
    else:
        severity = "medium"
        verdict  = f"Moderate intersectional bias: {len(amplified)} subgroups show amplified discrimination beyond the baseline gap."

    return {
        "title":             "Intersectional Bias Detection",
        "icon":              "⚡",
        "severity":          severity,
        "verdict":           verdict,
        "baseline_gap":      round(baseline_gap, 4),
        "intersections":     intersections[:10],
        "amplified_groups":  amplified[:5],
        "columns_tested":    candidate_cols[:6],
        "explanation": (
            f"Standard fairness metrics compare '{privileged_value}' vs '{unprivileged_value}' as whole groups. "
            f"Intersectional analysis checks whether the bias is worse for specific subgroups "
            f"(e.g., 'unprivileged + young' or 'unprivileged + certain occupation'). "
            f"Baseline gap: {baseline_gap*100:.1f}%. "
            f"Tested {len(candidate_cols)} secondary attributes, found {len(intersections)} intersections, "
            f"{len(amplified)} with amplified discrimination."
        ),
    }


# ══════════════════════════════════════════════════════════════════════════════
# INVESTIGATION 4 – Decision Boundary Audit
# ══════════════════════════════════════════════════════════════════════════════

def _investigate_decision_boundary(df, label_col, protected_col,
                                    privileged_value, unprivileged_value,
                                    positive_label):
    """
    Finds the exact numeric tipping points for approval per group.
    "You need X to be approved if Male, but Y if Female — a Z-point penalty."
    """
    X, y_raw, encoders = _encode_df(df, label_col)
    y_bin = (y_raw == positive_label).astype(int)

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y_bin, test_size=0.3, random_state=42, stratify=y_bin)
    sc    = StandardScaler()
    model = LogisticRegression(max_iter=600, random_state=42)
    model.fit(sc.fit_transform(X_tr), y_tr)

    feature_cols = list(X.columns)
    priv_mask_te   = X_te[protected_col] == (
        encoders[protected_col].transform([str(privileged_value)])[0]
        if protected_col in encoders else privileged_value)
    unpriv_mask_te = X_te[protected_col] == (
        encoders[protected_col].transform([str(unprivileged_value)])[0]
        if protected_col in encoders else unprivileged_value)

    priv_proba   = model.predict_proba(sc.transform(X_te[priv_mask_te]))[:, 1]
    unpriv_proba = model.predict_proba(sc.transform(X_te[unpriv_mask_te]))[:, 1]

    # Average approval probability gap
    avg_priv_prob   = float(priv_proba.mean())   if len(priv_proba)   > 0 else 0.5
    avg_unpriv_prob = float(unpriv_proba.mean()) if len(unpriv_proba) > 0 else 0.5
    prob_gap        = avg_priv_prob - avg_unpriv_prob

    # For each top numeric feature: find threshold difference per group
    numeric_cols = X.select_dtypes(include="number").columns.tolist()
    numeric_cols = [c for c in numeric_cols if c != protected_col][:6]

    boundary_findings = []
    for feat in numeric_cols:
        # Skip if this feature was originally categorical (encoded)
        if feat in encoders:
            continue
            
        # Check if original feature exists in DataFrame
        if feat not in df.columns:
            continue
            
        orig_feat = df[feat].dropna()
        if orig_feat.nunique() < 5:
            continue

        priv_sub   = df[df[protected_col] == privileged_value][[feat, label_col]].dropna()
        unpriv_sub = df[df[protected_col] == unprivileged_value][[feat, label_col]].dropna()
        if len(priv_sub) < 20 or len(unpriv_sub) < 20:
            continue

        # Find median of positive-outcome group for each
        priv_pos_med   = float(priv_sub[priv_sub[label_col] == positive_label][feat].median())
        unpriv_pos_med = float(unpriv_sub[unpriv_sub[label_col] == positive_label][feat].median())
        priv_neg_med   = float(priv_sub[priv_sub[label_col] != positive_label][feat].median())
        unpriv_neg_med = float(unpriv_sub[unpriv_sub[label_col] != positive_label][feat].median())

        # Estimated threshold = midpoint between positive and negative medians
        priv_threshold   = (priv_pos_med   + priv_neg_med)   / 2
        unpriv_threshold = (unpriv_pos_med + unpriv_neg_med) / 2
        penalty          = unpriv_threshold - priv_threshold  # positive = harder for unpriv

        if abs(penalty) > (orig_feat.std() * 0.1):
            unit = ""
            if "age" in feat.lower():       unit = " years"
            elif "score" in feat.lower():   unit = " points"
            elif "income" in feat.lower():  unit = " USD"
            elif "amount" in feat.lower():  unit = " USD"
            elif "hour" in feat.lower():    unit = " hrs/week"

            boundary_findings.append({
                "feature":            feat,
                "priv_threshold":     round(priv_threshold,  2),
                "unpriv_threshold":   round(unpriv_threshold, 2),
                "penalty":            round(penalty, 2),
                "penalty_direction":  "harder for unprivileged" if penalty > 0 else "easier for unprivileged",
                "unit":               unit,
                "description": (
                    f"'{feat}': '{privileged_value}' needs ~{priv_threshold:.1f}{unit} for positive outcome, "
                    f"but '{unprivileged_value}' needs ~{unpriv_threshold:.1f}{unit} — "
                    f"a {'disadvantage' if penalty > 0 else 'advantage'} of "
                    f"{abs(penalty):.1f}{unit} for the unprivileged group."
                ),
            })

    boundary_findings.sort(key=lambda x: -abs(x["penalty"]))

    if not boundary_findings:
        severity = "low"
        verdict  = "No clear numeric threshold differences detected between groups."
    elif abs(prob_gap) > 0.15 or (boundary_findings and abs(boundary_findings[0]["penalty"]) > 5):
        severity = "high"
        top      = boundary_findings[0]
        verdict  = (f"CONCRETE DISCRIMINATION TIPPING POINT FOUND: "
                    f"For '{top['feature']}', '{privileged_value}' needs {top['priv_threshold']:.1f}{top['unit']} "
                    f"vs {top['unpriv_threshold']:.1f}{top['unit']} for '{unprivileged_value}' — "
                    f"a {abs(top['penalty']):.1f}{top['unit']} penalty purely based on group membership. "
                    f"Average approval probability gap: {prob_gap*100:.1f}pp.")
    else:
        severity = "medium"
        verdict  = (f"Moderate threshold differences detected. "
                    f"Average approval probability gap: {prob_gap*100:.1f}pp between groups.")

    return {
        "title":               "Decision Boundary Audit",
        "icon":                "📏",
        "severity":            severity,
        "verdict":             verdict,
        "avg_priv_approval":   round(avg_priv_prob,   4),
        "avg_unpriv_approval": round(avg_unpriv_prob, 4),
        "approval_prob_gap":   round(prob_gap, 4),
        "boundary_findings":   boundary_findings[:6],
        "explanation": (
            f"We trained a logistic regression model and measured the average approval "
            f"probability for each group: '{privileged_value}' averages "
            f"{avg_priv_prob*100:.1f}% vs '{unprivileged_value}' at {avg_unpriv_prob*100:.1f}% "
            f"(gap: {prob_gap*100:.1f}pp). For each numeric feature, we estimated the "
            f"outcome tipping point per group by comparing the median feature values "
            f"of approved vs rejected cases within each group."
        ),
    }


# ══════════════════════════════════════════════════════════════════════════════
# MAIN AUTOPSY FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

def run_bias_autopsy(
    df: pd.DataFrame,
    label_col: str,
    protected_col: str,
    privileged_value,
    unprivileged_value,
    positive_label=1,
    overall_bias_score: float = 0.0,
) -> dict:
    """
    Run all four root-cause investigations and synthesise a verdict.
    Returns a structured autopsy report dict.
    """
    results = {}
    errors  = {}

    for name, fn in [
        ("historical",    _investigate_historical),
        ("proxy_chains",  _investigate_proxy_chains),
        ("intersectional",_investigate_intersectional),
        ("decision_boundary", _investigate_decision_boundary),
    ]:
        try:
            results[name] = fn(df, label_col, protected_col,
                               privileged_value, unprivileged_value,
                               positive_label)
        except Exception as e:
            errors[name] = str(e)
            results[name] = {
                "title":    name.replace("_", " ").title(),
                "icon":     "⚠",
                "severity": "none",
                "verdict":  f"Investigation could not complete: {e}",
                "explanation": "",
            }

    # ── Synthesise overall verdict ────────────────────────────────────────────
    sev_rank = {"none": 0, "low": 1, "medium": 2, "high": 3}
    severities = {k: v.get("severity", "none") for k, v in results.items()}
    max_sev    = max(severities.values(), key=lambda s: sev_rank.get(s, 0))

    # Primary cause = investigation with highest severity
    primary_cause = max(severities.items(), key=lambda x: sev_rank.get(x[1], 0))[0]
    cause_labels  = {
        "historical":        "Historical Outcome Inequality in Training Data",
        "proxy_chains":      "Indirect Discrimination Through Proxy Features",
        "intersectional":    "Intersectional Discrimination in Subgroups",
        "decision_boundary": "Different Decision Thresholds Per Group",
    }

    # Build narrative summary
    hist_sev  = sev_rank.get(severities.get("historical",  "none"), 0)
    proxy_sev = sev_rank.get(severities.get("proxy_chains","none"), 0)
    inter_sev = sev_rank.get(severities.get("intersectional","none"),0)
    bound_sev = sev_rank.get(severities.get("decision_boundary","none"),0)

    causes_found = [k for k, s in severities.items() if sev_rank.get(s,0) >= 2]

    if not causes_found:
        narrative = (
            f"The bias audit detected a score of {overall_bias_score:.0f}/100, but deep root-cause "
            f"investigation did not find a single dominant cause. The bias appears to be "
            f"distributed across multiple small factors rather than one clear source. "
            f"This type of diffuse bias is harder to fix but less severe than structural bias."
        )
    elif len(causes_found) == 1:
        narrative = (
            f"Root cause identified: <strong>{cause_labels[causes_found[0]]}</strong>. "
            f"{results[causes_found[0]]['verdict']} "
            f"Fixing this single root cause should substantially reduce the bias score of {overall_bias_score:.0f}/100."
        )
    else:
        cause_names = " + ".join([cause_labels[c] for c in causes_found])
        narrative = (
            f"Multiple root causes identified: {cause_names}. "
            f"This model is biased through {len(causes_found)} simultaneous mechanisms. "
            f"All identified causes must be addressed to meaningfully reduce the bias score of {overall_bias_score:.0f}/100."
        )

    return {
        "overall": {
            "primary_cause":    cause_labels.get(primary_cause, primary_cause),
            "max_severity":     max_sev,
            "causes_found":     len(causes_found),
            "narrative":        narrative,
            "bias_score":       overall_bias_score,
            "severities":       severities,
        },
        "investigations": results,
        "errors":          errors,
    }
