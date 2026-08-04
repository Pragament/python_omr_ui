import { Request, Response } from 'express';
import { dbManager } from '../db/db';

export const getHealth = async (req: Request, res: Response): Promise<void> => {
  res.json({
    status: 'online',
    service: 'OMR TypeScript CMS & ORM API',
    database: 'Prisma / SQLite / PostgreSQL Ready',
    timestamp: new Date().toISOString()
  });
};

export const getTests = async (req: Request, res: Response): Promise<void> => {
  try {
    const tests = await dbManager.getAllTests();
    res.json({
      success: true,
      count: tests.length,
      data: tests
    });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
};

export const getTestById = async (req: Request, res: Response): Promise<void> => {
  try {
    const id = parseInt(req.params.id, 10);
    const test = await dbManager.getTestById(id);
    if (!test) {
      res.status(404).json({ success: false, error: 'Test not found' });
      return;
    }
    res.json({ success: true, data: test });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
};

export const createTest = async (req: Request, res: Response): Promise<void> => {
  try {
    const { name, date, template_folder, templateFolder } = req.body;
    const folder = template_folder || templateFolder;
    if (!name || !date || !folder) {
      res.status(400).json({ success: false, error: 'Missing required fields: name, date, template_folder' });
      return;
    }
    const newTest = await dbManager.createTest(name, date, folder);
    res.status(201).json({
      success: true,
      message: 'Test created successfully',
      data: newTest
    });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
};

export const updateTest = async (req: Request, res: Response): Promise<void> => {
  try {
    const id = parseInt(req.params.id, 10);
    const { name, date, template_folder, templateFolder } = req.body;
    const folder = template_folder || templateFolder;
    const updated = await dbManager.updateTest(id, name, date, folder);
    if (!updated) {
      res.status(404).json({ success: false, error: 'Test not found' });
      return;
    }
    res.json({
      success: true,
      message: 'Test updated successfully',
      data: updated
    });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
};

export const deleteTest = async (req: Request, res: Response): Promise<void> => {
  try {
    const id = parseInt(req.params.id, 10);
    const deleted = await dbManager.deleteTest(id);
    if (!deleted) {
      res.status(404).json({ success: false, error: 'Test not found' });
      return;
    }
    res.json({
      success: true,
      message: `Test ${id} deleted successfully`
    });
  } catch (error: any) {
    res.status(500).json({ success: false, error: error.message });
  }
};
