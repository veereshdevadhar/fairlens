"""
FairLens – Gemini AI Chat
Context-aware AI assistant that has already read the audit results
and can answer questions in plain English.
"""
import os
import json

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


def _build_system_context(audit_context: dict) -> str:
    overall  = audit_context.get("overall", {})
    metrics  = audit_context.get("metrics", {})
    groups   = audit_context.get("group_stats", {})
    proxies  = audit_context.get("proxy_features", {})
    recs     = audit_context.get("recommendations", [])
    dataset  = audit_context.get("dataset_name", "the dataset")

    def fmt_metric(m):
        v = m.get("value")
        return f"{v:.4f} ({m.get('severity','?')} severity)" if v is not None else "N/A"

    ctx = f"""You are FairLens AI — an expert in algorithmic fairness and AI bias. 
You have just completed a full bias audit and have the following results in front of you.

=== AUDIT RESULTS ===
Dataset: {dataset}
Protected attribute: {overall.get('protected_attribute','?')}
Privileged group: {overall.get('privileged_group','?')}
Unprivileged group: {overall.get('unprivileged_group','?')}
Total rows: {overall.get('total_rows','?')}
Model accuracy: {overall.get('model_accuracy','?')}
Bias score: {overall.get('bias_score','?')}/100
Overall severity: {overall.get('severity','?').upper()}

=== FAIRNESS METRICS ===
Statistical Parity Difference: {fmt_metric(metrics.get('statistical_parity_difference',{}))}
  (negative = unprivileged group gets fewer positive outcomes)
Disparate Impact Ratio: {fmt_metric(metrics.get('disparate_impact',{}))}
  (below 0.8 = legally significant in many jurisdictions)
Equalized Odds (TPR): {fmt_metric(metrics.get('equalized_odds_difference_tpr',{}))}
Equalized Odds (FPR): {fmt_metric(metrics.get('equalized_odds_difference_fpr',{}))}
Predictive Parity: {fmt_metric(metrics.get('predictive_parity_difference',{}))}
Accuracy Difference: {fmt_metric(metrics.get('accuracy_difference',{}))}

=== GROUP STATISTICS ==="""
    for gname, gdata in groups.items():
        ctx += f"""
{gname}:
  Positive outcome rate: {gdata.get('positive_rate','?')}
  Model accuracy: {gdata.get('model_accuracy','?')}
  True positive rate: {gdata.get('true_positive_rate','?')}
  False positive rate: {gdata.get('false_positive_rate','?')}"""

    if proxies:
        ctx += f"\n\n=== PROXY FEATURES DETECTED ===\n"
        for feat, corr in proxies.items():
            ctx += f"  {feat}: correlation {corr:.3f} with protected attribute\n"

    if recs:
        ctx += "\n=== RECOMMENDED FIXES ===\n"
        for r in recs:
            ctx += f"  {r.get('priority','?').upper()} priority: {r.get('title','?')}\n"

    ctx += """

=== YOUR ROLE ===
You are a helpful, clear, and honest AI fairness expert. 
- Answer questions about these specific audit results
- Explain concepts in simple, plain language — avoid jargon unless asked
- Use concrete examples from this audit when explaining
- Be honest about the severity and real-world implications
- When asked to write something (email, report summary, explanation), do it directly
- Keep answers concise but complete — no padding
- Never make up numbers not in the audit results above"""

    return ctx


def _fallback_response(question: str, audit_context: dict) -> str:
    """
    Highly accurate rule-based fallback when Gemini API is unavailable.
    Provides specific, contextual answers based on actual audit data.
    """
    q = question.lower()
    overall = audit_context.get("overall", {})
    metrics = audit_context.get("metrics", {})
    groups  = audit_context.get("group_stats", {})
    proxies = audit_context.get("proxy_features", {})
    recs    = audit_context.get("recommendations", [])
    score   = overall.get("bias_score", 0)
    sev     = overall.get("severity", "unknown")
    prot    = overall.get("protected_attribute", "the protected attribute")
    priv    = overall.get("privileged_group", "the privileged group")
    unpriv  = overall.get("unprivileged_group", "the unprivileged group")
    spd     = metrics.get("statistical_parity_difference", {}).get("value", None)
    di      = metrics.get("disparate_impact", {}).get("value", None)
    tpr_diff = metrics.get("equalized_odds_difference_tpr", {}).get("value", None)
    fpr_diff = metrics.get("equalized_odds_difference_fpr", {}).get("value", None)
    pred_parity = metrics.get("predictive_parity_difference", {}).get("value", None)
    acc_diff = metrics.get("accuracy_difference", {}).get("value", None)
    
    # Helper functions for formatting
    def fmt_float(val, decimals=4):
        return f"{val:.{decimals}f}" if val is not None else "N/A"
    
    def get_group_rate(group_name):
        for gname, gdata in groups.items():
            if str(group_name).lower() in str(gname).lower() or str(gname).lower() in str(group_name).lower():
                return gdata.get('positive_rate', 0)
        return 0

    # 🎯 SPECIFIC QUESTION HANDLING WITH HIGH ACCURACY
    
    # Basic Understanding Questions
    if any(w in q for w in ["what is","explain","what does","what are","define","meaning"]):
        if "statistical parity" in q or "spd" in q:
            return (f"Statistical Parity Difference (SPD) measures how differently the model treats "
                    f"'{priv}' vs '{unpriv}'. In your audit, SPD = {fmt_float(spd)}. "
                    f"Negative {fmt_float(spd)} means '{unpriv}' gets {abs(spd or 0)*100:.1f}% fewer positive outcomes. "
                    f"Industry threshold is ±0.1 — yours is {'within' if spd and abs(spd)<=0.1 else 'outside'} standards.")
        
        if "disparate impact" in q or "di" in q:
            return (f"Disparate Impact Ratio measures positive outcomes for '{unpriv}' ÷ '{priv}'. "
                    f"Your DI = {fmt_float(di)}. {'Above 0.8 legal threshold' if di and di >= 0.8 else 'Below 0.8 - legal concern'}. "
                    f"Value of 1.0 = perfect equality. Your ratio means '{unpriv}' gets {(di or 0)*100:.1f}% of the positive outcomes that '{priv}' gets.")
        
        if "bias" in q and "score" in q:
            return (f"Your bias score is {score}/100 ({sev} severity). "
                    f"This combines 6 fairness metrics measuring unfair treatment of '{unpriv}' vs '{priv}'. "
                    f"0 = no bias, 100 = extreme bias. Your score indicates {'minimal' if score < 25 else 'moderate' if score < 50 else 'significant'} bias.")
        
        if "equalized odds" in q:
            if "tpr" in q:
                return (f"Equalized Odds TPR gap: {fmt_float(tpr_diff)}. "
                        f"{'Positive' if tpr_diff and tpr_diff > 0 else 'Negative'} difference means '{unpriv}' has "
                        f"{'higher' if tpr_diff and tpr_diff > 0 else 'lower'} true positive rates than '{priv}'. "
                        f"Near 0 = equal opportunity.")
            if "fpr" in q:
                return (f"Equalized Odds FPR gap: {fmt_float(fpr_diff)}. "
                        f"Measures false positive rate equality. "
                        f"{'Higher' if fpr_diff and fpr_diff > 0 else 'Lower'} FPR for '{unpriv}' indicates unequal error rates.")

    # Seriousness/Legal Questions  
    if any(w in q for w in ["how bad","how serious","should i be worried","severe","legal","compliant","risk"]):
        legal_status = "COMPLIANT" if di and di >= 0.8 else "NON-COMPLIANT"
        risk_level = "LOW" if score < 25 else "MEDIUM" if score < 50 else "HIGH"
        
        return (f"BIAS ASSESSMENT: {sev.upper()} severity (score: {score}/100)\n\n"
                f"Legal Status: {legal_status} (DI: {fmt_float(di)} {'✓' if di and di >= 0.8 else '✗'})\n"
                f"Industry Standards: SPD {fmt_float(spd)} {'✓' if spd and abs(spd) <= 0.1 else '✗'}\n"
                f"Business Risk: {risk_level}\n"
                f"Impact: '{unpriv}' positive rate: {get_group_rate(unpriv):.1%} vs '{priv}': {get_group_rate(priv):.1%}\n"
                f"Action: {'Monitor' if score < 25 else 'Fix before deployment' if score < 50 else 'DO NOT DEPLOY'}")

    # Root Cause Analysis
    if any(w in q for w in ["why","cause","reason","feature","proxy"]):
        if "proxy" in q:
            if proxies:
                top_proxy = max(proxies.items(), key=lambda x: x[1])
                return (f"PROXY ANALYSIS: {len(proxies)} proxy features detected\n\n"
                        f"Top proxy: '{top_proxy[0]}' (correlation: {top_proxy[1]:.3f} with '{prot}')\n"
                        f"Danger: Model discriminates indirectly even if '{prot}' is removed\n"
                        f"Action: Remove or transform high-correlation proxies (>0.5)")
            return "No significant proxy features detected - good news for fairness!"
        
        if "feature" in q and ("causing" in q or "most bias" in q):
            if proxies:
                top_proxy = max(proxies.items(), key=lambda x: x[1])
                return (f"FEATURE CAUSING MOST BIAS:\n\n"
                        f"Top Problem: '{top_proxy[0]}'\n"
                        f"• Correlation with protected attribute: {top_proxy[1]:.3f}\n"
                        f"• Impact: Enables indirect discrimination\n"
                        f"• Action: Remove this feature first for maximum bias reduction")
            return (f"MAIN BIAS DRIVER:\n\n"
                    f"Data imbalance between groups is the primary cause.\n"
                    f"'{unpriv}': {get_group_rate(unpriv):.1%} positive outcomes\n"
                    f"'{priv}': {get_group_rate(priv):.1%} positive outcomes\n"
                    f"Fix: Balance training data representation.")
        
        if "cause" in q or "why" in q:
            unpriv_rate = get_group_rate(unpriv)
            priv_rate = get_group_rate(priv)
            return (f"ROOT CAUSES:\n\n"
                    f"1. Data Imbalance: '{unpriv}' {unpriv_rate:.1%} positive rate vs '{priv}' {priv_rate:.1%}\n"
                    f"2. Proxy Features: {len(proxies)} indirect discriminators detected\n"
                    f"3. Historical Bias: Training data reflects existing societal biases\n"
                    f"4. Model Learning: Algorithm amplifies small differences")

    # Fix Recommendations  
    if any(w in q for w in ["fix","how to fix","what can i do","solution","recommendation","implement"]):
        if recs:
            r = recs[0]
            return (f"TOP PRIORITY FIX: {r.get('title')}\n\n"
                    f"Description: {r.get('description')}\n"
                    f"Priority: {r.get('priority')} | Expected Impact: {r.get('impact')}\n"
                    f"Implementation: See Fixes tab for code examples\n"
                    f"Total fixes available: {len(recs)}")
        return "Check the Fixes tab for detailed technical recommendations."
        
        if "show me the code" in q or "code example" in q:
            if recs:
                r = recs[0]
                return (f"CODE EXAMPLE:\n\n"
                        f"```python\n"
                        f"# {r.get('title')}\n"
                        f"# {r.get('description')}\n\n"
                        f"# Remove protected attribute and proxies\n"
                        f"features = [f for f in X.columns if f != '{prot}']\n"
                        f"if proxies:\n"
                        f"    features = [f for f in features if f not in proxies.keys()]\n"
                        f"\n"
                        f"# Retrain cleaned model\n"
                        f"X_clean = X[features]\n"
                        f"model.fit(X_clean, y)\n"
                        f"```\n\n"
                        f"See Fixes tab for complete implementations.")
            return "No code examples available - check Fixes tab for recommendations."
        
        if "reweighting" in q or "threshold" in q:
            return (f"FIX COMPARISON:\n\n"
                    f"**Reweighting** (Recommended first):\n"
                    f"• Balances training data representation\n"
                    f"• Preserves model accuracy\n"
                    f"• Best for data imbalance issues\n\n"
                    f"**Threshold Adjustment**:\n"
                    f"• Changes decision cutoffs per group\n"
                    f"• Directly controls outcome rates\n"
                    f"• Use if reweighting insufficient\n\n"
                    f"Test both in What-If Simulator!")

    # Business Communication
    if any(w in q for w in ["email","write","draft","letter","board","ceo","summary","presentation"]):
        if "board" in q or "ceo" in q:
            return (f"BOARD COMMUNICATION:\n\n"
                    f"Subject: AI Fairness Audit - {sev.upper()} Risk Level\n\n"
                    f"Executive Summary:\n"
                    f"• Bias Score: {score}/100 ({sev} severity)\n"
                    f"• Legal Compliance: {'✓ Compliant' if di and di >= 0.8 else '⚠ Non-compliant'}\n"
                    f"• Business Impact: {get_group_rate(unpriv):.1%} vs {get_group_rate(priv):.1%} positive rates\n"
                    f"• Action Required: {len(recs)} technical fixes\n"
                    f"• Timeline: 2-4 weeks\n"
                    f"• Recommendation: {'Proceed with monitoring' if score < 25 else 'Fix before deployment'}")
        
        if "presentation" in q or "slide" in q:
            return (f"PRESENTATION STRUCTURE:\n\n"
                    f"1. Audit Overview: {sev.upper()} bias detected\n"
                    f"2. Key Metrics: SPD={fmt_float(spd)}, DI={fmt_float(di)}, Score={score}/100\n"
                    f"3. Impact Analysis: Group outcomes and affected population\n"
                    f"4. Root Causes: Data issues and proxy features\n"
                    f"5. Solutions: {len(recs)} prioritized fixes\n"
                    f"6. Timeline: Implementation roadmap")
        
        if "stakeholder" in q or "non-technical" in q:
            return (f"SIMPLE EXPLANATION FOR NON-TECHNICAL AUDIENCE:\n\n"
                    f"Our AI system is treating people unfairly based on {prot}.\n\n"
                    f"THE PROBLEM:\n"
                    f"• '{unpriv}' group gets positive outcomes only {get_group_rate(unpriv):.1%} of the time\n"
                    f"• '{priv}' group gets positive outcomes {get_group_rate(priv):.1%} of the time\n"
                    f"• This difference is {'legally problematic' if di and di < 0.8 else 'concerning'}\n\n"
                    f"WHY IT MATTERS:\n"
                    f"• Real people being affected unfairly\n"
                    f"• Potential legal issues for the company\n"
                    f"• Reputational and financial risks\n\n"
                    f"WHAT WE'RE DOING:\n"
                    f"• Found {len(recs)} ways to fix the problem\n"
                    f"• Will implement solutions over 2-4 weeks\n"
                    f"• Goal: Make the AI fair for everyone")

    # Deployment Risk & Feature Analysis
    if any(w in q for w in ["deploy","deployment","what if","happen if","as-is"]):
        # Check for specific feature removal questions
        import re
        feature_match = re.search(r"removed? ['\"]([^'\"]+)['\"]", q)
        if feature_match:
            feature_name = feature_match.group(1)
            if feature_name in proxies:
                return (f"REMOVING '{feature_name}' FEATURE:\n\n"
                        f"Expected Impact: HIGH bias reduction\n"
                        f"• This feature has {proxies.get(feature_name, 0):.3f} correlation with '{prot}'\n"
                        f"• Removing it will reduce indirect discrimination\n"
                        f"• Bias score could drop by {proxies.get(feature_name, 0)*30:.0f} points\n"
                        f"• Recommendation: Remove this feature first")
            else:
                return (f"REMOVING '{feature_name}' FEATURE:\n\n"
                        f"Expected Impact: MODERATE bias reduction\n"
                        f"• Not a proxy feature, but may still help\n"
                        f"• Test in What-If Simulator for exact impact\n"
                        f"• Consider removing if not critical for predictions")
        
        risk_factors = []
        if di and di < 0.8:
            risk_factors.append("Legal discrimination risk")
        if spd and abs(spd) > 0.1:
            risk_factors.append("Industry standard violation")
        if score > 50:
            risk_factors.append("High bias severity")
        
        return (f"DEPLOYMENT RISK ASSESSMENT:\n\n"
                f"Current Status: {sev.upper()} bias (score: {score}/100)\n"
                f"Risk Factors: {', '.join(risk_factors) if risk_factors else 'Minimal'}\n"
                f"Recommendation: {'Deploy with monitoring' if score < 25 else 'Fix critical issues first' if score < 50 else 'DO NOT DEPLOY'}\n"
                f"Consequences of deploying as-is: "
                f"{'Minor reputational risk' if score < 25 else 'Potential legal challenges' if score < 50 else 'High likelihood of discrimination claims'}")
    
    # Strategy Comparison
    if any(w in q for w in ["compare","strategy","mitigation","approach"]):
        return (f"BIAS MITIGATION STRATEGY COMPARISON:\n\n"
                f"**1. DATA-LEVEL FIXES** (Recommended first):\n"
                f"• Reweighting: Balance training samples\n"
                f"• Oversampling: Increase minority representation\n"
                f"• Impact: Medium bias reduction, preserves accuracy\n\n"
                f"**2. FEATURE-LEVEL FIXES**:\n"
                f"• Remove proxies: Eliminate indirect discrimination\n"
                f"• Feature selection: Keep only fair features\n"
                f"• Impact: High bias reduction, may affect accuracy\n\n"
                f"**3. ALGORITHM-LEVEL FIXES**:\n"
                f"• Fairness constraints: Add bias penalties\n"
                f"• Threshold adjustment: Balance outcomes\n"
                f"• Impact: Precise control, complex implementation\n\n"
                f"**RECOMMENDATION**: Start with data fixes, then feature removal, test with What-If Simulator")

    # Default response
    return (f"FairLens Audit Results:\n"
            f"Bias Score: {score}/100 ({sev} severity)\n"
            f"Key Metrics: SPD={fmt_float(spd)}, DI={fmt_float(di)}\n"
            f"Groups: '{unpriv}' ({get_group_rate(unpriv):.1%}) vs '{priv}' ({get_group_rate(priv):.1%})\n"
            f"Fixes Available: {len(recs)} recommendations\n"
            f"Ask about specific metrics, fixes, legal implications, or communication drafts.")


def chat_with_gemini(
    question: str,
    audit_context: dict,
    history: list = None,
    api_key: str = None,
) -> dict:
    """
    Send a question to Gemini with the audit context as system prompt.
    Falls back to rule-based answers if Gemini is unavailable.
    
    history: list of {"role": "user"|"model", "parts": [{"text": "..."}]}
    """
    api_key = api_key or os.environ.get("GEMINI_API_KEY", "")

    # Try Gemini with fallback model names in order
    GEMINI_MODELS = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]

    if GEMINI_AVAILABLE and api_key and api_key.strip() and api_key != "YOUR_GEMINI_API_KEY":
        last_error = None
        for model_name in GEMINI_MODELS:
            try:
                genai.configure(api_key=api_key.strip())
                system_ctx = _build_system_context(audit_context)
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system_ctx,
                )
                hist = history or []
                # Filter history to only valid roles
                clean_hist = [
                    h for h in hist
                    if h.get("role") in ("user", "model") and h.get("parts")
                ]
                chat = model.start_chat(history=clean_hist)
                resp = chat.send_message(question)
                return {
                    "answer": resp.text,
                    "source": "gemini",
                    "model": model_name,
                    "tokens_used": getattr(resp, "usage_metadata", {}),
                }
            except Exception as e:
                last_error = str(e)
                # If it's an auth/key error, no point trying other models
                err_lower = str(e).lower()
                if any(x in err_lower for x in ["api_key", "api key", "invalid", "unauthorized", "403", "401"]):
                    break
                continue

    # Fallback
    answer = _fallback_response(question, audit_context)
    return {
        "answer": answer,
        "source": "fallback",
        "note": "Gemini API not configured or unavailable. Add a valid GEMINI_API_KEY for full AI responses.",
    }
