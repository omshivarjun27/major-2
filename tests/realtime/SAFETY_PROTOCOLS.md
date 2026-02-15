# Safety Protocols for Spatial Perception Testing

## CRITICAL SAFETY NOTICE

**This system is a RESEARCH PROTOTYPE and is NOT intended for independent navigation by blind or visually impaired individuals without sighted supervision.**

---

## 1. Fundamental Safety Requirements

### 1.1 Supervision Requirement

> **MANDATORY: All testing involving blind or visually impaired users MUST be conducted with a sighted guide present at all times.**

- Sighted guide must be within arm's reach
- Guide must have clear view of all obstacles
- Guide must be prepared to intervene immediately
- Guide must not be distracted (no phone use)

### 1.2 Testing Environment Safety

**Indoor Testing:**
- Clear emergency exit paths
- Remove trip hazards (cables, rugs)
- Ensure adequate lighting
- Mark glass doors/walls visibly

**Outdoor Testing:**
- Test in controlled areas first (courtyards, parking lots)
- Avoid traffic areas initially
- Have clear boundaries
- Check weather conditions

### 1.3 Equipment Safety

- Secure all cables to prevent tripping
- Ensure camera mount is stable
- Have backup communication method
- Test audio output before each session

---

## 2. System Failure Protocols

### 2.1 Graceful Degradation

The system MUST implement these fallbacks:

| Failure Mode | Detection | Response |
|--------------|-----------|----------|
| Camera failure | No frames | "Camera unavailable. Stop moving." |
| Model failure | Exception | Fall back to mock detector |
| High latency (>1s) | Timer | "System slow. Proceed with caution." |
| Memory exhaustion | OOM | Disable depth, reduce features |
| Complete crash | Unhandled exception | Audio: "System error. Wait for assistance." |

### 2.2 Safe Fallback Messages

```python
SAFE_FALLBACK_MESSAGES = {
    "camera_error": "Camera not available. Please stop and wait for assistance.",
    "system_slow": "System is responding slowly. Move cautiously.",
    "processing_error": "Unable to analyze surroundings. Please wait.",
    "unknown_error": "System encountered an error. Stop and wait for help.",
    "initialization": "System starting up. Please wait before moving.",
}
```

### 2.3 Recovery Procedures

**If system becomes unresponsive:**
1. User: STOP moving immediately
2. Guide: Verbally confirm user location
3. Guide: Take over navigation
4. Operator: Restart system if needed

**If false clear path detected:**
1. Guide: Immediately warn user
2. User: STOP
3. Operator: Log incident with frame capture
4. Review: Analyze failure cause

---

## 3. Testing Safety Checklist

### Pre-Test Checklist

- [ ] Sighted guide briefed and present
- [ ] Emergency contact numbers available
- [ ] Test environment inspected for hazards
- [ ] Camera and audio tested
- [ ] System running in debug mode with overlay
- [ ] Baseline test completed (desk environment)
- [ ] User briefed on limitations
- [ ] Stop signal agreed upon

### During-Test Monitoring

- [ ] Guide maintaining visual contact with user
- [ ] Guide watching for missed obstacles
- [ ] Operator monitoring system performance
- [ ] Audio cues audible to user
- [ ] Latency within acceptable range
- [ ] No system errors in log

### Post-Test Review

- [ ] Review session recording for false negatives
- [ ] Document any near-misses
- [ ] Collect user feedback
- [ ] Log any system issues
- [ ] Update test protocols if needed

---

## 4. Critical Failure Scenarios

### 4.1 High-Priority Safety Cases

These scenarios MUST be detected reliably:

| Scenario | Required Detection | Failure Impact |
|----------|-------------------|----------------|
| Stairs (down) | CRITICAL | Fall risk |
| Moving vehicle | CRITICAL | Collision |
| Open door (swinging) | HIGH | Impact |
| Curb/step | HIGH | Trip |
| Glass door | HIGH | Collision |
| Wet floor | MEDIUM | Slip |
| Low obstacle (knee height) | HIGH | Trip |

### 4.2 Known Limitations

**The system may NOT reliably detect:**
- Transparent obstacles (glass without frames)
- Very thin objects (wires, poles in certain angles)
- Objects matching background color
- Rapidly moving objects
- Holes/drop-offs with dark appearance
- Overhanging obstacles above camera view
- Objects in very low light

**Users and guides MUST be aware of these limitations.**

---

## 5. Incident Response

### 5.1 Near-Miss Protocol

If user comes close to an undetected obstacle:

1. **STOP** - Guide halts user immediately
2. **SECURE** - Ensure user is in safe location
3. **DOCUMENT** - Record:
   - Time and location
   - Obstacle type and distance
   - What system reported vs. reality
   - Frame captures if available
4. **REVIEW** - Analyze system logs
5. **REPORT** - File incident report

### 5.2 Incident Report Template

```
INCIDENT REPORT - Spatial Perception System

Date/Time: ________________
Location: ________________
Session ID: ________________

WHAT HAPPENED:
□ False negative (missed obstacle)
□ False positive (phantom detection)
□ System crash
□ Incorrect distance
□ Late warning
□ Other: ________________

OBSTACLE DETAILS:
Type: ________________
Actual distance: ________________
Reported distance: ________________
User action: ________________

OUTCOME:
□ No contact
□ Contact avoided by guide
□ Minor contact
□ Injury (describe): ________________

CONTRIBUTING FACTORS:
□ Lighting conditions
□ Obstacle type
□ System latency
□ User speed
□ Other: ________________

CORRECTIVE ACTIONS:
________________
________________

Reported by: ________________
Reviewed by: ________________
```

---

## 6. User Briefing Template

Before any testing session with users, read this briefing:

---

**PARTICIPANT BRIEFING**

"Thank you for participating in this research study. Before we begin, I need to explain some important safety information.

This is a RESEARCH PROTOTYPE of a navigation assistance system. It uses a camera to detect obstacles and provides audio guidance.

**Important limitations you should know:**

1. This system may NOT detect all obstacles. There may be things in your path that it does not warn you about.

2. This system may give FALSE warnings about obstacles that aren't there.

3. This system may estimate distances INCORRECTLY. An object may be closer or farther than reported.

4. This system CAN FAIL without warning. The camera, software, or audio may stop working.

**For your safety:**

1. A sighted guide will be with you at ALL times.

2. If you hear 'System error' or no guidance for several seconds, STOP moving immediately.

3. If you feel uncertain at any time, STOP and ask for assistance.

4. You may end the session at any time for any reason.

Do you understand these limitations and agree to proceed?"

---

## 7. Emergency Contacts

| Role | Contact | Phone |
|------|---------|-------|
| Research Lead | _______ | _______ |
| Safety Officer | _______ | _______ |
| Emergency Services | 911 | 911 |
| Building Security | _______ | _______ |

---

## 8. Regulatory Considerations

### 8.1 IRB/Ethics Approval

Before testing with human participants:
- [ ] Obtain IRB approval if required
- [ ] Prepare informed consent forms
- [ ] Document inclusion/exclusion criteria
- [ ] Plan for data privacy

### 8.2 Liability

- All participants must sign informed consent
- Clearly document research nature of system
- Maintain safety records
- Have appropriate insurance coverage

---

## 9. System Safety Configuration

### 9.1 Required Safety Settings

```python
# config.py - Safety settings

# Minimum warning distance (meters)
MIN_CRITICAL_DISTANCE = 0.3  # Never allow closer than this

# Maximum silence between updates (seconds)
MAX_SILENCE_DURATION = 2.0  # Speak if nothing said for this long

# Fallback message if processing fails
FALLBACK_MESSAGE = "Unable to analyze. Stop and wait for assistance."

# Enable safety mode (extra conservative)
SAFETY_MODE = True

# In safety mode:
# - Lower confidence thresholds (more false positives OK)
# - Larger detection radius
# - More frequent updates
# - Explicit "clear path" confirmations
```

### 9.2 Safety Mode Behavior

When `SAFETY_MODE = True`:
- Detection confidence threshold: 0.3 (vs normal 0.5)
- All objects within 3m are reported
- "Path appears clear" said every 3 seconds
- Any processing delay triggers warning
- System self-checks every 30 seconds

---

## Appendix: Quick Reference Card

### For Guides

```
REMEMBER:
✓ Stay within arm's reach
✓ Watch for obstacles system may miss
✓ Listen to audio - is it working?
✓ Watch for system lag
✓ Be ready to say "STOP"

IF SYSTEM FAILS:
1. Say "STOP" to user
2. Describe surroundings verbally  
3. Guide manually to safe spot
4. Report incident
```

### For Operators

```
MONITOR:
✓ Debug overlay showing detections
✓ Latency < 500ms
✓ FPS > 15
✓ No error messages
✓ Audio output working

IF PROBLEMS:
1. Tell guide immediately
2. Switch to fallback mode
3. Log the incident
4. Capture diagnostics
```

---

*This document must be reviewed before each testing session.*

*Last updated: 2024*
