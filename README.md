# OMR Test Manager & Multi-Backend REST API (Express.js & TypeScript Prisma)

A comprehensive, cross-platform solution for OMR (Optical Mark Recognition) test evaluation, featuring a Python Tkinter desktop application with native PDF processing, standalone Windows/macOS installer packaging, FCM parent push notifications, CSV verification tools, and dual REST API backends (Express.js JavaScript & TypeScript Prisma ORM) with PostgreSQL/SQLite multi-school support.

---

## 🌟 Architecture Overview

```
 ┌─────────────────────────────────────────────────────────────────────────┐
 │               OMR Test Manager (Python Desktop GUI App)                │
 │         index.py + Core Engine (src/ core.py, evaluation.py)            │
 └────────────────────────────────────┬────────────────────────────────────┘
                                      │ REST JSON API (HTTP / Google Auth)
                                      ▼
 ┌─────────────────────────────────────────────────────────────────────────┐
 │                       REST API Backend Options                          │
 │  ┌─────────────────────────────────┐   ┌─────────────────────────────┐  │
 │  │ Express.js REST API (Port 5000) │   │ Node.js/TypeScript Prisma   │  │
 │  │ (express-api/ + Multi-School)   │   │ CMS API (omr-cms-ts-api/)   │  │
 │  └────────────────┬────────────────┘   └──────────────┬──────────────┘  │
 └───────────────────┼───────────────────────────────────┼─────────────────┘
                     │ SQL Connection Pool (JSONB)       │ Prisma Client ORM
                     ▼                                   ▼
 ┌─────────────────────────────────────────────────────────────────────────┐
 │                     PostgreSQL / SQLite Database                        │
 └─────────────────────────────────────────────────────────────────────────┘
```

---

# PART 1: Technical & Developer Setup Guide

## 🚀 Key Features

### 📱 OMR Test Manager Desktop Application (`index.py` & `src/`)
- **PIN-Protected Access**: 6-digit PIN authentication (default: `123456`).
- **Multi-School & User Authentication**: Integrated Strapi Google OAuth and multi-tenant school access controls.
- **Database & API Synchronization**: Switch seamlessly between local SQLite and remote PostgreSQL via Express or Prisma REST APIs.
- **Native 300 DPI PDF Converter**: Powered by PyMuPDF (`fitz`) and `pypdf` to convert OMR sheet PDFs into high-resolution images with **zero external software dependencies**.
- **First-Page Answer Key Fallback**: Automatically extracts answer keys from page 1 of scanned PDFs.
- **Interactive Results Verifier**: Visual popup to inspect student OMR sheets side-by-side with correction comparison tables using Pillow.
- **FCM Push Notifications**: One-click FCM push notifications to parent devices via Google Cloud Firestore token lookups.
- **Executable Packaging**: Package as a standalone Windows executable (`.exe`) or macOS installer (`.dmg`) using PyInstaller (`build_installer.py`, `build_installer_win.bat`).

### 🌐 Express.js REST JSON API Backend (`express-api/`)
- **Multi-School Scoping**: Multi-tenant database design supporting test management across multiple assigned schools.
- **Strapi Users & Permissions Integration**: Support for Google OAuth login and user profile management (`/api/auth/google`, `/api/users/me`).
- **PostgreSQL & JSONB Storage**: Flexible schema for dynamic CSV columns produced by OMR scanner scripts.
- **Graceful Fallback Mode**: Functions in-memory safely if PostgreSQL is offline during local development.

### 🔷 TypeScript & Prisma CMS API Backend (`omr-cms-ts-api/`)
- **Type-Safe Controllers & Services**: Full TypeScript API built with Express and Prisma ORM Toolkit (`prisma/schema.prisma`).
- **Dual Database Support**: Configuration for SQLite (`dev.db`) and PostgreSQL.
- **CMS Content Schema**: Collection schema endpoints (`/api/cms/schema`).

---

## 🛠️ Installation & Setup Instructions

### 1. Requirements
- **Python**: 3.7 or higher
- **Node.js**: v16 or higher
- **PostgreSQL**: (Optional for production; APIs include in-memory and SQLite dev modes)

### 2. Desktop Application Launch
```bash
pip install -r requirements.txt
python index.py
```
*(Or double-click **`run_app.bat`** on Windows)*

### 3. Build Standalone Windows Executable (`.exe`)
To package the desktop application into a single executable to send to school computers:
```cmd
build_installer_win.bat
```
The output file **`dist/OMRTestManager.exe`** can be copied and run on any Windows PC without Python pre-installed.

---

## 💻 Developer & Backend API Setup Guide

### Option A: Express.js JavaScript API (`express-api/`)
```bash
cd express-api
npm install
npm start
```
*The Express API will run on `http://localhost:5000/api`.*

### Option B: Node.js & TypeScript Prisma CMS API (`omr-cms-ts-api/`)
```bash
cd omr-cms-ts-api
npm install
cp .env.example .env
npm run db:push
npm run dev
```
*The Prisma CMS API will run on `http://localhost:5000/api`.*

---

## 📖 Express.js & Strapi REST API Documentation

### Base URL: `http://localhost:5000/api`

### Endpoints Reference

| Category | Method | Endpoint | Description | Request Body / Query |
|---|---|---|---|---|
| **Health** | `GET` | `/api/health` | API & DB status | None |
| **Auth** | `POST` | `/api/auth/google` | Strapi Google OAuth Auth | `{ email, username }` |
| **Auth** | `GET` | `/api/users/me` | Current user profile | `?email=user@gmail.com` |
| **Schools** | `GET` | `/api/user/schools` | Assigned user schools | `?email=user@gmail.com` |
| **Schools** | `GET` | `/api/schools` | List all schools | None |
| **Tests** | `GET` | `/api/schools/:schoolId/tests` | Fetch tests for school | None |
| **Tests** | `POST` | `/api/schools/:schoolId/tests` | Create test for school | `{ name, date, template_folder }` |
| **Tests** | `GET` | `/api/tests` | Fetch all tests | `?school_id=1` |
| **Tests** | `GET` | `/api/tests/:id` | Fetch test by ID | None |
| **Tests** | `POST` | `/api/tests` | Create new test | `{ name, date, template_folder, school_id }` |
| **Tests** | `PUT` | `/api/tests/:id` | Update test details | `{ name, date, template_folder }` |
| **Tests** | `DELETE` | `/api/tests/:id` | Delete test & results | None |
| **Results** | `POST` | `/api/schools/:schoolId/tests/:id/results` | Upload school test scores | `{ test_name, rows: [...] }` |
| **Results** | `GET` | `/api/schools/:schoolId/tests/:id/results` | Fetch school test scores | None |
| **Results** | `POST` | `/api/tests/:id/results` | Upload test scores | `{ test_name, rows: [...] }` |
| **Results** | `GET` | `/api/tests/:id/results` | Fetch test scores | None |

---

### Request & Response Examples

#### 1. Service Health Check
- **Endpoint**: `GET /api/health`
- **Response**:
```json
{
  "status": "online",
  "service": "OMR Express API",
  "postgresql_connected": true,
  "timestamp": "2026-08-22T10:40:00.000Z"
}
```

#### 2. Strapi Google OAuth Login
- **Endpoint**: `POST /api/auth/google`
- **Request Body**:
```json
{
  "email": "teacher@gmail.com",
  "username": "Teacher User"
}
```
- **Response**:
```json
{
  "jwt": "mock-strapi-jwt-token",
  "user": {
    "id": 1,
    "username": "Teacher User",
    "email": "teacher@gmail.com",
    "role": { "id": 3, "name": "test_editor" }
  }
}
```

#### 3. Upload OMR CSV Score Rows
- **Endpoint**: `POST /api/schools/1/tests/1/results`
- **Request Body**:
```json
{
  "test_name": "NEET Grand Test 1",
  "rows": [
    { "RollNo": "10001", "Name": "Student A", "Score": "95", "Correct": "25", "Incorrect": "5" },
    { "RollNo": "10002", "Name": "Student B", "Score": "88", "Correct": "23", "Incorrect": "4" }
  ]
}
```
- **Response**:
```json
{
  "success": true,
  "message": "Successfully pushed 2 test result rows for school.",
  "inserted_count": 2,
  "school_id": 1,
  "test_id": 1
}
```

---

## 🧪 Automated Testing

Run the automated integration and unit test suites:

- **Python API & DB Integration Suite**:
  ```bash
  python test_python_app_api.py
  ```
- **Multi-School & Strapi Google Auth Test**:
  ```bash
  python test_multi_school_api.py
  ```
- **Node.js Express API Test Suite**:
  ```bash
  node express-api/test-api.js
  ```
- **TypeScript Prisma API Test Suite**:
  ```bash
  cd omr-cms-ts-api && npm test
  ```

---

# PART 2: End-User Manual & Operating Guide (for Schools / Staff)

## 1. Setup & Requirements
* Install Python on your Windows or Mac system.
* Install requirements: `pip install -r requirements.txt`.
* Run the app: double-click `run_app.bat` or run `python index.py`.

## 2. Configuration & Preferences
1. Log in using your 6-digit PIN (Default: `123456`).
2. In the menu bar, go to **Settings → Preferences**.
3. Configure the folders:
   * **Input Directory**: Folder where scanned pages are prepared.
   * **Output Directory**: Folder where graded CSV results are saved.
   * **Templates Folder**: Choose the template folder (e.g. `samples`).
   * **Python Command**: Path to main.py script (`python main.py --inputDir {input} --outputDir {output}`).
   * **Firestore Auth Key**: Browse and load Google Cloud credentials JSON file.
4. Click **Save**.

## 3. Standard Workflow (How to process exams)

### Step A: Add a Test Exam
1. Click **Add Test** on the dashboard.
2. Enter the **Test Name** and **Date (YYYY-MM-DD)**.
3. Select the appropriate layout template from the **Template Folder** dropdown.
4. Click **Save**.

### Step B: Load and Convert the Scan PDF
1. Select your test from the left-hand menu.
2. Click **Input PDF**.
3. Choose the scanned PDF containing student answer sheets.
4. Confirm page count. The app automatically splits pages into high-res images and copies the layout template.

### Step C: Run OMR Grading
1. Click **Run Command**.
2. Click **Yes** to confirm.
3. The OMR engine grades the sheets. Score results will display in the right panel table preview.

### Step D: Verify Results (Optional)
1. Click **Verify CSV** to open the interactive visualizer.
2. Step page by page to review student OMR bubbles side-by-side with correction comparison tables.

### Step E: Export Results (Optional)
1. Click **Export CSV**.
2. Select a save location on your device to export a clean CSV.

### Step F: Push FCM Notifications / Cloud Sync
1. Click **Notify All Parents** to send FCM push notifications to registered parent devices.
2. Click **Push Results to API** to save scores in the database.

---

# PART 3: AI Pair Programming History & Prompt Log

This section details historical developer steps, prompts, commits, and debugging processes:

## Step 1: macOS Compatibility & Firestore Bug Fixes
* Added platform-specific configuration keys (`_darwin`, `_win32`) in `SettingsManager` to support multi-platform user environments, fixed Poppler paths, and cleared Firestore variable NameErrors. (`Commit: 82dd9bd`)

## Step 2: CSV Preview Formatting & Indentation Error
* Filtered path columns from CSV preview, formatted file labels, and resolved start-up indent block issue.

## Step 3: Documentation Separation
* Restructured documentation into developer setup (Part 1) and end-user setup (Part 2) guides.

## Step 4: Standalone Packaging & Eliminating Poppler
* Replaced `pdf2image` with `pymupdf` (pure python PDF library) to eliminate external Poppler dependencies. (`Commit: 758897a`)

## Step 5: Windows Executable & CI Build Errors
* Added `build_installer_win.bat` for local Windows compiling and created a GitHub Actions workflow (`build.yml`). (`Commit: 860c3c9`)

## Step 6: OMR Refinements, Directory Isolation, and Crash Fixes
* Isolated test folders by test ID, fixed relative path alignment issues, disabled OpenCV thread debug popups, recursive template scanning, and resolved a page_count `NameError` crash. (`Commits: 7f76f8f to 8f2a2ca`)

## Step 7: Packaging and Distributing Installers
* Successfully compiled macOS `.dmg` installer locally and verified Windows `.exe` automated build.

## Step 8: Project Completion & Installer Distribution
* Generated and validated final installers on macOS (`.dmg`) and Windows (`.exe` via GitHub Actions) and submitted PR #4.

## Step 9: Option Analysis, 60Q Template, and Robust Answer Key Validation
* Created 60-question `Standard_Template` layout, added post-processing Option Analysis report generator (`Option_Analysis.csv`), and modified answer key verification. (`Commit: 2fa619b`)

## Step 10: PyInstaller Frozen Dynamic Loader Fix
* Registered built-in OMR Checker processor classes (CropOnMarkers, CropPage, FeatureBasedAlignment, Levels, MedianBlur, GaussianBlur) to prevent binary crashes. (`Commit: 93b6345`)

## Step 11: Auto-Extract Answer Key, Option Analysis Filtering, & GUI/Firestore Exclusions
* Implemented automatic answer key extraction from first page of scanned PDF. (`Commit: 8ee0a0a`)

## Step 12: FCM Push Notifications for Parents
* Added GUI "Notify All Parents" button and FCM v1 REST API background notification delivery logic.

## Step 13: Export CSV, Results Verifier, and First-Page Answer Key Fallback
* Implemented Export CSV formatting, responsive sheet visualizer, first-page answer key fallback, and dynamic question mapping. (`Commit: 2a44993`)

## Step 14: Multi-Backend REST API & Documentation Verification
* Added Express.js PostgreSQL/SQLite API with Multi-School scoping and Strapi Google OAuth Auth, Node.js TypeScript Prisma CMS API (`omr-cms-ts-api`), PyMuPDF dependency fix in `requirements.txt`, installer build scripts, and complete API endpoint documentation.

---

## 📂 Repository File Structure

```
.
├── index.py                 # Main Tkinter Desktop Application UI & API client
├── main.py                  # CLI entry point for OMR evaluation script
├── build_installer.py       # PyInstaller cross-platform build script
├── build_installer_win.bat  # One-click Windows .exe builder script
├── run_app.bat              # One-click Windows batch launcher
├── app_config.json          # Desktop application configuration
├── requirements.txt         # Python dependencies (pymupdf, pypdf, pdf2image, Pillow, etc.)
├── test_python_app_api.py   # Python API & DB integration test suite
├── test_multi_school_api.py # Python Multi-School & Strapi Auth test suite
├── src/                     # Core Python OMR engine package
│   ├── core.py              # Main OMR image processing pipeline
│   ├── evaluation.py        # Answer evaluation and grading logic
│   ├── entry.py             # Execution entry logic
│   ├── template.py          # OMR template parser & helper methods
│   ├── logger.py            # Console & file logging helper
│   ├── constants/           # OMR processing constants
│   ├── defaults/            # Default template configurations
│   ├── processors/          # Custom image processing utilities
│   ├── schemas/             # JSON validation schemas
│   ├── utils/               # Image & File IO utilities
│   └── tests/               # Core engine unit tests
├── express-api/             # Express.js REST JSON API Backend
│   ├── server.js            # Express server entry point
│   ├── routes/tests.js      # REST Router for tests, schools & results
│   ├── db/db.js             # PostgreSQL connection pool & mock DB fallback
│   ├── db/schema.sql        # PostgreSQL DDL table definitions
│   ├── test-api.js          # API test suite
│   └── package.json         # Node.js dependencies
├── omr-cms-ts-api/          # TypeScript Node.js CMS & Prisma ORM API
│   ├── prisma/              # Prisma schema models (Test & TestResult)
│   ├── src/                 # Controllers, CMS configs, DB managers, routes
│   ├── test-api.ts          # TypeScript API test suite
│   ├── package.json         # Node.js dependencies & scripts
│   └── tsconfig.json        # TypeScript compiler options
├── samples/                 # Sample OMR PDF templates & sheets
└── README.md                # Project documentation
```
