# TinySonos Tests

This directory contains test scripts for validating the TinySonos controller architecture.

## Test Files

### Unit Tests
- **test_commands.py** - Tests for the command system (Command, CommandType, CommandQueue)
- **test_controller.py** - Unit tests for the PlaybackController with mock Sonos

### Integration Tests
- **test_integration.py** - Validates server.py integration with new controller architecture
- **test_controller_quick.py** - Quick validation test for PlaybackController functionality
- **test_quick.py** - Quick validation for command system

### Mock Objects
- **mock_sonos.py** - Mock Sonos speaker for testing without hardware

## Running Tests

### Unit Tests
```bash
# Test command system
python tests/test_commands.py

# Test controller
python tests/test_controller.py

# Quick validation
python tests/test_quick.py
python tests/test_controller_quick.py
```

### Integration Tests
```bash
# Test server integration (requires Sonos speaker or mock)
python tests/test_integration.py
```

## Test Coverage

Current tests cover:
- Command queue operations
- Controller command processing
- State management
- Queue manipulation
- Playback control (play, pause, stop, next, prev)
- Server.py integration with USE_NEW_CONTROLLER feature flag

## Future Test Additions

Consider adding:
- End-to-end HTTP endpoint tests
- SSE event stream tests
- Album art handling tests
- External source takeover scenarios
- Edge cases (empty queue, network errors, etc.)
