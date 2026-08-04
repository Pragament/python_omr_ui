# OMR Test Manager & Express.js REST JSON API (PostgreSQL Backend)

A complete solution for OMR (Optical Mark Recognition) test evaluation, featuring a cross-platform desktop GUI application (Python Tkinter) and an Express.js REST JSON API backed by PostgreSQL to manage tests and student score results.

---

## 🌟 Architecture Overview

```
 ┌──────────────────────────────────────────────┐
 │     OMR Test Manager (Python Desktop GUI)    │
 └──────────────────────┬───────────────────────┘
                        │ HTTP REST JSON API
 ┌──────────────────────▼───────────────────────┐
 │       Express.js REST API (Port 5000)        │
 └──────────────────────┬───────────────────────┘
                        │ SQL Connection Pool (JSONB)
 ┌──────────────────────▼───────────────────────┐
 │            PostgreSQL Database               │
 └──────────────────────────────────────────────┘
```

---

## 🚀 Key Features

### 📱 OMR Test Manager Desktop Application (`index.py`)
- **PostgreSQL Database Synchronization**: Switch between Local SQLite and PostgreSQL Database seamlessly.
- **PIN-Protected Access**: 6-digit PIN authentication (default: `123456`).
- **Test Management (CRUD)**: Create, edit, delete, and view tests synchronized with PostgreSQL via API.
- **Native 300 DPI PDF Converter**: Uses PyMuPDF (`fitz`) to convert OMR sheet PDFs to images with **zero external software dependencies**.
- **Template Auto-Discovery**: Automatically links templates (`answer_key.csv`, `evaluation.json`, `template.json`) with an intuitive `📁 Browse Dir` picker.
- **OMR Evaluation Engine (`main.py`)**: Evaluates OMR sheet images, scores student answers, and outputs `OMR_Results.csv`.
- **Upload & Inspect Database Scores**:
  - **`☁️ Push Results to PostgreSQL (API)`**: Uploads CSV score rows to PostgreSQL via Express API.
  - **`View DB Results for Selected Test`**: Queries PostgreSQL via Express API to inspect student score records.

### 🌐 Express.js REST JSON API (`express-api/`)
- **Full RESTful JSON Endpoints**: Endpoints for health status, test CRUD operations, and OMR CSV result uploads.
- **PostgreSQL & JSONB Storage**: Flexible storage for dynamic CSV columns produced by OMR scanner scripts.
- **Graceful Fallback Mode**: Operates in-memory safely if PostgreSQL is offline during local development.

---

## 📖 Express.js REST API Documentation

### Base URL: `http://localhost:5000/api`

### Endpoints Overview

| Method | Endpoint | Description | Request Body | Response Format |
|---|---|---|---|---|
| `GET` | `/api/health` | Service & DB Health Check | None | `{ status: "online", postgresql_connected: boolean }` |
| `GET` | `/api/tests` | Fetch all tests from PostgreSQL | None | `{ success: true, count: number, data: [...] }` |
| `GET` | `/api/tests/:id` | Fetch single test details | None | `{ success: true, data: { id, name, date, template_folder } }` |
| `POST` | `/api/tests` | Create a new test | `{ name, date, template_folder }` | `{ success: true, data: { id, name, ... } }` |
| `PUT` | `/api/tests/:id` | Update an existing test | `{ name, date, template_folder }` | `{ success: true, data: { ... } }` |
| `DELETE` | `/api/tests/:id` | Delete test & associated results | None | `{ success: true, message: "Deleted" }` |
| `POST` | `/api/tests/:id/results` | Upload OMR CSV score rows to test | `{ test_id, test_name, rows: [...] }` | `{ success: true, inserted_count: number }` |
| `GET` | `/api/tests/:id/results` | Fetch student scores for test | None | `{ success: true, count: number, data: [...] }` |
| `POST` | `/api/results` | Batch upload score rows | `{ test_name, rows: [...] }` | `{ success: true, inserted_count: number }` |

---

### Detailed API Request & Response Examples

#### 1. Service Health Check
- **Endpoint**: `GET /api/health`
- **Response**:
```json
{
  "status": "online",
  "service": "OMR Express API",
  "postgresql_connected": true,
  "timestamp": "2026-08-02T10:40:07.310Z"
}
```

#### 2. Create a Test
- **Endpoint**: `POST /api/tests`
- **Request Body**:
```json
{
  "name": "NEET Grand Test 1",
  "date": "2026-08-05",
  "template_folder": "neet_60_template"
}
```
- **Response**:
```json
{
  "success": true,
  "message": "Test created successfully",
  "data": {
    "id": 1,
    "name": "NEET Grand Test 1",
    "date": "2026-08-05",
    "template_folder": "neet_60_template",
    "created_at": "2026-08-02T10:40:07.337Z"
  }
}
```

#### 3. Upload OMR CSV Score Rows
- **Endpoint**: `POST /api/tests/1/results`
- **Request Body**:
```json
{
  "test_id": 1,
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
  "message": "Successfully pushed 2 test result rows to database.",
  "inserted_count": 2,
  "test_id": 1
}
```

#### 4. Fetch Student Results for Test
- **Endpoint**: `GET /api/tests/1/results`
- **Response**:
```json
{
  "success": true,
  "count": 2,
  "data": [
    {
      "id": 1,
      "test_id": 1,
      "test_name": "NEET Grand Test 1",
      "data": {
        "RollNo": "10001",
        "Name": "Student A",
        "Score": "95",
        "Correct": "25",
        "Incorrect": "5"
      },
      "uploaded_at": "2026-08-02T10:40:07.345Z"
    }
  ]
}
```

---

## 🛠️ Installation & Setup

### 1. Requirements
- **Python**: 3.7 or higher
- **Node.js**: v16 or higher
- **PostgreSQL**: (Optional for production; API includes in-memory dev mode if PostgreSQL is offline)

### 2. Express API Server Setup
```bash
cd express-api
npm install
npm start
```
*The Express API will run on `http://localhost:5000/api`.*

### 3. Python Application Setup
```bash
pip install -r requirements.txt
run_app.bat
```
*(Or run directly with `python index.py`)*

---

## 📖 How to Use the Application

1. **Login**: Launch the app using `run_app.bat` and enter the default 6-digit PIN **`123456`**.
2. **Add / Manage Tests**: Click **`➕ Add Test`** to create a test, choose a date, and select a template folder. The test automatically syncs with PostgreSQL.
3. **Process PDF OMR Sheet**:
   - Select your test and click **`📄 Input PDF`**.
   - Pick an OMR PDF sheet (e.g. `sample_omr_sheet.pdf`).
   - The app converts pages to images at 300 DPI and copies the template files.
4. **Run OMR Evaluation Engine**:
   - Click **`⚙️ Run OMR Command`**.
   - `main.py` evaluates the sheet images against `answer_key.csv` and displays student score rows in the preview box.
5. **Push to PostgreSQL**:
   - Click **`☁️ Push Results to PostgreSQL (API)`** to save the scores in PostgreSQL.
6. **View Database Results**:
   - Click **`View DB Results for Selected Test`** to query live scores stored in PostgreSQL.

---

## 🧪 Automated Testing

- **Node.js API Test Suite**: `node express-api/test-api.js`
- **Python App API Integration Suite**: `python test_python_app_api.py`

---

## 📂 Repository File Structure

```
.
├── index.py                 # Main Tkinter Desktop Application
├── main.py                  # OMR Evaluation Engine script
├── app_config.json          # Application configuration
├── requirements.txt         # Python dependencies (Pillow, PyMuPDF, pypdf)
├── run_app.bat              # One-click Windows batch launcher
├── test_python_app_api.py   # Python API integration test suite
├── express-api/             # Express.js REST JSON API Backend
│   ├── server.js            # Express server entry point
│   ├── routes/tests.js      # REST Router for tests & JSONB results
│   ├── db/db.js             # PostgreSQL connection pool & memory fallback
│   ├── db/schema.sql        # PostgreSQL DDL table definitions
│   ├── test-api.js          # API test suite
│   └── package.json         # Node.js dependencies
└── README.md                # Project documentation
```
