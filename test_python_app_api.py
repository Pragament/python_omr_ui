import os
import csv
from index import ExpressAPIClient

def test_integration():
    print("🧪 Running Integration Test: Python OMR App -> Express.js API -> PostgreSQL DB...\n")

    client = ExpressAPIClient("http://localhost:5000/api")

    # 1. Health check
    print("1. Checking API & DB Connection Health...")
    online, details = client.check_health()
    print(f"Health Status: Online = {online}, Details = {details}\n")
    assert online, "Express API is not online"

    # 2. Push test created in Python app to database via API
    print("2. Pushing test created in Python app to PostgreSQL database via API...")
    test_name = "Python App Automated Integration Test"
    test_date = "2026-08-02"
    template_folder = "omr_template_v1"

    created_test = client.create_test(test_name, test_date, template_folder)
    print("Created Test Result:", created_test)
    assert created_test and created_test.get("name") == test_name, "Failed to create test in database"
    test_id = created_test.get("id")

    # 3. Fetch/Show tests from database in Python app
    print("\n3. Showing/Fetching tests from PostgreSQL database in Python app...")
    db_tests = client.get_all_tests()
    print(f"Total Tests fetched from Database: {len(db_tests)}")
    found = any(t.get("id") == test_id or t.get("name") == test_name for t in db_tests)
    assert found, "Created test not found in database list"

    # 4. Create dummy CSV file and push OMR results to PostgreSQL DB via API
    print("\n4. Pushing OMR CSV results to PostgreSQL database via API...")
    sample_csv_path = "sample_omr_results.csv"
    with open(sample_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["roll_no", "student_name", "score", "status"])
        writer.writerow(["2001", "Sanjana User 1", "98", "PASSED"])
        writer.writerow(["2002", "Sanjana User 2", "92", "PASSED"])

    def progress(msg):
        print("Progress Callback:", msg)

    upload_res = client.upload_csv(
        csv_path=sample_csv_path,
        test_id=test_id,
        test_name=test_name,
        progress_callback=progress
    )
    print("Upload Response:", upload_res)
    assert upload_res.get("success"), "Failed to upload CSV rows to database"

    # 5. Fetch OMR test results for the test from database
    print("\n5. Fetching test results from PostgreSQL database for test ID", test_id)
    results = client.get_test_results(test_id)
    print(f"Fetched {len(results)} result rows from database for test ID {test_id}:")
    for r in results:
        print("  Row:", r.get("data"))

    # Cleanup sample csv
    if os.path.exists(sample_csv_path):
        os.remove(sample_csv_path)

    print("\n🎉 ALL PYTHON APP <-> EXPRESS API <-> POSTGRESQL INTEGRATION TESTS PASSED!")

if __name__ == "__main__":
    test_integration()
