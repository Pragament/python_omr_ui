const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
const API_KEY = import.meta.env.VITE_API_KEY || '';

const headers = {
  'Content-Type': 'application/json',
  'X-API-Key': API_KEY
};

export const api = {
  // System
  health: async () => {
    const res = await fetch('http://localhost:8000/health');
    return res.json();
  },
  
  getSettings: async () => {
    const res = await fetch(`${API_URL}/settings`, { headers });
    if (!res.ok) throw new Error('Failed to fetch settings');
    return res.json();
  },

  // Templates
  getTemplates: async () => {
    const res = await fetch(`${API_URL}/templates`, { headers });
    if (!res.ok) throw new Error('Failed to fetch templates');
    return res.json();
  },

  // Tests CRUD
  getTests: async () => {
    const res = await fetch(`${API_URL}/tests`, { headers });
    if (!res.ok) throw new Error('Failed to fetch tests');
    return res.json();
  },

  createTest: async (testData) => {
    const res = await fetch(`${API_URL}/tests`, {
      method: 'POST',
      headers,
      body: JSON.stringify(testData)
    });
    if (!res.ok) {
        const d = await res.json();
        throw new Error(d.detail || 'Failed to create test');
    }
    return res.json();
  },

  deleteTest: async (id) => {
    const res = await fetch(`${API_URL}/tests/${id}`, {
      method: 'DELETE',
      headers
    });
    if (!res.ok) throw new Error('Failed to delete test');
    return true;
  },

  // OMR Operations
  uploadPdf: async (testId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    // Omit content-type so browser sets it with boundary
    const h = { 'X-API-Key': API_KEY };
    const res = await fetch(`${API_URL}/tests/${testId}/upload-pdf`, {
      method: 'POST',
      headers: h,
      body: formData
    });
    if (!res.ok) {
        const d = await res.json();
        throw new Error(d.detail || 'Upload failed');
    }
    return res.json();
  },

  runOmr: async (testId) => {
    const res = await fetch(`${API_URL}/tests/${testId}/run`, {
      method: 'POST',
      headers
    });
    if (!res.ok) {
        const d = await res.json();
        throw new Error(d.detail || 'OMR Run failed');
    }
    return res.json();
  },

  getJobStatus: async (testId) => {
    const res = await fetch(`${API_URL}/tests/${testId}/status`, { headers });
    if (!res.ok) throw new Error('Status check failed');
    return res.json();
  },

  getResults: async (testId) => {
    const res = await fetch(`${API_URL}/tests/${testId}/results`, { headers });
    if (!res.ok) {
        const d = await res.json();
        throw new Error(d.detail || 'Results not found');
    }
    return res.json();
  },

  pushFirestore: async (testId) => {
    const res = await fetch(`${API_URL}/tests/${testId}/push-firestore`, {
      method: 'POST',
      headers
    });
    if (!res.ok) {
        const d = await res.json();
        throw new Error(d.detail || 'Firestore sync failed');
    }
    return res.json();
  }
};
