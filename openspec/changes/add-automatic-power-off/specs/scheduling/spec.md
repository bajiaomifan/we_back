## ADDED Requirements
### Requirement: Background Task Scheduler
The system SHALL provide a background task scheduler for delayed power-off operations.

#### Scenario: Schedule delayed task
- **WHEN** system needs to execute power-off after specified duration
- **THEN** system SHALL schedule task for execution at calculated time

#### Scenario: Task persistence
- **WHEN** power-off tasks are scheduled
- **THEN** system SHALL store tasks in database with status tracking

#### Scenario: Task execution
- **WHEN** scheduled time is reached
- **THEN** system SHALL execute the power-off operation

#### Scenario: Task cancellation
- **WHEN** associated booking is cancelled
- **THEN** system SHALL cancel corresponding power-off task

### Requirement: Power-Off Time Calculation
The system SHALL calculate power-off time based on booking duration and door open time.

#### Scenario: Early door open calculation
- **WHEN** user opens door before booking start time
- **THEN** power-off time SHALL be booking end time + 40 minutes buffer

#### Scenario: Late door open calculation
- **WHEN** user opens door after booking start time
- **THEN** power-off time SHALL be booking end time + 40 minutes buffer

#### Scenario: Time buffer application
- **WHEN** calculating power-off time
- **THEN** system SHALL add 40-minute buffer to booking end time for user convenience