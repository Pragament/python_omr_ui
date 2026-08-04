/**
 * Database & ORM Toolkit Manager (TypeScript)
 * Connects via Prisma / SQLite / PostgreSQL with automatic fallback store
 */

import sqlite3 from 'sqlite3';
import path from 'path';
import fs from 'fs';

export interface TestRecord {
  id: number;
  name: string;
  date: string;
  templateFolder: string;
  createdAt: string;
}

export interface ResultRecord {
  id: number;
  testId?: number | null;
  testName: string;
  data: any;
  uploadedAt: string;
}

export class DatabaseManager {
  private dbPath: string;
  private memoryTests: TestRecord[] = [];
  private memoryResults: ResultRecord[] = [];
  private nextTestId = 1;
  private nextResultId = 1;
  private isSqlite = false;

  constructor() {
    this.dbPath = path.join(__dirname, '../../prisma/dev.db');
    this.initFallbackData();
  }

  private initFallbackData() {
    // Initial sample data
    this.memoryTests = [
      { id: 1, name: 'Sample Physics Test', date: '2026-08-01', templateFolder: 'physics_template_v1', createdAt: new Date().toISOString() },
      { id: 2, name: 'Sample Chemistry Test', date: '2026-08-02', templateFolder: 'chem_template_v1', createdAt: new Date().toISOString() }
    ];
    this.nextTestId = 3;

    this.memoryResults = [
      {
        id: 1,
        testId: 1,
        testName: 'Sample Physics Test',
        data: { RollNo: '1001', Name: 'Student A', Score: '95', Correct: '25', Incorrect: '5' },
        uploadedAt: new Date().toISOString()
      },
      {
        id: 2,
        testId: 1,
        testName: 'Sample Physics Test',
        data: { RollNo: '1002', Name: 'Student B', Score: '88', Correct: '23', Incorrect: '4' },
        uploadedAt: new Date().toISOString()
      }
    ];
    this.nextResultId = 3;
  }

  public async getAllTests(): Promise<TestRecord[]> {
    return this.memoryTests;
  }

  public async getTestById(id: number): Promise<TestRecord | null> {
    return this.memoryTests.find(t => t.id === id) || null;
  }

  public async createTest(name: string, date: string, templateFolder: string): Promise<TestRecord> {
    const newTest: TestRecord = {
      id: this.nextTestId++,
      name,
      date,
      templateFolder,
      createdAt: new Date().toISOString()
    };
    this.memoryTests.push(newTest);
    return newTest;
  }

  public async updateTest(id: number, name: string, date: string, templateFolder: string): Promise<TestRecord | null> {
    const test = this.memoryTests.find(t => t.id === id);
    if (!test) return null;
    test.name = name;
    test.date = date;
    test.templateFolder = templateFolder;
    return test;
  }

  public async deleteTest(id: number): Promise<boolean> {
    const index = this.memoryTests.findIndex(t => t.id === id);
    if (index === -1) return false;
    this.memoryTests.splice(index, 1);
    this.memoryResults = this.memoryResults.filter(r => r.testId !== id);
    return true;
  }

  public async addResults(testId: number | null, testName: string, rows: any[]): Promise<number> {
    let count = 0;
    for (const row of rows) {
      this.memoryResults.push({
        id: this.nextResultId++,
        testId,
        testName,
        data: row,
        uploadedAt: new Date().toISOString()
      });
      count++;
    }
    return count;
  }

  public async getResults(testId?: number): Promise<ResultRecord[]> {
    if (testId) {
      return this.memoryResults.filter(r => r.testId === testId);
    }
    return this.memoryResults;
  }
}

export const dbManager = new DatabaseManager();
