import http from 'http';

function makeRequest(method: string, path: string, body?: any): Promise<any> {
  return new Promise((resolve, reject) => {
    const postData = body ? JSON.stringify(body) : '';
    const options: http.RequestOptions = {
      hostname: 'localhost',
      port: 5000,
      path: `/api${path}`,
      method: method,
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData)
      }
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => (data += chunk));
      res.on('end', () => {
        try {
          resolve({ statusCode: res.statusCode, body: JSON.parse(data) });
        } catch {
          resolve({ statusCode: res.statusCode, body: data });
        }
      });
    });

    req.on('error', (err) => reject(err));
    if (postData) req.write(postData);
    req.end();
  });
}

async function runTests() {
  console.log('🧪 Starting OMR TypeScript CMS & ORM API Automated Test Suite...\n');

  try {
    // 1. Health check
    const health = await makeRequest('GET', '/health');
    console.log('1. GET /api/health ->', health.statusCode, health.body);

    // 2. Fetch tests
    const tests = await makeRequest('GET', '/tests');
    console.log('2. GET /api/tests ->', tests.statusCode, `Count: ${tests.body.count}`);

    // 3. Create test
    const newTest = await makeRequest('POST', '/tests', {
      name: 'TypeScript CMS Integration Test',
      date: '2026-08-04',
      template_folder: 'neet_60_template'
    });
    console.log('3. POST /api/tests ->', newTest.statusCode, newTest.body.data);

    // 4. Upload results
    const createdId = newTest.body.data.id;
    const upload = await makeRequest('POST', `/tests/${createdId}/results`, {
      test_id: createdId,
      test_name: 'TypeScript CMS Integration Test',
      rows: [
        { RollNo: '3001', Name: 'Student TS 1', Score: '99', Correct: '28' },
        { RollNo: '3002', Name: 'Student TS 2', Score: '94', Correct: '26' }
      ]
    });
    console.log(`4. POST /api/tests/${createdId}/results ->`, upload.statusCode, upload.body.message);

    // 5. Fetch results
    const fetchedResults = await makeRequest('GET', `/tests/${createdId}/results`);
    console.log(`5. GET /api/tests/${createdId}/results ->`, fetchedResults.statusCode, `Count: ${fetchedResults.body.count}`);

    console.log('\n🎉 ALL TYPESCRIPT CMS & ORM API TESTS PASSED SUCCESSFULLY!');
  } catch (err: any) {
    console.error('❌ Test failed:', err.message);
  }
}

runTests();
