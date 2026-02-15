# Human Evaluation Forms for Spatial Perception Testing

## Form A: Detection Accuracy Evaluation

**Session ID:** ________________  
**Evaluator:** ________________  
**Date/Time:** ________________  
**Environment:** [ ] Desk [ ] Indoor [ ] Outdoor  
**Duration:** ________________  

---

### Instructions

Watch the debug overlay video alongside the actual scene (or in replay mode).
For each 30-second segment, count and record the following:

---

### Detection Counts (per 30-second segment)

| Segment | True Positives | False Positives | False Negatives | Notes |
|---------|---------------|-----------------|-----------------|-------|
| 0:00-0:30 | | | | |
| 0:30-1:00 | | | | |
| 1:00-1:30 | | | | |
| 1:30-2:00 | | | | |
| 2:00-2:30 | | | | |
| 2:30-3:00 | | | | |
| 3:00-3:30 | | | | |
| 3:30-4:00 | | | | |
| 4:00-4:30 | | | | |
| 4:30-5:00 | | | | |

**Definitions:**
- **True Positive (TP):** System correctly detected an obstacle that exists
- **False Positive (FP):** System detected an obstacle that doesn't exist
- **False Negative (FN):** System missed an obstacle that exists

---

### Totals

| Metric | Count |
|--------|-------|
| Total True Positives | |
| Total False Positives | |
| Total False Negatives | |
| **Precision** (TP / (TP + FP)) | |
| **Recall** (TP / (TP + FN)) | |
| **F1 Score** | |

---

### Missed Object Categories

For each false negative, categorize the missed object:

| Category | Count | Examples |
|----------|-------|----------|
| Person | | |
| Furniture | | |
| Small obstacle | | |
| Transparent/glass | | |
| Moving object | | |
| Dark object | | |
| Other | | |

---

### Notes on Problematic Detections

Describe any recurring issues:

_______________________________________________
_______________________________________________
_______________________________________________

---

## Form B: Distance Accuracy Evaluation

**Session ID:** ________________  
**Evaluator:** ________________  

---

### Instructions

For selected detected objects, compare the reported distance with measured distance.

---

### Distance Measurements

| Object Type | Reported Distance | Actual Distance | Error (m) | Error (%) |
|-------------|------------------|-----------------|-----------|-----------|
| | | | | |
| | | | | |
| | | | | |
| | | | | |
| | | | | |
| | | | | |
| | | | | |
| | | | | |
| | | | | |
| | | | | |

---

### Summary Statistics

| Metric | Value |
|--------|-------|
| Mean Absolute Error | |
| Max Error | |
| % within ±0.5m | |
| % within ±1.0m | |

---

## Form C: Navigation Cue Quality Evaluation

**Session ID:** ________________  
**Evaluator:** ________________  

---

### Instructions

Rate each criterion on a scale of 1-5:
- 1 = Very Poor
- 2 = Poor  
- 3 = Acceptable
- 4 = Good
- 5 = Excellent

---

### Navigation Cue Ratings

| Criterion | Rating (1-5) | Comments |
|-----------|--------------|----------|
| **Clarity** - Are cues easy to understand? | | |
| **Timing** - Are warnings given early enough? | | |
| **Accuracy** - Do cues match the actual scene? | | |
| **Completeness** - Are all important obstacles mentioned? | | |
| **Priority** - Are the most dangerous obstacles prioritized? | | |
| **Conciseness** - Are cues short enough for quick understanding? | | |
| **Consistency** - Are similar situations described consistently? | | |
| **Stability** - Are cues stable (not flickering)? | | |

---

### Cue Flickering Assessment

Count instances of cue flickering (rapid changes without scene change):

| Segment | Flicker Count | Description |
|---------|---------------|-------------|
| 0:00-1:00 | | |
| 1:00-2:00 | | |
| 2:00-3:00 | | |
| 3:00-4:00 | | |
| 4:00-5:00 | | |

**Average flickers per minute:** ________________

---

### Confusing Cue Examples

Document any cues that were confusing or misleading:

| Cue Given | Actual Situation | Problem |
|-----------|------------------|---------|
| | | |
| | | |
| | | |

---

## Form D: Safety Assessment

**Session ID:** ________________  
**Evaluator:** ________________  
**Environment:** ________________  

---

### Critical Safety Questions

| Question | Yes | No | N/A | Notes |
|----------|-----|-----|-----|-------|
| Would the system have prevented collision with detected obstacles? | | | | |
| Were there any undetected obstacles that could cause injury? | | | | |
| Was "clear path" ever indicated when path was NOT clear? | | | | |
| Were critical/near hazards appropriately flagged? | | | | |
| Did the system fail or crash during testing? | | | | |
| Was audio output consistent and audible? | | | | |

---

### Near-Miss Incidents

Document any situations where user could have been endangered:

| Time | Obstacle Type | Distance | Detection? | Cue Given | Risk Level |
|------|---------------|----------|------------|-----------|------------|
| | | | | | [ ] Low [ ] Med [ ] High |
| | | | | | [ ] Low [ ] Med [ ] High |
| | | | | | [ ] Low [ ] Med [ ] High |

---

### High-Risk Object Detection Check

Verify detection of safety-critical obstacles:

| Object Type | Presented | Detected? | Distance Accurate? | Cue Appropriate? |
|-------------|-----------|-----------|-------------------|------------------|
| Stairs (down) | [ ] Yes | | | |
| Moving person | [ ] Yes | | | |
| Open door | [ ] Yes | | | |
| Curb/step | [ ] Yes | | | |
| Low obstacle | [ ] Yes | | | |
| Chair | [ ] Yes | | | |

---

### Overall Safety Rating

Based on this evaluation, rate overall safety:

[ ] 1 - Unsafe - Would cause injury  
[ ] 2 - Concerning - Multiple dangerous misses  
[ ] 3 - Marginal - Some concerning issues  
[ ] 4 - Acceptable - Minor issues only  
[ ] 5 - Good - No safety concerns observed  

---

### Recommendation

[ ] Ready for expanded testing  
[ ] Needs improvement before expanding  
[ ] Major issues - stop testing  

**Justification:**
_______________________________________________
_______________________________________________

---

## Form E: User Experience Evaluation

*For use when testing with blind/VI participants*

**Participant ID:** ________________  
**Session ID:** ________________  
**Date:** ________________  

---

### Pre-Test Questions

1. Prior experience with navigation aids? ________________
2. Comfort level with technology (1-5)? ________________
3. Expectations for this session? ________________

---

### Post-Test Questions

Rate each on a scale of 1-5:

| Question | Rating | Comments |
|----------|--------|----------|
| How confident did you feel navigating with this system? | | |
| How clear were the audio guidance cues? | | |
| How timely were the warnings? | | |
| How trustworthy did the system feel? | | |
| How comfortable was the experience? | | |
| How useful would this be in daily life? | | |

---

### Open-Ended Feedback

**What worked well?**
_______________________________________________
_______________________________________________

**What was frustrating or confusing?**
_______________________________________________
_______________________________________________

**What would you change?**
_______________________________________________
_______________________________________________

**Would you use this system again?** [ ] Yes [ ] No [ ] Maybe

---

## Appendix: Scoring Rubric

### Detection Accuracy Score

| Metric | Excellent | Good | Acceptable | Poor |
|--------|-----------|------|------------|------|
| Precision | >95% | 85-95% | 75-85% | <75% |
| Recall | >90% | 80-90% | 70-80% | <70% |
| F1 Score | >92% | 82-92% | 72-82% | <72% |

### Distance Accuracy Score

| Metric | Excellent | Good | Acceptable | Poor |
|--------|-----------|------|------------|------|
| Mean Error | <0.3m | 0.3-0.5m | 0.5-1.0m | >1.0m |
| % within ±0.5m | >90% | 75-90% | 50-75% | <50% |

### Navigation Cue Score

| Average Rating | Grade |
|----------------|-------|
| 4.5-5.0 | Excellent |
| 3.5-4.4 | Good |
| 2.5-3.4 | Acceptable |
| <2.5 | Poor |

---

*Forms should be completed during or immediately after each test session.*
*Store completed forms with session logs for correlation analysis.*
