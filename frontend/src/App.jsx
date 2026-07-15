import { useState, useEffect } from 'react';
import { api } from './api';
import { 
  Plus, UploadCloud, Play, Settings,
  CheckCircle, Loader, Cloud, Trash2,
  FileText, LayoutDashboard, Calendar, RefreshCcw
} from 'lucide-react';

function App() {
  const [tests, setTests] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('dashboard');
  
  // Modals & Forms
  const [showCreate, setShowCreate] = useState(false);
  const [newTest, setNewTest] = useState({ name: '', date: '', template_folder: '' });
  
  // Selected Test View
  const [selectedTest, setSelectedTest] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [testResults, setTestResults] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [tData, tmpData] = await Promise.all([
        api.getTests(),
        api.getTemplates()
      ]);
      setTests(tData);
      setTemplates(tmpData.templates || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTest = async (e) => {
    e.preventDefault();
    try {
      await api.createTest(newTest);
      setShowCreate(false);
      setNewTest({ name: '', date: '', template_folder: '' });
      fetchData();
    } catch (err) {
      alert("Error: " + err.message);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm("Are you sure you want to delete this test and all its files?")) return;
    try {
      await api.deleteTest(id);
      if (selectedTest?.id === id) setSelectedTest(null);
      fetchData();
    } catch (err) {
      alert(err.message);
    }
  };

  const fetchResults = async (id) => {
    try {
      const res = await api.getResults(id);
      setTestResults(res.results);
    } catch (err) {
      setTestResults(null);
    }
  };

  // --- Active Test Actions ---
  const handleSelectTest = async (test) => {
    setSelectedTest(test);
    setTestResults(null);
    checkStatus(test.id);
    fetchResults(test.id);
  };

  const checkStatus = async (id) => {
    try {
      const res = await api.getJobStatus(id);
      setJobStatus(res);
      // Poll if running
      if (res.status === 'running') {
        setTimeout(() => checkStatus(id), 2000);
      } else if (res.status === 'done') {
        fetchResults(id);
      }
    } catch (err) {
      setJobStatus({ status: 'idle', message: 'Ready' });
    }
  };

  const uploadPdf = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      await api.uploadPdf(selectedTest.id, file);
      checkStatus(selectedTest.id);
    } catch (err) {
      alert(err.message);
    }
  };

  const runEngine = async () => {
    try {
      await api.runOmr(selectedTest.id);
      checkStatus(selectedTest.id);
    } catch (err) {
      alert(err.message);
    }
  };

  const syncFirestore = async () => {
    try {
      await api.pushFirestore(selectedTest.id);
      checkStatus(selectedTest.id);
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="glass-panel" style={{ width: '280px', margin: '1.5rem', padding: '2rem 1.5rem', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '3rem' }}>
          <div style={{ 
            width: '40px', height: '40px', borderRadius: '12px',
            background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: 'var(--shadow-glow)'
          }}>
            <FileText size={20} color="white" />
          </div>
          <h2 style={{ margin: 0, fontSize: '1.25rem' }}>OMR <span className="text-gradient">Manager</span></h2>
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', flex: 1 }}>
          <button 
            className={`btn-outline ${activeTab === 'dashboard' ? 'active' : ''}`}
            style={{ 
              display: 'flex', alignItems: 'center', gap: '10px', width: '100%', 
              textAlign: 'left', border: 'none', background: activeTab === 'dashboard' ? 'rgba(255,255,255,0.1)' : 'transparent' 
            }}
            onClick={() => { setActiveTab('dashboard'); setSelectedTest(null); }}
          >
            <LayoutDashboard size={18} /> Dashboard
          </button>
          <button 
            className="btn-outline"
            style={{ display: 'flex', alignItems: 'center', gap: '10px', width: '100%', textAlign: 'left', border: 'none' }}
            onClick={() => setShowCreate(true)}
          >
            <Plus size={18} /> New Test
          </button>
        </nav>
        
        <div style={{ marginTop: 'auto', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
          System Status: <span style={{ color: 'var(--success)' }}>Online</span>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content animate-fade-in">
        {selectedTest ? (
          <div className="test-detail-view animate-fade-in">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem' }}>
              <div>
                <button 
                  className="btn-outline" 
                  style={{ padding: '0.25rem 0.75rem', marginBottom: '1rem', fontSize: '0.875rem' }}
                  onClick={() => setSelectedTest(null)}
                >
                  ← Back to Dashboard
                </button>
                <h1 style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>{selectedTest.name}</h1>
                <div style={{ display: 'flex', gap: '1rem', color: 'var(--text-secondary)' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><Calendar size={16}/> {selectedTest.date}</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><Settings size={16}/> {selectedTest.template_folder}</span>
                </div>
              </div>
              <button className="btn-outline" style={{ color: 'var(--danger)', borderColor: 'rgba(239, 68, 68, 0.3)' }} onClick={() => handleDelete(selectedTest.id)}>
                <Trash2 size={16} />
              </button>
            </div>

            {/* Status Banner */}
            <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '2rem', display: 'flex', alignItems: 'center', gap: '1rem', borderLeft: '4px solid var(--accent-primary)' }}>
              {jobStatus?.status === 'running' ? <RefreshCcw className="rotating" size={24} color="var(--accent-primary)" /> : <CheckCircle size={24} color="var(--success)" />}
              <div style={{ flex: 1 }}>
                <h4 style={{ margin: 0, marginBottom: '4px' }}>System Status: {jobStatus?.status?.toUpperCase() || 'IDLE'}</h4>
                <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{jobStatus?.message || 'Ready for operations'}</p>
              </div>
            </div>

            {/* Action Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
              
              {/* Step 1: Upload */}
              <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center' }}>
                <div style={{ background: 'rgba(59, 130, 246, 0.1)', padding: '1rem', borderRadius: '50%', marginBottom: '1rem' }}>
                  <UploadCloud size={32} color="var(--accent-primary)" />
                </div>
                <h3>1. Upload PDF</h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '1.5rem', flex: 1 }}>
                  Upload scanned bubble sheets. They will be converted to high-res images automatically.
                </p>
                <label className="btn-primary" style={{ width: '100%', cursor: 'pointer', textAlign: 'center' }}>
                  Select PDF
                  <input type="file" accept=".pdf" style={{ display: 'none' }} onChange={uploadPdf} />
                </label>
              </div>

              {/* Step 2: Grade */}
              <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center' }}>
                <div style={{ background: 'rgba(139, 92, 246, 0.1)', padding: '1rem', borderRadius: '50%', marginBottom: '1rem' }}>
                  <Play size={32} color="var(--accent-secondary)" />
                </div>
                <h3>2. Grade Exams</h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '1.5rem', flex: 1 }}>
                  Run the AI computer vision engine to extract answers from the images.
                </p>
                <button className="btn-primary" style={{ width: '100%' }} onClick={runEngine} disabled={jobStatus?.status === 'running'}>
                  Start Engine
                </button>
              </div>

              {/* Step 3: Sync */}
              <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center' }}>
                <div style={{ background: 'rgba(16, 185, 129, 0.1)', padding: '1rem', borderRadius: '50%', marginBottom: '1rem' }}>
                  <Cloud size={32} color="var(--success)" />
                </div>
                <h3>3. Sync Cloud</h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '1.5rem', flex: 1 }}>
                  Push the final graded results directly to the Google Firestore database.
                </p>
                <button className="btn-outline" style={{ width: '100%' }} onClick={syncFirestore} disabled={jobStatus?.status === 'running'}>
                  Push to Firestore
                </button>
              </div>

            </div>

            {/* Results Section */}
            {testResults && testResults.length > 0 && (
              <div className="glass-panel" style={{ marginTop: '2rem', padding: '1.5rem', overflowX: 'auto' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <h3 style={{ margin: 0 }}>Graded Results</h3>
                  <button className="btn-outline" style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem', display: 'flex', alignItems: 'center' }} onClick={() => fetchResults(selectedTest.id)}>
                    <RefreshCcw size={14} style={{ marginRight: '6px' }}/> Refresh
                  </button>
                </div>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--surface-border)' }}>
                      {Object.keys(testResults[0]).map(k => (
                        <th key={k} style={{ padding: '1rem', color: 'var(--text-secondary)', fontWeight: 600 }}>{k.toUpperCase()}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {testResults.map((row, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        {Object.values(row).map((v, j) => (
                          <td key={j} style={{ padding: '1rem' }}>{v}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ) : (
          <div className="dashboard-view animate-fade-in">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '3rem' }}>
              <div>
                <h1 style={{ fontSize: '3rem', marginBottom: '0.5rem' }}>Welcome Back.</h1>
                <p style={{ color: 'var(--text-secondary)', fontSize: '1.1rem' }}>Manage your optical mark recognition workflows.</p>
              </div>
              <button className="btn-primary" style={{ display: 'flex', alignItems: 'center', gap: '8px' }} onClick={() => setShowCreate(true)}>
                <Plus size={18} /> Create Test
              </button>
            </div>

            <h3 style={{ marginBottom: '1.5rem', fontWeight: 500 }}>Recent Tests</h3>
            
            {loading ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem' }}>
                <Loader className="rotating" size={32} color="var(--accent-primary)" />
              </div>
            ) : tests.length === 0 ? (
              <div className="glass-panel" style={{ padding: '4rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                <FileText size={48} style={{ opacity: 0.5, marginBottom: '1rem' }} />
                <h3>No tests found</h3>
                <p>Create your first test to get started.</p>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1.5rem' }}>
                {tests.map(t => (
                  <div key={t.id} className="glass-card" style={{ cursor: 'pointer' }} onClick={() => handleSelectTest(t)}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                      <h3 style={{ margin: 0, fontSize: '1.25rem' }}>{t.name}</h3>
                      <span className="badge done" style={{ fontSize: '0.7rem' }}>ID: {t.id}</span>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><Calendar size={14}/> {t.date}</span>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><Settings size={14}/> {t.template_folder}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Create Modal */}
      {showCreate && (
        <div style={{ 
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, 
          background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(5px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 
        }}>
          <div className="glass-panel animate-fade-in" style={{ width: '100%', maxWidth: '500px', padding: '2.5rem' }}>
            <h2 style={{ marginBottom: '1.5rem' }}>Create New Test</h2>
            <form onSubmit={handleCreateTest} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Test Name</label>
                <input required className="input-field" value={newTest.name} onChange={e => setNewTest({...newTest, name: e.target.value})} placeholder="e.g. Fall Midterm 2026" />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Date (YYYY-MM-DD)</label>
                <input required type="date" className="input-field" value={newTest.date} onChange={e => setNewTest({...newTest, date: e.target.value})} />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>OMR Template</label>
                <select required className="input-field" value={newTest.template_folder} onChange={e => setNewTest({...newTest, template_folder: e.target.value})} style={{ appearance: 'none', background: 'rgba(0,0,0,0.3)' }}>
                  <option value="" disabled>Select a template...</option>
                  {templates.map(tmp => <option key={tmp} value={tmp}>{tmp}</option>)}
                </select>
              </div>
              
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
                <button type="button" className="btn-outline" onClick={() => setShowCreate(false)}>Cancel</button>
                <button type="submit" className="btn-primary">Create Test</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Global CSS for rotating icon */}
      <style>{`
        .rotating { animation: spin 2s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

export default App;
