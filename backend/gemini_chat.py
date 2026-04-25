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
    Rule-based fallback when Gemini API is unavailable.
    Answers common questions using the audit data directly.
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
        if "bias" in q:
            return (f"Your model has a bias score of {score}/100 ({sev} severity). "
                    f"This measures how unfairly the model treats '{unpriv}' compared to '{priv}' "
                    f"across 6 fairness dimensions. A score of 0 means no bias; 100 means extreme bias.")

    if any(w in q for w in ["how bad","how serious","should i be worried","severe"]):
        impact = {
            "none": "No significant action is needed right now, but monitor regularly.",
            "low": "Minor bias exists. Review the recommendations as a precaution.",
            "medium": "This is a real problem. Implement the recommended fixes before deployment.",
            "high": "This is severe. Do not deploy this model without fixing it. Real people are being harmed."
        }
        return (f"Your bias score is {score}/100 — classified as {sev.upper()} severity. "
                f"{impact.get(sev,'')} "
                f"The biggest issue is that '{unpriv}' has a positive outcome rate of "
                f"{groups.get(str(unpriv),{}).get('positive_rate','?')} "
                f"compared to {groups.get(str(priv),{}).get('positive_rate','?')} for '{priv}'.")

    if any(w in q for w in ["fix","how to fix","what can i do","solution","recommendation"]):
        if recs:
            r = recs[0]
            return (f"The top recommendation is: {r.get('title')}. "
                    f"{r.get('description','')} "
                    f"This is a {r.get('priority')} priority fix with {r.get('impact')} expected impact. "
                    f"Go to the Fixes tab to see all {len(recs)} recommendations with code examples.")
        return "Check the Fixes tab for detailed recommendations."

    if "proxy" in q:
        if proxies:
            top = list(proxies.items())[0]
            return (f"A proxy feature is one that's correlated with the protected attribute — "
                    f"meaning the model can discriminate indirectly even if you remove '{prot}' directly. "
                    f"Your top proxy is '{top[0]}' with a correlation of {top[1]:.3f}. "
                    f"This means the model is effectively using '{prot}' information through this feature.")
        return (f"No significant proxy features were detected. "
                f"This means the model isn't using indirect proxies for '{prot}'.")

    if any(w in q for w in ["email","write","draft","letter","board","ceo","explain to"]):
        return (f"Here is a draft you can adapt:\n\n"
                f"Subject: AI Fairness Audit Results — Action Required\n\n"
                f"Our recent FairLens bias audit of our AI system has identified a {sev} level of bias "
                f"(score: {score}/100). The model shows statistically significant differences in outcomes "
                f"between '{priv}' and '{unpriv}' groups, with a Statistical Parity Difference of {spd:.4f}. "
                f"We have identified {len(recs)} specific technical interventions that can address this. "
                f"We recommend implementing these fixes before further deployment to avoid legal and ethical risks.")

    # Default
    return (f"Your bias audit shows a score of {score}/100 ({sev} severity). "
            f"The model treats '{unpriv}' less favourably than '{priv}' across multiple fairness metrics. "
            f"You can ask me to explain any specific metric, how to fix the bias, "
            f"or to draft a report for your team.")


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
