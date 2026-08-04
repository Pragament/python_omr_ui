const express = require('express');
const router = express.Router();
const db = require('../db/db');

// Strapi Users & Permissions Plugin - Google Auth Provider Endpoint (/api/auth/google & /api/auth/connect/google)
router.post(['/auth/google', '/auth/connect/google'], async (req, res) => {
  try {
    const { email, username } = req.body;
    if (!email) {
      return res.status(400).json({ error: { status: 400, name: 'ValidationError', message: 'Google email is required.' } });
    }
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail.endsWith('@gmail.com') || cleanEmail.length < 11) {
      return res.status(400).json({
        error: {
          status: 400,
          name: 'ForbiddenError',
          message: 'Access denied. Only valid @gmail.com accounts are permitted for Google Login.'
        }
      });
    }

    const strapiAuth = await db.authenticateStrapiGoogleUser(cleanEmail, username);
    res.json(strapiAuth);
  } catch (err) {
    res.status(400).json({ error: { status: 400, name: 'ApplicationError', message: err.message } });
  }
});

// Strapi Users & Permissions Plugin - Current User Profile Endpoint (/api/users/me)
router.get('/users/me', async (req, res) => {
  try {
    const email = req.query.email || '';
    const userMe = await db.getStrapiUserMe(email);
    res.json(userMe);
  } catch (err) {
    res.status(400).json({ error: { status: 400, name: 'ApplicationError', message: err.message } });
  }
});

// Get User Assigned Schools (test_editor role across multiple schools)
router.get('/user/schools', async (req, res) => {
  try {
    const email = req.query.email || '';
    const schools = await db.getUserSchools(email);
    res.json({ success: true, count: schools.length, data: schools });
  } catch (err) {
    res.status(400).json({ success: false, error: err.message });
  }
});

// List all Schools
router.get('/schools', async (req, res) => {
  try {
    const schools = await db.getUserSchools('');
    res.json({ success: true, count: schools.length, data: schools });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// GET Tests Scoped by School ID
router.get('/schools/:schoolId/tests', async (req, res) => {
  try {
    const { schoolId } = req.params;
    const tests = await db.getTestsBySchool(schoolId);
    res.json({ success: true, school_id: parseInt(schoolId, 10), count: tests.length, data: tests });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// Backward Compatible GET All Tests
router.get('/tests', async (req, res) => {
  try {
    const schoolId = req.query.school_id || 0;
    const tests = await db.getTestsBySchool(schoolId);
    res.json({ success: true, count: tests.length, data: tests });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// POST Create Test Scoped by School ID
router.post('/schools/:schoolId/tests', async (req, res) => {
  try {
    const { schoolId } = req.params;
    const { name, date, template_folder } = req.body;
    if (!name || !date || !template_folder) {
      return res.status(400).json({ success: false, error: 'Missing required fields: name, date, template_folder' });
    }
    const newTest = await db.createTestForSchool(schoolId, name, date, template_folder);
    res.status(201).json({
      success: true,
      message: 'Test created successfully for school',
      data: newTest
    });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// Backward Compatible POST Create Test
router.post('/tests', async (req, res) => {
  try {
    const schoolId = req.body.school_id || 1;
    const { name, date, template_folder } = req.body;
    if (!name || !date || !template_folder) {
      return res.status(400).json({ success: false, error: 'Missing required fields: name, date, template_folder' });
    }
    const newTest = await db.createTestForSchool(schoolId, name, date, template_folder);
    res.status(201).json({
      success: true,
      message: 'Test created successfully',
      data: newTest
    });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// PUT Update Test
router.put('/tests/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const { name, date, template_folder } = req.body;
    const updatedTest = await db.updateTest(id, name, date, template_folder);
    if (!updatedTest) {
      return res.status(404).json({ success: false, error: 'Test not found' });
    }
    res.json({ success: true, message: 'Test updated successfully', data: updatedTest });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// DELETE Test
router.delete('/tests/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const deleted = await db.deleteTest(id);
    if (!deleted) {
      return res.status(404).json({ success: false, error: 'Test not found' });
    }
    res.json({ success: true, message: `Test ${id} deleted successfully.` });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// POST OMR Results Scoped by School & Test ID
router.post('/schools/:schoolId/tests/:id/results', async (req, res) => {
  try {
    const { schoolId, id } = req.params;
    const { test_name, rows } = req.body;
    if (!Array.isArray(rows) || rows.length === 0) {
      return res.status(400).json({ success: false, error: 'Request body must contain non-empty "rows" array.' });
    }
    const insertedCount = await db.uploadResultsForSchool(schoolId, id, test_name || 'OMR Test', rows);
    res.status(201).json({
      success: true,
      message: `Successfully pushed ${insertedCount} test result rows for school.`,
      inserted_count: insertedCount,
      school_id: parseInt(schoolId, 10),
      test_id: parseInt(id, 10)
    });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// GET OMR Results Scoped by School & Test ID
router.get('/schools/:schoolId/tests/:id/results', async (req, res) => {
  try {
    const { schoolId, id } = req.params;
    const results = await db.getResultsForSchool(schoolId, id);
    res.json({
      success: true,
      school_id: parseInt(schoolId, 10),
      test_id: parseInt(id, 10),
      count: results.length,
      data: results
    });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

module.exports = router;
