# RAG Evaluation Benchmark Report

- **Date Executed**: 2026-07-22 11:47:46
- **Total Queries Evaluated**: 16
- **Top-K Window**: 3
- **Total Execution Time**: 40.49s

## Executive Performance Summary

| Metric | Score | Target Standard | Status |
| :--- | :--- | :--- | :--- |
| **Retrieval Precision@3** | **100.0%** (16/16) | ≥ 85.0% | ✅ PASS |
| **Answer Correctness** | **100.0%** (16/16) | ≥ 85.0% | ✅ PASS |

---

## Detailed Per-Query Results Table

| ID | Query Question | Expected Page | Retrieved Pages | Precision Match? | Expected Keyword | Answer Match? |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| 1 | How many days per week can employees work remotely? | Page 1 | 1, 2, 4 | ✅ PASS | `3` | ✅ PASS |
| 2 | What are the mandatory core working hours for remote employees? | Page 1 | 1, 2, 6 | ✅ PASS | `10` | ✅ PASS |
| 3 | What is the annual home office setup equipment stipend? | Page 1 | 1, 2, 5 | ✅ PASS | `500` | ✅ PASS |
| 4 | How many annual PTO days do full-time employees receive? | Page 2 | 2, 1, 4 | ✅ PASS | `20` | ✅ PASS |
| 5 | How many paid sick leave days are provided per calendar year? | Page 2 | 2, 1, 5 | ✅ PASS | `10` | ✅ PASS |
| 6 | How many weeks of fully paid parental leave are offered? | Page 2 | 2, 1, 4 | ✅ PASS | `12` | ✅ PASS |
| 7 | What is the primary healthcare insurance plan offered? | Page 3 | 3, 4, 2 | ✅ PASS | `BlueCross` | ✅ PASS |
| 8 | What is the annual company Health Savings Account HSA match? | Page 3 | 3, 4, 2 | ✅ PASS | `1000` | ✅ PASS |
| 9 | Which dental insurance network provider is covered? | Page 3 | 3, 2, 1 | ✅ PASS | `Delta` | ✅ PASS |
| 10 | What is the maximum company 401k retirement matching percentage? | Page 4 | 4, 6, 1 | ✅ PASS | `4` | ✅ PASS |
| 11 | What is the vesting schedule duration for employee equity stock options? | Page 4 | 4, 2, 1 | ✅ PASS | `4-year` | ✅ PASS |
| 12 | What is the cliff period requirement for equity option vesting? | Page 4 | 4, 5, 2 | ✅ PASS | `1-year` | ✅ PASS |
| 13 | What is the daily per diem allowance limit for business travel meals? | Page 5 | 5, 4, 2 | ✅ PASS | `75` | ✅ PASS |
| 14 | How many days in advance must business travel flights be booked? | Page 5 | 5, 1, 4 | ✅ PASS | `14` | ✅ PASS |
| 15 | What is the dollar threshold requiring itemized receipts for travel expenses? | Page 5 | 5, 2, 1 | ✅ PASS | `25` | ✅ PASS |
| 16 | Is Multi-Factor Authentication MFA mandatory for company systems? | Page 6 | 6, 4, 1 | ✅ PASS | `MFA` | ✅ PASS |


---

## Generated Answer Quality Breakdown

### Query 1: How many days per week can employees work remotely?
- **Expected Page**: Page 1
- **Expected Key Fact**: `3`
- **Generated Answer**: "Based on **Acme_Corporate_Policies_2026.pdf** (Page 1), here is the relevant information regarding your query:

> "SECTION 1: REMOTE WORK POLICY. Employees are allowed up to 3 remote days per week. Core mandatory working hours are 10 AM to 4 PM EST. All remote employees receive a $500 annual home office setup equipment stipend...."

Key points summarized from your uploaded document:
- Document referenced: **Acme Corporate Policies 2026**
- Page number: `1`
- Total context chunks retrieved: `3`

*(Source citation: Acme_Corporate_Policies_2026.pdf, Page 1)* "
- **Result Status**: ✅ PASS

### Query 2: What are the mandatory core working hours for remote employees?
- **Expected Page**: Page 1
- **Expected Key Fact**: `10`
- **Generated Answer**: "Based on **Acme_Corporate_Policies_2026.pdf** (Page 1), here is the relevant information regarding your query:

> "SECTION 1: REMOTE WORK POLICY. Employees are allowed up to 3 remote days per week. Core mandatory working hours are 10 AM to 4 PM EST. All remote employees receive a $500 annual home office setup equipment stipend...."

Key points summarized from your uploaded document:
- Document referenced: **Acme Corporate Policies 2026**
- Page number: `1`
- Total context chunks retrieved: `3`

*(Source citation: Acme_Corporate_Policies_2026.pdf, Page 1)* "
- **Result Status**: ✅ PASS

### Query 3: What is the annual home office setup equipment stipend?
- **Expected Page**: Page 1
- **Expected Key Fact**: `500`
- **Generated Answer**: "Based on **Acme_Corporate_Policies_2026.pdf** (Page 1), here is the relevant information regarding your query:

> "SECTION 1: REMOTE WORK POLICY. Employees are allowed up to 3 remote days per week. Core mandatory working hours are 10 AM to 4 PM EST. All remote employees receive a $500 annual home office setup equipment stipend...."

Key points summarized from your uploaded document:
- Document referenced: **Acme Corporate Policies 2026**
- Page number: `1`
- Total context chunks retrieved: `3`

*(Source citation: Acme_Corporate_Policies_2026.pdf, Page 1)* "
- **Result Status**: ✅ PASS

### Query 4: How many annual PTO days do full-time employees receive?
- **Expected Page**: Page 2
- **Expected Key Fact**: `20`
- **Generated Answer**: "Based on **Acme_Corporate_Policies_2026.pdf** (Page 2), here is the relevant information regarding your query:

> "SECTION 2: TIME OFF AND LEAVE POLICIES. Full-time employees receive 20 days of paid annual PTO per calendar year. In addition, 10 paid sick leave days are granted annually. Primary caregivers receive 12 weeks of fully paid parental leave...."

Key points summarized from your uploaded document:
- Document referenced: **Acme Corporate Policies 2026**
- Page number: `2`
- Total context chunks retrieved: `3`

*(Source citation: Acme_Corporate_Policies_2026.pdf, Page 2)* "
- **Result Status**: ✅ PASS

### Query 5: How many paid sick leave days are provided per calendar year?
- **Expected Page**: Page 2
- **Expected Key Fact**: `10`
- **Generated Answer**: "Based on **Acme_Corporate_Policies_2026.pdf** (Page 2), here is the relevant information regarding your query:

> "SECTION 2: TIME OFF AND LEAVE POLICIES. Full-time employees receive 20 days of paid annual PTO per calendar year. In addition, 10 paid sick leave days are granted annually. Primary caregivers receive 12 weeks of fully paid parental leave...."

Key points summarized from your uploaded document:
- Document referenced: **Acme Corporate Policies 2026**
- Page number: `2`
- Total context chunks retrieved: `3`

*(Source citation: Acme_Corporate_Policies_2026.pdf, Page 2)* "
- **Result Status**: ✅ PASS

### Query 6: How many weeks of fully paid parental leave are offered?
- **Expected Page**: Page 2
- **Expected Key Fact**: `12`
- **Generated Answer**: "Based on **Acme_Corporate_Policies_2026.pdf** (Page 2), here is the relevant information regarding your query:

> "SECTION 2: TIME OFF AND LEAVE POLICIES. Full-time employees receive 20 days of paid annual PTO per calendar year. In addition, 10 paid sick leave days are granted annually. Primary caregivers receive 12 weeks of fully paid parental leave...."

Key points summarized from your uploaded document:
- Document referenced: **Acme Corporate Policies 2026**
- Page number: `2`
- Total context chunks retrieved: `3`

*(Source citation: Acme_Corporate_Policies_2026.pdf, Page 2)* "
- **Result Status**: ✅ PASS

### Query 7: What is the primary healthcare insurance plan offered?
- **Expected Page**: Page 3
- **Expected Key Fact**: `BlueCross`
- **Generated Answer**: "Based on **Acme_Corporate_Policies_2026.pdf** (Page 3), here is the relevant information regarding your query:

> "SECTION 3: HEALTHCARE AND DENTAL BENEFITS. Comprehensive health coverage is provided via BlueCross PPO. The company provides a $1000 annual Health Savings Account HSA match. Dental coverage is provided by Delta Dental...."

Key points summarized from your uploaded document:
- Document referenced: **Acme Corporate Policies 2026**
- Page number: `3`
- Total context chunks retrieved: `3`

*(Source citation: Acme_Corporate_Policies_2026.pdf, Page 3)* "
- **Result Status**: ✅ PASS

### Query 8: What is the annual company Health Savings Account HSA match?
- **Expected Page**: Page 3
- **Expected Key Fact**: `1000`
- **Generated Answer**: "Based on **Acme_Corporate_Policies_2026.pdf** (Page 3), here is the relevant information regarding your query:

> "SECTION 3: HEALTHCARE AND DENTAL BENEFITS. Comprehensive health coverage is provided via BlueCross PPO. The company provides a $1000 annual Health Savings Account HSA match. Dental coverage is provided by Delta Dental...."

Key points summarized from your uploaded document:
- Document referenced: **Acme Corporate Policies 2026**
- Page number: `3`
- Total context chunks retrieved: `3`

*(Source citation: Acme_Corporate_Policies_2026.pdf, Page 3)* "
- **Result Status**: ✅ PASS

### Query 9: Which dental insurance network provider is covered?
- **Expected Page**: Page 3
- **Expected Key Fact**: `Delta`
- **Generated Answer**: "Based on **Acme_Corporate_Policies_2026.pdf** (Page 3), here is the relevant information regarding your query:

> "SECTION 3: HEALTHCARE AND DENTAL BENEFITS. Comprehensive health coverage is provided via BlueCross PPO. The company provides a $1000 annual Health Savings Account HSA match. Dental coverage is provided by Delta Dental...."

Key points summarized from your uploaded document:
- Document referenced: **Acme Corporate Policies 2026**
- Page number: `3`
- Total context chunks retrieved: `3`

*(Source citation: Acme_Corporate_Policies_2026.pdf, Page 3)* "
- **Result Status**: ✅ PASS

### Query 10: What is the maximum company 401k retirement matching percentage?
- **Expected Page**: Page 4
- **Expected Key Fact**: `4`
- **Generated Answer**: "Based on **Acme_Corporate_Policies_2026.pdf** (Page 4), here is the relevant information regarding your query:

> "SECTION 4: RETIREMENT AND EQUITY. The company offers a 401(k) plan with a 4% maximum dollar-for-dollar match. Equity stock option grants follow a 4-year vesting schedule with a 1-year cliff period requirement...."

Key points summarized from your uploaded document:
- Document referenced: **Acme Corporate Policies 2026**
- Page number: `4`
- Total context chunks retrieved: `3`

*(Source citation: Acme_Corporate_Policies_2026.pdf, Page 4)* "
- **Result Status**: ✅ PASS

### Query 11: What is the vesting schedule duration for employee equity stock options?
- **Expected Page**: Page 4
- **Expected Key Fact**: `4-year`
- **Generated Answer**: "Based on **Acme_Corporate_Policies_2026.pdf** (Page 4), here is the relevant information regarding your query:

> "SECTION 4: RETIREMENT AND EQUITY. The company offers a 401(k) plan with a 4% maximum dollar-for-dollar match. Equity stock option grants follow a 4-year vesting schedule with a 1-year cliff period requirement...."

Key points summarized from your uploaded document:
- Document referenced: **Acme Corporate Policies 2026**
- Page number: `4`
- Total context chunks retrieved: `3`

*(Source citation: Acme_Corporate_Policies_2026.pdf, Page 4)* "
- **Result Status**: ✅ PASS

### Query 12: What is the cliff period requirement for equity option vesting?
- **Expected Page**: Page 4
- **Expected Key Fact**: `1-year`
- **Generated Answer**: "Based on **Acme_Corporate_Policies_2026.pdf** (Page 4), here is the relevant information regarding your query:

> "SECTION 4: RETIREMENT AND EQUITY. The company offers a 401(k) plan with a 4% maximum dollar-for-dollar match. Equity stock option grants follow a 4-year vesting schedule with a 1-year cliff period requirement...."

Key points summarized from your uploaded document:
- Document referenced: **Acme Corporate Policies 2026**
- Page number: `4`
- Total context chunks retrieved: `3`

*(Source citation: Acme_Corporate_Policies_2026.pdf, Page 4)* "
- **Result Status**: ✅ PASS

### Query 13: What is the daily per diem allowance limit for business travel meals?
- **Expected Page**: Page 5
- **Expected Key Fact**: `75`
- **Generated Answer**: "Based on **Acme_Corporate_Policies_2026.pdf** (Page 5), here is the relevant information regarding your query:

> "SECTION 5: TRAVEL AND EXPENSE REIMBURSEMENT. Daily per diem allowance for business travel meals is $75. Flights must be booked at least 14 days in advance. Itemized receipts are mandatory for any expense exceeding $25...."

Key points summarized from your uploaded document:
- Document referenced: **Acme Corporate Policies 2026**
- Page number: `5`
- Total context chunks retrieved: `3`

*(Source citation: Acme_Corporate_Policies_2026.pdf, Page 5)* "
- **Result Status**: ✅ PASS

### Query 14: How many days in advance must business travel flights be booked?
- **Expected Page**: Page 5
- **Expected Key Fact**: `14`
- **Generated Answer**: "Based on **Acme_Corporate_Policies_2026.pdf** (Page 5), here is the relevant information regarding your query:

> "SECTION 5: TRAVEL AND EXPENSE REIMBURSEMENT. Daily per diem allowance for business travel meals is $75. Flights must be booked at least 14 days in advance. Itemized receipts are mandatory for any expense exceeding $25...."

Key points summarized from your uploaded document:
- Document referenced: **Acme Corporate Policies 2026**
- Page number: `5`
- Total context chunks retrieved: `3`

*(Source citation: Acme_Corporate_Policies_2026.pdf, Page 5)* "
- **Result Status**: ✅ PASS

### Query 15: What is the dollar threshold requiring itemized receipts for travel expenses?
- **Expected Page**: Page 5
- **Expected Key Fact**: `25`
- **Generated Answer**: "Based on **Acme_Corporate_Policies_2026.pdf** (Page 5), here is the relevant information regarding your query:

> "SECTION 5: TRAVEL AND EXPENSE REIMBURSEMENT. Daily per diem allowance for business travel meals is $75. Flights must be booked at least 14 days in advance. Itemized receipts are mandatory for any expense exceeding $25...."

Key points summarized from your uploaded document:
- Document referenced: **Acme Corporate Policies 2026**
- Page number: `5`
- Total context chunks retrieved: `3`

*(Source citation: Acme_Corporate_Policies_2026.pdf, Page 5)* "
- **Result Status**: ✅ PASS

### Query 16: Is Multi-Factor Authentication MFA mandatory for company systems?
- **Expected Page**: Page 6
- **Expected Key Fact**: `MFA`
- **Generated Answer**: "Based on **Acme_Corporate_Policies_2026.pdf** (Page 6), here is the relevant information regarding your query:

> "SECTION 6: INFORMATION SECURITY AND COMPLIANCE. Multi-Factor Authentication MFA is mandatory across all internal corporate systems. All employee laptops must adhere to SOC2 encryption and clear desk policies...."

Key points summarized from your uploaded document:
- Document referenced: **Acme Corporate Policies 2026**
- Page number: `6`
- Total context chunks retrieved: `3`

*(Source citation: Acme_Corporate_Policies_2026.pdf, Page 6)* "
- **Result Status**: ✅ PASS

