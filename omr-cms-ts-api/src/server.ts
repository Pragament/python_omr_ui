import express, { Request, Response } from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import apiRouter from './routes/api';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Welcome root endpoint
app.get('/api', (req: Request, res: Response) => {
  res.json({
    status: 'online',
    service: 'OMR Test Manager TypeScript CMS & ORM API',
    version: '1.0.0',
    endpoints: {
      cms_schema: 'GET /api/cms/schema',
      health: 'GET /api/health',
      tests: {
        list: 'GET /api/tests',
        get_one: 'GET /api/tests/:id',
        create: 'POST /api/tests',
        update: 'PUT /api/tests/:id',
        delete: 'DELETE /api/tests/:id'
      },
      results: {
        list_all: 'GET /api/results',
        list_by_test: 'GET /api/tests/:id/results',
        upload_for_test: 'POST /api/tests/:id/results',
        upload_batch: 'POST /api/results'
      }
    }
  });
});

// Mount API routes
app.use('/api', apiRouter);

// Start server
app.listen(PORT, () => {
  console.log(`🚀 Node.js & TypeScript CMS API running on port ${PORT}`);
  console.log(`📡 Base URL: http://localhost:${PORT}/api`);
});

export default app;
