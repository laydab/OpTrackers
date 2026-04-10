# Normalization Analysis: Professional Opportunity Tracker

This report evaluates the database schema against the standard Normal Forms (1NF, 2NF, 3NF, and BCNF) to ensure data integrity and minimize redundancy.

---

### 1. First Normal Form (1NF)
**Requirement:** All attributes must be atomic (no lists or sets) and each table must have a primary key.
- **Proof:** 
    - Every table has a clearly defined Primary Key.
    - We handled the multi-valued attribute **Industry** by creating a separate `Company_Industry` table rather than using an array or comma-separated string in the `Company` table.
    - All other fields (Names, dates, IDs) are atomic.
- **Status:** **PASS**

---

### 2. Second Normal Form (2NF)
**Requirement:** Must be in 1NF and have no **partial dependencies** (non-key attributes must depend on the *entire* primary key).
- **Proof:**
    - For tables with single-attribute primary keys (`Company`, `Job_Posting`, `Application`, `Document`, `Contact_Person`), partial dependency is mathematically impossible.
    - For tables with composite keys:
        - `Company_Industry(CompanyID, Industry)`: There are no non-key attributes.
        - `Application_Notes(AppID, Note)`: There are no non-key attributes.
        - `Interview_Round(AppID, RoundNumber)`: Non-key attributes like `Date`, `Time`, and `Format` depend on the specific round of a specific application. You cannot determine the date using only the `AppID` (multiple rounds) or only the `RoundNumber` (multiple apps).
- **Status:** **PASS**

---

### 3. Third Normal Form (3NF)
**Requirement:** Must be in 2NF and have no **transitive dependencies** (non-key attributes must depend *directly* on the primary key, not on another non-key attribute).
- **Analysis:**
    - In `Job_Posting`, all attributes (JobTitle, Salary, etc.) depend on `PostingID`. While `CompanyID` is present, it is a Foreign Key, not a determinant for the other fields.
    - In `Contact_Person`, `Email` and `Phone` depend on the `ContactID`. One might argue `Email -> FullName`, but in database design, we assume only the Primary Key is the unique identifier for a person (since people can share emails or names).
    - There are no cases where `A -> B -> C` where B and C are non-key.
- **Status:** **PASS**

---

### 4. Boyce-Codd Normal Form (BCNF)
**Requirement:** For every functional dependency `X -> Y`, `X` must be a superkey.
- **Proof:**
    - In every table, the only determinants (attributes that define other attributes) are the Primary Keys we defined. 
    - There are no overlapping candidate keys or hidden dependencies where a non-key attribute determines a part of a composite key.
- **Status:** **PASS**

---

### Summary of Functional Dependencies (FDs)
To help with your project report, here are the core FDs:
1. `CompanyID` → `Name, Location, Website`
2. `PostingID` → `JobTitle, Location, Description, SalaryRange, DatePosted, ApplicationDeadline, CompanyID`
3. `AppID` → `SubmissionDate, Status, OfferDeadline, PostingID`
4. `(AppID, RoundNumber)` → `Date, Time, Format, Feedback`
5. `DocID` → `FileName, FilePath, UploadDate, AppID`
6. `ContactID` → `FullName, Email, Phone, LinkedInURL, CompanyID`

**Conclusion:** The schema is fully normalized to **BCNF**, which is the highest practical standard for relational databases. This ensures your project meets the "Consistency and Minimal Redundancy" requirements of CMPT 354.
