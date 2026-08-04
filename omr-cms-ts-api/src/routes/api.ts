import { Router } from 'express';
import {
  getHealth,
  getTests,
  getTestById,
  createTest,
  updateTest,
  deleteTest
} from '../controllers/testController';
import { uploadResults, getResults } from '../controllers/resultController';
import { CMSConfig } from '../cms/config';

const router = Router();

// CMS Schema & Collection Info Endpoint
router.get('/cms/schema', (req, res) => {
  res.json({ success: true, cms: CMSConfig });
});

// Health check
router.get('/health', getHealth);

// Test CRUD endpoints
router.get('/tests', getTests);
router.get('/tests/:id', getTestById);
router.post('/tests', createTest);
router.put('/tests/:id', updateTest);
router.delete('/tests/:id', deleteTest);

// OMR Result endpoints
router.post('/tests/:id/results', uploadResults);
router.get('/tests/:id/results', getResults);
router.post('/results', uploadResults);
router.get('/results', getResults);

export default router;
