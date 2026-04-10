# CMPT 354: Professional Opportunity Tracker
## SQL Requirements Report

This document outlines the implementation of the six required SQL query types and schema features for the course project.

---

### 1. Join Query
**Requirement:** A query that joins at least 2-3 tables.
**Implementation:** This query retrieves all applications along with the corresponding job title and company name by joining the `Application`, `Job_Posting`, and `Company` tables.

```sql
SELECT a.AppID, jp.JobTitle, c.Name AS CompanyName, a.Status, a.SubmissionDate
FROM Application a
JOIN Job_Posting jp ON a.PostingID = jp.PostingID
JOIN Company c ON jp.CompanyID = c.CompanyID
ORDER BY a.SubmissionDate DESC;
```

---

### 2. Division Query
**Requirement:** A query that involves the "division" operation (e.g., finding entities related to *all* of another set).
**Goal:** Find "Full-Coverage Interviewers"—contacts who have participated in **every** interview round for whichever applications they are associated with.

**Explanation:** 
We use the "Double NOT EXISTS" logic (here implemented using `EXCEPT` for readability). 
- We look for a `Contact_Person` where there is **no** `Interview_Round` that they were *supposed* to attend but *didn't*.
- The subquery finds all rounds for the applications they are linked to.
- The `EXCEPT` clause removes the rounds they actually attended.
- If the result is empty (NOT EXISTS), it means they attended everything.

```sql
SELECT cp.ContactID, cp.FullName
FROM Contact_Person cp
WHERE NOT EXISTS (
    SELECT ir.AppID, ir.RoundNumber
    FROM Interview_Round ir
    WHERE ir.AppID IN (
        SELECT DISTINCT pi.AppID FROM Participated_In pi WHERE pi.ContactID = cp.ContactID
    )
    EXCEPT
    SELECT pi2.AppID, pi2.RoundNumber
    FROM Participated_In pi2
    WHERE pi2.ContactID = cp.ContactID
);
```

---

### 3. Aggregation Query
**Requirement:** Use functions like `SUM`, `COUNT`, `AVG`, `MIN`, or `MAX`.
**Implementation:** This query calculates high-level metrics for the entire dashboard.

```sql
SELECT
    COUNT(*) AS TotalApps,
    COUNT(DISTINCT jp.CompanyID) AS CompaniesApplied,
    ROUND(COUNT(*)::numeric / NULLIF(COUNT(DISTINCT jp.CompanyID), 0), 1) AS AvgPerCompany
FROM Application a
JOIN Job_Posting jp ON a.PostingID = jp.PostingID;
```

---

### 4. Aggregation with Group-By
**Requirement:** Calculate an aggregated value for each group.
**Implementation:** This calculates the total applications and the "Offer Success Rate" for **each company** individually.

```sql
SELECT c.Name, COUNT(a.AppID) AS TotalApps,
       SUM(CASE WHEN a.Status = 'Offer' THEN 1 ELSE 0 END) AS Offers,
       ROUND(SUM(CASE WHEN a.Status = 'Offer' THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100) AS SuccessRate
FROM Application a
JOIN Job_Posting jp ON a.PostingID = jp.PostingID
JOIN Company c ON jp.CompanyID = c.CompanyID
GROUP BY c.Name
ORDER BY TotalApps DESC;
```

---

### 5. Delete Operation with Cascade
**Requirement:** Demonstate a DELETE that triggers cascading deletes in child tables.
**Implementation:** Every foreign key in our schema (e.g., in `Job_Posting`, `Application`, `Document`) is defined with `ON DELETE CASCADE`. 
If you delete a `Company`, all its postings, applications, interviews, and notes are automatically removed by the database engine.

```sql
-- This will automatically delete all related data in 5+ other tables
DELETE FROM Company WHERE CompanyID = 4;
```

---

### 6. Update Operation
**Requirement:** A standard UPDATE query.
**Implementation:** Updating the status of a specific application (e.g., when an offer is received).

```sql
UPDATE Application SET Status = 'Offer' WHERE AppID = 201;
```

---

### Bonus: Triggers & Assertions
The schema also includes **3 Advanced Triggers**:
1. **`trg_auto_reject_expired`**: Periodically/On-update auto-rejects applications if the `OfferDeadline` has passed.
2. **`trg_validate_interview_date`**: An assertion that ensures an interview date cannot be earlier than the application submission date.
3. **`trg_set_upload_date`**: Automatically sets the current date for new document uploads if not provided.
