# Sanjana OMR Express.js REST JSON API (PostgreSQL Backend)

This is an Express.js REST JSON API designed to replace Google Firestore with a PostgreSQL database for the **Sanjana OMR Python Desktop Application**.

## Features

- **PostgreSQL Database Storage**: Replaces Firestore to store tests and OMR CSV test results.
- **JSONB Data Storage**: Flexible storage for dynamic CSV rows produced by OMR scanner script.
- **Test Synchronization**: REST endpoints for full CRUD operations on tests.
- **Test Results Storage & Retrieval**: Endpoints for uploading and retrieving student test scores.
- **Graceful Fallback Mode**: If PostgreSQL is offline during development, operates safely in-memory so development is never blocked.

---

## Prerequisites

1. **Node.js** (v16+ recommended)
2. **PostgreSQL** installed locally or access to a PostgreSQL instance (e.g. Supabase, Render, ElephantSQL, or local service).

---

## Setup Instructions

1. **Install Dependencies**:
   ```bash
   cd express-api
   npm install
   ```

2. **Database Setup**:
   - Create a database in PostgreSQL:
     ```sql
     CREATE DATABASE sanjana_omr_db;
     ```
   - Run the SQL schema script in `db/schema.sql`:
     ```bash
     psql -U postgres -d sanjana_omr_db -f db/schema.sql
     ```
   *(Note: The API server will also automatically create missing tables on startup if permissions permit).*

3. **Configure Environment Variables**:
   Edit `.env` (or copy `.env.example` to `.env`) with your PostgreSQL connection parameters:
   ```ini
   PORT=5000
   PGHOST=localhost
   PGPORT=5432
   PGUSER=postgres
   PGPASSWORD=your_password
   PGDATABASE=sanjana_omr_db
   ```

4. **Start the API Server**:
   ```bash
   npm start
   ```
   Or for auto-reload development:
   ```bash
   npm run dev
   ```

5. **Run Endpoint Tests**:
   ```bash
   npm test
   ```

---

## API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/health` | API & PostgreSQL database connection status |
| `GET`  | `/api/tests` | List all tests from PostgreSQL |
| `GET`  | `/api/tests/:id` | Get details of a single test by ID |
| `POST` | `/api/tests` | Create a new test in PostgreSQL |
| `PUT`  | `/api/tests/:id` | Update test details in PostgreSQL |
| `DELETE` | `/api/tests/:id` | Delete a test and its results |
| `POST` | `/api/tests/:id/results` | Push OMR CSV rows for a test to PostgreSQL |
| `GET`  | `/api/tests/:id/results` | Fetch OMR results for a specific test |
| `POST` | `/api/results` | Push OMR CSV rows by test name/collection |
| `GET`  | `/api/results` | Fetch recent OMR test results across all tests |
