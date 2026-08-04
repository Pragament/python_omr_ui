const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

const pool = new Pool({
  host: process.env.PGHOST || 'localhost',
  port: parseInt(process.env.PGPORT || '5432', 10),
  user: process.env.PGUSER || 'postgres',
  password: process.env.PGPASSWORD || 'postgres',
  database: process.env.PGDATABASE || 'omr_db',
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

let isPgConnected = false;

pool.on('connect', () => {
  isPgConnected = true;
});

pool.on('error', (err) => {
  isPgConnected = false;
  console.warn('⚠️ PostgreSQL connection warning:', err.message);
});

// ==================== STRAPI CMS COMPATIBLE MULTI-SCHOOL STORE ====================
const StrapiRoles = {
  TEST_EDITOR: {
    id: 3,
    name: 'test_editor',
    type: 'test_editor',
    description: 'Test Editor role for managing OMR tests across assigned schools'
  }
};

let mockSchools = [
  { id: 1, name: 'Pragathi Central School', code: 'PCS_HYD', createdAt: '2026-08-01T00:00:00.000Z' },
  { id: 2, name: 'Delhi Public School (DPS)', code: 'DPS_DELHI', createdAt: '2026-08-01T00:00:00.000Z' },
  { id: 3, name: 'St. Xavier High School', code: 'STX_MUMBAI', createdAt: '2026-08-01T00:00:00.000Z' },
  { id: 4, name: 'Greenwood International', code: 'GWI_BLR', createdAt: '2026-08-01T00:00:00.000Z' }
];

let mockUsers = [
  {
    id: 1,
    username: 'sreehasathota@gmail.com',
    email: 'sreehasathota@gmail.com',
    provider: 'google',
    confirmed: true,
    blocked: false,
    role: StrapiRoles.TEST_EDITOR,
    schoolIds: [1, 2, 3, 4]
  }
];

let mockTests = [
  { id: 1, school_id: 1, name: 'Pragathi Central School Annual NEET Test 2026', date: '2026-08-05', template_folder: 'neet_60_template', created_at: new Date().toISOString() },
  { id: 2, school_id: 1, name: 'Pragathi Central School Physics Midterm', date: '2026-08-01', template_folder: 'physics_template_v1', created_at: new Date().toISOString() },
  { id: 3, school_id: 2, name: 'DPS Chemistry Test 1', date: '2026-08-02', template_folder: 'chem_template_v1', created_at: new Date().toISOString() }
];

let mockResults = [
  { id: 1, test_id: 1, school_id: 1, test_name: 'Pragathi Central School Annual NEET Test 2026', data: { RollNo: 'PCS1001', Name: 'Student A', Score: '95', Correct: '25', Incorrect: '5' }, uploaded_at: new Date().toISOString() }
];

let nextTestId = 4;
let nextResultId = 2;

module.exports = {
  pool,
  isDbConnected: () => isPgConnected,

  // Strapi Users & Permissions Google OAuth Provider Handler
  authenticateStrapiGoogleUser: async (email, username, googleToken = '') => {
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail.endsWith('@gmail.com') || cleanEmail.length < 11) {
      throw new Error('Access denied. Only valid @gmail.com accounts are permitted for Google Login.');
    }

    let user = mockUsers.find(u => u.email.toLowerCase() === cleanEmail);
    if (!user) {
      // Create user in Strapi Users-Permissions plugin with test_editor role
      user = {
        id: mockUsers.length + 1,
        username: username || cleanEmail,
        email: cleanEmail,
        provider: 'google',
        confirmed: true,
        blocked: false,
        role: StrapiRoles.TEST_EDITOR,
        schoolIds: [1, 2, 3, 4]
      };
      mockUsers.push(user);
    }

    const assignedSchools = mockSchools.filter(s => user.schoolIds.includes(s.id));
    const jwtToken = `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.strapi_google_user_${user.id}_${Date.now()}`;

    return {
      jwt: jwtToken,
      user: {
        id: user.id,
        username: user.username,
        email: user.email,
        provider: user.provider,
        confirmed: user.confirmed,
        blocked: user.blocked,
        role: user.role,
        schools: assignedSchools
      }
    };
  },

  // Get Strapi Current Logged In User Profile (/api/users/me)
  getStrapiUserMe: async (email) => {
    const cleanEmail = email.trim().toLowerCase();
    const user = mockUsers.find(u => u.email.toLowerCase() === cleanEmail) || mockUsers[0];
    const assignedSchools = mockSchools.filter(s => user.schoolIds.includes(s.id));
    return {
      id: user.id,
      username: user.username,
      email: user.email,
      provider: user.provider,
      role: user.role,
      schools: assignedSchools
    };
  },

  // Get Accessible Schools for User by Email
  getUserSchools: async (email) => {
    const cleanEmail = email.trim().toLowerCase();
    if (cleanEmail && (!cleanEmail.endsWith('@gmail.com') || cleanEmail.length < 11)) {
      throw new Error('Access denied. Only valid @gmail.com accounts are permitted.');
    }
    const user = mockUsers.find(u => u.email.toLowerCase() === cleanEmail);
    if (!user) return mockSchools;
    return mockSchools.filter(s => user.schoolIds.includes(s.id));
  },

  // Get Tests Scoped by School ID
  getTestsBySchool: async (schoolId) => {
    const sId = parseInt(schoolId, 10);
    return mockTests.filter(t => !sId || t.school_id === sId);
  },

  // Create Test Scoped by School ID
  createTestForSchool: async (schoolId, name, date, template_folder) => {
    const newTest = {
      id: nextTestId++,
      school_id: parseInt(schoolId, 10) || 1,
      name,
      date,
      template_folder,
      created_at: new Date().toISOString()
    };
    mockTests.unshift(newTest);
    return newTest;
  },

  // Update Test
  updateTest: async (id, name, date, template_folder) => {
    const test = mockTests.find(t => t.id === parseInt(id, 10));
    if (!test) return null;
    test.name = name;
    test.date = date;
    test.template_folder = template_folder;
    return test;
  },

  // Delete Test
  deleteTest: async (id) => {
    const tId = parseInt(id, 10);
    const index = mockTests.findIndex(t => t.id === tId);
    if (index === -1) return false;
    mockTests.splice(index, 1);
    mockResults = mockResults.filter(r => r.test_id !== tId);
    return true;
  },

  // Upload OMR CSV Results Scoped by School & Test ID
  uploadResultsForSchool: async (schoolId, testId, testName, rows) => {
    const sId = parseInt(schoolId, 10) || 1;
    const tId = testId ? parseInt(testId, 10) : null;
    let count = 0;
    for (const row of rows) {
      mockResults.unshift({
        id: nextResultId++,
        test_id: tId,
        school_id: sId,
        test_name: testName,
        data: row,
        uploaded_at: new Date().toISOString()
      });
      count++;
    }
    return count;
  },

  // Get OMR Results Scoped by School / Test ID
  getResultsForSchool: async (schoolId, testId) => {
    const sId = parseInt(schoolId, 10);
    const tId = testId ? parseInt(testId, 10) : null;
    return mockResults.filter(r => {
      const matchSchool = !sId || r.school_id === sId;
      const matchTest = !tId || r.test_id === tId;
      return matchSchool && matchTest;
    });
  }
};
