const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
const db = require('./db/db');
const testsRouter = require('./routes/tests');

dotenv.config();

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Request Logger
app.use((req, res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.originalUrl}`);
  next();
});

// Helper for API welcome / sitemap payload
const apiInfo = (req, res) => {
  res.json({
    status: 'online',
    service: 'OMR Express REST JSON API',
    postgresql_connected: db.isDbConnected(),
    endpoints: {
      health: 'GET /api/health',
      get_all_tests: 'GET /api/tests',
      get_single_test: 'GET /api/tests/:id',
      create_test: 'POST /api/tests',
      update_test: 'PUT /api/tests/:id',
      delete_test: 'DELETE /api/tests/:id',
      push_test_results: 'POST /api/tests/:id/results or POST /api/results',
      get_test_results: 'GET /api/tests/:id/results or GET /api/results'
    }
  });
};

// Root & /api Index Routes
app.get('/', apiInfo);
app.get('/api', apiInfo);

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({
    status: 'online',
    service: 'OMR Express API',
    postgresql_connected: db.isDbConnected(),
    timestamp: new Date().toISOString()
  });
});

// Mount Routes
app.use('/api', testsRouter);

// 404 Handler
app.use((req, res) => {
  res.status(404).json({ success: false, error: 'Endpoint not found' });
});

// Global Error Handler
app.use((err, req, res, next) => {
  console.error('Unhandled Server Error:', err);
  res.status(500).json({ success: false, error: 'Internal Server Error', message: err.message });
});

// Start Server with EADDRINUSE error handling
const server = app.listen(PORT, () => {
  console.log(`🚀 OMR Express REST JSON API running on port ${PORT}`);
  console.log(`📡 Base URL: http://localhost:${PORT}/api`);
});

server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    console.error(`\n❌ Error: Port ${PORT} is already in use by another process.`);
    console.error(`💡 Solution: Close any previous node server or run: taskkill /F /IM node.exe\n`);
  } else {
    console.error('Server error:', err);
  }
  process.exit(1);
});
