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
    Comprehensive rule-based fallback when Gemini API is unavailable.
    Handles all major question categories with specific, contextual answers.
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

    # 🎯 BASIC UNDERSTANDING QUESTIONS
    if any(w in q for w in ["what is","explain","what does","what are","define","meaning"]):
        if "statistical parity" in q or "spd" in q:
            return (f"Statistical Parity Difference (SPD) measures how differently the model treats "
                    f"'{priv}' vs '{unpriv}'. In your audit, SPD = {spd:.4f}. "
                    f"A value of 0 means perfect equality. Negative means '{unpriv}' gets fewer positive outcomes. "
                    f"The industry standard threshold is ±0.1 — yours is "
                    f"{'within' if spd and abs(spd)<=0.1 else 'outside'} that range.")
        
        if "disparate impact" in q or "di " in q:
            return (f"Disparate Impact Ratio measures the ratio of positive outcomes for '{unpriv}' "
                    f"divided by '{priv}'. Your value is {di:.4f}. "
                    f"A ratio below 0.8 is considered legally significant in the US (the '4/5ths rule'). "
                    f"A value of 1.0 means perfectly equal treatment.")
        
        if "equalized odds" in q:
            if "tpr" in q:
                return (f"Equalized Odds TPR gap measures if both groups have equal true positive rates. "
                        f"Your TPR difference is {tpr_diff:.4f}. "
                        f"This means '{unpriv}' has {'higher' if tpr_diff>0 else 'lower'} true positive rates than '{priv}'. "
                        f"Values near 0 indicate equal opportunity.")
            if "fpr" in q:
                return (f"Equalized Odds FPR gap measures if both groups have equal false positive rates. "
                        f"Your FPR difference is {fpr_diff:.4f}. "
                        f"This means '{unpriv}' has {'higher' if fpr_diff>0 else 'lower'} false positive rates than '{priv}'. "
                        f"Values near 0 indicate equal error rates.")
        
        if "predictive parity" in q:
            return (f"Predictive Parity measures if positive predictions are equally accurate across groups. "
                    f"Your difference is {pred_parity:.4f}. "
                    f"Values near 0 mean the model is equally reliable for both groups.")
        
        if "accuracy difference" in q:
            return (f"Accuracy Difference measures if the model performs equally well for both groups. "
                    f"Your difference is {acc_diff:.4f}. "
                    f"Values near 0 indicate equal overall performance.")
        
        if "bias" in q:
            return (f"Your model has a bias score of {score}/100 ({sev} severity). "
                    f"This measures how unfairly the model treats '{unpriv}' compared to '{priv}' "
                    f"across 6 fairness dimensions. A score of 0 means no bias; 100 means extreme bias.")

    # 🚨 SERIOUSNESS/LEGAL QUESTIONS
    if any(w in q for w in ["how bad","how serious","should i be worried","severe","legal","compliant","risk"]):
        impact = {
            "none": "No significant action is needed right now, but monitor regularly.",
            "low": "Minor bias exists. Review the recommendations as a precaution.",
            "medium": "This is a real problem. Implement the recommended fixes before deployment.",
            "high": "This is severe. Do not deploy this model without fixing it. Real people are being harmed."
        }
        
        legal_risk = ""
        if di and di < 0.8:
            legal_risk = f" Your Disparate Impact of {di:.3f} is below the 0.8 legal threshold, creating compliance risk."
        if spd and abs(spd) > 0.1:
            legal_risk += f" Your SPD of {spd:.3f} exceeds the ±0.1 industry standard."
        
        return (f"Your bias score is {score}/100 — classified as {sev.upper()} severity. "
                f"{impact.get(sev,'')}{legal_risk} "
                f"The biggest issue is that '{unpriv}' has a positive outcome rate of "
                f"{groups.get(str(unpriv),{}).get('positive_rate','?')} "
                f"compared to {groups.get(str(priv),{}).get('positive_rate','?')} for '{priv}'.")

    # 🔍 ROOT CAUSE ANALYSIS
    if any(w in q for w in ["why","cause","reason","feature","proxy","training data"]):
        if "feature" in q or "cause" in q:
            if proxies:
                top_proxy = max(proxies.items(), key=lambda x: x[1])
                return (f"The main bias drivers are: 1) Proxy features - '{top_proxy[0]}' "
                        f"has {top_proxy[1]:.3f} correlation with '{prot}'. "
                        f"2) Training data imbalance - '{unpriv}' has only "
                        f"{groups.get(str(unpriv),{}).get('positive_rate','?')} positive rate vs "
                        f"{groups.get(str(priv),{}).get('positive_rate','?')} for '{priv}'.")
            return (f"Primary bias sources: 1) Dataset imbalance between groups, "
                    f"2) Model learning patterns that disadvantage '{unpriv}', "
                    f"3) Potential historical bias in training data.")
        
        if "proxy" in q:
            if proxies:
                return (f"Proxy features detected: {', '.join([f'{k} (corr: {v:.3f})' for k,v in proxies.items()])}. "
                        f"These features correlate with '{prot}' and enable indirect discrimination. "
                        f"Consider removing or transforming them.")
            return "No significant proxy features detected in your model."

    # 🛠️ FIX RECOMMENDATIONS
    if any(w in q for w in ["fix","how to fix","what can i do","solution","recommendation","implement"]):
        if recs:
            r = recs[0]
            return (f"TOP PRIORITY FIX: {r.get('title')}\n\n"
                    f"Description: {r.get('description','')}\n"
                    f"Priority: {r.get('priority')} | Expected Impact: {r.get('impact')}\n\n"
                    f"Implementation: Go to the Fixes tab for detailed code examples. "
                    f"Total fixes available: {len(recs)}. "
                    f"Start with {r.get('priority')} priority items for maximum impact.")
        
        if "statistical parity" in q:
            return (f"To fix Statistical Parity Difference ({spd:.3f}): "
                    f"1) Reweight training samples to balance group representation, "
                    f"2) Apply fairness constraints during training, "
                    f"3) Adjust decision thresholds per group. "
                    f"Use the What-If Simulator to test these interventions.")
        
        if "disparate impact" in q:
            return (f"To fix Disparate Impact ({di:.3f}): "
                    f"1) Oversample underrepresented '{unpriv}' group, "
                    f"2) Remove proxy features correlated with '{prot}', "
                    f"3) Use fairness-aware algorithms. "
                    f"Target: get DI above 0.8 for legal compliance.")
        
        return "Check the Fixes tab for detailed technical recommendations with code examples."

    # 📊 BUSINESS COMMUNICATION
    if any(w in q for w in ["email","write","draft","letter","board","ceo","summary","presentation","explain to"]):
        if "ceo" in q or "board" in q:
            return (f"EXECUTIVE SUMMARY:\n\n"
                    f"• Bias Level: {sev.upper()} (Score: {score}/100)\n"
                    f"• Legal Risk: {'HIGH' if di and di < 0.8 else 'MODERATE' if abs(spd or 0) > 0.1 else 'LOW'}\n"
                    f"• Impact: '{unpriv}' group receives {groups.get(str(unpriv),{}).get('positive_rate','?')} positive outcomes "
                    f"vs {groups.get(str(priv),{}).get('positive_rate','?')} for '{priv}'\n"
                    f"• Action Required: Implement {len(recs)} technical fixes before deployment\n"
                    f"• Timeline: 2-4 weeks for remediation\n"
                    f"• Business Risk: Potential discrimination claims, regulatory penalties")
        
        if "presentation" in q or "slide" in q:
            return (f"PRESENTATION OUTLINE:\n\n"
                    f"Slide 1: FairLens Audit Results - {sev.upper()} Bias Detected\n"
                    f"Slide 2: Key Metrics - SPD: {spd:.3f}, DI: {di:.3f}, Bias Score: {score}/100\n"
                    f"Slide 3: Impact Analysis - Group comparison and affected population\n"
                    f"Slide 4: Root Causes - Data imbalance and proxy features\n"
                    f"Slide 5: Remediation Plan - {len(recs)} technical fixes prioritized\n"
                    f"Slide 6: Timeline and Resources - 2-4 week implementation plan")
        
        return (f"COMMUNICATION DRAFT:\n\n"
                f"Subject: AI Fairness Audit Results - {sev.upper()} Bias Detected\n\n"
                f"Our FairLens audit identified {sev} bias (score: {score}/100) in our AI model. "
                f"The model shows {spd:.3f} statistical parity difference and {di:.3f} disparate impact. "
                f"We've identified {len(recs)} specific technical fixes to address this. "
                f"Immediate action recommended before further deployment.")

    # 🧪 ADVANCED ANALYSIS
    if any(w in q for w in ["what if","scenario","compare","algorithm","random forest","logistic regression"]):
        if "what if" in q:
            return (f"Use the What-If Simulator to test interventions: "
                    f"1) Remove proxy features, 2) Reweight samples, 3) Adjust thresholds. "
                    f"The simulator shows real-time impact on all fairness metrics.")
        
        if "algorithm" in q or "model" in q:
            return (f"Algorithm comparison: Different models have different bias characteristics. "
                    f"Logistic regression is often more interpretable for bias analysis. "
                    f"Random forest may capture complex patterns but can be harder to debias. "
                    f"Consider fairness-aware algorithms like AIF360's methods.")
        
        if "compare" in q:
            return (f"Compare bias before/after fixes using the Results dashboard. "
                    f"Track changes in bias score, individual metrics, and group outcomes. "
                    f"The What-If Simulator provides side-by-side comparisons.")

    # 💡 CREATIVE/STRATEGIC
    if any(w in q for w in ["design","pipeline","monitor","prevent","best practice","teach","learn"]):
        if "pipeline" in q or "design" in q:
            return (f"FAIRNESS PIPELINE DESIGN:\n\n"
                    f"1. Data Collection: Ensure representative sampling\n"
                    f"2. Preprocessing: Remove bias, handle missing data fairly\n"
                    f"3. Model Training: Use fairness-aware algorithms\n"
                    f"4. Validation: Test multiple fairness metrics\n"
                    f"5. Deployment: Monitor for drift and bias\n"
                    f"6. Iteration: Continuous improvement cycle")
        
        if "monitor" in q:
            return (f"MONITORING PLAN:\n\n"
                    f"• Daily: Track key metrics (SPD, DI, accuracy)\n"
                    f"• Weekly: Review group outcome distributions\n"
                    f"• Monthly: Full fairness audit with FairLens\n"
                    f"• Quarterly: Model retraining with updated data\n"
                    f"• Alerts: Trigger when bias score increases >10 points")
        
        if "teach" in q or "learn" in q:
            return (f"ALGORITHMIC FAIRNESS FUNDAMENTALS:\n\n"
                    f"• Fairness is multidimensional - no single metric captures it all\n"
                    f"• Trade-offs exist between accuracy and fairness\n"
                    f"• Context matters - different applications need different fairness definitions\n"
                    f"• Continuous monitoring is essential\n"
                    f"• Transparency and explainability build trust")

    # Default response
    return (f"Your bias audit shows a score of {score}/100 ({sev} severity). "
            f"Key metrics: SPD={spd:.3f}, DI={di:.3f}. "
            f"The model treats '{unpriv}' less favorably than '{priv}' across multiple fairness metrics. "
            f"You can ask me about specific metrics, root causes, fixes, legal implications, "
            f"or help drafting communications for stakeholders.")


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
