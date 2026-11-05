# Service Monitoring

## ADDED Requirements

### Requirement: Monitor backend and database health locally

The project SHALL provide a local Gatus check for the backend health endpoint. The check SHALL consider the backend healthy only when the endpoint responds with HTTP 200 and reports both `status: ok` and `database: ok`. The Gatus web interface SHALL listen on the loopback interface and retain check history across restarts.

#### Scenario: Backend and database are healthy

- **WHEN** Gatus checks `GET /health` and the response is HTTP 200 with `status: ok` and `database: ok`
- **THEN** the backend endpoint is shown as healthy in Gatus

#### Scenario: Backend or database is unhealthy

- **WHEN** the health endpoint is unreachable, returns a non-200 status, or reports a degraded status
- **THEN** the backend endpoint is shown as unhealthy in Gatus

#### Scenario: Gatus is started locally

- **WHEN** Gatus is running with the project configuration
- **THEN** its web interface is reachable at `http://localhost:8081` and is not bound to external network interfaces
- **AND** check history is stored under the project's ignored `data/` directory
