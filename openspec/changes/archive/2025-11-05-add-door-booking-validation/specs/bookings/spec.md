## ADDED Requirements
### Requirement: Door Access Booking Validation
The BookingService SHALL provide methods to validate user bookings for door access.

#### Scenario: Check current valid booking
- **WHEN** system checks if user has valid booking for door access
- **THEN** system SHALL return booking details if user has confirmed booking within allowed time window

#### Scenario: Check booking time window
- **WHEN** system validates booking time for door access
- **THEN** system SHALL allow access if current time is within 1 hour before booking start time

#### Scenario: No valid booking found
- **WHEN** system searches for user's current bookings
- **THEN** system SHALL return null if no valid bookings exist

### Requirement: Booking Status Validation
The system SHALL validate booking status to determine door access eligibility.

#### Scenario: Confirmed booking allows access
- **WHEN** user has confirmed booking status
- **THEN** system SHALL allow door access within time window

#### Scenario: Pending booking denies access
- **WHEN** user has only pending booking status
- **THEN** system SHALL deny door access with appropriate message

#### Scenario: Cancelled booking denies access
- **WHEN** user has cancelled booking status
- **THEN** system SHALL deny door access with appropriate message