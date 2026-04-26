# RCM Intelligence Platform

End-to-end Healthcare Revenue Cycle Management platform built on Databricks Free Edition using real CMS Medicare data. Identifies **$343.54B** in national revenue leakage across **2,945 hospitals** and predicts claim denial risk before submission using machine learning.

---

## The Problem

**$262B is lost annually** across US hospitals from claim denials and underpayments. Hospital billing teams submit claims blind — no visibility into which claims are likely to get denied until after Medicare rejects them. This platform changes that.

---

## Architecture

```
CMS Medicare API → Bronze → Silver → Gold → ML → Dashboard → Streamlit App
```

| Layer | Description |
|---|---|
| Bronze | Raw ingestion from CMS Inpatient API and Hospital CSV |
| Silver | Type casting, 11 RCM features engineered, SCD Type 1/2 dimensions |
| Gold | Star schema fact table, KPI aggregations, AR aging, hospital scorecard |
| ML | Gradient Boosting denial risk model tracked in MLflow |
| Dashboard | Databricks AI/BI dashboard + Genie natural language interface |
| App | 4-page Streamlit app deployed on Databricks Apps |

---

## Data

- **Source:** CMS Medicare public data — real data, no authentication required
- **Scale:** 146,426 claims · 2,945 hospitals · 51 states · 534 DRG codes
- **Pipeline:** Automated via Databricks Workflows — weekly data refresh, monthly model retrain

---

## Key Findings

- **$343.54B** total Medicare revenue gap identified nationally
- **$162B** sitting in 90+ day AR bucket — at risk of never being collected
- **39.04%** of all claims are underpaid relative to DRG benchmarks
- **DRG 871** (Septicemia) alone accounts for **$38.15B** in revenue gap
- **385 hospitals** graded F-Critical — severe revenue cycle dysfunction
- **DC** has the highest state underpayment rate at **69.58%**
- Urban Core hospitals: **40.61%** underpayment vs Small Rural: **18.58%**

---

## ML Model

| Metric | Value |
|---|---|
| Algorithm | Gradient Boosting Classifier |
| Target | Claim underpayment flag — predicted pre-submission using 16 features |
| AUC-ROC | 0.8775 |
| Recall | 78.3% |
| Precision | 71.6% |
| CV AUC | 0.8736 ± 0.0003 — stable, no overfitting |

Registered in MLflow Model Registry · 146,426 claims batch scored.

---

## App

Four interactive pages built in Streamlit and deployed on Databricks Apps:

### Executive Overview
National portfolio intelligence — KPI brief, revenue gap choropleth (click any state to drill down), AR aging, hospital grade distribution, denial risk distribution, and top recovery opportunities with one-click Hospital 360 navigation.

### Hospital 360
Search any of 2,945 hospitals for a complete RCM scorecard — financial exposure, CMS program risk (HRRP, penalties, 30-day mortality), patient experience (HCAHPS), denial risk gauge, national percentile radar chart, and DRG breakdown. Includes PDF intelligence brief export.

### Claim Risk Scorer
Select a hospital and DRG, get a real-time ML denial risk prediction with recommendation. Pre-submission triage tool for billing teams.

### State Intelligence
State-level peer benchmarking — interactive scatter chart (click any hospital to open its 360 profile), grade-colored hospital scorecard table, denial risk by hospital, and top DRGs by revenue leakage.

---

## Tech Stack

Databricks Free Edition · Delta Lake · Unity Catalog · PySpark · MLflow · Streamlit · Plotly · Databricks SQL · Databricks Workflows · Databricks Apps · Python 3.11

---

## Author

**Mayank Joshi** · University of Southern California

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?style=flat&logo=linkedin)](https://www.linkedin.com/in/jmayank574)
