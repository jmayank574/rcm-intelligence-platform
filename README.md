# RCM Intelligence Platform

End-to-end Healthcare Revenue Cycle Management platform built on Databricks Free Edition using real CMS Medicare data. Analyzes **2,945 hospitals** across **51 states** and predicts claim denial risk before submission using machine learning.

---

## The Problem

Hospitals lose billions annually to claim denials and underpayments. Billing teams submit claims blind — no visibility into which claims are likely to get denied until after Medicare rejects them. This platform changes that.

---

## Architecture

```
CMS Medicare API → Bronze → Silver → Gold → ML → Dashboard → Streamlit App
```

| Layer | Description |
|---|---|
| Bronze | Raw ingestion from CMS Medicare API — inpatient, outpatient, and HCAHPS datasets |
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

**What's measured per hospital:**

| Category | Metrics |
|---|---|
| Inpatient | Discharges, charge-to-payment ratio, revenue gap, underpayment rate |
| Outpatient | Beneficiaries, charge-to-payment ratio, revenue gap, underpayment rate |
| Patient Experience (HCAHPS) | Overall star rating, nurse/doctor/cleanliness/quietness scores, % recommend |
| CMS Quality | 30-day mortality (HF, PN, AMI, Stroke), HRRP readmission ratios (6 conditions) |
| CMS Penalties | HRRP penalty flags, PSI-90 patient safety score, total penalty count |
| Denial Risk | ML-scored claims — high / medium / low risk with pre-submission recommendation |

---

## ML Model

| Metric | Value |
|---|---|
| Algorithm | Gradient Boosting Classifier |
| Target | Claim denial risk — predicted pre-submission using 16 features |
| AUC-ROC | 0.8775 |
| Recall | 78.3% |
| Precision | 71.6% |
| CV AUC | 0.8736 ± 0.0003 — stable, no overfitting |

Registered in MLflow Model Registry · 146,426 claims batch scored.

---

## App

Four interactive pages built in Streamlit and deployed on Databricks Apps:

### Executive Overview
National portfolio intelligence — revenue gap by state (clickable choropleth), AR aging, hospital grade distribution, denial risk distribution, and top recovery opportunities with one-click Hospital 360 navigation.

### Hospital 360
Full hospital profile — inpatient and outpatient financials, HCAHPS patient experience scores, 30-day mortality rates, HRRP readmission ratios, CMS penalty exposure, denial risk gauge, national percentile radar chart, and DRG breakdown. Includes PDF intelligence brief export.

### Claim Risk Scorer
Select a hospital and DRG, get a real-time ML denial risk score with explanation of why the claim is at risk and a pre-submission recommendation.

### State Intelligence
State-level peer benchmarking — interactive scatter chart (click any hospital to open its 360 profile), grade-colored hospital scorecard table, denial risk by hospital, and top DRGs by revenue leakage.

---

## Tech Stack

Databricks Free Edition · Delta Lake · Unity Catalog · PySpark · MLflow · Streamlit · Plotly · Databricks SQL · Databricks Workflows · Databricks Apps · Python 3.11

---

## Author

**Mayank Joshi** · University of Southern California

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?style=flat&logo=linkedin)](https://www.linkedin.com/in/jmayank574)
