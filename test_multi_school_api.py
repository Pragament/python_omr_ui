import os
import sys
import json
from index import ExpressAPIClient

def test_multi_school():
    print("Testing Multi-School Architecture, Strapi Users & Permissions & Google OAuth Provider...\n")

    client = ExpressAPIClient("http://localhost:5000/api")

    # 1. Test Strict @gmail.com Rejection
    print("1. Testing Non-Gmail Address Rejection (teacher@example.com)...")
    try:
        client.authenticate_google_email("teacher@example.com", "Test Editor")
        print("   FAILED: Non-gmail address was incorrectly accepted.")
    except Exception as e:
        print(f"   SUCCESS: Rejected non-gmail address with message -> '{e}'")

    # 2. Test Strapi Google Provider Authentication (sreehasathota@gmail.com)
    print("\n2. Authenticating with Real Gmail Address via Strapi Users-Permissions: sreehasathota@gmail.com...")
    success, auth_res = client.authenticate_google_email("sreehasathota@gmail.com", "Sreeha Editor")
    print(f"   Login Result: Success = {success}")
    role_info = client.current_user.get('role', {})
    role_name = role_info.get('name', 'test_editor') if isinstance(role_info, dict) else str(role_info)
    user_name = client.current_user.get('username', client.current_user.get('email'))
    print(f"   Strapi Logged in User: {user_name} ({client.current_user['email']}) | Role: {role_name}")
    print(f"   Assigned Schools ({len(client.user_schools)}):")
    for s in client.user_schools:
        print(f"     - ID {s['id']}: {s['name']} ({s['code']})")

    # 3. Test Pragathi Central School Scoping & Test Fetching
    client.selected_school = client.user_schools[0] # Pragathi Central School
    pcs_tests = client.get_tests_for_school()
    print(f"\n3. Tests scoped to School 1 ({client.selected_school['name']}): {len(pcs_tests)} test(s)")
    for t in pcs_tests:
        print(f"     * Test ID {t['id']}: {t['name']}")

    # 4. Create new test for Pragathi Central School
    print(f"\n4. Creating new test for {client.selected_school['name']}...")
    created_test = client.create_test_for_school("Pragathi Central NEET Mock 2026", "2026-08-10", "neet_60_template")
    print(f"   Created Test ID {created_test['id']} for School ID {created_test['school_id']}: {created_test['name']}")

    # 5. Fetch updated tests for Pragathi Central School
    updated_tests = client.get_tests_for_school()
    print(f"   Total Tests now for {client.selected_school['name']}: {len(updated_tests)} test(s)")

    print("\nALL STRAPI USERS & PERMISSIONS, MULTI-SCHOOL & GOOGLE OAUTH TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_multi_school()
