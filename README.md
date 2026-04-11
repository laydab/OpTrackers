# Professional Opportunity Tracker (OpTracker)

A Flask-based web application for tracking professional opportunities (job applications, interviews, contacts, etc.) with a PostgreSQL backend.

## Prerequisites

Before running the application, ensure you have the following installed on your system:

-   **Python 3.8+**
-   **PostgreSQL** (version 14 or higher recommended)
-   **Homebrew** (for easy installation of PostgreSQL on macOS)

## 1. Setting up PostgreSQL

The application requires a PostgreSQL database to run. If you don't have it running, the login page will fail silently.

### Start the PostgreSQL Service (macOS)

If you installed PostgreSQL via Homebrew, you can start it using:

```bash
# Start PostgreSQL (replace with your specific version if needed, e.g., postgresql@14)
brew services start postgresql
```

To verify it is running:
```bash
brew services list | grep postgresql
# You should see status 'started'
```

### Create the Database and Schema

Once PostgreSQL is running, you need to create the database and populate it with the schema and initial data.

1.  **Create the database**:
    ```bash
    createdb opportunity_tracker
    ```

2.  **Load the schema and seed data**:
    ```bash
    psql opportunity_tracker < schema.sql
    ```
    This command will create all the necessary tables, triggers, and populate the database with dummy data, including the demo user.

## 2. Setting up the Application Environment

It is recommended to use a Python virtual environment.

1.  **Create a virtual environment (optional but recommended)**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  **Install requirements**:
    The application requires Flask and psycopg2. Install them using pip:
    ```bash
    pip install Flask psycopg2-binary
    # Or, if you have a requirements.txt file:
    # pip install -r requirements.txt
    ```

## 3. Running the Application

Once the database is running and dependencies are installed, you can start the Flask application.

1.  **Start the server**:
    ```bash
    # Ensure you are in the project root directory
    flask run
    # OR
    python3 -m flask run
    ```
    *Note: To run in development mode with auto-reloading, use `flask --app app --debug run`*

2.  **Access the application**:
    Open your web browser and navigate to:
    ```
    http://127.0.0.1:5000
    ```

## 4. Default Login Credentials

After seeding the database with `schema.sql`, you can log in using the following demo credentials:

-   **Email**: `demo@optracker.com`
-   **Password**: `password123`

---
### Troubleshooting connection issues

If the app still fails to login or connect to the database, verify your environment variables. By default, the app looks for:
*   `DB_NAME` = "opportunity_tracker"
*   `DB_USER` = "postgres" (or your macOS username)
*   `DB_PASS` = ""
*   `DB_HOST` = "localhost"
*   `DB_PORT` = "5432"

If your local PostgreSQL requires a password or uses a different port, you can set them before running the app:
```bash
export DB_USER="your_username"
export DB_PASS="your_password"
flask run
```
