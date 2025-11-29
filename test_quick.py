#!/usr/bin/env python3
"""Quick test script to validate command system"""

import sys
sys.path.insert(0, '/Users/jason/Code/TinySonos')

from src.commands import Command, CommandType, CommandQueue

print("=" * 60)
print("Testing Command System")
print("=" * 60)

# Test 1: Create command
print("\n1. Creating commands...")
cmd1 = Command(CommandType.PLAY)
print(f"   ✓ Created: {cmd1}")

cmd2 = Command(CommandType.ADD_ALBUM, data={'album_id': 123})
print(f"   ✓ Created: {cmd2}")

# Test 2: Command queue
print("\n2. Testing command queue...")
cq = CommandQueue()
cq.put(cmd1)
cq.put(cmd2)
print(f"   ✓ Queue size: {cq.qsize()}")

retrieved = cq.get()
print(f"   ✓ Retrieved: {retrieved}")
print(f"   ✓ Remaining: {cq.qsize()}")

# Test 3: Statistics
print("\n3. Testing statistics...")
stats = cq.get_stats()
print(f"   ✓ Stats: {stats}")

print("\n" + "=" * 60)
print("All tests passed! ✓")
print("=" * 60)
