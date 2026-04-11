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
from werkzeug.utils import secure_filename


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
            if sql.strip().upper().find("RETURNING") != -1:
                rows = cur.fetchall()
                conn.commit()
                return (rows[0] if rows else None) if one else rows
            else:
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
# MOCK DATA COMPLETELY REMOVED -- CONNECTING STRAIGHT TO POSTGRESQL
# ---------------------------------------------------------------------------



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


def login_required(f):
    """Redirect to /login if the user is not authenticated."""
    from functools import wraps
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
        user = query_db("SELECT * FROM App_User WHERE UserID = %s", (session["user_id"],), one=True)
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
        user = query_db("SELECT * FROM App_User WHERE Email = %s", (email,), one=True)
        if user and check_password(user["passwordhash"], password):
            session["user_id"] = user["userid"]
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
        else:
            existing = query_db("SELECT 1 FROM App_User WHERE Email = %s", (email,), one=True)
            if existing:
                flash("An account with that email already exists.", "error")
            else:
                hashed_pw = hash_password(password)
                query_db("INSERT INTO App_User (FullName, Email, PasswordHash) VALUES (%s, %s, %s)",
                         (fullname, email, hashed_pw), commit=True)
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
        return query_db("SELECT * FROM Company_Industry WHERE CompanyID = %s", (company_id,)) or []
    return query_db("SELECT * FROM Company_Industry") or []


def get_companies():
    uid = session.get("user_id")
    companies = query_db("SELECT * FROM Company WHERE UserID = %s ORDER BY Name", (uid,)) or []
    for c in companies:
        inds = get_company_industries(c["companyid"])
        c["industries"] = [i["industry"] for i in inds]
    return companies


def get_company(company_id):
    uid = session.get("user_id")
    row = query_db("SELECT * FROM Company WHERE CompanyID = %s AND UserID = %s", (company_id, uid), one=True)
    if row:
        row = dict(row)
        inds = get_company_industries(company_id)
        row["industries"] = [i["industry"] for i in inds]
    return row

def get_postings(search=None):
    uid = session.get("user_id")
    rows = query_db("""
        SELECT jp.*, c.Name AS company_name
        FROM Job_Posting jp JOIN Company c ON jp.CompanyID = c.CompanyID
        WHERE c.UserID = %s
        ORDER BY jp.DatePosted DESC
    """, (uid,))
    postings = rows or []
    if search:
        s = search.lower()
        postings = [p for p in postings if s in p.get("jobtitle", "").lower() or s in p.get("location", "").lower()]
    return postings


def get_posting(posting_id):
    uid = session.get("user_id")
    return query_db("""
        SELECT jp.*, c.Name AS company_name
        FROM Job_Posting jp JOIN Company c ON jp.CompanyID = c.CompanyID
        WHERE jp.PostingID = %s AND c.UserID = %s
    """, (posting_id, uid), one=True)

def get_applications():
    uid = session.get("user_id")
    return query_db("""
        SELECT a.*, jp.JobTitle AS jobtitle, c.Name AS company_name, jp.Location AS location
        FROM Application a
        JOIN Job_Posting jp ON a.PostingID = jp.PostingID
        JOIN Company c ON jp.CompanyID = c.CompanyID
        WHERE a.UserID = %s
        ORDER BY a.SubmissionDate DESC NULLS LAST
    """, (uid,)) or []

def get_application(app_id):
    uid = session.get("user_id")
    return query_db("""
        SELECT a.*, jp.JobTitle AS jobtitle, jp.Description AS job_description,
               jp.SalaryRange AS salaryrange, jp.Location AS location,
               jp.ApplicationDeadline AS applicationdeadline,
               c.Name AS company_name, c.Website AS company_website, c.CompanyID AS companyid
        FROM Application a
        JOIN Job_Posting jp ON a.PostingID = jp.PostingID
        JOIN Company c ON jp.CompanyID = c.CompanyID
        WHERE a.AppID = %s AND a.UserID = %s
    """, (app_id, uid), one=True)

def get_interviews(app_id=None):
    if app_id:
        return query_db("""
            SELECT * FROM Interview_Round WHERE AppID = %s ORDER BY RoundNumber
        """, (app_id,)) or []
    else:
        uid = session.get("user_id")
        return query_db("""
            SELECT ir.* FROM Interview_Round ir
            JOIN Application a ON ir.AppID = a.AppID
            WHERE a.UserID = %s
            ORDER BY ir.Date, ir.Time
        """, (uid,)) or []

def get_documents(app_id):
    rows = query_db("""
        SELECT d.*, r.Version, cl.TailoredCompanyName
        FROM Document d
        LEFT JOIN Resume r ON d.DocID = r.DocID
        LEFT JOIN Cover_Letter cl ON d.DocID = cl.DocID
        WHERE d.AppID = %s ORDER BY d.UploadDate
    """, (app_id,)) or []
    for doc in rows:
        if doc.get("version"):
            doc["type"] = "Resume"
        elif doc.get("tailoredcompanyname"):
            doc["type"] = "Cover Letter"
        else:
            doc["type"] = "Other"
    return rows

def get_notes(app_id):
    return query_db("SELECT * FROM Application_Notes WHERE AppID = %s", (app_id,)) or []
def get_contacts():
    uid = session.get("user_id")
    return query_db("""
        SELECT cp.*, c.Name AS company_name
        FROM Contact_Person cp JOIN Company c ON cp.CompanyID = c.CompanyID
        WHERE cp.UserID = %s
        ORDER BY cp.FullName
    """, (uid,)) or []

def get_contact(contact_id):
    uid = session.get("user_id")
    return query_db("SELECT cp.*, c.Name AS company_name FROM Contact_Person cp JOIN Company c ON cp.CompanyID = c.CompanyID WHERE cp.ContactID = %s AND cp.UserID = %s", (contact_id, uid), one=True)


def get_participated_in(app_id):
    return query_db("""
        SELECT pi.*, cp.FullName, cp.Email
        FROM Participated_In pi
        JOIN Contact_Person cp ON pi.ContactID = cp.ContactID
        WHERE pi.AppID = %s
    """, (app_id,)) or []


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
        WHERE a.UserID = %s
        GROUP BY c.Name ORDER BY cnt DESC
    """, (session.get("user_id"),)) or []
    apps_per_company = {r["name"]: r["cnt"] for r in apps_per_company_rows}

    # ── SQL GROUP BY: Success rate by industry ──
    industry_rows = query_db("""
        SELECT ci.Industry,
               COUNT(a.AppID) AS total,
               SUM(CASE WHEN a.Status = 'Offer' THEN 1 ELSE 0 END) AS offers,
               ROUND(SUM(CASE WHEN a.Status = 'Offer' THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100) AS rate
        FROM Application a
        JOIN Job_Posting jp ON a.PostingID = jp.PostingID
        JOIN Company_Industry ci ON jp.CompanyID = ci.CompanyID
        WHERE a.UserID = %s
        GROUP BY ci.Industry ORDER BY rate DESC
    """, (session.get("user_id"),)) or []
    industry_stats = {r["industry"]: {"total": r["total"], "offers": r["offers"], "rate": r["rate"]} for r in industry_rows}

    # ── SQL AGGREGATION: Overall stats ──
    agg_row = query_db("""
        SELECT COUNT(*) AS total_apps,
               COUNT(DISTINCT jp.CompanyID) AS companies_applied,
               ROUND(COUNT(*)::numeric / NULLIF(COUNT(DISTINCT jp.CompanyID), 0), 1) AS avg_per_company
        FROM Application a
        JOIN Job_Posting jp ON a.PostingID = jp.PostingID
        WHERE a.UserID = %s
    """, (session.get("user_id"),), one=True)
    agg_stats = agg_row if agg_row else {
        "total_apps": total,
        "companies_applied": len(apps_per_company),
        "avg_per_company": round(total / max(len(apps_per_company), 1), 1),
    }

    # ── DIVISION QUERY: Contacts who participated in ALL rounds of their apps ──
    division_rows = query_db("""
        SELECT cp.ContactID, cp.FullName
        FROM Contact_Person cp
        WHERE cp.UserID = %s
        AND NOT EXISTS (
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
    """, (session.get("user_id"),))
    if division_rows is None:
        division_rows = []

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
    uid = session.get("user_id")
    result = query_db(
        "UPDATE Application SET Status = %s WHERE AppID = %s AND UserID = %s",
        (new_status, app_id, uid), commit=True,
    )
    flash(f"Status updated to {new_status}.", "success")
    return redirect(request.referrer or url_for("applications"))


@app.route("/applications/<int:app_id>/delete", methods=["POST"])
@login_required
def delete_application(app_id):
    uid = session.get("user_id")
    query_db("DELETE FROM Application WHERE AppID = %s AND UserID = %s", (app_id, uid), commit=True)
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
            uid = session.get("user_id")
            result = query_db(
                "INSERT INTO Company (Name, Location, Website, UserID) VALUES (%s, %s, %s, %s) RETURNING CompanyID",
                (new_company_name, comp_location, comp_website, uid), commit=True,
            )
            if not result:
                flash("Error creating company.", "error")
                return redirect(url_for("new_application"))
            company_id = result[0].get("companyid")
            
            for ind in [i.strip() for i in comp_industries.split(",") if i.strip()]:
                query_db("INSERT INTO Company_Industry (CompanyID, Industry) VALUES (%s, %s)",
                         (company_id, ind), commit=True)

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
            if not result:
                flash("Error creating job posting.", "error")
                return redirect(url_for("new_application"))
            posting_id = result[0].get("postingid")

        # --- Create the application ---
        uid = session.get("user_id")
        result = query_db(
            "INSERT INTO Application (SubmissionDate, Status, OfferDeadline, PostingID, UserID) VALUES (%s, %s, %s, %s, %s) RETURNING AppID",
            (submission_date, status, offer_deadline, posting_id, uid), commit=True,
        )
        if not result:
            flash("Error creating application.", "error")
            return redirect(url_for("new_application"))
        new_app_id = result[0].get("appid")

        # Create resume document if provided
        resume_filename = request.form.get("resume_filename", "").strip()
        path = ""
        if 'resume_file' in request.files:
            file = request.files['resume_file']
            if file and file.filename:
                orig_filename = secure_filename(file.filename)
                upload_dir = os.path.join(app.root_path, 'static', 'uploads', 'docs')
                os.makedirs(upload_dir, exist_ok=True)
                file.save(os.path.join(upload_dir, orig_filename))
                path = f"/static/uploads/docs/{orig_filename}"
                if not resume_filename:
                    resume_filename = orig_filename
                    
        if not path and resume_filename:
            path = f"/docs/resumes/{resume_filename}"
            
        if resume_filename and path:
            res = query_db("INSERT INTO Document (FileName, FilePath, UploadDate, AppID) VALUES (%s, %s, %s, %s) RETURNING DocID",
                           (resume_filename, path, date.today(), new_app_id), commit=True)
            doc_id = res[0].get("docid") if res else 1
            query_db("INSERT INTO Resume (DocID, Version) VALUES (%s, %s)",
                     (doc_id, request.form.get("resume_version", "1.0")), commit=True)

        # Create cover letter document if provided
        cl_filename = request.form.get("cl_filename", "").strip()
        path = ""
        if 'cl_file' in request.files:
            file = request.files['cl_file']
            if file and file.filename:
                orig_filename = secure_filename(file.filename)
                upload_dir = os.path.join(app.root_path, 'static', 'uploads', 'docs')
                os.makedirs(upload_dir, exist_ok=True)
                file.save(os.path.join(upload_dir, orig_filename))
                path = f"/static/uploads/docs/{orig_filename}"
                if not cl_filename:
                    cl_filename = orig_filename
                    
        if not path and cl_filename:
            path = f"/docs/coverletters/{cl_filename}"

        if cl_filename and path:
            res = query_db("INSERT INTO Document (FileName, FilePath, UploadDate, AppID) VALUES (%s, %s, %s, %s) RETURNING DocID",
                           (cl_filename, path, date.today(), new_app_id), commit=True)
            doc_id = res[0].get("docid") if res else 1
            query_db("INSERT INTO Cover_Letter (DocID, TailoredCompanyName) VALUES (%s, %s)",
                     (doc_id, request.form.get("cl_tailored", "")), commit=True)

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
        query_db(
            "UPDATE Application SET Status = %s, SubmissionDate = %s, OfferDeadline = %s WHERE AppID = %s AND UserID = %s",
            (status, submission_date, offer_deadline, app_id, session.get("user_id")), commit=True,
        )
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
            jp.JobTitle as jobtitle, c.Name as company_name,
            array_agg(p.ContactID) as participant_ids
        FROM Interview_Round i
        JOIN Application a ON i.AppID = a.AppID
        JOIN Job_Posting jp ON a.PostingID = jp.PostingID
        JOIN Company c ON jp.CompanyID = c.CompanyID
        LEFT JOIN Participated_In p ON i.RoundNumber = p.RoundNumber AND i.AppID = p.AppID
        WHERE a.UserID = %s
        GROUP BY i.RoundNumber, i.AppID, jp.JobTitle, c.Name
        ORDER BY i.Date DESC NULLS LAST, i.Time DESC NULLS LAST
    """, (session.get("user_id"),))
    interviews = result or []
    return render_template("interviews_list.html", interviews=interviews)

@app.route("/documents")
@login_required
def documents_page():
    result = query_db("""
        SELECT d.*, jp.JobTitle as jobtitle, c.Name as company_name,
               r.Version as resume_version, cl.TailoredCompanyName as cl_tailored
        FROM Document d
        JOIN Application a ON d.AppID = a.AppID
        JOIN Job_Posting jp ON a.PostingID = jp.PostingID
        JOIN Company c ON jp.CompanyID = c.CompanyID
        LEFT JOIN Resume r ON d.DocID = r.DocID
        LEFT JOIN Cover_Letter cl ON d.DocID = cl.DocID
        WHERE a.UserID = %s
        ORDER BY d.UploadDate DESC
    """, (session.get("user_id"),))
    documents = result or []

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
        uid = session.get("user_id")
        result = query_db(
            "INSERT INTO Company (Name, Location, Website, UserID) VALUES (%s, %s, %s, %s) RETURNING CompanyID",
            (name, location, website, uid), commit=True,
        )
        company_id = result[0].get("companyid") if result else 1
        for ind in [i.strip() for i in industries.split(",") if i.strip()]:
            query_db("INSERT INTO Company_Industry (CompanyID, Industry) VALUES (%s, %s)",
                     (company_id, ind), commit=True)
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
        uid = session.get("user_id")
        query_db(
            "UPDATE Company SET Name=%s, Location=%s, Website=%s WHERE CompanyID=%s AND UserID=%s",
            (name, location, website, company_id, uid), commit=True,
        )
        # Update industries: delete old, insert new
        query_db("DELETE FROM Company_Industry WHERE CompanyID = %s", (company_id,), commit=True)
        for ind in [i.strip() for i in industries.split(",") if i.strip()]:
            query_db("INSERT INTO Company_Industry (CompanyID, Industry) VALUES (%s, %s)",
                     (company_id, ind), commit=True)
        flash("Company updated.", "success")
        return redirect(url_for("company_detail", company_id=company_id))
    return render_template("form_edit_company.html", company=company)


@app.route("/companies/<int:company_id>/delete", methods=["POST"])
@login_required
def delete_company(company_id):
    uid = session.get("user_id")
    query_db("DELETE FROM Company WHERE CompanyID = %s AND UserID = %s", (company_id, uid), commit=True)
    flash("Company deleted.", "success")
    return redirect(url_for("companies"))


@app.route("/companies/<int:company_id>/jobs/new", methods=["GET", "POST"])
@login_required
def new_job(company_id):
    company = get_company(company_id)
    if not company:
        flash("Company not found.", "error")
        return redirect(url_for("companies"))
    if request.method == "POST":
        query_db(
            """INSERT INTO Job_Posting (JobTitle, Location, Description, SalaryRange, DatePosted, ApplicationDeadline, CompanyID)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (request.form["title"], request.form["location"], request.form.get("description", ""),
             request.form.get("salary", ""), request.form.get("date_posted", date.today().isoformat()),
             request.form.get("deadline") or None, company_id), commit=True,
        )
        flash("Job posting created.", "success")
        return redirect(url_for("company_detail", company_id=company_id))
    return render_template("form_job.html", company=company)


@app.route("/companies/<int:company_id>/jobs/<int:posting_id>/edit", methods=["GET", "POST"])
@login_required
def edit_job(company_id, posting_id):
    company = get_company(company_id)
    posting = get_posting(posting_id)
    if not company or not posting:
        flash("Job posting or company not found.", "error")
        return redirect(url_for("companies"))
    if request.method == "POST":
        query_db(
            """UPDATE Job_Posting SET JobTitle=%s, Location=%s, Description=%s,
               SalaryRange=%s, ApplicationDeadline=%s WHERE PostingID=%s""",
            (request.form["title"], request.form["location"], request.form.get("description", ""),
             request.form.get("salary", ""), request.form.get("deadline") or None, posting_id), commit=True,
        )
        flash("Job posting updated.", "success")
        return redirect(url_for("company_detail", company_id=company_id))
    return render_template("form_edit_job.html", company=company, posting=posting)


@app.route("/companies/<int:company_id>/jobs/<int:posting_id>/delete", methods=["POST"])
@login_required
def delete_job(company_id, posting_id):
    # Verify the company belongs to this user
    company = get_company(company_id)
    if not company:
        flash("Company not found.", "error")
        return redirect(url_for("companies"))
    query_db("DELETE FROM Job_Posting WHERE PostingID = %s AND CompanyID = %s", (posting_id, company_id), commit=True)
    flash("Job posting deleted.", "success")
    return redirect(url_for("company_detail", company_id=company_id))


# ---------------------------------------------------------------------------
# Routes — Contacts
# ---------------------------------------------------------------------------

@app.route("/contacts/new", methods=["GET", "POST"])
@login_required
def new_contact():
    if request.method == "POST":
        uid = session.get("user_id")
        query_db(
            """INSERT INTO Contact_Person (FullName, Email, Phone, LinkedInURL, CompanyID, UserID)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (request.form["fullname"], request.form.get("email"), request.form.get("phone"),
             request.form.get("linkedin"), request.form.get("company_id"), uid), commit=True,
        )
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
        query_db(
            "UPDATE Contact_Person SET FullName=%s, Email=%s, Phone=%s, LinkedInURL=%s WHERE ContactID=%s AND UserID=%s",
            (request.form["fullname"], request.form.get("email"), request.form.get("phone"),
             request.form.get("linkedin"), contact_id, session.get("user_id")), commit=True,
        )
        flash("Contact updated.", "success")
        return redirect(url_for("companies"))
    return render_template("form_edit_contact.html", contact=contact, companies=get_companies())


@app.route("/contacts/<int:contact_id>/delete", methods=["POST"])
@login_required
def delete_contact(contact_id):
    uid = session.get("user_id")
    query_db("DELETE FROM Contact_Person WHERE ContactID = %s AND UserID = %s", (contact_id, uid), commit=True)
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
        # Verify ownership
        if not get_application(app_id):
            flash("Application not found.", "error")
            return redirect(url_for("applications"))
        round_num = int(request.form.get("round_number", 1))
        res = query_db(
            """INSERT INTO Interview_Round (AppID, RoundNumber, Date, Time, Format, Feedback)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (app_id, round_num, request.form.get("date") or None,
             request.form.get("time") or None, request.form.get("format", ""),
             request.form.get("feedback")), commit=True,
        )
        
        if res is None:
            flash("Error: Could not add interview round. Ensure the round number is unique and the date is after the application submission date.", "error")
            return redirect(url_for("application_detail", app_id=app_id))
            
        # Add participants if selected
        contact_ids = request.form.getlist("contact_ids")
        for cid in contact_ids:
            if cid:
                query_db("INSERT INTO Participated_In (ContactID, AppID, RoundNumber) VALUES (%s, %s, %s)",
                         (int(cid), app_id, round_num), commit=True)
                         
        flash("Interview round added.", "success")
        return redirect(url_for("application_detail", app_id=app_id))
    apps = get_applications()
    contacts = get_contacts()
    return render_template("form_interview.html", applications=apps, contacts=contacts)


@app.route("/interviews/<int:app_id>/<int:round_num>/edit", methods=["GET", "POST"])
@login_required
def edit_interview(app_id, round_num):
    # Verify ownership through application
    if not get_application(app_id):
        flash("Application not found.", "error")
        return redirect(url_for("applications"))
    interview = next((i for i in get_interviews(app_id) if i["roundnumber"] == round_num), None)
    if not interview:
        flash("Interview not found.", "error")
        return redirect(url_for("application_detail", app_id=app_id))
    if request.method == "POST":
        query_db(
            """UPDATE Interview_Round SET Date=%s, Time=%s, Format=%s, Feedback=%s
               WHERE AppID=%s AND RoundNumber=%s""",
            (request.form.get("date") or None, request.form.get("time") or None,
             request.form.get("format", ""), request.form.get("feedback"),
             app_id, round_num), commit=True,
        )
        flash("Interview updated.", "success")
        return redirect(url_for("application_detail", app_id=app_id))
    contacts = get_contacts()
    return render_template("form_edit_interview.html", interview=interview, app_id=app_id, contacts=contacts)


@app.route("/interviews/<int:app_id>/<int:round_num>/delete", methods=["POST"])
@login_required
def delete_interview(app_id, round_num):
    # Verify ownership through application
    if not get_application(app_id):
        flash("Application not found.", "error")
        return redirect(url_for("applications"))
    query_db("DELETE FROM Interview_Round WHERE AppID=%s AND RoundNumber=%s", (app_id, round_num), commit=True)
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
        # Verify ownership
        if not get_application(app_id):
            flash("Application not found.", "error")
            return redirect(url_for("applications"))
        doc_type = request.form.get("doc_type", "Resume")
        filename_input = request.form.get("filename", "").strip()
        db_filepath = ""

        if 'document_file' in request.files:
            file = request.files['document_file']
            if file and file.filename:
                orig_filename = secure_filename(file.filename)
                upload_dir = os.path.join(app.root_path, 'static', 'uploads', 'docs')
                os.makedirs(upload_dir, exist_ok=True)
                file_dest = os.path.join(upload_dir, orig_filename)
                file.save(file_dest)
                db_filepath = f"/static/uploads/docs/{orig_filename}"
                if not filename_input:
                    filename_input = orig_filename
        
        if not db_filepath:
            db_filepath = request.form.get("filepath", "")

        res = query_db(
            """INSERT INTO Document (FileName, FilePath, UploadDate, AppID)
               VALUES (%s, %s, %s, %s) RETURNING DocID""",
            (filename_input, db_filepath,
             date.today().isoformat(), app_id), commit=True,
        )
        doc_id = res[0].get("docid") if res else 1
        if doc_type == "Resume":
            query_db("INSERT INTO Resume (DocID, Version) VALUES (%s, %s)",
                     (doc_id, request.form.get("version", "1.0")), commit=True)
        elif doc_type == "Cover Letter":
            query_db("INSERT INTO Cover_Letter (DocID, TailoredCompanyName) VALUES (%s, %s)",
                     (doc_id, request.form.get("tailored", "")), commit=True)
                     
        flash("Document added.", "success")
        return redirect(url_for("application_detail", app_id=app_id))
    apps = get_applications()
    return render_template("form_document.html", applications=apps)


@app.route("/documents/<int:doc_id>/delete", methods=["POST"])
@login_required
def delete_document(doc_id):
    app_id = request.form.get("app_id", 0, type=int)
    # Verify ownership through application
    if app_id and not get_application(app_id):
        flash("Application not found.", "error")
        return redirect(url_for("applications"))
    query_db("DELETE FROM Document WHERE DocID = %s", (doc_id,), commit=True)
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
    # Verify ownership
    if not get_application(app_id):
        flash("Application not found.", "error")
        return redirect(url_for("applications"))
    note_text = request.form.get("note", "").strip()
    if not note_text:
        flash("Note cannot be empty.", "error")
        return redirect(url_for("application_detail", app_id=app_id))
    query_db(
        "INSERT INTO Application_Notes (AppID, Note) VALUES (%s, %s)",
        (app_id, note_text), commit=True,
    )
    flash("Note added.", "success")
    return redirect(url_for("application_detail", app_id=app_id))


@app.route("/applications/<int:app_id>/notes/delete", methods=["POST"])
@login_required
def delete_note(app_id):
    # Verify ownership
    if not get_application(app_id):
        flash("Application not found.", "error")
        return redirect(url_for("applications"))
    note_text = request.form.get("note", "")
    query_db(
        "DELETE FROM Application_Notes WHERE AppID = %s AND Note = %s",
        (app_id, note_text), commit=True,
    )
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
    uid = session.get("user_id")
    query_db(
        "UPDATE Application SET Status = %s WHERE AppID = %s AND UserID = %s",
        (new_status, app_id, uid), commit=True,
    )
    return jsonify({"success": True, "status": new_status})


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, port=5001)
