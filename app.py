"""
Professional Opportunity Tracker
Flask application with PostgreSQL backend (CMPT 354 Project)
"""

import os
import hashlib
import secrets
from functools import wraps
from datetime import date, time, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session

# ---------------------------------------------------------------------------
# App Configuration
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key-change-in-production")

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

DB_CONFIG = {
    "dbname": os.environ.get("DB_NAME", "opportunity_tracker"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASS", ""),
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": os.environ.get("DB_PORT", "5432"),
}

def get_db():
    """Return a psycopg2 connection (or None when DB is unavailable)."""
    try:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = False
        return conn
    except Exception:
        return None


def query_db(sql, args=(), one=False, commit=False):
    """Execute *sql* against the live database.  Returns rows as dicts."""
    conn = get_db()
    if conn is None:
        return None
    try:
        import psycopg2.extras
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, args)
        if commit:
            conn.commit()
            return True
        rows = cur.fetchall()
        return (rows[0] if rows else None) if one else rows
    except Exception as e:
        conn.rollback()
        print(f"DB Error: {e}")
        return None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Mock / Sample Data  (used when PostgreSQL is not available)
# ---------------------------------------------------------------------------

MOCK_COMPANIES = [
    {"companyid": 1, "name": "Stripe",      "location": "San Francisco, CA", "website": "https://stripe.com",   "userid": 1},
    {"companyid": 2, "name": "Shopify",     "location": "Ottawa, ON",        "website": "https://shopify.com",  "userid": 1},
    {"companyid": 3, "name": "Notion",      "location": "New York, NY",      "website": "https://notion.so",    "userid": 1},
    {"companyid": 4, "name": "Figma",       "location": "San Francisco, CA", "website": "https://figma.com",    "userid": 1},
    {"companyid": 5, "name": "Datadog",     "location": "New York, NY",      "website": "https://datadoghq.com","userid": 1},
    {"companyid": 6, "name": "Coinbase",    "location": "Remote",            "website": "https://coinbase.com", "userid": 1},
]

MOCK_COMPANY_INDUSTRIES = [
    {"companyid": 1, "industry": "FinTech"},
    {"companyid": 1, "industry": "Payments"},
    {"companyid": 2, "industry": "E-Commerce"},
    {"companyid": 3, "industry": "Productivity"},
    {"companyid": 3, "industry": "SaaS"},
    {"companyid": 4, "industry": "Design"},
    {"companyid": 4, "industry": "SaaS"},
    {"companyid": 5, "industry": "Cloud"},
    {"companyid": 5, "industry": "Monitoring"},
    {"companyid": 6, "industry": "FinTech"},
    {"companyid": 6, "industry": "Crypto"},
]

MOCK_POSTINGS = [
    {"postingid": 1, "jobtitle": "Software Engineer Intern",     "location": "San Francisco, CA", "description": "Join our payments infrastructure team for a 12-week internship.", "salaryrange": "$45-55/hr",       "dateposted": date(2026, 1, 15), "applicationdeadline": date(2026, 3, 30), "companyid": 1, "company_name": "Stripe"},
    {"postingid": 2, "jobtitle": "Backend Developer Co-op",      "location": "Ottawa, ON",        "description": "Work on Shopify's core commerce platform.",                       "salaryrange": "$CAD 5,000/mo",   "dateposted": date(2026, 1, 20), "applicationdeadline": date(2026, 4, 1),  "companyid": 2, "company_name": "Shopify"},
    {"postingid": 3, "jobtitle": "Full-Stack Engineer",          "location": "New York, NY",      "description": "Build collaborative editing features for Notion.",                "salaryrange": "$140K-180K",      "dateposted": date(2026, 2, 1),  "applicationdeadline": date(2026, 4, 15), "companyid": 3, "company_name": "Notion"},
    {"postingid": 4, "jobtitle": "Product Design Engineer",      "location": "San Francisco, CA", "description": "Bridge design & engineering on Figma's plugin platform.",           "salaryrange": "$150K-190K",      "dateposted": date(2026, 2, 5),  "applicationdeadline": date(2026, 3, 25), "companyid": 4, "company_name": "Figma"},
    {"postingid": 5, "jobtitle": "Site Reliability Engineer",    "location": "New York, NY",      "description": "Ensure uptime and performance of Datadog's monitoring stack.",      "salaryrange": "$160K-200K",      "dateposted": date(2026, 2, 10), "applicationdeadline": date(2026, 4, 20), "companyid": 5, "company_name": "Datadog"},
    {"postingid": 6, "jobtitle": "Blockchain Engineer Intern",   "location": "Remote",            "description": "Work on smart contract tooling and DeFi protocols.",               "salaryrange": "$50-60/hr",       "dateposted": date(2026, 2, 12), "applicationdeadline": date(2026, 3, 28), "companyid": 6, "company_name": "Coinbase"},
]

MOCK_APPLICATIONS = [
    {"appid": 1, "submissiondate": date(2026, 2, 10), "status": "Interview",  "offerdeadline": None,              "postingid": 1, "jobtitle": "Software Engineer Intern",   "company_name": "Stripe",   "location": "San Francisco, CA", "userid": 1},
    {"appid": 2, "submissiondate": date(2026, 2, 15), "status": "Submitted",  "offerdeadline": None,              "postingid": 2, "jobtitle": "Backend Developer Co-op",    "company_name": "Shopify",  "location": "Ottawa, ON",        "userid": 1},
    {"appid": 3, "submissiondate": date(2026, 2, 18), "status": "Offer",      "offerdeadline": date(2026, 4, 1),  "postingid": 3, "jobtitle": "Full-Stack Engineer",        "company_name": "Notion",   "location": "New York, NY",      "userid": 1},
    {"appid": 4, "submissiondate": date(2026, 2, 20), "status": "Rejected",   "offerdeadline": None,              "postingid": 4, "jobtitle": "Product Design Engineer",    "company_name": "Figma",    "location": "San Francisco, CA", "userid": 1},
    {"appid": 5, "submissiondate": None,               "status": "Draft",      "offerdeadline": None,              "postingid": 5, "jobtitle": "Site Reliability Engineer",  "company_name": "Datadog",  "location": "New York, NY",      "userid": 1},
    {"appid": 6, "submissiondate": date(2026, 3, 1),  "status": "Interview",  "offerdeadline": None,              "postingid": 6, "jobtitle": "Blockchain Engineer Intern", "company_name": "Coinbase", "location": "Remote",            "userid": 1},
]

MOCK_INTERVIEWS = [
    {"appid": 1, "roundnumber": 1, "date": date(2026, 3, 18), "time": time(10, 0),  "format": "Phone Screen",     "feedback": "Went well — asked about distributed systems."},
    {"appid": 1, "roundnumber": 2, "date": date(2026, 3, 25), "time": time(14, 0),  "format": "Technical",        "feedback": None},
    {"appid": 3, "roundnumber": 1, "date": date(2026, 3, 5),  "time": time(11, 0),  "format": "Phone Screen",     "feedback": "Great culture fit discussion."},
    {"appid": 3, "roundnumber": 2, "date": date(2026, 3, 12), "time": time(13, 30), "format": "Technical",        "feedback": "Solved 2/3 coding questions."},
    {"appid": 3, "roundnumber": 3, "date": date(2026, 3, 15), "time": time(10, 0),  "format": "On-site",          "feedback": "Team loved the system design approach."},
    {"appid": 6, "roundnumber": 1, "date": date(2026, 3, 20), "time": time(9, 30),  "format": "Phone Screen",     "feedback": None},
]

MOCK_CONTACTS = [
    {"contactid": 1, "fullname": "Sarah Chen",       "email": "s.chen@stripe.com",    "phone": "415-555-0101", "linkedinurl": "https://linkedin.com/in/sarachen",   "companyid": 1, "company_name": "Stripe",  "userid": 1},
    {"contactid": 2, "fullname": "James Park",       "email": "j.park@shopify.com",   "phone": "613-555-0202", "linkedinurl": "https://linkedin.com/in/jamespark",  "companyid": 2, "company_name": "Shopify", "userid": 1},
    {"contactid": 3, "fullname": "Priya Sharma",     "email": "p.sharma@notion.so",   "phone": "212-555-0303", "linkedinurl": "https://linkedin.com/in/priyasharma", "companyid": 3, "company_name": "Notion",  "userid": 1},
    {"contactid": 4, "fullname": "Alex Rivera",      "email": "a.rivera@figma.com",   "phone": "415-555-0404", "linkedinurl": "https://linkedin.com/in/alexrivera",  "companyid": 4, "company_name": "Figma",   "userid": 1},
    {"contactid": 5, "fullname": "Morgan Williams",  "email": "m.will@datadoghq.com", "phone": "212-555-0505", "linkedinurl": "https://linkedin.com/in/morganw",     "companyid": 5, "company_name": "Datadog", "userid": 1},
]

MOCK_DOCUMENTS = [
    {"docid": 1, "filename": "Resume_v3_SWE.pdf",        "filepath": "/docs/resumes/resume_v3.pdf",      "uploaddate": date(2026, 2, 8),  "appid": 1},
    {"docid": 2, "filename": "CL_Stripe_SWE.pdf",        "filepath": "/docs/coverletters/cl_stripe.pdf", "uploaddate": date(2026, 2, 9),  "appid": 1},
    {"docid": 3, "filename": "Resume_v2_Backend.pdf",    "filepath": "/docs/resumes/resume_v2.pdf",      "uploaddate": date(2026, 2, 14), "appid": 2},
    {"docid": 4, "filename": "Resume_v3_FullStack.pdf",  "filepath": "/docs/resumes/resume_v3_fs.pdf",   "uploaddate": date(2026, 2, 17), "appid": 3},
    {"docid": 5, "filename": "CL_Notion_FullStack.pdf",  "filepath": "/docs/coverletters/cl_notion.pdf", "uploaddate": date(2026, 2, 17), "appid": 3},
    {"docid": 6, "filename": "Resume_v1_Blockchain.pdf", "filepath": "/docs/resumes/resume_v1_bc.pdf",   "uploaddate": date(2026, 2, 28), "appid": 6},
]

MOCK_RESUMES = [
    {"docid": 1, "version": "3.0"},
    {"docid": 3, "version": "2.0"},
    {"docid": 4, "version": "3.1"},
    {"docid": 6, "version": "1.0"},
]

MOCK_COVER_LETTERS = [
    {"docid": 2, "tailoredcompanyname": "Stripe"},
    {"docid": 5, "tailoredcompanyname": "Notion"},
]

MOCK_NOTES = [
    {"appid": 1, "note": "Referred by Sarah Chen — mention infrastructure projects."},
    {"appid": 1, "note": "Need to brush up on distributed systems before Round 2."},
    {"appid": 3, "note": "Team seems great — asked about remote flexibility."},
    {"appid": 3, "note": "Offer received! Need to negotiate salary by April 1."},
    {"appid": 4, "note": "Rejection email mentioned they went with more senior candidate."},
    {"appid": 6, "note": "Coinbase requires US work authorization — double-check eligibility."},
]

MOCK_PARTICIPATED_IN = [
    {"contactid": 1, "appid": 1, "roundnumber": 1},
    {"contactid": 1, "appid": 1, "roundnumber": 2},
    {"contactid": 3, "appid": 3, "roundnumber": 1},
    {"contactid": 3, "appid": 3, "roundnumber": 2},
    {"contactid": 3, "appid": 3, "roundnumber": 3},
]


# ---------------------------------------------------------------------------
# Authentication helpers
# ---------------------------------------------------------------------------

def hash_password(password):
    """Hash a password with a random salt using SHA-256."""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${hashed}"


def check_password(stored, password):
    """Verify a password against its stored hash."""
    if '$' not in stored:
        return False
    salt, hashed = stored.split('$', 1)
    return hashlib.sha256((salt + password).encode()).hexdigest() == hashed


MOCK_USERS = [
    {
        "id": 1,
        "fullname": "Demo User",
        "email": "demo@optracker.com",
        "password": hash_password("password123"),
    },
]


def login_required(f):
    """Redirect to /login if the user is not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to continue.", "info")
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated


@app.context_processor
def inject_user():
    """Make current_user available in every template."""
    user = None
    if "user_id" in session:
        user = next((u for u in MOCK_USERS if u["id"] == session["user_id"]), None)
    return dict(current_user=user)


# ---------------------------------------------------------------------------
# Routes — Authentication
# ---------------------------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = next((u for u in MOCK_USERS if u["email"] == email), None)
        if user and check_password(user["password"], password):
            session["user_id"] = user["id"]
            flash(f"Welcome back, {user['fullname']}!", "success")
            return redirect(request.form.get("next") or url_for("dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("login.html", next=request.args.get("next", ""))


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        fullname = request.form.get("fullname", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not fullname or not email or not password:
            flash("All fields are required.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        elif any(u["email"] == email for u in MOCK_USERS):
            flash("An account with that email already exists.", "error")
        else:
            new_id = max(u["id"] for u in MOCK_USERS) + 1 if MOCK_USERS else 1
            MOCK_USERS.append({
                "id": new_id,
                "fullname": fullname,
                "email": email,
                "password": hash_password(password),
            })
            flash("Account created! Please sign in.", "success")
            return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Helper: fetch data (DB → mock fallback)
# ---------------------------------------------------------------------------

def get_company_industries(company_id=None):
    if company_id:
        rows = query_db("SELECT * FROM Company_Industry WHERE CompanyID = %s", (company_id,))
    else:
        rows = query_db("SELECT * FROM Company_Industry")
    if rows is not None:
        return rows
    if company_id:
        return [i for i in MOCK_COMPANY_INDUSTRIES if i["companyid"] == company_id]
    return MOCK_COMPANY_INDUSTRIES


def get_companies():
    uid = session.get("user_id")
    rows = query_db("SELECT * FROM Company WHERE UserID = %s ORDER BY Name", (uid,))
    companies = rows if rows is not None else [dict(c) for c in MOCK_COMPANIES if c.get("userid") == uid]
    for c in companies:
        inds = get_company_industries(c["companyid"])
        c["industries"] = [i["industry"] for i in inds]
    return companies


def get_company(company_id):
    uid = session.get("user_id")
    row = query_db("SELECT * FROM Company WHERE CompanyID = %s AND UserID = %s", (company_id, uid), one=True)
    if row is None:
        row = next((c for c in MOCK_COMPANIES if c["companyid"] == company_id and c.get("userid") == uid), None)
    if row:
        row = dict(row)
        inds = get_company_industries(company_id)
        row["industries"] = [i["industry"] for i in inds]
    return row

def get_postings(search=None):
    rows = query_db("""
        SELECT jp.*, c.Name AS company_name
        FROM Job_Posting jp JOIN Company c ON jp.CompanyID = c.CompanyID
        ORDER BY jp.DatePosted DESC
    """)
    postings = rows if rows is not None else list(MOCK_POSTINGS)
    if search:
        s = search.lower()
        postings = [p for p in postings if s in p.get("jobtitle", "").lower() or s in p.get("location", "").lower()]
    return postings


def get_posting(posting_id):
    row = query_db("""
        SELECT jp.*, c.Name AS company_name
        FROM Job_Posting jp JOIN Company c ON jp.CompanyID = c.CompanyID
        WHERE jp.PostingID = %s
    """, (posting_id,), one=True)
    if row is not None:
        return row
    return next((p for p in MOCK_POSTINGS if p["postingid"] == posting_id), None)

def get_applications():
    uid = session.get("user_id")
    rows = query_db("""
        SELECT a.*, jp.JobTitle AS jobtitle, c.Name AS company_name, jp.Location AS location
        FROM Application a
        JOIN Job_Posting jp ON a.PostingID = jp.PostingID
        JOIN Company c ON jp.CompanyID = c.CompanyID
        WHERE a.UserID = %s
        ORDER BY a.SubmissionDate DESC NULLS LAST
    """, (uid,))
    return rows if rows is not None else [a for a in MOCK_APPLICATIONS if a.get("userid") == uid]

def get_application(app_id):
    uid = session.get("user_id")
    row = query_db("""
        SELECT a.*, jp.JobTitle AS jobtitle, jp.Description AS job_description,
               jp.SalaryRange AS salaryrange, jp.Location AS location,
               jp.ApplicationDeadline AS applicationdeadline,
               c.Name AS company_name, c.Website AS company_website, c.CompanyID AS companyid
        FROM Application a
        JOIN Job_Posting jp ON a.PostingID = jp.PostingID
        JOIN Company c ON jp.CompanyID = c.CompanyID
        WHERE a.AppID = %s AND a.UserID = %s
    """, (app_id, uid), one=True)
    if row is not None:
        return row
    return next((a for a in MOCK_APPLICATIONS if a["appid"] == app_id and a.get("userid") == uid), None)

def get_interviews(app_id=None):
    if app_id:
        rows = query_db("""
            SELECT * FROM Interview_Round WHERE AppID = %s ORDER BY RoundNumber
        """, (app_id,))
    else:
        rows = query_db("SELECT * FROM Interview_Round ORDER BY Date, Time")
    if rows is not None:
        return rows
    if app_id:
        return [i for i in MOCK_INTERVIEWS if i["appid"] == app_id]
    return MOCK_INTERVIEWS

def get_documents(app_id):
    rows = query_db("""
        SELECT d.*, r.Version, cl.TailoredCompanyName
        FROM Document d
        LEFT JOIN Resume r ON d.DocID = r.DocID
        LEFT JOIN Cover_Letter cl ON d.DocID = cl.DocID
        WHERE d.AppID = %s ORDER BY d.UploadDate
    """, (app_id,))
    if rows is not None:
        for doc in rows:
            if doc.get("version"):
                doc["type"] = "Resume"
            elif doc.get("tailoredcompanyname"):
                doc["type"] = "Cover Letter"
            else:
                doc["type"] = "Other"
        return rows
    docs = [dict(d) for d in MOCK_DOCUMENTS if d["appid"] == app_id]
    for doc in docs:
        resume = next((r for r in MOCK_RESUMES if r["docid"] == doc["docid"]), None)
        cover = next((c for c in MOCK_COVER_LETTERS if c["docid"] == doc["docid"]), None)
        if resume:
            doc["type"] = "Resume"
            doc["version"] = resume["version"]
        elif cover:
            doc["type"] = "Cover Letter"
            doc["tailoredcompanyname"] = cover["tailoredcompanyname"]
        else:
            doc["type"] = "Other"
    return docs

def get_notes(app_id):
    rows = query_db("SELECT * FROM Application_Notes WHERE AppID = %s", (app_id,))
    if rows is not None:
        return rows
    return [n for n in MOCK_NOTES if n["appid"] == app_id]

def get_contacts():
    uid = session.get("user_id")
    rows = query_db("""
        SELECT cp.*, c.Name AS company_name
        FROM Contact_Person cp JOIN Company c ON cp.CompanyID = c.CompanyID
        WHERE cp.UserID = %s
        ORDER BY cp.FullName
    """, (uid,))
    return rows if rows is not None else [c for c in MOCK_CONTACTS if c.get("userid") == uid]

def get_contact(contact_id):
    uid = session.get("user_id")
    row = query_db("SELECT cp.*, c.Name AS company_name FROM Contact_Person cp JOIN Company c ON cp.CompanyID = c.CompanyID WHERE cp.ContactID = %s AND cp.UserID = %s", (contact_id, uid), one=True)
    if row is not None:
        return row
    return next((c for c in MOCK_CONTACTS if c["contactid"] == contact_id and c.get("userid") == uid), None)


def get_participated_in(app_id):
    rows = query_db("""
        SELECT pi.*, cp.FullName, cp.Email
        FROM Participated_In pi
        JOIN Contact_Person cp ON pi.ContactID = cp.ContactID
        WHERE pi.AppID = %s
    """, (app_id,))
    if rows is not None:
        return rows
    result = [dict(p) for p in MOCK_PARTICIPATED_IN if p["appid"] == app_id]
    for p in result:
        contact = next((c for c in MOCK_CONTACTS if c["contactid"] == p["contactid"]), None)
        if contact:
            p["fullname"] = contact["fullname"]
            p["email"] = contact["email"]
    return result


# ---------------------------------------------------------------------------
# Routes — Dashboard
# ---------------------------------------------------------------------------

@app.route("/")
@login_required
def dashboard():
    apps = get_applications()
    all_interviews = get_interviews()
    user_app_ids = {a["appid"] for a in apps}
    interviews = [i for i in all_interviews if i["appid"] in user_app_ids]
    companies = get_companies()
    today = date.today()

    total = len(apps)
    by_status = {}
    for a in apps:
        s = a.get("status", "Draft")
        by_status[s] = by_status.get(s, 0) + 1

    upcoming_interviews = sorted(
        [i for i in interviews if i.get("date") and i["date"] >= today],
        key=lambda x: x["date"],
    )[:5]

    for iv in upcoming_interviews:
        app_match = next((a for a in apps if a["appid"] == iv["appid"]), None)
        if app_match:
            iv["jobtitle"] = app_match.get("jobtitle", "")
            iv["company_name"] = app_match.get("company_name", "")

    upcoming_deadlines = sorted(
        [a for a in apps if a.get("offerdeadline") and a["offerdeadline"] >= today],
        key=lambda x: x["offerdeadline"],
    )[:5]

    offers = by_status.get("Offer", 0)
    interviews_total = by_status.get("Interview", 0) + offers
    success_rate = round((offers / interviews_total * 100) if interviews_total else 0)

    # ── SQL GROUP BY: Applications per company ──
    apps_per_company_rows = query_db("""
        SELECT c.Name, COUNT(a.AppID) AS cnt
        FROM Application a
        JOIN Job_Posting jp ON a.PostingID = jp.PostingID
        JOIN Company c ON jp.CompanyID = c.CompanyID
        GROUP BY c.Name ORDER BY cnt DESC
    """)
    if apps_per_company_rows is not None:
        apps_per_company = {r["name"]: r["cnt"] for r in apps_per_company_rows}
    else:
        apps_per_company = {}
        for a in apps:
            name = a.get("company_name", "Unknown")
            apps_per_company[name] = apps_per_company.get(name, 0) + 1

    # ── SQL GROUP BY: Success rate by industry ──
    industry_rows = query_db("""
        SELECT ci.Industry,
               COUNT(a.AppID) AS total,
               SUM(CASE WHEN a.Status = 'Offer' THEN 1 ELSE 0 END) AS offers,
               ROUND(SUM(CASE WHEN a.Status = 'Offer' THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100) AS rate
        FROM Application a
        JOIN Job_Posting jp ON a.PostingID = jp.PostingID
        JOIN Company_Industry ci ON jp.CompanyID = ci.CompanyID
        GROUP BY ci.Industry ORDER BY total DESC
    """)
    if industry_rows is not None:
        industry_stats = {r["industry"]: {"total": r["total"], "offers": r["offers"], "rate": r["rate"]} for r in industry_rows}
    else:
        industry_stats = {}
        for a in apps:
            company = next((c for c in companies if c["name"] == a.get("company_name", "")), None)
            if not company:
                continue
            for ind in company.get("industries", []):
                if ind not in industry_stats:
                    industry_stats[ind] = {"total": 0, "offers": 0}
                industry_stats[ind]["total"] += 1
                if a.get("status") == "Offer":
                    industry_stats[ind]["offers"] += 1
        for ind in industry_stats:
            t = industry_stats[ind]["total"]
            o = industry_stats[ind]["offers"]
            industry_stats[ind]["rate"] = round((o / t * 100) if t else 0)

    # ── SQL AGGREGATION: Overall stats ──
    agg_row = query_db("""
        SELECT COUNT(*) AS total_apps,
               COUNT(DISTINCT jp.CompanyID) AS companies_applied,
               ROUND(COUNT(*)::numeric / NULLIF(COUNT(DISTINCT jp.CompanyID), 0), 1) AS avg_per_company
        FROM Application a
        JOIN Job_Posting jp ON a.PostingID = jp.PostingID
    """, one=True)
    agg_stats = agg_row if agg_row else {
        "total_apps": total,
        "companies_applied": len(apps_per_company),
        "avg_per_company": round(total / max(len(apps_per_company), 1), 1),
    }

    # ── DIVISION QUERY: Contacts who participated in ALL rounds of their apps ──
    division_rows = query_db("""
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
        )
        AND EXISTS (SELECT 1 FROM Participated_In pi3 WHERE pi3.ContactID = cp.ContactID)
    """)
    if division_rows is None:
        # Mock fallback: compute in Python
        division_rows = []
        contact_apps = {}
        for p in MOCK_PARTICIPATED_IN:
            cid = p["contactid"]
            if cid not in contact_apps:
                contact_apps[cid] = {}
            aid = p["appid"]
            if aid not in contact_apps[cid]:
                contact_apps[cid][aid] = set()
            contact_apps[cid][aid].add(p["roundnumber"])
        for cid, app_rounds in contact_apps.items():
            all_covered = True
            for aid, rounds in app_rounds.items():
                total_rounds_for_app = len([i for i in MOCK_INTERVIEWS if i["appid"] == aid])
                if len(rounds) < total_rounds_for_app:
                    all_covered = False
                    break
            if all_covered:
                contact = next((c for c in MOCK_CONTACTS if c["contactid"] == cid), None)
                if contact:
                    division_rows.append({"contactid": cid, "fullname": contact["fullname"]})

    return render_template(
        "dashboard.html",
        total=total,
        by_status=by_status,
        offers=offers,
        interviews_count=interviews_total,
        total_rounds=len(interviews),
        success_rate=success_rate,
        upcoming_interviews=upcoming_interviews,
        upcoming_deadlines=upcoming_deadlines,
        recent=apps[:5],
        apps_per_company=apps_per_company,
        industry_stats=industry_stats,
        agg_stats=agg_stats,
        division_contacts=division_rows,
    )


# ---------------------------------------------------------------------------
# Routes — Applications
# ---------------------------------------------------------------------------

@app.route("/applications")
@login_required
def applications():
    apps = get_applications()
    statuses = ["Draft", "Submitted", "Interview", "Offer", "Rejected"]

    # Filtering
    status_filter = request.args.get("status", "")
    search = request.args.get("search", "").lower()
    if status_filter:
        apps = [a for a in apps if a.get("status") == status_filter]
    if search:
        apps = [a for a in apps if search in a.get("jobtitle", "").lower() or search in a.get("company_name", "").lower()]

    # Sorting
    sort_by = request.args.get("sort", "")
    if sort_by == "date_asc":
        apps = sorted(apps, key=lambda a: a.get("submissiondate") or date.min)
    elif sort_by == "date_desc":
        apps = sorted(apps, key=lambda a: a.get("submissiondate") or date.min, reverse=True)
    elif sort_by == "status":
        status_order = {s: i for i, s in enumerate(statuses)}
        apps = sorted(apps, key=lambda a: status_order.get(a.get("status", "Draft"), 99))

    columns = {s: [a for a in apps if a.get("status") == s] for s in statuses}
    return render_template("applications.html", applications=apps, columns=columns, statuses=statuses)


@app.route("/applications/<int:app_id>")
@login_required
def application_detail(app_id):
    app_data = get_application(app_id)
    if not app_data:
        flash("Application not found.", "error")
        return redirect(url_for("applications"))
    interviews = get_interviews(app_id)
    documents = get_documents(app_id)
    notes = get_notes(app_id)
    contacts = get_contacts()
    participated = get_participated_in(app_id)
    company_contacts = [c for c in contacts if c.get("companyid") == app_data.get("companyid")]
    return render_template(
        "application_detail.html",
        app=app_data,
        interviews=interviews,
        documents=documents,
        notes=notes,
        contacts=company_contacts,
        participated=participated,
        today=date.today(),
    )


@app.route("/applications/<int:app_id>/status", methods=["POST"])
@login_required
def update_status(app_id):
    new_status = request.form.get("status")
    result = query_db(
        "UPDATE Application SET Status = %s WHERE AppID = %s",
        (new_status, app_id), commit=True,
    )
    if result is None:
        # mock fallback: update in-memory
        for a in MOCK_APPLICATIONS:
            if a["appid"] == app_id:
                a["status"] = new_status
    flash(f"Status updated to {new_status}.", "success")
    return redirect(request.referrer or url_for("applications"))


@app.route("/applications/<int:app_id>/delete", methods=["POST"])
@login_required
def delete_application(app_id):
    result = query_db("DELETE FROM Application WHERE AppID = %s", (app_id,), commit=True)
    if result is None:
        global MOCK_APPLICATIONS, MOCK_INTERVIEWS, MOCK_DOCUMENTS, MOCK_NOTES
        MOCK_APPLICATIONS = [a for a in MOCK_APPLICATIONS if a["appid"] != app_id]
        MOCK_INTERVIEWS = [i for i in MOCK_INTERVIEWS if i["appid"] != app_id]
        MOCK_DOCUMENTS = [d for d in MOCK_DOCUMENTS if d["appid"] != app_id]
        MOCK_NOTES = [n for n in MOCK_NOTES if n["appid"] != app_id]
    flash("Application deleted (cascaded).", "success")
    return redirect(url_for("applications"))


@app.route("/applications/new", methods=["GET", "POST"])
@login_required
def new_application():
    if request.method == "POST":
        status = request.form.get("status", "Draft")
        submission_date = request.form.get("submission_date") or None
        offer_deadline = request.form.get("offer_deadline") or None

        # --- Inline company creation ---
        new_company_name = request.form.get("new_company_name", "").strip()
        posting_id = request.form.get("posting_id")

        if new_company_name:
            # Create the company first
            comp_location = request.form.get("new_company_location", "")
            comp_website = request.form.get("new_company_website", "")
            comp_industries = request.form.get("new_company_industries", "")
            result = query_db(
                "INSERT INTO Company (Name, Location, Website) VALUES (%s, %s, %s) RETURNING CompanyID",
                (new_company_name, comp_location, comp_website), commit=False,
            )
            if result is None:
                company_id = max(c["companyid"] for c in MOCK_COMPANIES) + 1 if MOCK_COMPANIES else 1
                MOCK_COMPANIES.append({
                    "companyid": company_id, "name": new_company_name,
                    "location": comp_location, "website": comp_website,
                    "userid": session.get("user_id"),
                })
                for ind in [i.strip() for i in comp_industries.split(",") if i.strip()]:
                    MOCK_COMPANY_INDUSTRIES.append({"companyid": company_id, "industry": ind})
            else:
                company_id = result[0].get("companyid", 1)

            # Create the job posting for this company
            job_title = request.form.get("new_job_title", "").strip()
            job_location = request.form.get("new_job_location", "")
            job_salary = request.form.get("new_job_salary", "")
            job_deadline = request.form.get("new_job_deadline") or None
            job_description = request.form.get("new_job_description", "")

            result = query_db(
                """INSERT INTO Job_Posting (JobTitle, Location, Description, SalaryRange, DatePosted, ApplicationDeadline, CompanyID)
                   VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING PostingID""",
                (job_title or new_company_name + " Role", job_location or comp_location,
                 job_description, job_salary, date.today().isoformat(), job_deadline, company_id), commit=True,
            )
            if result is None:
                posting_id = max(p["postingid"] for p in MOCK_POSTINGS) + 1 if MOCK_POSTINGS else 1
                MOCK_POSTINGS.append({
                    "postingid": posting_id,
                    "jobtitle": job_title or new_company_name + " Role",
                    "location": job_location or comp_location,
                    "description": job_description, "salaryrange": job_salary,
                    "dateposted": date.today(),
                    "applicationdeadline": date.fromisoformat(job_deadline) if job_deadline else None,
                    "companyid": company_id, "company_name": new_company_name,
                })
            else:
                posting_id = result[0].get("postingid", 1)

        # --- Create the application ---
        result = query_db(
            "INSERT INTO Application (SubmissionDate, Status, OfferDeadline, PostingID) VALUES (%s, %s, %s, %s)",
            (submission_date, status, offer_deadline, posting_id), commit=True,
        )
        if result is None:
            posting = next((p for p in MOCK_POSTINGS if p["postingid"] == int(posting_id)), None)
            new_id = max(a["appid"] for a in MOCK_APPLICATIONS) + 1
            MOCK_APPLICATIONS.append({
                "appid": new_id, "submissiondate": date.fromisoformat(submission_date) if submission_date else None,
                "status": status, "offerdeadline": date.fromisoformat(offer_deadline) if offer_deadline else None,
                "postingid": int(posting_id),
                "jobtitle": posting["jobtitle"] if posting else "", "company_name": posting["company_name"] if posting else "",
                "location": posting["location"] if posting else "",
                "userid": session.get("user_id"),
            })

            # Create resume document if provided
            resume_filename = request.form.get("resume_filename", "").strip()
            if resume_filename:
                doc_id = max(d["docid"] for d in MOCK_DOCUMENTS) + 1 if MOCK_DOCUMENTS else 1
                MOCK_DOCUMENTS.append({
                    "docid": doc_id, "filename": resume_filename,
                    "filepath": f"/docs/resumes/{resume_filename}", "uploaddate": date.today(), "appid": new_id,
                })
                MOCK_RESUMES.append({"docid": doc_id, "version": request.form.get("resume_version", "1.0")})

            # Create cover letter document if provided
            cl_filename = request.form.get("cl_filename", "").strip()
            if cl_filename:
                doc_id = max(d["docid"] for d in MOCK_DOCUMENTS) + 1 if MOCK_DOCUMENTS else 1
                MOCK_DOCUMENTS.append({
                    "docid": doc_id, "filename": cl_filename,
                    "filepath": f"/docs/coverletters/{cl_filename}", "uploaddate": date.today(), "appid": new_id,
                })
                MOCK_COVER_LETTERS.append({"docid": doc_id, "tailoredcompanyname": request.form.get("cl_tailored", "")})

        flash("Application created.", "success")
        return redirect(url_for("applications"))
    postings = get_postings()
    companies = get_companies()
    return render_template("form_application.html", postings=postings, companies=companies)


@app.route("/applications/<int:app_id>/edit", methods=["GET", "POST"])
@login_required
def edit_application(app_id):
    app_data = get_application(app_id)
    if not app_data:
        flash("Application not found.", "error")
        return redirect(url_for("applications"))
    if request.method == "POST":
        status = request.form.get("status", app_data.get("status"))
        submission_date = request.form.get("submission_date") or None
        offer_deadline = request.form.get("offer_deadline") or None
        result = query_db(
            "UPDATE Application SET Status = %s, SubmissionDate = %s, OfferDeadline = %s WHERE AppID = %s",
            (status, submission_date, offer_deadline, app_id), commit=True,
        )
        if result is None:
            for a in MOCK_APPLICATIONS:
                if a["appid"] == app_id:
                    a["status"] = status
                    a["submissiondate"] = date.fromisoformat(submission_date) if submission_date else None
                    a["offerdeadline"] = date.fromisoformat(offer_deadline) if offer_deadline else None
        flash("Application updated.", "success")
        return redirect(url_for("application_detail", app_id=app_id))
    return render_template("form_edit_application.html", app=app_data)


# ---------------------------------------------------------------------------
# Routes — Directory (Companies, Contacts, Interviews, Documents)
# ---------------------------------------------------------------------------

@app.route("/contacts")
@login_required
def contacts_page():
    contacts = get_contacts()
    return render_template("contacts_list.html", contacts=contacts)

@app.route("/interviews")
@login_required
def interviews_page():
    applications = get_applications()
    app_map = {a["appid"]: a for a in applications}
    
    interviews = []
    # Fetch all interviews across all applications
    result = query_db("""
        SELECT i.*, 
            a.JobTitle as jobtitle, c.Name as company_name,
            array_agg(p.ContactID) as participant_ids
        FROM Interview_Round i
        JOIN Application a ON i.AppID = a.AppID
        JOIN Job_Posting jp ON a.PostingID = jp.PostingID
        JOIN Company c ON jp.CompanyID = c.CompanyID
        LEFT JOIN Participated_In p ON i.RoundNumber = p.RoundNumber AND i.AppID = p.AppID
        GROUP BY i.RoundNumber, i.AppID, a.JobTitle, c.Name
        ORDER BY i.Date DESC NULLS LAST, i.Time DESC NULLS LAST
    """)
    if result is not None:
        interviews = result
    else:
        # Mock fallback
        for app in applications:
            app_id = app["appid"]
            app_ivs = [iv.copy() for iv in MOCK_INTERVIEWS if iv["appid"] == app_id]
            for iv in app_ivs:
                iv["jobtitle"] = app.get("jobtitle", "")
                iv["company_name"] = app.get("company_name", "")
            interviews.extend(app_ivs)
        interviews.sort(key=lambda x: (x.get("date") or date.max, x.get("time") or time.max), reverse=True)
        
    return render_template("interviews_list.html", interviews=interviews)

@app.route("/documents")
@login_required
def documents_page():
    result = query_db("""
        SELECT d.*, a.JobTitle as jobtitle, c.Name as company_name,
               r.Version as resume_version, cl.TailoredCompanyName as cl_tailored
        FROM Document d
        JOIN Application a ON d.AppID = a.AppID
        JOIN Job_Posting jp ON a.PostingID = jp.PostingID
        JOIN Company c ON jp.CompanyID = c.CompanyID
        LEFT JOIN Resume r ON d.DocID = r.DocID
        LEFT JOIN Cover_Letter cl ON d.DocID = cl.DocID
        ORDER BY d.UploadDate DESC
    """)
    if result is not None:
        documents = result
    else:
        # Mock fallback
        documents = []
        apps = {a["appid"]: a for a in get_applications()}
        for doc in MOCK_DOCUMENTS:
            d = doc.copy()
            app = apps.get(d["appid"], {})
            d["jobtitle"] = app.get("jobtitle", "")
            d["company_name"] = app.get("company_name", "")
            
            res = next((r for r in MOCK_RESUMES if r["docid"] == d["docid"]), None)
            cl = next((c for c in MOCK_COVER_LETTERS if c["docid"] == d["docid"]), None)
            
            if res:
                d["resume_version"] = res.get("version")
            if cl:
                d["cl_tailored"] = cl.get("tailoredcompanyname")
                
            documents.append(d)
        documents.sort(key=lambda x: x.get("uploaddate") or date.min, reverse=True)

    return render_template("documents_list.html", documents=documents)


@app.route("/companies")
@login_required
def companies():
    company_list = get_companies()
    postings = get_postings()
    contacts = get_contacts()
    search = request.args.get("search", "").lower()
    industry = request.args.get("industry", "").lower()
    job_search = request.args.get("job_search", "").lower()
    if search:
        company_list = [c for c in company_list if search in c.get("name", "").lower() or search in c.get("location", "").lower()]
    if industry:
        company_list = [c for c in company_list if industry in " ".join(c.get("industries", [])).lower()]
    if job_search:
        postings = [p for p in postings if job_search in p.get("jobtitle", "").lower() or job_search in p.get("location", "").lower()]
    return render_template("companies.html", companies=company_list, postings=postings, contacts=contacts)


@app.route("/companies/<int:company_id>")
@login_required
def company_detail(company_id):
    company = get_company(company_id)
    if not company:
        flash("Company not found.", "error")
        return redirect(url_for("companies"))
    postings = [p for p in get_postings() if p.get("companyid") == company_id]
    contacts = [c for c in get_contacts() if c.get("companyid") == company_id]
    return render_template("company_detail.html", company=company, postings=postings, contacts=contacts)


@app.route("/companies/new", methods=["GET", "POST"])
@login_required
def new_company():
    if request.method == "POST":
        name = request.form.get("name")
        location = request.form.get("location")
        website = request.form.get("website")
        industries = request.form.get("industries", "")
        result = query_db(
            "INSERT INTO Company (Name, Location, Website) VALUES (%s, %s, %s) RETURNING CompanyID",
            (name, location, website), commit=False,
        )
        if result is None:
            new_id = max(c["companyid"] for c in MOCK_COMPANIES) + 1 if MOCK_COMPANIES else 1
            MOCK_COMPANIES.append({
                "companyid": new_id, "name": name, "location": location, "website": website,
                "userid": session.get("user_id"),
            })
            for ind in [i.strip() for i in industries.split(",") if i.strip()]:
                MOCK_COMPANY_INDUSTRIES.append({"companyid": new_id, "industry": ind})
        flash("Company added.", "success")
        return redirect(url_for("companies"))
    return render_template("form_company.html")


@app.route("/companies/<int:company_id>/edit", methods=["GET", "POST"])
@login_required
def edit_company(company_id):
    company = get_company(company_id)
    if not company:
        flash("Company not found.", "error")
        return redirect(url_for("companies"))
    if request.method == "POST":
        name = request.form.get("name")
        location = request.form.get("location")
        website = request.form.get("website")
        industries = request.form.get("industries", "")
        result = query_db(
            "UPDATE Company SET Name=%s, Location=%s, Website=%s WHERE CompanyID=%s",
            (name, location, website, company_id), commit=True,
        )
        if result is None:
            for c in MOCK_COMPANIES:
                if c["companyid"] == company_id:
                    c["name"] = name
                    c["location"] = location
                    c["website"] = website
            # update industries
            global MOCK_COMPANY_INDUSTRIES
            MOCK_COMPANY_INDUSTRIES = [i for i in MOCK_COMPANY_INDUSTRIES if i["companyid"] != company_id]
            for ind in [i.strip() for i in industries.split(",") if i.strip()]:
                MOCK_COMPANY_INDUSTRIES.append({"companyid": company_id, "industry": ind})
        flash("Company updated.", "success")
        return redirect(url_for("company_detail", company_id=company_id))
    return render_template("form_edit_company.html", company=company)


@app.route("/companies/<int:company_id>/delete", methods=["POST"])
@login_required
def delete_company(company_id):
    result = query_db("DELETE FROM Company WHERE CompanyID = %s", (company_id,), commit=True)
    if result is None:
        global MOCK_COMPANIES, MOCK_POSTINGS
        MOCK_COMPANIES = [c for c in MOCK_COMPANIES if c["companyid"] != company_id]
        MOCK_COMPANY_INDUSTRIES = [i for i in MOCK_COMPANY_INDUSTRIES if i["companyid"] != company_id]
        MOCK_POSTINGS = [p for p in MOCK_POSTINGS if p["companyid"] != company_id]
    flash("Company deleted.", "success")
    return redirect(url_for("companies"))


@app.route("/companies/<int:company_id>/jobs/new", methods=["GET", "POST"])
@login_required
def new_job(company_id):
    company = next((c for c in get_companies() if c.get("companyid") == company_id), None)
    if request.method == "POST":
        result = query_db(
            """INSERT INTO Job_Posting (JobTitle, Location, Description, SalaryRange, DatePosted, ApplicationDeadline, CompanyID)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (request.form["title"], request.form["location"], request.form.get("description", ""),
             request.form.get("salary", ""), request.form.get("date_posted", date.today().isoformat()),
             request.form.get("deadline") or None, company_id), commit=True,
        )
        if result is None:
            new_id = max(p["postingid"] for p in MOCK_POSTINGS) + 1
            MOCK_POSTINGS.append({
                "postingid": new_id, "jobtitle": request.form["title"], "location": request.form["location"],
                "description": request.form.get("description", ""), "salaryrange": request.form.get("salary", ""),
                "dateposted": date.today(), "applicationdeadline": date.fromisoformat(request.form["deadline"]) if request.form.get("deadline") else None,
                "companyid": company_id, "company_name": company["name"] if company else "",
            })
        flash("Job posting created.", "success")
        return redirect(url_for("company_detail", company_id=company_id))
    return render_template("form_job.html", company=company)


@app.route("/companies/<int:company_id>/jobs/<int:posting_id>/edit", methods=["GET", "POST"])
@login_required
def edit_job(company_id, posting_id):
    company = get_company(company_id)
    posting = get_posting(posting_id)
    if not posting:
        flash("Job posting not found.", "error")
        return redirect(url_for("company_detail", company_id=company_id))
    if request.method == "POST":
        result = query_db(
            """UPDATE Job_Posting SET JobTitle=%s, Location=%s, Description=%s,
               SalaryRange=%s, ApplicationDeadline=%s WHERE PostingID=%s""",
            (request.form["title"], request.form["location"], request.form.get("description", ""),
             request.form.get("salary", ""), request.form.get("deadline") or None, posting_id), commit=True,
        )
        if result is None:
            for p in MOCK_POSTINGS:
                if p["postingid"] == posting_id:
                    p["jobtitle"] = request.form["title"]
                    p["location"] = request.form["location"]
                    p["description"] = request.form.get("description", "")
                    p["salaryrange"] = request.form.get("salary", "")
                    p["applicationdeadline"] = date.fromisoformat(request.form["deadline"]) if request.form.get("deadline") else None
        flash("Job posting updated.", "success")
        return redirect(url_for("company_detail", company_id=company_id))
    return render_template("form_edit_job.html", company=company, posting=posting)


@app.route("/companies/<int:company_id>/jobs/<int:posting_id>/delete", methods=["POST"])
@login_required
def delete_job(company_id, posting_id):
    result = query_db("DELETE FROM Job_Posting WHERE PostingID = %s", (posting_id,), commit=True)
    if result is None:
        global MOCK_POSTINGS
        MOCK_POSTINGS = [p for p in MOCK_POSTINGS if p["postingid"] != posting_id]
    flash("Job posting deleted.", "success")
    return redirect(url_for("company_detail", company_id=company_id))


# ---------------------------------------------------------------------------
# Routes — Contacts
# ---------------------------------------------------------------------------

@app.route("/contacts/new", methods=["GET", "POST"])
@login_required
def new_contact():
    if request.method == "POST":
        result = query_db(
            """INSERT INTO Contact_Person (FullName, Email, Phone, LinkedInURL, CompanyID)
               VALUES (%s, %s, %s, %s, %s)""",
            (request.form["fullname"], request.form.get("email"), request.form.get("phone"),
             request.form.get("linkedin"), request.form.get("company_id")), commit=True,
        )
        if result is None:
            new_id = max(c["contactid"] for c in MOCK_CONTACTS) + 1
            comp = next((c for c in MOCK_COMPANIES if c["companyid"] == int(request.form.get("company_id", 0))), None)
            MOCK_CONTACTS.append({
                "contactid": new_id, "fullname": request.form["fullname"],
                "email": request.form.get("email"), "phone": request.form.get("phone"),
                "linkedinurl": request.form.get("linkedin"),
                "companyid": int(request.form.get("company_id", 0)),
                "company_name": comp["name"] if comp else "",
                "userid": session.get("user_id"),
            })
        flash("Contact added.", "success")
        return redirect(url_for("companies"))
    return render_template("form_contact.html", companies=get_companies())


@app.route("/contacts/<int:contact_id>/edit", methods=["GET", "POST"])
@login_required
def edit_contact(contact_id):
    contact = get_contact(contact_id)
    if not contact:
        flash("Contact not found.", "error")
        return redirect(url_for("companies"))
    if request.method == "POST":
        result = query_db(
            "UPDATE Contact_Person SET FullName=%s, Email=%s, Phone=%s, LinkedInURL=%s WHERE ContactID=%s",
            (request.form["fullname"], request.form.get("email"), request.form.get("phone"),
             request.form.get("linkedin"), contact_id), commit=True,
        )
        if result is None:
            for c in MOCK_CONTACTS:
                if c["contactid"] == contact_id:
                    c["fullname"] = request.form["fullname"]
                    c["email"] = request.form.get("email")
                    c["phone"] = request.form.get("phone")
                    c["linkedinurl"] = request.form.get("linkedin")
        flash("Contact updated.", "success")
        return redirect(url_for("companies"))
    return render_template("form_edit_contact.html", contact=contact, companies=get_companies())


@app.route("/contacts/<int:contact_id>/delete", methods=["POST"])
@login_required
def delete_contact(contact_id):
    result = query_db("DELETE FROM Contact_Person WHERE ContactID = %s", (contact_id,), commit=True)
    if result is None:
        global MOCK_CONTACTS, MOCK_PARTICIPATED_IN
        MOCK_CONTACTS = [c for c in MOCK_CONTACTS if c["contactid"] != contact_id]
        MOCK_PARTICIPATED_IN = [p for p in MOCK_PARTICIPATED_IN if p["contactid"] != contact_id]
    flash("Contact deleted.", "success")
    return redirect(request.referrer or url_for("companies"))


# ---------------------------------------------------------------------------
# Routes — Interviews
# ---------------------------------------------------------------------------

@app.route("/interviews/new", methods=["GET", "POST"])
@login_required
def new_interview():
    if request.method == "POST":
        app_id = int(request.form["app_id"])
        round_num = int(request.form.get("round_number", 1))
        result = query_db(
            """INSERT INTO Interview_Round (AppID, RoundNumber, Date, Time, Format, Feedback)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (app_id, round_num, request.form.get("date") or None,
             request.form.get("time") or None, request.form.get("format", ""),
             request.form.get("feedback")), commit=True,
        )
        if result is None:
            MOCK_INTERVIEWS.append({
                "appid": app_id, "roundnumber": round_num,
                "date": date.fromisoformat(request.form["date"]) if request.form.get("date") else None,
                "time": time.fromisoformat(request.form["time"]) if request.form.get("time") else None,
                "format": request.form.get("format", ""), "feedback": request.form.get("feedback"),
            })
            # Add participants if selected
            contact_ids = request.form.getlist("contact_ids")
            for cid in contact_ids:
                if cid:
                    MOCK_PARTICIPATED_IN.append({"contactid": int(cid), "appid": app_id, "roundnumber": round_num})
        flash("Interview round added.", "success")
        return redirect(url_for("application_detail", app_id=app_id))
    apps = get_applications()
    contacts = get_contacts()
    return render_template("form_interview.html", applications=apps, contacts=contacts)


@app.route("/interviews/<int:app_id>/<int:round_num>/edit", methods=["GET", "POST"])
@login_required
def edit_interview(app_id, round_num):
    interview = next((i for i in get_interviews(app_id) if i["roundnumber"] == round_num), None)
    if not interview:
        flash("Interview not found.", "error")
        return redirect(url_for("application_detail", app_id=app_id))
    if request.method == "POST":
        result = query_db(
            """UPDATE Interview_Round SET Date=%s, Time=%s, Format=%s, Feedback=%s
               WHERE AppID=%s AND RoundNumber=%s""",
            (request.form.get("date") or None, request.form.get("time") or None,
             request.form.get("format", ""), request.form.get("feedback"),
             app_id, round_num), commit=True,
        )
        if result is None:
            for i in MOCK_INTERVIEWS:
                if i["appid"] == app_id and i["roundnumber"] == round_num:
                    i["date"] = date.fromisoformat(request.form["date"]) if request.form.get("date") else None
                    i["time"] = time.fromisoformat(request.form["time"]) if request.form.get("time") else None
                    i["format"] = request.form.get("format", "")
                    i["feedback"] = request.form.get("feedback")
        flash("Interview updated.", "success")
        return redirect(url_for("application_detail", app_id=app_id))
    contacts = get_contacts()
    return render_template("form_edit_interview.html", interview=interview, app_id=app_id, contacts=contacts)


@app.route("/interviews/<int:app_id>/<int:round_num>/delete", methods=["POST"])
@login_required
def delete_interview(app_id, round_num):
    result = query_db("DELETE FROM Interview_Round WHERE AppID=%s AND RoundNumber=%s", (app_id, round_num), commit=True)
    if result is None:
        global MOCK_INTERVIEWS
        MOCK_INTERVIEWS = [i for i in MOCK_INTERVIEWS if not (i["appid"] == app_id and i["roundnumber"] == round_num)]
        global MOCK_PARTICIPATED_IN
        MOCK_PARTICIPATED_IN = [p for p in MOCK_PARTICIPATED_IN if not (p["appid"] == app_id and p["roundnumber"] == round_num)]
    flash("Interview round deleted.", "success")
    return redirect(url_for("application_detail", app_id=app_id))


# ---------------------------------------------------------------------------
# Routes — Documents
# ---------------------------------------------------------------------------

@app.route("/documents/new", methods=["GET", "POST"])
@login_required
def new_document():
    if request.method == "POST":
        app_id = int(request.form["app_id"])
        doc_type = request.form.get("doc_type", "Resume")
        result = query_db(
            """INSERT INTO Document (FileName, FilePath, UploadDate, AppID)
               VALUES (%s, %s, %s, %s)""",
            (request.form["filename"], request.form.get("filepath", ""),
             date.today().isoformat(), app_id), commit=True,
        )
        if result is None:
            new_id = max(d["docid"] for d in MOCK_DOCUMENTS) + 1 if MOCK_DOCUMENTS else 1
            MOCK_DOCUMENTS.append({
                "docid": new_id, "filename": request.form["filename"],
                "filepath": request.form.get("filepath", ""), "uploaddate": date.today(), "appid": app_id,
            })
            if doc_type == "Resume":
                MOCK_RESUMES.append({"docid": new_id, "version": request.form.get("version", "1.0")})
            elif doc_type == "Cover Letter":
                MOCK_COVER_LETTERS.append({"docid": new_id, "tailoredcompanyname": request.form.get("tailored", "")})
        flash("Document added.", "success")
        return redirect(url_for("application_detail", app_id=app_id))
    apps = get_applications()
    return render_template("form_document.html", applications=apps)


@app.route("/documents/<int:doc_id>/delete", methods=["POST"])
@login_required
def delete_document(doc_id):
    app_id = request.form.get("app_id", 0, type=int)
    result = query_db("DELETE FROM Document WHERE DocID = %s", (doc_id,), commit=True)
    if result is None:
        global MOCK_DOCUMENTS, MOCK_RESUMES, MOCK_COVER_LETTERS
        MOCK_DOCUMENTS = [d for d in MOCK_DOCUMENTS if d["docid"] != doc_id]
        MOCK_RESUMES = [r for r in MOCK_RESUMES if r["docid"] != doc_id]
        MOCK_COVER_LETTERS = [c for c in MOCK_COVER_LETTERS if c["docid"] != doc_id]
    flash("Document deleted.", "success")
    if app_id:
        return redirect(url_for("application_detail", app_id=app_id))
    return redirect(url_for("applications"))


# ---------------------------------------------------------------------------
# Routes — Notes (inline)
# ---------------------------------------------------------------------------

@app.route("/applications/<int:app_id>/notes", methods=["POST"])
@login_required
def add_note(app_id):
    note_text = request.form.get("note", "").strip()
    if not note_text:
        flash("Note cannot be empty.", "error")
        return redirect(url_for("application_detail", app_id=app_id))
    result = query_db(
        "INSERT INTO Application_Notes (AppID, Note) VALUES (%s, %s)",
        (app_id, note_text), commit=True,
    )
    if result is None:
        MOCK_NOTES.append({"appid": app_id, "note": note_text})
    flash("Note added.", "success")
    return redirect(url_for("application_detail", app_id=app_id))


@app.route("/applications/<int:app_id>/notes/delete", methods=["POST"])
@login_required
def delete_note(app_id):
    note_text = request.form.get("note", "")
    result = query_db(
        "DELETE FROM Application_Notes WHERE AppID = %s AND Note = %s",
        (app_id, note_text), commit=True,
    )
    if result is None:
        global MOCK_NOTES
        MOCK_NOTES = [n for n in MOCK_NOTES if not (n["appid"] == app_id and n["note"] == note_text)]
    flash("Note deleted.", "success")
    return redirect(url_for("application_detail", app_id=app_id))


# ---------------------------------------------------------------------------
# API-style route for Kanban drag-and-drop
# ---------------------------------------------------------------------------

@app.route("/api/applications/<int:app_id>/status", methods=["POST"])
@login_required
def api_update_status(app_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if not new_status:
        return jsonify({"error": "Missing status"}), 400
    result = query_db(
        "UPDATE Application SET Status = %s WHERE AppID = %s",
        (new_status, app_id), commit=True,
    )
    if result is None:
        for a in MOCK_APPLICATIONS:
            if a["appid"] == app_id:
                a["status"] = new_status
    return jsonify({"success": True, "status": new_status})


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, port=5001)
