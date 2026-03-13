"""Bootstrap a fresh VirtualAI instance: register admin user + create API key.

Usage:
    python seed_test_bootstrap.py --url http://localhost:3081

Prints the API key to stdout on success.
"""
import argparse
import requests
import sys


def bootstrap(base_url: str) -> str:
    email = "admin@virtualai.com"
    password = "SeedTest123!"

    # 1. Register user
    resp = requests.post(
        f"{base_url}/api/auth/register",
        json={"email": email, "password": password, "has_verified_email": True},
        timeout=10,
    )
    if resp.status_code in (200, 201):
        print(f"  [OK] Registered {email} (role={resp.json().get('role')})")
    elif resp.status_code == 400 and "REGISTER_USER_ALREADY_EXISTS" in resp.text:
        print(f"  [OK] User {email} already exists")
    else:
        print(f"  [FAIL] Register: {resp.status_code} {resp.text[:200]}")
        sys.exit(1)

    # 2. Login to get session cookie
    session = requests.Session()
    resp = session.post(
        f"{base_url}/api/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    if resp.status_code != 200 and resp.status_code != 204:
        print(f"  [FAIL] Login: {resp.status_code} {resp.text[:200]}")
        sys.exit(1)
    print("  [OK] Logged in")

    # 3. Create API key
    resp = session.post(
        f"{base_url}/api/admin/api-key",
        json={"name": "seed-test-key"},
        timeout=10,
    )
    if resp.status_code == 200:
        api_key = resp.json()["api_key"]
        print(f"  [OK] API key created: {api_key[:20]}...")
        return api_key
    else:
        print(f"  [FAIL] API key: {resp.status_code} {resp.text[:200]}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:3081")
    args = parser.parse_args()
    key = bootstrap(args.url)
    print(f"\nAPI_KEY={key}")
