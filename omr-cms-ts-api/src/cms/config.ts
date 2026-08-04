/**
 * Node.js & TypeScript CMS Schema Configuration
 * Defines CMS Content Collections and Schema Types for OMR Test Manager
 */

export interface CMSCollectionField {
  name: string;
  type: 'text' | 'date' | 'json' | 'relation' | 'number';
  required: boolean;
  label: string;
}

export interface CMSCollection {
  name: string;
  slug: string;
  fields: CMSCollectionField[];
}

export const CMSConfig: { name: string; collections: CMSCollection[] } = {
  name: 'OMR Test Manager CMS',
  collections: [
    {
      name: 'Tests',
      slug: 'tests',
      fields: [
        { name: 'name', type: 'text', required: true, label: 'Test Name' },
        { name: 'date', type: 'date', required: true, label: 'Test Date (YYYY-MM-DD)' },
        { name: 'templateFolder', type: 'text', required: true, label: 'Template Folder' }
      ]
    },
    {
      name: 'Test Results',
      slug: 'results',
      fields: [
        { name: 'testId', type: 'relation', required: false, label: 'Associated Test' },
        { name: 'testName', type: 'text', required: true, label: 'Test Title' },
        { name: 'data', type: 'json', required: true, label: 'Student OMR Scores (JSON/CSV rows)' }
      ]
    }
  ]
};
