import { Request, Response } from 'express';
import { dbManager } from '../db/db';

export const uploadResults = async (req: Request, res: Response): Promise<void> => {
  try {
    const testId = req.params.id ? parseInt(req.params.id, 10) : (req.body.test_id ? parseInt(req.body.test_id, 10) : null);
    const testName = req.body.test_name || req.body.testName || 'OMR Test';
    const rows = req.body.rows || [];

    if (!Array.isArray(rows) || rows.length === 0) {
      res.status(400).json({ success: false, error: 'Request body must contain non-empty "rows" array.' });
      return;
    }

    const insertedCount = await dbManager.addResults(testId, testName, rows);
    res.status(201).json({
      success: true,
      message: `Successfully pushed ${insertedCount} test result rows to database.`,
      inserted_count: insertedCount,
      test_id: testId
    });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
};

export const getResults = async (req: Request, res: Response): Promise<void> => {
  try {
    const testId = req.params.id ? parseInt(req.params.id, 10) : undefined;
    const results = await dbManager.getResults(testId);
    res.json({
      success: true,
      count: results.length,
      data: results
    });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
};
