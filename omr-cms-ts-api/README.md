# OMR Test Manager - Node.js & TypeScript CMS & ORM API

A modern, high-performance Node.js & TypeScript CMS and REST JSON API using Prisma ORM & Database Toolkit for **OMR Test Manager**, backed by PostgreSQL and SQLite.

---

## 🌟 Key Technologies

- **CMS & Framework**: Node.js, TypeScript, Express.js (Modular Content Schema Definitions)
- **Database Toolkit / ORM**: Prisma ORM & Database Toolkit (`prisma/schema.prisma`), SQLite / PostgreSQL
- **Architecture**: Modular Controller-Router-Service Pattern with Full TypeScript Type Safety

---

## 🚀 API Endpoints Overview

Base URL: `http://localhost:5000/api`

| Method | Endpoint | Description | Request Body | Response Format |
|---|---|---|---|---|
| `GET` | `/api/health` | API & Database Health Check | None | `{ status: "online", database: "Prisma..." }` |
| `GET` | `/api/cms/schema` | CMS Collection & Content Schema | None | `{ success: true, cms: { collections: [...] } }` |
| `GET` | `/api/tests` | Fetch all OMR tests | None | `{ success: true, count: number, data: [...] }` |
| `GET` | `/api/tests/:id` | Fetch single test details | None | `{ success: true, data: { id, name, ... } }` |
| `POST` | `/api/tests` | Create a new test | `{ name, date, template_folder }` | `{ success: true, data: { id, name, ... } }` |
| `PUT` | `/api/tests/:id` | Update test details | `{ name, date, template_folder }` | `{ success: true, data: { ... } }` |
| `DELETE` | `/api/tests/:id` | Delete test & associated results | None | `{ success: true, message: "Deleted" }` |
| `POST` | `/api/tests/:id/results` | Upload OMR CSV score rows | `{ test_id, test_name, rows: [...] }` | `{ success: true, inserted_count: number }` |
| `GET` | `/api/tests/:id/results` | Fetch student scores for test | None | `{ success: true, count: number, data: [...] }` |
| `POST` | `/api/results` | Batch upload score rows | `{ test_name, rows: [...] }` | `{ success: true, inserted_count: number }` |
| `GET` | `/api/results` | Fetch all OMR test results | None | `{ success: true, count: number, data: [...] }` |

---

## 🛠️ Setup & Running Instructions

### 1. Install Dependencies
```bash
npm install
```

### 2. Environment Configuration
Edit `.env` (or copy `.env.example` to `.env`):
```ini
PORT=5000
DATABASE_URL="file:./dev.db"

# For PostgreSQL production, use:
# DATABASE_URL="postgresql://postgres:postgres@localhost:5432/omr_db?schema=public"
```

### 3. Database ORM Migration (Prisma)
```bash
npm run db:push
```

### 4. Build & Start Server
- **Development (TypeScript execution)**:
  ```bash
  npm run dev
  ```
- **Production Build & Start**:
  ```bash
  npm run build
  npm start
  ```

### 5. Run Automated Tests
```bash
npm test
```

---

## 📁 Repository Structure

```
omr-cms-ts-api/
├── prisma/
│   └── schema.prisma         # Prisma ORM Database Models (Test & TestResult)
├── src/
│   ├── cms/
│   │   └── config.ts         # TypeScript CMS Schema & Content Collections Config
│   ├── controllers/
│   │   ├── testController.ts # TypeScript Controllers for Test Management
│   │   └── resultController.ts # TypeScript Controllers for OMR Results
│   ├── db/
│   │   └── db.ts             # Database ORM Toolkit Manager
│   ├── routes/
│   │   └── api.ts            # API Express Router
│   └── server.ts             # Main Server Entry Point
├── .env                      # Environment Variables
├── .env.example              # Environment Template
├── package.json              # Node.js Dependencies & Scripts
├── tsconfig.json             # TypeScript Compiler Configuration
├── test-api.ts               # TypeScript Automated Test Suite
└── README.md                 # Project Documentation
```
