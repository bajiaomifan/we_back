## MODIFIED Requirements
### Requirement: Door Open Endpoint
The door open endpoint SHALL schedule automatic power-off tasks when users open doors.

#### Scenario: Power-off scheduled on door open
- **WHEN** an authenticated user with valid booking opens a door
- **THEN** system SHALL schedule automatic power-off for booking end time

#### Scenario: Power-off time calculation
- **WHEN** user opens door before booking start time
- **THEN** system SHALL calculate power-off time as booking end time + 40 minutes buffer

#### Scenario: Power-off time calculation for late opening
- **WHEN** user opens door after booking start time
- **THEN** system SHALL calculate power-off time as booking end time + 40 minutes buffer

## ADDED Requirements
### Requirement: Automatic Power-Off Execution
The system SHALL automatically turn off room power when scheduled time is reached.

#### Scenario: Scheduled power-off execution
- **WHEN** scheduled power-off time is reached
- **THEN** system SHALL send power-off command to room's electrical relay

#### Scenario: Power-off success logging
- **WHEN** automatic power-off is successfully executed
- **THEN** system SHALL create audit log with task ID, room ID, and success status

#### Scenario: Power-off failure handling
- **WHEN** automatic power-off command fails
- **THEN** system SHALL log error and retry up to 3 times

### Requirement: Power-Off Task Management
The system SHALL provide management interfaces for scheduled power-off tasks.

#### Scenario: List active power-off tasks
- **WHEN** administrator requests active power-off tasks
- **THEN** system SHALL return list of pending and executing tasks

#### Scenario: Cancel power-off task
- **WHEN** user cancels booking before power-off execution
- **THEN** system SHALL cancel corresponding power-off task

#### Scenario: Power-off task status tracking
- **WHEN** system queries power-off task status
- **THEN** system SHALL return current status (scheduled, executing, completed, failed)