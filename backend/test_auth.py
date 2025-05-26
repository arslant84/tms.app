"""
Test script to verify authentication functionality.
This script tests the token endpoint directly using Python's built-in http.client.
"""
import http.client
import json
import urllib.parse

# Backend URL
HOST = "127.0.0.1"
PORT = 8000

def test_login(email, password):
    """Test the login endpoint with the provided credentials."""
    print(f"Testing login with email: {email}")
    
    # Prepare the form data
    params = urllib.parse.urlencode({
        "username": email,  # FastAPI OAuth2 expects 'username'
        "password": password
    })
    
    # Set up the connection
    conn = http.client.HTTPConnection(HOST, PORT)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    # Make the request
    conn.request("POST", "/token", body=params, headers=headers)
    response = conn.getresponse()
    
    # Print the status code
    print(f"Status code: {response.status}")
    
    # Try to parse the response
    try:
        response_data = response.read().decode('utf-8')
        if response.status == 200:
            result = json.loads(response_data)
            print("Login successful!")
            print(f"Token: {result.get('access_token')[:20]}...")
            print(f"User ID: {result.get('user_id')}")
            print(f"Name: {result.get('name')}")
            print(f"Role: {result.get('role')}")
            print(f"Is Admin: {result.get('is_admin')}")
            conn.close()
            return result
        else:
            print(f"Error: {response_data}")
            conn.close()
            return None
    except Exception as e:
        print(f"Error parsing response: {e}")
        print(f"Response data: {response.read().decode('utf-8')}")
        conn.close()
        return None

def test_protected_endpoint(token):
    """Test a protected endpoint using the provided token."""
    if not token:
        print("No token provided, skipping protected endpoint test")
        return
    
    # Set up the connection
    conn = http.client.HTTPConnection(HOST, PORT)
    headers = {"Authorization": f"Bearer {token}"}
    
    # Make the request with the token
    conn.request("GET", "/users/me", headers=headers)
    response = conn.getresponse()
    
    # Print the status code
    print(f"\nProtected endpoint status code: {response.status}")
    
    # Try to parse the response
    try:
        response_data = response.read().decode('utf-8')
        if response.status == 200:
            result = json.loads(response_data)
            print("Protected endpoint access successful!")
            print(f"User data: {json.dumps(result, indent=2)}")
        else:
            print(f"Error: {response_data}")
    except Exception as e:
        print(f"Error parsing response: {e}")
        print(f"Response data: {response.read().decode('utf-8')}")
    finally:
        conn.close()

def check_endpoint(path):
    """Check if an endpoint exists and return its status code."""
    conn = http.client.HTTPConnection(HOST, PORT)
    try:
        conn.request("GET", path)
        response = conn.getresponse()
        print(f"Path {path}: Status {response.status}")
        return response.status
    except Exception as e:
        print(f"Error checking {path}: {e}")
        return None
    finally:
        conn.close()

if __name__ == "__main__":
    # Check various endpoint paths
    print("=== Checking API Endpoints ===")
    check_endpoint("/")
    check_endpoint("/docs")
    check_endpoint("/api")
    check_endpoint("/api/docs")
    check_endpoint("/token")
    check_endpoint("/api/token")
    
    # Test with admin credentials
    print("\n=== Testing Admin Login ===")
    result = test_login("admin@tms.com", "Admin@123")
    
    # If login was successful, test a protected endpoint
    if result:
        token = result.get('access_token')
        test_protected_endpoint(token)
    
    print("\nDone!")
