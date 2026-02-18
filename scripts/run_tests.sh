#!/bin/bash
# Test runner script for comprehensive test execution

set -e

echo "🧪 Running Phase 0 Requirements Tests..."
python manage.py test tests.test_phase0_requirements -v 2

echo ""
echo "🧪 Running API Endpoints Tests..."
python manage.py test tests.test_api_endpoints -v 2

echo ""
echo "🧪 Running All Tests..."
pytest tests/ -v --tb=short --cov=. --cov-report=html --cov-report=term

echo ""
echo "✅ All tests completed!"

