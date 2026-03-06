# Test Data & Sample Questions for Workflow Testing

This directory contains **CSV datasets** and **copy-paste-ready sample questions** for testing
all coding workflows, domain-specific multi-agent workflows, and the Data Analyst persona.
Every prompt is designed to exercise the full pipeline and produce **charts (PNG)**, **tables**,
and **insight reports**.

> **Workflow IDs** are assigned at creation time and may differ on your server.
> Check your server's `/api/admin/workflow` endpoint for current IDs.

---

## Domain-Specific Multi-Agent Workflows (6 New)

These workflows feature 9-10 specialist agents per workflow, dynamic LLM-based routing,
HITL (Human-in-the-Loop) pause/resume, PythonTool data analysis, and guard rail validation
(verifying correct specialists called AND wrong specialists NOT called).

| # | Workflow | JSON | Test Suite | Test Data | Agents |
|---|---------|------|------------|-----------|--------|
| 22 | Medical Diagnosis Panel | `22_medical_diagnosis.json` | `test_medical_diagnosis.py` | `patients/{P1,P2,P3}` | 10 |
| 23 | Financial Crime Investigation | `23_financial_crime.json` | `test_financial_crime.py` | `financial_crime/{C1,C2,C3}` | 9 |
| 24 | Engineering Failure Analysis | `24_engineering_failure.json` | `test_engineering_failure.py` | `engineering_failure/{F1,F2,F3}` | 10 |
| 25 | Cybersecurity Incident Response | `25_cybersecurity_ir.json` | `test_cybersecurity_ir.py` | `cybersecurity/{I1,I2,I3}` | 9 |
| 26 | Insurance Claims Investigation | `26_insurance_claims.json` | `test_insurance_claims.py` | `insurance_claims/{CL1,CL2,CL3}` | 9 |
| 27 | M&A Due Diligence | `27_mna_due_diligence.json` | `test_mna_due_diligence.py` | `mna_due_diligence/{D1,D2,D3}` | 10 |
| 28 | Drug Development Pipeline | `28_drug_development.json` | `test_drug_development.py` | `drug_development/{RX1,RX2,RX3}` | 10 |

### Test Data Structure
All test data is **CSV format** (compatible with UI file upload). Each case has a folder
with multiple CSVs representing different data sources (e.g., lab panels, financial statements,
network logs). See individual test suite files for case details.

### Guard Rail Validation
Each test validates that the **correct specialists** were called AND **wrong specialists**
were NOT called. For example, in Medical Diagnosis P1 (autoimmune case), the test verifies
Endocrinologist + Rheumatologist were called but Cardiologist + Gastroenterologist were NOT.

### Running Domain Workflow Tests
```bash
# Deploy a workflow
python create_workflows.py --file workflows/22_medical_diagnosis.json

# Run a specific test suite
python test_medical_diagnosis.py
python test_financial_crime.py
python test_engineering_failure.py
python test_cybersecurity_ir.py
python test_insurance_claims.py
python test_mna_due_diligence.py
python test_drug_development.py

# With custom server
python test_medical_diagnosis.py --url http://myserver:3000 --key MY_API_KEY
```

---

## Datasets in this directory

| File | Rows | Columns | Domain | Used by |
|------|------|---------|--------|---------|
| `sales_quarterly.csv` | 108 | 7 | Revenue by product/region | Data Analysis Pipeline |
| `employee_attrition.csv` | 40 | 16 | HR attrition factors | Data Analysis Pipeline |
| `ecommerce_funnel.csv` | 45 | 10 | Conversion funnel by channel | Data Analysis Pipeline |
| `manufacturing_quality.csv` | 40 | 11 | Factory QC defect tracking | Data Analysis Pipeline |
| `housing_prices.csv` | 30 | 12 | Seattle house prices | ML Model Prototyper |
| `customer_churn.csv` | 30 | 17 | Telecom churn prediction | ML Model Prototyper |
| `credit_card_fraud_sample.csv` | 40 | 12 | Fraud detection (imbalanced) | ML Model Prototyper |
| `student_performance.csv` | 40 | 12 | Exam score prediction | ML Model Prototyper |

---

## 1. Automated Data Analysis Pipeline

**Workflow file:** `workflows/17_data_analysis_pipeline.json`
**Agents:** Data Intake → Data Profiler → Analysis Engine → Visualization Generator → Insight Report Writer
**Produces:** Statistical tables, 3-5 PNG charts, business insight report

### Q1 — Sales revenue analysis (generates trend + bar + heatmap charts)
```
Analyze our company revenue data: CSV with columns date, product_line (Enterprise/SMB/Consumer),
region (North America/Europe/APAC), revenue, units_sold, discount_pct, customer_segment.
12 months of data (Jan-Dec 2023), 108 rows.
I want to know:
1) Which product lines are growing fastest? Show month-over-month growth rates
2) Regional performance comparison — rank regions by total revenue and growth rate
3) Impact of discounts on revenue — scatter plot of discount_pct vs units_sold with correlation
4) Seasonal patterns — compare Q4 vs Q1 revenue and identify the peak month
```

### Q2 — Employee attrition deep-dive (generates correlation heatmap + grouped bars)
```
Employee HR data: columns employee_id, department (Sales/Engineering/HR/Marketing),
job_role, age, gender, education, monthly_income, years_at_company, years_since_promotion,
overtime (Yes/No), job_satisfaction (1-4), work_life_balance (1-4), performance_rating (2-4),
distance_from_home_km, num_companies_worked, attrition (Yes/No). 40 employees.
Analysis goals:
1) Top 5 factors most correlated with attrition — show correlation chart
2) Attrition rate by department — which department loses the most people?
3) Overtime vs attrition — compare attrition rates for overtime=Yes vs No
4) Salary distribution for stayed vs left employees — box plot comparison
```

### Q3 — E-commerce conversion funnel (generates funnel + device comparison charts)
```
E-commerce funnel data: columns date, traffic_source (Organic/Paid/Social/Email/Direct),
device_type (Desktop/Mobile/Tablet), sessions, product_views, add_to_cart, checkouts,
purchases, revenue, avg_order_value. 4 months of bi-weekly data, ~45 rows.
Analysis objectives:
1) Conversion rate by traffic source — sessions to purchases, show as funnel or bar chart
2) Desktop vs Mobile vs Tablet — compare conversion rates and average order value
3) Revenue per session by traffic source — identify highest ROI channel
4) Monthly trend — is overall conversion improving or declining over the 4 months?
```

### Q4 — Manufacturing quality control (generates scatter + shift comparison charts)
```
Manufacturing quality data: columns batch_id, production_line (A/B/C), shift (Day/Night),
operator_id, temperature_celsius (170-186), pressure_bar (3.2-4.5), humidity_pct (42-64),
cycle_time_seconds, defect_count, defect_type (None/Cosmetic/Structural/Functional),
pass_fail (Pass/Fail). 40 batches.
Analysis objectives:
1) Defect rate by production line — bar chart showing fail % per line
2) Day shift vs Night shift — compare average defect counts with statistical significance
3) Temperature and pressure sweet spots — scatter plot of temp vs defect_count, color by pass/fail
4) Top 3 operators by quality (lowest defect rate) and bottom 3 (highest defect rate)
```

### Q5 — SaaS subscription metrics (no CSV — agents generate data)
```
SaaS subscription analytics: columns month (Jan 2023 - Dec 2024), plan_tier
(Free/Starter/Professional/Enterprise), new_signups, churned_customers,
active_users, monthly_recurring_revenue, average_revenue_per_user, support_tickets,
NPS_score (0-100), feature_adoption_pct. 24 months, ~96 rows (4 tiers x 24 months).
Analysis objectives:
1) MRR growth trend by tier — stacked area chart showing revenue composition over time
2) Churn rate by plan tier — which tier has the worst retention?
3) Correlation between NPS score and churn — scatter with trend line
4) Revenue concentration risk — what % of total MRR comes from Enterprise tier?
```

### Q6 — Hospital patient flow (no CSV — agents generate data)
```
Hospital operations data: columns date, department (Emergency/ICU/Surgery/General/Pediatrics),
admissions, discharges, bed_occupancy_pct, avg_length_of_stay_days, readmission_count,
staff_on_duty, patient_satisfaction_score (1-10), wait_time_minutes. 12 months of daily
data, ~1800 rows.
Analysis objectives:
1) Bed occupancy trends — line chart by department, highlight overcapacity (>90%)
2) Average wait times by department — which departments have the longest waits?
3) Readmission rates vs staff levels — is understaffing causing readmissions?
4) Seasonal admission patterns — are there monthly spikes (winter flu, summer injuries)?
```

---

## 2. Code Debug & Fix Assistant

**Workflow file:** `workflows/18_code_debug_fix.json`
**Agents:** Bug Intake → Reproducer & Diagnoser → Fix Generator → Test Writer → PR Summary
**Produces:** Bug reproduction output, fixed code with diff, test suite results, PR summary

### Q1 — Sorting with duplicates (TypeError on unhashable types)
```
Bug Report:

Function: custom_sort_and_deduplicate

Code:
def custom_sort_and_deduplicate(items, key=None):
    seen = set()
    result = []
    for item in sorted(items, key=key):
        val = key(item) if key else item
        if val not in seen:
            seen.add(val)
            result.append(item)
    return result

Error: When key=None and items contain dicts, crashes with TypeError: unhashable type.

Test case:
data = [{'name': 'Alice', 'score': 90}, {'name': 'Bob', 'score': 85}, {'name': 'Alice', 'score': 90}]
result = custom_sort_and_deduplicate(data, key=lambda x: x['name'])
# Expected: [{'name': 'Alice', 'score': 90}, {'name': 'Bob', 'score': 85}]
# Actual: TypeError
```

### Q2 — CSV parser off-by-one (header included in data)
```
Bug Report:

Two functions with related bugs:

def parse_csv_with_headers(csv_text):
    lines = csv_text.strip().split('\n')
    headers = lines[0].split(',')
    records = []
    for i in range(len(lines)):
        values = lines[i].split(',')
        record = {}
        for j in range(len(headers)):
            record[headers[j]] = values[j] if j < len(values) else ''
        records.append(record)
    return records

def calculate_column_stats(records, column):
    values = [float(r[column]) for r in records]
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return {'mean': mean, 'std': variance ** 0.5, 'count': len(values)}

Bug 1: parse_csv_with_headers includes header row as data (loop starts at i=0 not i=1)
Bug 2: calculate_column_stats crashes trying to float('salary') because of bug 1

Test: csv_data = 'name,age,salary\nAlice,30,75000\nBob,25,65000\nCharlie,35,85000'
Expected stats: {'mean': 75000.0, 'std': 8164.97, 'count': 3}
Actual: ValueError: could not convert string to float: 'salary'
```

### Q3 — Shopping cart bulk discount (logic error)
```
Bug in e-commerce cart. apply_bulk_discount should give 15% off when customer buys
3+ of the SAME item, but it checks total cart quantity instead.

Code:
def apply_bulk_discount(cart_items, min_qty=3, discount=0.15):
    total_qty = sum(item['quantity'] for item in cart_items)
    if total_qty >= min_qty:
        for item in cart_items:
            item['price'] = round(item['price'] * (1 - discount), 2)
    return cart_items

Test that fails:
cart = [
    {'name': 'Widget', 'price': 25.00, 'quantity': 1},
    {'name': 'Gadget', 'price': 50.00, 'quantity': 1},
    {'name': 'Doohickey', 'price': 10.00, 'quantity': 1}
]
result = apply_bulk_discount(cart)
# Expected: No discount (no single item has qty >= 3)
# Actual: All items get 15% off because total_qty=3

Also test: cart with Widget qty=5 should discount only Widget.
```

### Q4 — Recursive flatten ignores max_depth
```
Nested data flattener ignores max_depth — always fully flattens.

Code:
def flatten(data, max_depth=None, _current_depth=0):
    result = []
    for item in data:
        if isinstance(item, (list, tuple)):
            result.extend(flatten(item, max_depth, _current_depth))
        else:
            result.append(item)
    return result

Tests:
nested = [1, [2, [3, [4, [5]]]]]
flatten(nested, max_depth=1)    # Expected: [1, 2, [3, [4, [5]]]]
flatten(nested, max_depth=2)    # Expected: [1, 2, 3, [4, [5]]]
flatten(nested, max_depth=None) # Expected: [1, 2, 3, 4, 5]
# Actual: always returns [1, 2, 3, 4, 5] regardless of max_depth

Bugs: _current_depth never incremented, max_depth never checked.
```

### Q5 — Rate limiter timestamp bug
```
Token bucket rate limiter never updates last_check, so tokens accumulate incorrectly.

Code:
import time

class RateLimiter:
    def __init__(self, max_tokens=10, refill_rate=1.0):
        self.max_tokens = max_tokens
        self.tokens = max_tokens
        self.refill_rate = refill_rate
        self.last_check = time.time()

    def allow(self):
        now = time.time()
        self.tokens += self.refill_rate * (now - self.last_check)
        if self.tokens > self.max_tokens:
            self.tokens = self.max_tokens
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False

Bug: last_check is never updated after refill calculation.
After draining all 10 tokens, wait 5 seconds — should have ~5 tokens.
But second call to allow() recalculates from original init time, giving wrong count.

Expected behavior: Each call updates last_check = now after computing refill.
```

### Q6 — Matrix transpose with non-square input
```
Matrix transpose function fails on non-square matrices.

Code:
def transpose(matrix):
    n = len(matrix)
    result = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            result[j][i] = matrix[i][j]
    return result

Test:
m = [[1, 2, 3], [4, 5, 6]]  # 2x3 matrix
transpose(m)
# Expected: [[1, 4], [2, 5], [3, 6]]  (3x2 matrix)
# Actual: IndexError because result is 2x2, not 3x2

Bug: Uses len(matrix) for both dimensions instead of rows and cols separately.
Also fails on empty matrix: transpose([]) should return [].
```

---

## 3. ML Model Rapid Prototyper

**Workflow file:** `workflows/19_ml_model_prototyper.json`
**Agents:** Requirements Collector → Data Preprocessor → Feature Engineer → Model Trainer → Reporter
**Produces:** Preprocessing report, feature importance, model comparison table, charts, deployment report

### Q1 — House price regression (generates scatter + feature importance charts)
```
Build a regression model to predict house sale prices.
Features: bedrooms, bathrooms, sqft_living, sqft_lot, floors, waterfront (0/1),
view_score (0-4), condition (1-5), grade (1-13), year_built, zipcode.
Target: sale_price. Dataset: 30 houses from Seattle area.
Price range $245K to $3.2M. Waterfront homes are 2-3x more expensive.
Grade and sqft_living are the strongest predictors.
Train: Linear Regression, Random Forest, Gradient Boosting.
Report RMSE, MAE, R-squared for each.
Generate: predicted vs actual scatter plot AND feature importance bar chart.
```

### Q2 — Telecom churn classification (generates ROC + importance charts)
```
Build a classification model to predict customer churn for a telecom company.
Features: tenure_months, monthly_charges, total_charges, contract_type
(Month-to-month/One year/Two year), payment_method, internet_service
(DSL/Fiber optic), online_security (Yes/No), tech_support (Yes/No),
streaming_tv, streaming_movies, paperless_billing, gender, senior_citizen (0/1),
partner (Yes/No), dependents (Yes/No), num_support_tickets, avg_monthly_usage_gb.
Target: churned (Yes/No). 30 customers, ~40% churn rate.
Key pattern: month-to-month + fiber optic + electronic check = high churn risk.
Train: Logistic Regression, Random Forest, Gradient Boosting.
Report accuracy, precision, recall, F1, AUC-ROC.
Minimize false negatives. Generate ROC curves and feature importance plot.
```

### Q3 — Credit card fraud (imbalanced, generates ROC + precision-recall charts)
```
Build a fraud detection model for credit card transactions.
Features: transaction_amount, merchant_category (retail/food/travel/online/entertainment),
time_of_day (hour 0-23), day_of_week (0-6), card_age_days,
num_transactions_24h, avg_transaction_amount, distance_from_home_km,
is_international (0/1), is_weekend (0/1), amount_vs_avg_ratio.
Target: is_fraud (0/1).
Dataset: 5000 transactions, 1.5% fraud rate (highly imbalanced).
Priority: Maximize recall while keeping false positive rate under 3%.
Use class_weight='balanced' or SMOTE.
Train: Logistic Regression, Random Forest, Gradient Boosting.
Generate: ROC curve comparison + precision-recall curve for best model.
```

### Q4 — Student exam scores (regression, generates scatter + residual charts)
```
Predict student final exam scores.
Features: study_hours_per_week, attendance_pct, previous_gpa (0-4.0),
parent_education (High School/Bachelor/Master/PhD), extracurricular_activities (0-5),
sleep_hours_avg, commute_minutes, part_time_job (Yes/No), tutoring (Yes/No),
practice_tests_completed.
Target: final_score (0-100).
Dataset: 200 students. Score mean ~68, std ~15, range 25-98.
study_hours and previous_gpa are strongest predictors.
Train: Linear Regression, Random Forest, Gradient Boosting.
Report RMSE, MAE, R-squared.
Generate: predicted vs actual scatter plot + residual distribution histogram.
```

### Q5 — Loan default prediction (cost-sensitive classification)
```
Build a loan default prediction model for our lending platform.
Features: loan_amount, annual_income, debt_to_income_ratio, credit_score (300-850),
employment_length_years, home_ownership (Rent/Mortgage/Own), loan_purpose
(Debt consolidation/Home improvement/Business/Education/Medical),
num_open_accounts, num_delinquencies, months_since_last_delinquency,
total_credit_limit, credit_utilization_pct.
Target: defaulted (0/1). 3000 loans, 12% default rate.
Business: We lose $50K per missed default but only $500 per rejected good loan.
Train: Logistic Regression, Random Forest, Gradient Boosting.
Report cost-adjusted performance and expected savings per 1000 decisions.
Generate: confusion matrix heatmap + feature importance chart.
```

### Q6 — Customer lifetime value (regression with log transform)
```
Predict customer lifetime value (CLV) for our SaaS platform.
Features: signup_channel (Organic/Paid/Referral), plan_type (Free/Basic/Pro/Enterprise),
monthly_spend, months_active, num_support_tickets, feature_adoption_score (0-100),
login_frequency_weekly, team_size, industry (Tech/Finance/Healthcare/Education/Retail),
has_api_integration (Yes/No), NPS_score (0-10).
Target: lifetime_value_usd. 500 customers, CLV range $0-$150,000.
Heavy right skew — apply log transform on target.
Focus: feature engineering with interaction terms and ratios.
Train: Linear Regression, Random Forest, Gradient Boosting.
Generate: CLV distribution histogram + predicted vs actual (log scale) scatter.
```

---

## 4. IT Incident Triage & Resolution

**Workflow file:** `workflows/17_it_incident_triage.json`
**Agents:** Incident Intake → Diagnostic Engine → Resolution Advisor → Impact Analyzer → Report Drafter
**Produces:** Severity classification, root cause analysis, resolution plan, SLA report, communications

### Q1 — Payment gateway down (P1 Critical)
```
URGENT: Our payment processing is completely down since 10:15 AM. Stripe webhook
endpoint returns 503. All customer checkouts failing — estimated 2000 transactions/hour
affected. Error in logs: "Connection refused to payment-gateway-prod:8443".
We deployed a new API version at 9:45 AM. 15,000 active users on the platform right now.
Revenue impact ~$50K/hour.
```

### Q2 — Kubernetes pod crashloop (P2 High)
```
Our recommendation-engine deployment in Kubernetes has been crashlooping for the past
45 minutes. Pod restarts every 2-3 minutes with OOMKilled status. Memory limit is 2Gi
but the pod is consuming 3.5Gi. Started after we enabled a new ML model feature flag
yesterday. Affects product recommendations for ~30% of users on the website.
Logs show: "java.lang.OutOfMemoryError: Java heap space" in the recommendation-service container.
```

### Q3 — SSL certificate expiry (P3 Medium)
```
Getting reports from a few customers that they see "Your connection is not private"
warnings when accessing our developer portal at docs.ourcompany.com. Our monitoring
shows the SSL cert expired 6 hours ago. Main website and API are fine — different cert.
About 500 developers use the portal daily. No data exposure risk since it's public
documentation, but it looks unprofessional.
```

### Q4 — Database replication lag (P2 High)
```
Our PostgreSQL read replicas are showing 45-second replication lag since 2:30 PM.
Normally lag is under 100ms. This is causing stale data in our customer dashboard —
users see outdated account balances. The primary database is on AWS RDS, 3 read
replicas in us-east-1. We ran a large batch migration at 2:15 PM that inserted
500K rows. About 8000 concurrent users affected. No data loss but customer trust
impact is high.
```

### Q5 — Vague report triggering HITL (will pause for clarification)
```
Something is wrong with the system. Users are complaining.
```

---

## 5. Data Analyst - Chart Generator (Persona/Agent)

**Persona file:** `agents_creator/assistants/28_data_analyst.json`
**Tools:** PythonTool
**Produces:** matplotlib/seaborn PNG charts + statistical summaries

### Q1 — India GDP & economic dashboard (4 charts)
```
Create a comprehensive India economic dashboard with realistic data:
1) India GDP growth rate from 2015-2025 (line chart with year-over-year %)
2) Sector-wise GDP contribution — Agriculture, Industry, Services (stacked bar chart)
3) Population growth projection 2020-2050 (area chart with 1.4B to 1.7B range)
4) India vs China vs US GDP comparison (grouped bar chart)
Use realistic numbers based on known statistics. Save each chart as a separate PNG file.
```

### Q2 — Indian IT company stock analysis (4 charts)
```
Analyze stock market performance of top Indian IT companies: TCS, Infosys, Wipro,
HCL Tech, and Tech Mahindra. Generate realistic sample data for 2023-2025:
1) Stock price trends (multi-line chart with 20-day moving averages)
2) Market cap comparison (horizontal bar chart in billions USD)
3) Quarterly revenue growth rates (heatmap: companies x quarters)
4) Volatility comparison (box plot of daily returns distribution)
Save all charts as separate PNG files with descriptive names.
```

### Q3 — Climate visualization for Indian cities (4 charts)
```
Create climate visualizations for 6 Indian cities (Delhi, Mumbai, Bangalore,
Chennai, Kolkata, Jaipur) using realistic weather data:
1) Average monthly temperature comparison (multi-line chart, all cities on one plot)
2) Annual rainfall distribution (grouped bar chart by city, monsoon months highlighted)
3) Temperature vs Humidity scatter plot with city color coding and trend lines
4) AQI (Air Quality Index) monthly trends for Delhi vs Mumbai (dual-axis chart)
Make charts publication-quality with proper titles, axis labels, and legends.
```

### Q4 — COVID-19 India state analysis (4 charts)
```
Generate a COVID-19 analysis for Indian states using realistic data:
1) Top 10 states by total cases (horizontal bar chart with color gradient)
2) Daily new cases trend for Maharashtra, Kerala, Karnataka (multi-line, Jan-Dec 2021)
3) Vaccination progress by state (stacked bar: dose 1 vs dose 2 for top 8 states)
4) Case fatality rate comparison across 12 states (lollipop chart, sorted)
Print a summary statistics table to stdout showing totals per state.
```

### Q5 — Global energy & renewables dashboard (4 charts)
```
Create a global energy dashboard with realistic data:
1) World energy mix 2023 — Coal, Gas, Oil, Nuclear, Hydro, Solar, Wind (pie/donut chart)
2) Renewable energy growth by country (India, China, US, Germany, Brazil) 2018-2025
   (multi-line chart showing solar+wind capacity in GW)
3) Carbon emissions by sector — Power, Transport, Industry, Buildings, Agriculture
   (horizontal stacked bar for top 5 emitting countries)
4) Solar panel cost decline 2010-2025 (line chart, $/watt, showing 90% cost reduction)
Use realistic IEA/IRENA-based numbers. Save all as PNGs.
```

### Q6 — Indian election results visualization (3 charts)
```
Visualize Indian Lok Sabha 2024 election results with realistic seat counts:
1) Party-wise seats won — BJP, INC, SP, TMC, DMK, Others
   (horizontal bar chart, use party colors: BJP=saffron, INC=blue, SP=red, TMC=green)
2) Vote share comparison 2019 vs 2024 (grouped bar chart)
3) Region-wise seat distribution — North, South, East, West, Northeast
   (stacked bar by party for each region)
Print a summary table with party names, seats won, and vote share %.
```

---

## Running Tests

### Automated test runner (12 tests for coding workflows)
```bash
# Run all 12 coding workflow tests in parallel
python backend/tests/workflow_creator/test_coding_workflows.py

# Run a specific test by ID (1-12)
python backend/tests/workflow_creator/test_coding_workflows.py --test 7

# Run sequentially for debugging
python backend/tests/workflow_creator/test_coding_workflows.py --sequential

# Run against a remote server
python backend/tests/workflow_creator/test_coding_workflows.py --url http://192.168.1.10:3000
```

### Test ID mapping
| ID | Workflow | Test Case |
|----|----------|-----------|
| 1 | Data Analysis (45) | Quarterly Sales Revenue |
| 2 | Data Analysis (45) | Employee Attrition |
| 3 | Code Debug (47) | Sorting with Duplicates |
| 4 | Code Debug (47) | CSV Parser Off-By-One |
| 5 | ML Model (48) | House Price Regression |
| 6 | ML Model (48) | Customer Churn Classification |
| 7 | Data Analysis (45) | E-commerce Conversion Funnel |
| 8 | Data Analysis (45) | Manufacturing Quality Control |
| 9 | Code Debug (47) | Shopping Cart Bulk Discount |
| 10 | Code Debug (47) | Recursive Flatten Max Depth |
| 11 | ML Model (48) | Credit Card Fraud Detection |
| 12 | ML Model (48) | Student Exam Score Prediction |

### Manual testing (non-coding workflows)
```bash
# IT Incident Triage tests
python backend/tests/workflow_creator/test_all_workflows.py

# Data Analyst persona tests
python backend/tests/agents_creator/test_agents.py
```

### What the test validates
- PythonTool code execution (python_tool_start + python_tool_delta packets)
- Chart/PNG file generation (file_ids and enriched PythonToolFile metadata)
- Domain keyword presence in output (e.g., "revenue", "defect", "model")
- All 5 workflow agents run in sequence
- No unexpected HITL pause (all prompts provide full context)

---

## Test Case Design Principles

1. **Full-spec prompts** — all 3 critical fields (columns, data size, analysis questions) provided upfront to avoid HITL pauses
2. **Realistic domains** — e-commerce, HR, manufacturing, healthcare, finance, education
3. **Chart-generating prompts** — every question naturally requires visualizations (trends, comparisons, distributions)
4. **Keyword validation** — domain-specific terms the output MUST contain
5. **Edge cases** — highly imbalanced datasets (1.5% fraud), right-skewed targets (CLV), cost-sensitive metrics
6. **Varied chart types** — line, bar, scatter, heatmap, box plot, pie, area, lollipop, funnel, dual-axis
