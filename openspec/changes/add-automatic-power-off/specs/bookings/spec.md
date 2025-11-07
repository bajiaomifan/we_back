## MODIFIED Requirements
### Requirement: Booking Duration Management
The booking system SHALL support automatic power-off scheduling based on booking duration.

#### Scenario: Power-off scheduling on door open
- **WHEN** user opens door for a valid booking
- **THEN** system SHALL schedule power-off for booking end time + buffer

#### Scenario: Booking cancellation affects power-off
- **WHEN** booking is cancelled before power-off execution
- **THEN** system SHALL cancel scheduled power-off task

#### Scenario: Booking modification affects power-off
- **WHEN** booking duration is modified
- **THEN** system SHALL reschedule power-off task accordingly

## ADDED Requirements
### Requirement: Power-Off Task Association
Each booking SHALL be able to have associated power-off tasks.

#### Scenario: Task creation on door open
- **WHEN** user opens door for booking
- **THEN** system SHALL create power-off task linked to booking ID

#### Scenario: Task status synchronization
- **WHEN** booking status changes
- **THEN** system SHALL update corresponding power-off task status

#### Scenario: Task cleanup after completion
- **WHEN** power-off task is completed
- **THEN** system SHALL archive task and update booking status if needed