## ADDED Requirements
### Requirement: Door Access Authentication
The system SHALL require user authentication before processing door open requests.

#### Scenario: Authentication required
- **WHEN** a user attempts to open a door without authentication
- **THEN** the system SHALL return HTTP 401 Unauthorized error

#### Scenario: Authentication successful
- **WHEN** a user provides valid authentication
- **THEN** the system SHALL proceed to booking validation

### Requirement: Booking Validation for Door Access
The system SHALL validate that users have current valid bookings for door access.

#### Scenario: Valid booking allows door access
- **WHEN** an authenticated user has a confirmed booking for the current time
- **THEN** the system SHALL allow door access

#### Scenario: No booking denies door access
- **WHEN** an authenticated user has no current bookings
- **THEN** the system SHALL return HTTP 403 Forbidden error with message "您当前没有有效预订，无法开门"

#### Scenario: Expired booking denies door access
- **WHEN** an authenticated user's booking has expired
- **THEN** the system SHALL return HTTP 403 Forbidden error with message "您的预订已过期，无法开门"

### Requirement: Door Access Time Window
The system SHALL allow users to open doors up to 1 hour before their booking start time.

#### Scenario: Within advance time window
- **WHEN** a user tries to open a door less than 1 hour before booking start
- **THEN** the system SHALL allow door access

#### Scenario: Outside advance time window
- **WHEN** a user tries to open a door more than 1 hour before booking start
- **THEN** the system SHALL return HTTP 403 Forbidden error with message "距离预订时间超过1小时，无法开门"

### Requirement: Door Access Audit Logging
The system SHALL log all door access attempts for security tracking.

#### Scenario: Successful door access logged
- **WHEN** a user successfully opens a door
- **THEN** the system SHALL create an audit log with user ID, door ID, timestamp, and success status

#### Scenario: Failed door access logged
- **WHEN** a door access attempt is rejected
- **THEN** the system SHALL create an audit log with user ID, door ID, timestamp, and rejection reason

## MODIFIED Requirements
### Requirement: Door Open Endpoint
The door open endpoint SHALL require authentication and booking validation before processing requests.

#### Scenario: Door open with valid booking
- **WHEN** an authenticated user with valid booking sends door open request
- **THEN** the system SHALL process the door open command and return success response

#### Scenario: Door open without valid booking
- **WHEN** an authenticated user without valid booking sends door open request
- **THEN** the system SHALL reject the request with appropriate error message