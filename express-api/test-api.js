const http = require('http');

const PORT = process.env.PORT || 5000;
const BASE_URL = `http://localhost:${PORT}`;

function makeRequest(method, path, body = null) {
  return new Promise((resolve, reject) => {
    const url = new URL(path, BASE_URL);
    const options = {
      hostname: url.hostname,
      port: url.port,
      path: url.pathname + url.search,
      method: method,
      headers: {
        'Content-Type': 'application/json'
      }
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          resolve({ statusCode: res.statusCode, body: JSON.parse(data) });
        } catch (e) {
          resolve({ statusCode: res.statusCode, body: data });
        }
      });
    });

    req.on('error', (err) => reject(err));

    if (body) {
      req.write(JSON.stringify(body));
    }
    req.end();
  });
}

async function runTests() {
  console.log('🧪 Starting Sanjana OMR Express REST API Automated Tests...\n');

  try {
    // 1. Health check
    console.log('1. Testing GET /api/health...');
    let res = await makeRequest('GET', '/api/health');
    console.log(`Response [${res.statusCode}]:`, res.body);

    // 2. Fetch all tests
    console.log('\n2. Testing GET /api/tests...');
    res = await makeRequest('GET', '/api/tests');
    console.log(`Response [${res.statusCode}]: Count = ${res.body.count}`);

    // 3. Create a new test
    console.log('\n3. Testing POST /api/tests (Creating test)...');
    const newTestData = {
      name: 'NEET Grand Mock Test 2026',
      date: '2026-08-15',
      template_folder: 'neet_60_template'
    };
    res = await makeRequest('POST', '/api/tests', newTestData);
    console.log(`Response [${res.statusCode}]:`, res.body);
    const createdId = res.body.data ? res.body.data.id : null;

    if (createdId) {
      // 4. Fetch the created test
      console.log(`\n4. Testing GET /api/tests/${createdId}...`);
      res = await makeRequest('GET', `/api/tests/${createdId}`);
      console.log(`Response [${res.statusCode}]:`, res.body);

      // 5. Push OMR CSV result rows for the test
      console.log(`\n5. Testing POST /api/tests/${createdId}/results (Pushing CSV rows)...`);
      const sampleResults = {
        test_name: newTestData.name,
        rows: [
          { roll_no: '1001', student_name: 'Student A', score: '95', physics: '30', chemistry: '32', biology: '33' },
          { roll_no: '1002', student_name: 'Student B', score: '88', physics: '28', chemistry: '30', biology: '30' }
        ]
      };
      res = await makeRequest('POST', `/api/tests/${createdId}/results`, sampleResults);
      console.log(`Response [${res.statusCode}]:`, res.body);

      // 6. Fetch results for the test
      console.log(`\n6. Testing GET /api/tests/${createdId}/results...`);
      res = await makeRequest('GET', `/api/tests/${createdId}/results`);
      console.log(`Response [${res.statusCode}]: Count = ${res.body.count}, Sample Row:`, res.body.data[0]);

      // 7. Update test
      console.log(`\n7. Testing PUT /api/tests/${createdId} (Updating test)...`);
      res = await makeRequest('PUT', `/api/tests/${createdId}`, {
        name: 'NEET Grand Mock Test 2026 (Updated)',
        date: '2026-08-20',
        template_folder: 'neet_60_template'
      });
      console.log(`Response [${res.statusCode}]:`, res.body);
    }

    console.log('\n🎉 ALL TESTS COMPLETED SUCCESSFULLY!');
  } catch (err) {
    console.error('❌ Test failed with error:', err.message);
  }
}

// Allow slight delay for server to start if run concurrently
setTimeout(runTests, 1000);
