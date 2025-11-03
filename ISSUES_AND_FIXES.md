# Encoder Flicker Issues - Priority List with Fixes

## Issue 1: Multiple Concurrent TP Commands (HIGH PRIORITY)
**Severity**: HIGH  
**Description**: Three different update loops sending TP commands simultaneously:
- Main loop (`_run_encoder_update_loop`): TPA, TPB every 0.5s
- EncoderPanelUpdater: TPA, TPB, TPC, TPD every 50ms  
- Dialog loop (`encoder_setup_dialog`): TP{axis} every 0.1s

**Impact**: Commands queue up, causing response delays, stale data, and racing GUI updates.

### Potential Fixes:

#### Fix 1A: Add Thread-Safe Lock to TCP Client (RECOMMENDED)
**Implementation**:
- Add `threading.Lock()` to `FakeGclib.__init__()`
- Wrap entire `GCommand()` method with lock: `with self._command_lock:`
- Ensures only one command-response pair happens at a time

**Pros**:
- Simple, isolated change
- Prevents command/response mixing
- Works for all command types

**Cons**:
- Commands will queue and wait (adds latency)
- Could cause delays if one command hangs

**What Could Break**:
- If a command hangs, all subsequent commands wait (deadlock risk)
- Increased latency if multiple loops are active
- Could mask underlying timing issues

---

#### Fix 1B: Disable Other Loops When Dialog Opens
**Implementation**:
- In `encoder_setup_dialog.start_position_updates()`:
  - Pause `EncoderPanelUpdater`: `self.main_app._enc_updater.pause()`
  - Stop main loop: `self.main_app.test_encoder_update_running = False`
- In `encoder_setup_dialog.close()`:
  - Resume `EncoderPanelUpdater`: `self.main_app._enc_updater.resume()`
  - Restart main loop if needed

**Pros**:
- Eliminates concurrent commands entirely
- Dialog has exclusive access to TP commands
- Clean separation of concerns

**Cons**:
- Main display stops updating while dialog is open
- Need to track state properly
- Could miss updates in main display

**What Could Break**:
- Main display shows stale encoder positions while dialog is open
- If dialog crashes, loops might not restart
- State management could get out of sync

---

#### Fix 1C: Single Shared Update Loop
**Implementation**:
- Create one centralized encoder update loop
- All components request updates from this loop
- Loop distributes position data to subscribers

**Pros**:
- Single source of truth
- No duplicate TP commands
- Efficient

**Cons**:
- Major refactoring required
- Need publisher/subscriber pattern
- Complex state management

**What Could Break**:
- Everything - this is a major architectural change
- Could break existing update mechanisms
- Testing would be extensive

---

## Issue 2: EncoderPanelUpdater and Main Loop Both Update Same Display (HIGH PRIORITY)
**Severity**: HIGH  
**Description**: Both `EncoderPanelUpdater` and `_run_encoder_update_loop` update the same encoder position displays, causing racing updates.

**Impact**: Two different sources updating same display element causes flickering.

### Potential Fixes:

#### Fix 2A: Disable One When Other is Active (RECOMMENDED)
**Implementation**:
- In `_ensure_encoder_update_running()`: Don't start `EncoderPanelUpdater` if `test_encoder_update_running == True`
- In `start_encoder_update()`: Stop `EncoderPanelUpdater` before starting main loop
- Ensure only one is active at a time

**Pros**:
- Simple logic change
- Prevents racing updates
- Clear ownership

**Cons**:
- One display method disabled
- Need to choose which is primary

**What Could Break**:
- If main loop stops, `EncoderPanelUpdater` might not restart
- Could leave displays not updating
- State synchronization issues

---

#### Fix 2B: Single Update Source
**Implementation**:
- Choose one update mechanism (e.g., `EncoderPanelUpdater`)
- Remove or disable the other
- Consolidate all updates through one path

**Pros**:
- Eliminates race condition
- Simpler code
- Single update path

**Cons**:
- Loses functionality from removed mechanism
- May need to port features
- Could break existing behavior

**What Could Break**:
- Features that depend on the removed mechanism
- Update frequency changes
- Display update timing

---

## Issue 3: No Update Cancellation (MEDIUM-HIGH PRIORITY)
**Severity**: MEDIUM-HIGH  
**Description**: `after_idle()` callbacks are queued but not tracked/cancelled. Old updates can execute after new ones.

**Impact**: Display shows old value briefly, then new value (flicker).

### Potential Fixes:

#### Fix 3A: Track and Cancel Pending Updates (RECOMMENDED)
**Implementation**:
- Add `self._pending_update_id = None` to `EncoderSetupDialog.__init__()`
- Before queueing new update:
  ```python
  if self._pending_update_id:
      self.dialog.after_cancel(self._pending_update_id)
  self._pending_update_id = self.dialog.after_idle(lambda: ...)
  ```
- Clear `_pending_update_id` when callback executes

**Pros**:
- Prevents stale updates
- Simple to implement
- Minimal code change

**Cons**:
- Only works for `after_idle()` (not `after()`)
- Need to track ID properly

**What Could Break**:
- If callback ID is invalid, `after_cancel()` raises exception
- Could miss updates if cancellation fails
- Need proper cleanup on dialog close

---

#### Fix 3B: Use StringVar Instead of after_idle()
**Implementation**:
- Replace Canvas with Label using `StringVar`
- Update via `position_var.set()` directly from background thread
- Tkinter StringVar is thread-safe

**Pros**:
- No callback queuing issues
- Thread-safe by design
- Simpler code

**Cons**:
- Label might flicker more than Canvas
- Need to test thread-safety
- Could have different visual behavior

**What Could Break**:
- Visual appearance might change
- Label updates might be slower
- Could introduce new flickering if Label itself has issues

---

## Issue 4: Multiple GUI Update Mechanisms (MEDIUM PRIORITY)
**Severity**: MEDIUM  
**Description**: Different update mechanisms (`root.after(0, ...)`, `root.after(_period_ms, ...)`, `dialog.after_idle()`) racing.

**Impact**: Callbacks execute in unexpected order, causing display to flicker.

### Potential Fixes:

#### Fix 4A: Standardize Update Mechanism
**Implementation**:
- Use `after_idle()` for all immediate updates
- Use `after(delay, ...)` for periodic updates
- Document which to use when

**Pros**:
- Consistent behavior
- Easier to debug
- Predictable execution order

**Cons**:
- Need to refactor multiple places
- `after(0, ...)` might have different semantics
- Could change timing behavior

**What Could Break**:
- Update timing might change
- Some updates might not execute when expected
- Could introduce delays

---

#### Fix 4B: Add Update Queue with Priority
**Implementation**:
- Create update queue system
- Priority-based execution
- De-duplicate updates

**Pros**:
- Controlled execution order
- Prevents duplicate updates
- Sophisticated

**Cons**:
- Complex to implement
- Overkill for this problem
- Adds overhead

**What Could Break**:
- Everything - this is a major architectural change
- Could break timing-sensitive updates
- Complex debugging

---

## Issue 5: TCP Client Response Reading (Byte-by-Byte) (MEDIUM PRIORITY)
**Severity**: MEDIUM  
**Description**: TCP client reads response byte-by-byte, which could read wrong bytes if server sends fragmented/multiple responses.

**Impact**: Could get partial/corrupted responses.

### Potential Fixes:

#### Fix 5A: Read Full Response with Timeout (RECOMMENDED)
**Implementation**:
- Set socket timeout: `self.socket_client.settimeout(1.0)`
- Read until `\r\n` found:
  ```python
  response = b""
  while True:
      chunk = self.socket_client.recv(4096)  # Read larger chunks
      if not chunk:
          break
      response += chunk
      if b"\r\n" in response:
          break
  # Extract first line
  response = response.split(b"\r\n")[0]
  ```

**Pros**:
- More efficient (larger reads)
- Handles fragmented responses
- Timeout prevents hanging

**Cons**:
- Could read multiple responses if not careful
- Need to ensure only one response per command
- More complex parsing

**What Could Break**:
- If server sends multiple responses, could read wrong one
- Timeout could cause premature failures
- Need to handle partial reads correctly

---

#### Fix 5B: Add Thread-Safe Lock (Already in Fix 1A)
**Implementation**: See Fix 1A - lock prevents concurrent commands, so responses won't mix.

**What Could Break**: See Fix 1A.

---

## Issue 6: Canvas Text Update Check Race Condition (MEDIUM PRIORITY)
**Severity**: LOW-MEDIUM  
**Description**: Between `itemcget()` and `itemconfig()`, another callback could execute and update text, causing flicker.

**Impact**: Multiple callbacks could overwrite each other.

### Potential Fixes:

#### Fix 6A: Remove Check, Always Update
**Implementation**:
- Remove the `current_text != text` check
- Always call `itemconfig()` - Canvas handles optimization internally

**Pros**:
- Simpler code
- No race condition
- Canvas is efficient

**Cons**:
- Might cause unnecessary redraws
- Could be slightly slower

**What Could Break**:
- Unlikely - Canvas should handle redundant updates
- Might have slight performance impact

---

#### Fix 6B: Use Lock Around Update
**Implementation**:
- Add `threading.Lock()` to dialog
- Lock around `itemcget()` and `itemconfig()`

**Pros**:
- Prevents race condition
- Thread-safe

**Cons**:
- Overhead from locking
- Lock in main thread (usually not needed)
- More complex

**What Could Break**:
- Minimal - locks are lightweight
- Could cause slight delays if many updates

---

## Issue 7: Dialog Loop Not Stopped When Dialog Closes (MEDIUM PRIORITY)
**Severity**: MEDIUM  
**Description**: Need to verify `update_running` is set to False and thread is properly stopped when dialog closes.

**Impact**: Dialog loop continues running after dialog closes, sending TP commands unnecessarily.

### Potential Fixes:

#### Fix 7A: Ensure Proper Cleanup (RECOMMENDED)
**Implementation**:
- In `__del__()` or `close()` method:
  ```python
  self.update_running = False
  if self.update_thread and self.update_thread.is_alive():
      self.update_thread.join(timeout=1.0)
  ```

**Pros**:
- Ensures cleanup
- Prevents resource leaks
- Simple

**Cons**:
- Need to ensure `close()` always called
- Thread join might block briefly

**What Could Break**:
- If `close()` not called, cleanup won't happen
- Thread join could block if thread hangs
- Need proper exception handling

---

## Issue 8: Emulator Position Update Race Condition (LOW-MEDIUM PRIORITY)
**Severity**: MEDIUM  
**Description**: Background thread updates `axis.position` every 20ms while TP command reads it. No lock on access.

**Impact**: Could read partial/inconsistent value (though Python GIL might make int assignment atomic).

### Potential Fixes:

#### Fix 8A: Add Lock to Position Access (RECOMMENDED)
**Implementation**:
- Add `threading.Lock()` to `AxisState`
- Lock in `update_motion()` when updating `position`
- Lock in `_cmd_tell_position()` when reading `position`

**Pros**:
- Guaranteed thread-safety
- Prevents race conditions
- Safe for concurrent access

**Cons**:
- Lock overhead (minimal)
- More complex code
- Need locks for all position accesses

**What Could Break**:
- Unlikely - locks are well-tested
- Slight performance impact
- Need to ensure all accesses are locked

---

## Issue 9: Reverse Checkbox Reading (LOW PRIORITY)
**Severity**: LOW  
**Description**: Dialog reads `self.reverse_var.get()` in background thread. Tkinter variables are thread-safe, but could cause issues.

**Impact**: Could get inconsistent display value if checkbox changes during update.

### Potential Fixes:

#### Fix 9A: Cache Reverse State
**Implementation**:
- Read `reverse_var.get()` once at start of update loop iteration
- Cache value for that iteration
- Update cache when dialog updates

**Pros**:
- Consistent value for one update
- Simple

**Cons**:
- Might miss checkbox changes during update
- Need to handle state changes

**What Could Break**:
- Unlikely - checkbox changes are infrequent
- Might have slight delay in applying reverse

---

## Issue 10-12: Minor Issues (LOW PRIORITY)
**Severity**: LOW  
**Description**: Various edge cases (TCP server sharing, position update timing, string conversions).

**Impact**: Minimal - unlikely to cause flickering.

### Fixes:
- These are edge cases that are unlikely to be the root cause
- Address only if high-priority fixes don't resolve issue

---

## Recommended Fix Order

1. **Fix 1A + Fix 2A**: Add TCP client lock + disable competing loops
   - Addresses root cause (multiple concurrent commands)
   - Prevents racing updates
   - Low risk

2. **Fix 3A**: Track and cancel pending updates
   - Prevents stale updates
   - Simple implementation
   - Low risk

3. **Fix 5A**: Improve TCP response reading
   - Handles fragmented responses
   - Medium risk

4. **Fix 8A**: Add lock to emulator position access
   - Ensures thread-safety
   - Low risk

5. **Fix 7A**: Ensure proper cleanup
   - Prevents resource leaks
   - Low risk

