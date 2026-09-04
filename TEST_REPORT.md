# Peblo TV Mini - Test Report

## Test Environment

- Backend: FastAPI
- Database: PostgreSQL
- Containerization: Docker Compose
- Frontend: React + Vite
- API Documentation: FastAPI Swagger UI
- Operating System: Windows
- Browser: Google Chrome

---

## Test Cases

| Test ID | Test Scenario | Expected Result | Status |
|---|---|---|---|
| TC-01 | Health endpoint check | API returns healthy status and database connectivity | PASS |
| TC-02 | Admin authentication | Valid admin credentials return an access token | PASS |
| TC-03 | Role-based authorization | Editor user cannot perform admin-only operations | PASS |
| TC-04 | Artwork validation | Invalid artwork dimensions or ratio are rejected | PASS |
| TC-05 | Publish idempotency | Repeated publishing remains deterministic and does not create unintended duplicate content | PASS |
| TC-06 | Published catalog access | Public catalog endpoint returns published content | PASS |
| TC-07 | CMS API integration | CMS frontend successfully connects to the Peblo TV API | PASS |
| TC-08 | Database connectivity | PostgreSQL container becomes healthy and accepts connections | PASS |
| TC-09 | Docker environment startup | API and database services start successfully using Docker Compose | PASS |

---

## Automated Testing

Automated tests cover the highest-risk backend functionality, including:

- Authentication behavior
- Role-based access control
- Artwork validation
- Publish behavior
- Catalog generation

Run automated tests using:

```bash
docker compose exec api pytest tests/ -v
cat > TEST_REPORT.md << 'EOF'
```bash
---

## Manual Testing Evidence

The following functionality was manually verified:

1. Docker Compose successfully started the FastAPI and PostgreSQL services.
2. The `/health` endpoint returned a successful API status.
3. The Peblo TV CMS frontend connected successfully to the backend API.
4. Admin authentication completed successfully.
5. The published catalog was successfully loaded in the CMS frontend.
6. The catalog statistics correctly displayed the number of published shows and sections.

---

## Test Result Summary

| Category | Result |
|---|---|
| Backend API | PASS |
| Database Connectivity | PASS |
| Authentication | PASS |
| Role Authorization | PASS |
| Artwork Validation | PASS |
| Publishing Logic | PASS |
| Public Catalog | PASS |
| CMS Frontend Integration | PASS |
| Docker Environment | PASS |

**Overall Result: PASS**

The implemented Peblo TV Mini functionality was tested successfully in the local development environment.

