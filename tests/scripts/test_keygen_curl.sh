#!/bin/bash

# Test script for /keygen endpoint using cURL
# Make sure the server is running: uvicorn app.main:app --reload

echo "🧪 Testing /keygen endpoint with cURL..."
echo

# Get today's date in YYYYMMDD format
TODAY=$(date +%Y%m%d)

echo "📅 Using date: $TODAY"
echo

# Test 1: Valid request
echo "Test 1: Valid request with correct auth header"
curl -X POST http://localhost:8000/keygen \
     -H "Content-Type: application/json" \
     -H "X-Keygen-Auth: dy2025@fileBucket" \
     -d "{\"project_name\": \"TestProject\", \"request_date\": \"$TODAY\"}" \
     -w "\nHTTP Status: %{http_code}\n\n"

# Test 2: Invalid auth header
echo "Test 2: Invalid auth header"
curl -X POST http://localhost:8000/keygen \
     -H "Content-Type: application/json" \
     -H "X-Keygen-Auth: wrong-auth" \
     -d "{\"project_name\": \"TestProject\", \"request_date\": \"$TODAY\"}" \
     -w "\nHTTP Status: %{http_code}\n\n"

# Test 3: Missing auth header
echo "Test 3: Missing auth header"
curl -X POST http://localhost:8000/keygen \
     -H "Content-Type: application/json" \
     -d "{\"project_name\": \"TestProject\", \"request_date\": \"$TODAY\"}" \
     -w "\nHTTP Status: %{http_code}\n\n"

# Test 4: Invalid date format
echo "Test 4: Invalid date format"
curl -X POST http://localhost:8000/keygen \
     -H "Content-Type: application/json" \
     -H "X-Keygen-Auth: dy2025@fileBucket" \
     -d "{\"project_name\": \"TestProject\", \"request_date\": \"2025-08-10\"}" \
     -w "\nHTTP Status: %{http_code}\n\n"

# Test 5: Empty project name
echo "Test 5: Empty project name"
curl -X POST http://localhost:8000/keygen \
     -H "Content-Type: application/json" \
     -H "X-Keygen-Auth: dy2025@fileBucket" \
     -d "{\"project_name\": \"\", \"request_date\": \"$TODAY\"}" \
     -w "\nHTTP Status: %{http_code}\n\n"

echo "✅ All tests completed!"
echo
echo "💡 To run the server: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"