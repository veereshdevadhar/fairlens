"""
FairLens – Fairness Certificate Generator
Produces a signed, timestamped, shareable HTML certificate.
"""
from datetime import datetime
import hashlib
import json


SEV_COLOR = {
    "none":   ("#2E7D32", "#E8F5E9", "CERTIFIED FAIR"),
    "low":    ("#F9A825", "#FFFDE7", "MINOR BIAS DETECTED"),
    "medium": ("#E65100", "#FFF3E0", "BIAS REQUIRES ACTION"),
    "high":   ("#C62828", "#FFEBEE", "HIGH BIAS — NOT CERTIFIED"),
}


def _cert_id(dataset_name: str, score: float, timestamp: str) -> str:
    raw = f"{dataset_name}{score}{timestamp}"
    return "FL-" + hashlib.sha256(raw.encode()).hexdigest()[:12].upper()


def generate_certificate(
    dataset_name: str,
    protected_col: str,
    privileged_group: str,
    unprivileged_group: str,
    metrics_result: dict,
    recommendations: list,
    organization_name: str = "Your Organization",
) -> str:
    """Returns the certificate as a self-contained HTML string."""
    overall    = metrics_result.get("overall", {})
    metrics    = metrics_result.get("metrics", {})
    groups     = metrics_result.get("group_stats", {})
    score      = overall.get("bias_score", 0)
    severity   = overall.get("severity", "high")
    accuracy   = overall.get("model_accuracy", 0)
    total_rows = overall.get("total_rows", 0)

    now       = datetime.now()
    ts        = now.strftime("%B %d, %Y at %H:%M UTC")
    ts_short  = now.strftime("%Y-%m-%d")
    cert_id   = _cert_id(dataset_name, score, ts)

    col, bg, status_text = SEV_COLOR.get(severity, SEV_COLOR["high"])
    is_certified = severity in ("none", "low")

    # Metrics table rows
    metric_rows = ""
    metric_labels = {
        "statistical_parity_difference":    "Statistical Parity Difference",
        "disparate_impact":                 "Disparate Impact Ratio",
        "equalized_odds_difference_tpr":    "Equalized Odds (TPR)",
        "equalized_odds_difference_fpr":    "Equalized Odds (FPR)",
        "predictive_parity_difference":     "Predictive Parity",
        "accuracy_difference":              "Accuracy Difference",
    }
    for key, label in metric_labels.items():
        m     = metrics.get(key, {})
        val   = m.get("value")
        sev   = m.get("severity", "none")
        ideal = m.get("ideal", 0)
        sc    = {"none":"#2E7D32","low":"#F9A825","medium":"#E65100","high":"#C62828"}.get(sev,"#777")
        val_s = f"{val:.4f}" if val is not None else "N/A"
        metric_rows += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #eee;font-size:13px">{label}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #eee;font-weight:700;color:{sc};font-size:13px">{val_s}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #eee;font-size:12px;color:#777">{ideal}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #eee">
            <span style="background:{sc}22;color:{sc};font-size:10px;font-weight:700;padding:2px 8px;border-radius:999px">{sev.upper()}</span>
          </td>
        </tr>"""

    # Group rows
    group_rows = ""
    for gname, gdata in groups.items():
        is_p = gname == str(privileged_group)
        tag  = "PRIVILEGED" if is_p else "UNPRIVILEGED"
        tc   = "#1565C0" if is_p else "#E65100"
        group_rows += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #eee;font-size:13px">
            {gname}
            <span style="background:{tc}22;color:{tc};font-size:9px;font-weight:700;padding:2px 7px;border-radius:999px;margin-left:6px">{tag}</span>
          </td>
          <td style="padding:8px 12px;border-bottom:1px solid #eee;font-size:13px">{gdata.get('count','?')}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #eee;font-size:13px">{float(gdata.get('positive_rate',0))*100:.2f}%</td>
          <td style="padding:8px 12px;border-bottom:1px solid #eee;font-size:13px">{float(gdata.get('model_accuracy',0))*100:.2f}%</td>
          <td style="padding:8px 12px;border-bottom:1px solid #eee;font-size:13px">{float(gdata.get('true_positive_rate',0))*100:.2f}%</td>
          <td style="padding:8px 12px;border-bottom:1px solid #eee;font-size:13px">{float(gdata.get('false_positive_rate',0))*100:.2f}%</td>
        </tr>"""

    stamp_icon = "✓" if is_certified else "⚠"
    badge_border = f"4px solid {col}"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FairLens Fairness Certificate — {dataset_name}</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'DM Sans',sans-serif;background:#F8FAFE;color:#1A1A2E;min-height:100vh}}
  .page{{max-width:860px;margin:0 auto;padding:40px 24px}}
  .cert{{background:#fff;border-radius:20px;box-shadow:0 8px 48px rgba(0,0,0,0.10);overflow:hidden}}
  .cert-header{{background:linear-gradient(135deg,#0D1B6E,#1565C0);padding:48px 48px 36px;text-align:center}}
  .cert-logo{{font-family:Syne,sans-serif;font-size:28px;font-weight:800;color:#fff;margin-bottom:6px}}
  .cert-logo span{{color:#7AB3FF}}
  .cert-tagline{{font-size:13px;color:#90CAF9;letter-spacing:0.08em;text-transform:uppercase}}
  .cert-body{{padding:40px 48px}}
  .badge{{display:inline-flex;flex-direction:column;align-items:center;justify-content:center;
    width:140px;height:140px;border-radius:50%;border:{badge_border};
    background:{bg};margin:0 auto 28px;display:flex}}
  .badge-icon{{font-size:44px;color:{col};line-height:1}}
  .badge-score{{font-family:Syne,sans-serif;font-size:28px;font-weight:800;color:{col}}}
  .badge-label{{font-size:11px;font-weight:600;color:{col};letter-spacing:0.06em;text-transform:uppercase}}
  .status-banner{{background:{bg};border:2px solid {col};border-radius:12px;
    padding:14px 24px;text-align:center;margin-bottom:28px}}
  .status-text{{font-family:Syne,sans-serif;font-size:18px;font-weight:800;color:{col}}}
  .cert-meta{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:32px}}
  .meta-card{{background:#F8FAFE;border-radius:10px;padding:14px;text-align:center}}
  .meta-val{{font-family:Syne,sans-serif;font-size:20px;font-weight:700;color:#1565C0}}
  .meta-label{{font-size:11px;color:#777;text-transform:uppercase;letter-spacing:0.06em;margin-top:4px}}
  .section{{margin-bottom:32px}}
  .section-title{{font-family:Syne,sans-serif;font-size:15px;font-weight:700;
    color:#1565C0;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:14px;
    padding-bottom:8px;border-bottom:2px solid #E3F2FD}}
  table{{width:100%;border-collapse:collapse;font-size:13px}}
  th{{background:#F8FAFE;padding:8px 12px;text-align:left;font-size:11px;
      font-weight:700;color:#777;text-transform:uppercase;letter-spacing:0.06em;
      border-bottom:2px solid #E3F2FD}}
  .cert-footer{{background:#F8FAFE;border-top:1px solid #E3F2FD;padding:24px 48px;
    display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}}
  .cert-id{{font-size:12px;color:#777}}
  .cert-id strong{{color:#333}}
  .watermark{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%) rotate(-30deg);
    font-family:Syne,sans-serif;font-size:80px;font-weight:800;
    color:rgba(21,101,192,0.04);pointer-events:none;white-space:nowrap}}
  @media print{{
    body{{background:#fff}}
    .page{{padding:0}}
    .cert{{box-shadow:none}}
  }}
  @media(max-width:600px){{
    .cert-body{{padding:24px}}
    .cert-meta{{grid-template-columns:1fr 1fr}}
    .cert-footer{{flex-direction:column;text-align:center}}
  }}
</style>
</head>
<body>
<div class="page">
<div class="cert" style="position:relative">
  <div class="watermark">FAIRLENS</div>

  <!-- Header -->
  <div class="cert-header">
    <div class="cert-logo">⚖ Fair<span>Lens</span></div>
    <div class="cert-tagline">AI Bias Audit Certificate · Google Solution Challenge 2026</div>
  </div>

  <!-- Body -->
  <div class="cert-body">

    <!-- Badge + Status -->
    <div style="text-align:center;margin-bottom:28px">
      <div class="badge" style="margin:0 auto 20px">
        <div class="badge-icon">{stamp_icon}</div>
        <div class="badge-score">{score:.0f}</div>
        <div class="badge-label">Bias Score</div>
      </div>
      <div class="status-banner">
        <div class="status-text">{status_text}</div>
      </div>
      <p style="font-size:14px;color:#555;margin-top:12px">
        This certifies that the AI system described below was audited by FairLens on {ts}.
      </p>
    </div>

    <!-- Meta grid -->
    <div class="cert-meta">
      <div class="meta-card">
        <div class="meta-val">{dataset_name[:18]}</div>
        <div class="meta-label">Dataset Audited</div>
      </div>
      <div class="meta-card">
        <div class="meta-val">{protected_col}</div>
        <div class="meta-label">Protected Attribute</div>
      </div>
      <div class="meta-card">
        <div class="meta-val">{accuracy*100:.1f}%</div>
        <div class="meta-label">Model Accuracy</div>
      </div>
      <div class="meta-card">
        <div class="meta-val">{total_rows:,}</div>
        <div class="meta-label">Records Audited</div>
      </div>
      <div class="meta-card">
        <div class="meta-val">{privileged_group}</div>
        <div class="meta-label">Privileged Group</div>
      </div>
      <div class="meta-card">
        <div class="meta-val">{unprivileged_group}</div>
        <div class="meta-label">Unprivileged Group</div>
      </div>
    </div>

    <!-- Fairness Metrics -->
    <div class="section">
      <div class="section-title">Fairness Metrics</div>
      <table>
        <thead>
          <tr>
            <th>Metric</th><th>Value</th><th>Ideal</th><th>Status</th>
          </tr>
        </thead>
        <tbody>{metric_rows}</tbody>
      </table>
    </div>

    <!-- Group Statistics -->
    <div class="section">
      <div class="section-title">Group-Level Results</div>
      <table>
        <thead>
          <tr>
            <th>Group</th><th>Sample Size</th>
            <th>Positive Rate</th><th>Accuracy</th>
            <th>TPR</th><th>FPR</th>
          </tr>
        </thead>
        <tbody>{group_rows}</tbody>
      </table>
    </div>

    <!-- Recommendations summary -->
    <div class="section">
      <div class="section-title">Recommendations ({len(recommendations)} identified)</div>
      {"".join(f'<div style="display:flex;gap:10px;align-items:center;padding:8px 0;border-bottom:1px solid #eee"><span style="background:{"#C62828" if r.get("priority")=="high" else "#E65100" if r.get("priority")=="medium" else "#2E7D32"}22;color:{"#C62828" if r.get("priority")=="high" else "#E65100" if r.get("priority")=="medium" else "#2E7D32"};font-size:10px;font-weight:700;padding:3px 10px;border-radius:999px;white-space:nowrap">{r.get("priority","").upper()}</span><span style="font-size:13px">{r.get("title","")}</span></div>' for r in recommendations)}
    </div>

    <!-- Org name -->
    <div style="background:#E3F2FD;border-radius:10px;padding:14px 18px;margin-top:8px">
      <span style="font-size:13px;color:#1565C0">
        <strong>Audited for:</strong> {organization_name} &nbsp;·&nbsp;
        <strong>Audit date:</strong> {ts_short} &nbsp;·&nbsp;
        <strong>Certificate ID:</strong> {cert_id}
      </span>
    </div>
  </div>

  <!-- Footer -->
  <div class="cert-footer">
    <div class="cert-id">
      <strong>Certificate ID:</strong> {cert_id}<br>
      <span>Generated by FairLens v1.0 · {ts}</span>
    </div>
    <div style="font-size:12px;color:#aaa;text-align:right">
      Built for Google Solution Challenge 2026<br>
      Theme: Unbiased AI Decision
    </div>
  </div>
</div>
</div>
</body>
</html>"""
    return html
