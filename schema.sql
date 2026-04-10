-- ============================================================================
-- OpTracker — Professional Opportunity Tracker
-- CMPT 354 Database Schema + Data + Triggers
-- PostgreSQL
-- ============================================================================

-- Drop existing tables (in dependency order)
DROP TABLE IF EXISTS Participated_In CASCADE;
DROP TABLE IF EXISTS Contact_Person CASCADE;
DROP TABLE IF EXISTS Interview_Round CASCADE;
DROP TABLE IF EXISTS Cover_Letter CASCADE;
DROP TABLE IF EXISTS Resume CASCADE;
DROP TABLE IF EXISTS Document CASCADE;
DROP TABLE IF EXISTS Application_Notes CASCADE;
DROP TABLE IF EXISTS Application CASCADE;
DROP TABLE IF EXISTS Job_Posting CASCADE;
DROP TABLE IF EXISTS Company_Industry CASCADE;
DROP TABLE IF EXISTS Company CASCADE;


-- ============================================================================
-- TABLE DEFINITIONS
-- ============================================================================

CREATE TABLE Company (
    CompanyID   INT PRIMARY KEY,
    Name        VARCHAR(255) NOT NULL,
    Location    VARCHAR(255),
    Website     VARCHAR(255)
);

-- Multivalued attribute (Industry) modeled as separate table
CREATE TABLE Company_Industry (
    CompanyID   INT,
    Industry    VARCHAR(100),
    PRIMARY KEY (CompanyID, Industry),
    FOREIGN KEY (CompanyID) REFERENCES Company(CompanyID) ON DELETE CASCADE
);

CREATE TABLE Job_Posting (
    PostingID           INT PRIMARY KEY,
    JobTitle            VARCHAR(255) NOT NULL,
    Location            VARCHAR(255),
    Description         TEXT,
    SalaryRange         VARCHAR(100),
    DatePosted          DATE,
    ApplicationDeadline DATE,
    CompanyID           INT NOT NULL,
    FOREIGN KEY (CompanyID) REFERENCES Company(CompanyID) ON DELETE CASCADE
);

CREATE TABLE Application (
    AppID           INT PRIMARY KEY,
    SubmissionDate  DATE,
    Status          VARCHAR(50) CHECK (Status IN ('Draft','Submitted','Interview','Offer','Rejected')),
    OfferDeadline   DATE,
    PostingID       INT NOT NULL,
    FOREIGN KEY (PostingID) REFERENCES Job_Posting(PostingID) ON DELETE CASCADE
);

-- Weak entity: depends on Application
CREATE TABLE Application_Notes (
    AppID   INT,
    Note    VARCHAR(1000),
    PRIMARY KEY (AppID, Note),
    FOREIGN KEY (AppID) REFERENCES Application(AppID) ON DELETE CASCADE
);

CREATE TABLE Document (
    DocID       INT PRIMARY KEY,
    FileName    VARCHAR(255) NOT NULL,
    FilePath    VARCHAR(512),
    UploadDate  DATE,
    AppID       INT NOT NULL,
    FOREIGN KEY (AppID) REFERENCES Application(AppID) ON DELETE CASCADE
);

-- ISA subtype of Document
CREATE TABLE Resume (
    DocID   INT PRIMARY KEY,
    Version VARCHAR(50),
    FOREIGN KEY (DocID) REFERENCES Document(DocID) ON DELETE CASCADE
);

-- ISA subtype of Document
CREATE TABLE Cover_Letter (
    DocID               INT PRIMARY KEY,
    TailoredCompanyName VARCHAR(255),
    FOREIGN KEY (DocID) REFERENCES Document(DocID) ON DELETE CASCADE
);

-- Weak entity: depends on Application (composite key)
CREATE TABLE Interview_Round (
    AppID       INT,
    RoundNumber INT,
    Date        DATE,
    Time        TIME,
    Format      VARCHAR(50),
    Feedback    TEXT,
    PRIMARY KEY (AppID, RoundNumber),
    FOREIGN KEY (AppID) REFERENCES Application(AppID) ON DELETE CASCADE
);

CREATE TABLE Contact_Person (
    ContactID   INT PRIMARY KEY,
    FullName    VARCHAR(255) NOT NULL,
    Email       VARCHAR(255),
    Phone       VARCHAR(20),
    LinkedInURL VARCHAR(255),
    CompanyID   INT,
    FOREIGN KEY (CompanyID) REFERENCES Company(CompanyID) ON DELETE SET NULL
);

CREATE TABLE Participated_In (
    ContactID   INT,
    AppID       INT,
    RoundNumber INT,
    PRIMARY KEY (ContactID, AppID, RoundNumber),
    FOREIGN KEY (ContactID) REFERENCES Contact_Person(ContactID) ON DELETE CASCADE,
    FOREIGN KEY (AppID, RoundNumber) REFERENCES Interview_Round(AppID, RoundNumber) ON DELETE CASCADE
);


-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Trigger 1: Auto-reject applications whose offer deadline has passed
--            Fires on INSERT/UPDATE and sets Status = 'Rejected' if the
--            OfferDeadline is in the past and Status is not already final.
CREATE OR REPLACE FUNCTION auto_reject_expired_offers()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.OfferDeadline IS NOT NULL
       AND NEW.OfferDeadline < CURRENT_DATE
       AND NEW.Status NOT IN ('Offer', 'Rejected') THEN
        NEW.Status := 'Rejected';
        RAISE NOTICE 'Application % auto-rejected: offer deadline passed.', NEW.AppID;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_auto_reject_expired
    BEFORE INSERT OR UPDATE ON Application
    FOR EACH ROW
    EXECUTE FUNCTION auto_reject_expired_offers();


-- Trigger 2: Prevent scheduling an interview before the application was submitted
CREATE OR REPLACE FUNCTION validate_interview_date()
RETURNS TRIGGER AS $$
DECLARE
    sub_date DATE;
BEGIN
    SELECT SubmissionDate INTO sub_date
    FROM Application WHERE AppID = NEW.AppID;

    IF sub_date IS NOT NULL AND NEW.Date IS NOT NULL AND NEW.Date < sub_date THEN
        RAISE EXCEPTION 'Interview date (%) cannot be before submission date (%).',
            NEW.Date, sub_date;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_interview_date
    BEFORE INSERT OR UPDATE ON Interview_Round
    FOR EACH ROW
    EXECUTE FUNCTION validate_interview_date();


-- Trigger 3: Auto-set Document upload date to today if not provided
CREATE OR REPLACE FUNCTION set_upload_date()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.UploadDate IS NULL THEN
        NEW.UploadDate := CURRENT_DATE;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_set_upload_date
    BEFORE INSERT ON Document
    FOR EACH ROW
    EXECUTE FUNCTION set_upload_date();


-- ============================================================================
-- DATA POPULATION (≥ 5 tuples per table)
-- ============================================================================

INSERT INTO Company VALUES
    (1, 'Google',    'Mountain View, CA', 'https://google.com'),
    (2, 'Meta',      'Menlo Park, CA',    'https://meta.com'),
    (3, 'Amazon',    'Seattle, WA',       'https://amazon.com'),
    (4, 'Apple',     'Cupertino, CA',     'https://apple.com'),
    (5, 'Microsoft', 'Redmond, WA',       'https://microsoft.com');

INSERT INTO Company_Industry VALUES
    (1, 'Tech'),    (1, 'AI'),
    (2, 'Social Media'), (2, 'Tech'),
    (3, 'E-commerce'),   (3, 'Cloud'),
    (4, 'Consumer Electronics'), (4, 'Tech'),
    (5, 'Software'), (5, 'Cloud');

INSERT INTO Job_Posting VALUES
    (101, 'SWE Intern',       'Remote',       'Develop features.',       '10k/mo',    '2024-01-01', '2024-02-01', 1),
    (102, 'Data Analyst',     'New York, NY', 'Analyze data.',           '90k-110k',  '2024-01-05', '2024-02-05', 2),
    (103, 'Cloud Architect',  'Seattle, WA',  'Design cloud infra.',     '150k+',     '2024-01-10', '2024-02-10', 3),
    (104, 'UI Designer',      'Cupertino, CA','Design interfaces.',      '120k',      '2024-01-15', '2024-02-15', 4),
    (105, 'Product Manager',  'Redmond, WA',  'Manage products.',        '130k',      '2024-01-20', '2024-02-20', 5),
    (106, 'ML Engineer',      'Mountain View','Build ML pipelines.',     '160k+',     '2024-02-01', '2024-03-01', 1);

INSERT INTO Application VALUES
    (201, '2024-01-15', 'Interview',  NULL,         101),
    (202, '2024-01-20', 'Submitted',  NULL,         102),
    (203, '2024-01-25', 'Offer',      '2024-03-01', 103),
    (204, '2024-01-30', 'Rejected',   NULL,         104),
    (205, '2024-02-05', 'Draft',      NULL,         105),
    (206, '2024-02-10', 'Interview',  NULL,         106);

INSERT INTO Application_Notes VALUES
    (201, 'Follow up next week.'),
    (202, 'Recruiter was friendly.'),
    (203, 'Need to negotiate salary.'),
    (204, 'Practice coding more.'),
    (205, 'Update portfolio before sending.');

INSERT INTO Document VALUES
    (301, 'Resume_v1.pdf',          '/docs/r1.pdf',       '2024-01-15', 201),
    (302, 'CL_Google.pdf',          '/docs/cl1.pdf',      '2024-01-15', 201),
    (303, 'Resume_Final.pdf',       '/docs/rf.pdf',       '2024-01-20', 202),
    (304, 'CL_Meta.pdf',            '/docs/cl2.pdf',      '2024-01-20', 202),
    (305, 'Portfolio.pdf',          '/docs/p1.pdf',       '2024-01-25', 203),
    (306, 'Resume_Apple.pdf',       '/docs/r_apple.pdf',  '2024-01-30', 204),
    (307, 'Resume_MSFT.pdf',        '/docs/r_msft.pdf',   '2024-02-05', 205),
    (308, 'Resume_Generic_v2.pdf',  '/docs/r_v2.pdf',     '2024-02-10', 201),
    (309, 'CL_Amazon.pdf',          '/docs/cl3.pdf',      '2024-01-25', 203),
    (310, 'CL_Apple.pdf',           '/docs/cl4.pdf',      '2024-01-30', 204),
    (311, 'CL_Microsoft.pdf',       '/docs/cl5.pdf',      '2024-02-05', 205);

INSERT INTO Resume VALUES
    (301, 'General'), (303, 'Technical'), (306, 'Design Focused'),
    (307, 'Management'), (308, 'Legacy Version');

INSERT INTO Cover_Letter VALUES
    (302, 'Google'), (304, 'Meta'), (309, 'Amazon'),
    (310, 'Apple'), (311, 'Microsoft');

INSERT INTO Interview_Round VALUES
    (201, 1, '2024-02-10', '10:00', 'Phone Screen', 'Went well — asked about distributed systems.'),
    (201, 2, '2024-02-15', '14:00', 'On-site',      'Pending result.'),
    (203, 1, '2024-02-12', '09:00', 'Phone Screen', 'Great feedback from interviewer.'),
    (204, 1, '2024-02-14', '11:00', 'Technical',    'Hard algorithm questions.'),
    (204, 2, '2024-02-18', '13:00', 'Behavioral',   'Better but still tough.'),
    (206, 1, '2024-03-01', '10:00', 'Technical',    'ML system design went well.');

INSERT INTO Contact_Person VALUES
    (401, 'Alice Smith',   'alice@google.com',   '555-0101', 'https://linkedin.com/in/alice',   1),
    (402, 'Bob Brown',     'bob@meta.com',       '555-0102', 'https://linkedin.com/in/bob',     2),
    (403, 'Charlie Davis', 'charlie@amazon.com', '555-0103', 'https://linkedin.com/in/charlie', 3),
    (404, 'Diana Evans',   'diana@apple.com',    '555-0104', 'https://linkedin.com/in/diana',   4),
    (405, 'Edward Frank',  'edward@ms.com',      '555-0105', 'https://linkedin.com/in/edward',  5);

INSERT INTO Participated_In VALUES
    (401, 201, 1), (401, 201, 2),
    (403, 203, 1),
    (404, 204, 1), (404, 204, 2),
    (401, 206, 1);


-- ============================================================================
-- DEMO QUERIES (for reference / presentation)
-- These are the query types required by the rubric.
-- ============================================================================

-- 1) JOIN QUERY: List all applications with company name and job title
-- SELECT a.AppID, jp.JobTitle, c.Name AS CompanyName, a.Status, a.SubmissionDate
-- FROM Application a
-- JOIN Job_Posting jp ON a.PostingID = jp.PostingID
-- JOIN Company c ON jp.CompanyID = c.CompanyID
-- ORDER BY a.SubmissionDate DESC;

-- 2) DIVISION QUERY: Find contacts who participated in EVERY interview round
--    for all applications they are associated with.
-- SELECT cp.ContactID, cp.FullName
-- FROM Contact_Person cp
-- WHERE NOT EXISTS (
--     SELECT ir.AppID, ir.RoundNumber
--     FROM Interview_Round ir
--     WHERE ir.AppID IN (
--         SELECT DISTINCT pi.AppID FROM Participated_In pi WHERE pi.ContactID = cp.ContactID
--     )
--     EXCEPT
--     SELECT pi2.AppID, pi2.RoundNumber
--     FROM Participated_In pi2
--     WHERE pi2.ContactID = cp.ContactID
-- );

-- 3) AGGREGATION QUERY: Total applications, avg per company, max interviews
-- SELECT
--     COUNT(*) AS TotalApps,
--     COUNT(DISTINCT jp.CompanyID) AS CompaniesApplied,
--     ROUND(COUNT(*)::numeric / NULLIF(COUNT(DISTINCT jp.CompanyID), 0), 1) AS AvgPerCompany
-- FROM Application a
-- JOIN Job_Posting jp ON a.PostingID = jp.PostingID;

-- 4) AGGREGATION WITH GROUP BY: Applications per company with success rate
-- SELECT c.Name, COUNT(a.AppID) AS TotalApps,
--        SUM(CASE WHEN a.Status = 'Offer' THEN 1 ELSE 0 END) AS Offers,
--        ROUND(SUM(CASE WHEN a.Status = 'Offer' THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100) AS SuccessRate
-- FROM Application a
-- JOIN Job_Posting jp ON a.PostingID = jp.PostingID
-- JOIN Company c ON jp.CompanyID = c.CompanyID
-- GROUP BY c.Name
-- ORDER BY TotalApps DESC;

-- 5) DELETE WITH CASCADE: Deleting a company removes all postings, apps, interviews, docs
-- DELETE FROM Company WHERE CompanyID = 4;

-- 6) UPDATE OPERATION: Update application status
-- UPDATE Application SET Status = 'Offer' WHERE AppID = 201;
