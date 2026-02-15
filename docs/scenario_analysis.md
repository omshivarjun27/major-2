# Scenario Analysis — 30+ Blind-User Real-World Scenarios

> Generated for Voice-Vision Assistant — Features 7–12 integration analysis.
> Each scenario describes the user situation, the modules involved, the expected system behavior, and the user cue delivered.

---

## 1. Street Crossing — Traffic Light Recognition

**Situation:** User stands at an intersection, traffic light is red.
**Modules:** VQA Engine (scene analysis), Priority Scene (hazard), Audio Engine (traffic noise), TTS.
**Behavior:** Camera detects traffic light state. Audio engine detects heavy traffic. Priority scene flags "red light" as top hazard.
**User Cue:** "Traffic light is red. Heavy traffic detected — wait before crossing."

---

## 2. Person Approaching from Behind (Audio + Action)

**Situation:** Someone walks quickly toward the user from behind.
**Modules:** Audio Engine (footstep SSL → behind), Action Engine (approaching detection), Face Engine (optional ID).
**Behavior:** SSL localizes footsteps at +170° azimuth. Action recognizer detects "approaching" from flow expansion.
**User Cue:** "Someone is approaching from behind, about 3 meters away."

---

## 3. Known Person Greeting

**Situation:** A registered friend approaches and waves.
**Modules:** Face Engine (detect → embed → identify), Face Tracker, Social Cue Analyzer (waving), Action Engine (waving).
**Behavior:** Face detected, embedding matched to "Sarah" with consent. Social cues detect waving gesture + smile.
**User Cue:** "Sarah is in front of you, waving and smiling."

---

## 4. Car Horn Warning

**Situation:** A car honks while user is near a road.
**Modules:** Audio Event Detector (car_horn, CRITICAL), SSL (left -60°), Audio-Vision Fuser (matches car in scene).
**Behavior:** Event classified as car_horn with 0.85 confidence. SSL places source to the left. Vision confirms car object.
**User Cue:** "Car horn detected on your left — exercise caution."

---

## 5. Reading Braille on a Public Sign

**Situation:** User touches a braille plaque on a building entrance.
**Modules:** Braille Engine (capture → segment → classify → OCR), TTS.
**Behavior:** Camera frames the braille dots. Segmenter isolates dot patterns. Classifier maps to characters. OCR produces text.
**User Cue:** "The braille reads: 'Room 204 — Dr. Johnson, Ophthalmology.'"

---

## 6. QR Code on a Medicine Bottle

**Situation:** User holds a medicine bottle with a QR code.
**Modules:** QR Engine (detect → decode → cache), Memory Engine (store for future reference), TTS.
**Behavior:** QR decoded to "Ibuprofen 200mg — take 2 tablets every 6 hours." Cached for next scan.
**User Cue:** "QR code says: Ibuprofen 200mg, take 2 tablets every 6 hours."

---

## 7. Navigating a Crowded Sidewalk

**Situation:** Multiple people, objects, and obstacles on a busy sidewalk.
**Modules:** Object Detection, Depth Estimation, Priority Scene (top 3 hazards), Debouncer, TTS.
**Behavior:** 5 people detected, 2 within 2m. A fire hydrant at 1.5m flagged critical. Debouncer prevents spam.
**User Cue:** "Fire hydrant 1.5 meters ahead on your right. Two people nearby."

---

## 8. Entering an Unfamiliar Building

**Situation:** User approaches a building entrance for the first time.
**Modules:** OCR Engine (sign reading), Memory Engine (store landmark), Event Detector (landmark: entrance), TTS.
**Behavior:** OCR reads "City Library — Main Entrance." Event detector flags as landmark and memorizes.
**User Cue:** "You're at the City Library main entrance."

---

## 9. Emergency Siren Approaching

**Situation:** An ambulance siren grows louder.
**Modules:** Audio Event Detector (siren, CRITICAL), SSL (approaching from right), Audio-Vision Fuser.
**Behavior:** Siren classified at 0.9 confidence. SSL tracks azimuth shifting from +90° to +60° (approaching). Critical alert.
**User Cue:** "Emergency siren approaching from your right — stay alert and move to safety."

---

## 10. Dog Barking Nearby

**Situation:** A dog barks aggressively near the user's path.
**Modules:** Audio Event Detector (dog_bark), SSL (front-left), Audio-Vision Fuser (matches dog in scene).
**Behavior:** Dog bark detected. Vision confirms dog at 3m front-left. Moderate alert.
**User Cue:** "Dog barking to your front-left, about 3 meters away."

---

## 11. Cyclist Approaching Fast

**Situation:** A cyclist rides toward the user on a shared path.
**Modules:** Action Engine (cycling, high lateral flow), Object Detection (bicycle), Priority Scene.
**Behavior:** Action recognizer detects cycling pattern with high flow magnitude. Object detector confirms bicycle.
**User Cue:** "Cyclist approaching — move to the side."

---

## 12. Recalling a Previously Visited Location

**Situation:** User returns to a place they visited last week.
**Modules:** Memory Engine (RAG retrieval), Event Detector (landmark match), TTS.
**Behavior:** Scene features match memorized landmark. RAG retrieves notes: "Coffee shop, accessible entrance on right."
**User Cue:** "You've been here before. This is the coffee shop — accessible entrance is on the right."

---

## 13. Someone Falls Down Nearby

**Situation:** A person collapses or falls in the user's vicinity.
**Modules:** Action Engine (falling detection), Audio Engine (thud sound), Social Cue Analyzer.
**Behavior:** Action recognizer detects sudden downward flow. Audio detects impact. Alert triggered.
**User Cue:** "Someone may have fallen nearby. You may want to offer help or call for assistance."

---

## 14. Reading a Restaurant Menu (OCR + Memory)

**Situation:** User is handed a printed menu at a restaurant.
**Modules:** OCR Engine, Memory Engine (store menu for re-query), VQA (summarize), TTS.
**Behavior:** OCR extracts menu text. VQA summarizes: "This is a pizza restaurant. Prices range from $8–$15."
**User Cue:** "I can see a menu. Would you like me to read specific items?"

---

## 15. Night-Time Navigation — Low Visibility

**Situation:** User walks at night with poor lighting.
**Modules:** Freshness Gate (may reject dark frames), Audio Engine (becomes primary), Proactive Announcer.
**Behavior:** Camera frames too dark for reliable vision. System switches to audio-primary mode.
**User Cue:** "Lighting is very low — I'm relying more on sound. Traffic sounds from your left."

---

## 16. Elevator Arrival (Audio + OCR)

**Situation:** User waits for an elevator; door opens with a chime.
**Modules:** Audio Event Detector (door chime), OCR (floor number display), Event Detector (landmark: elevator).
**Behavior:** Chime detected. OCR reads "Floor 3." Landmark memorized.
**User Cue:** "Elevator arrived — you're on floor 3."

---

## 17. Forgotten Face — Privacy Deletion

**Situation:** User requests deletion of a registered face.
**Modules:** Face Embedding Store (forget/delete), Consent Log, API endpoint.
**Behavior:** User says "forget Sarah's face." System deletes embedding, logs consent withdrawal.
**User Cue:** "Sarah's face data has been completely deleted."

---

## 18. Cloud Sync — Switching Devices

**Situation:** User switches from phone to smart glasses; memories should persist.
**Modules:** Cloud Sync Adapter (Milvus/Weaviate), Memory Engine.
**Behavior:** Local FAISS synced to cloud. New device pulls memories. Encrypted in transit.
**User Cue:** "Your memories are synced. I remember the coffee shop you visited yesterday."

---

## 19. Multiple Faces in a Group Photo

**Situation:** User points camera at a group of people.
**Modules:** Face Detector (multi-face), Face Tracker (assign IDs), Embedding Store (identify known faces).
**Behavior:** 4 faces detected. 2 recognized (with consent). Tracker assigns stable IDs.
**User Cue:** "I see 4 people. I recognize Alice and Bob."

---

## 20. Stairs Detection

**Situation:** User approaches a staircase.
**Modules:** Object Detection (stairs), Depth Estimation (slope change), Event Detector (landmark: stairs), Priority Scene.
**Behavior:** Stairs detected at 2m. Depth shows significant elevation change. Priority: critical obstacle.
**User Cue:** "Stairs ahead, about 2 meters. Going up."

---

## 21. Bus Stop Identification

**Situation:** User stands at a bus stop trying to identify the bus number.
**Modules:** OCR Engine (bus number), QR Engine (bus stop QR), Memory Engine (store route info), TTS.
**Behavior:** OCR reads "Bus 42 — Downtown Express." QR code provides schedule URL.
**User Cue:** "Bus 42 to Downtown Express. Next arrival in 5 minutes."

---

## 22. Tavus Avatar Explaining a Scene

**Situation:** User has a paired display (e.g., tablet) with Tavus avatar.
**Modules:** Tavus Adapter, VQA Engine, TTS.
**Behavior:** Scene narration sent to Tavus. Avatar speaks and shows facial expressions matching tone.
**User Cue:** (Avatar speaks) "You're in a park. There's a bench on your left and a fountain ahead."

---

## 23. ATM Machine Interaction

**Situation:** User approaches an ATM.
**Modules:** OCR Engine (screen text), QR Engine (contactless code), Braille Engine (keypad braille), TTS.
**Behavior:** OCR reads screen prompts. Braille engine reads keypad labels. Step-by-step guidance.
**User Cue:** "ATM screen shows 'Insert Card.' The braille says 'Enter PIN' on the keypad."

---

## 24. Package Delivery — Reading Label

**Situation:** User receives a package and wants to know what it says.
**Modules:** OCR Engine (address/label), QR Engine (tracking code), Memory Engine (store tracking), TTS.
**Behavior:** OCR extracts sender, tracking number. QR decoded for tracking URL.
**User Cue:** "Package from Amazon. Tracking number ending in 4829."

---

## 25. Rainy Day — Wet Surface Warning

**Situation:** It's raining and surfaces are slippery.
**Modules:** VQA Engine (wet surface detection), Priority Scene, Audio Engine (rain sounds), TTS.
**Behavior:** Scene analysis detects wet/reflective surfaces. Audio confirms rain. Priority flags slippery surfaces.
**User Cue:** "Surfaces appear wet and slippery. Take care walking."

---

## 26. Supermarket Navigation — Aisle Reading

**Situation:** User navigates a supermarket.
**Modules:** OCR Engine (aisle signs), Memory Engine (store map), Event Detector (landmarks), TTS.
**Behavior:** OCR reads "Aisle 5 — Dairy & Eggs." Stored as navigation landmark.
**User Cue:** "You're in aisle 5, dairy and eggs."

---

## 27. Meeting a Stranger — No Consent Scenario

**Situation:** User's camera sees an unknown person. No consent for face storage.
**Modules:** Face Detector (detect only), Consent Gate (blocks embedding storage).
**Behavior:** Face detected but NOT stored (consent_required=true, no consent). Only transient tracking.
**User Cue:** "Someone is in front of you." (No name, no persistent data stored.)

---

## 28. Alarm Clock or Smoke Detector

**Situation:** Alarm sounds at home.
**Modules:** Audio Event Detector (alarm, CRITICAL), SSL (localize source), TTS.
**Behavior:** Alarm classified. SSL points to direction of sound source.
**User Cue:** "Alarm sounding from your right — check the source immediately."

---

## 29. Person Reaching Towards User

**Situation:** Someone extends their hand (handshake or threat).
**Modules:** Action Engine (reaching detection), Social Cue Analyzer (facial expression), Face Tracker.
**Behavior:** Action recognizer detects "reaching" with upper-body flow. Social cues indicate smile → likely handshake.
**User Cue:** "Someone is reaching toward you — they appear friendly, likely offering a handshake."

---

## 30. Long-Term Memory Recall — "Where did I leave my keys?"

**Situation:** User asks about a previously seen object.
**Modules:** Memory Engine (RAG query), Claude Opus 4.6 (reasoning), TTS.
**Behavior:** RAG retrieves memory from 2 hours ago: "Keys were on the kitchen counter near the toaster."
**User Cue:** "Based on what I saw earlier, your keys were on the kitchen counter near the toaster."

---

## 31. Construction Zone Warning

**Situation:** User approaches an active construction site.
**Modules:** Audio Engine (machinery sounds), Object Detection (barriers, cones), Priority Scene, TTS.
**Behavior:** Loud machinery detected. Visual confirms barriers/cones. Priority flags as critical.
**User Cue:** "Construction zone ahead. Barriers detected. Find an alternate path."

---

## 32. Detecting Head Nod / Shake in Conversation

**Situation:** User is talking to someone and wants to know if they're nodding or shaking head.
**Modules:** Face Tracker (head pose over time), Social Cue Analyzer (head movement pattern).
**Behavior:** Head pose tracked over frames. Repeated pitch changes → nod. Repeated yaw changes → shake.
**User Cue:** "The person is nodding — they seem to agree."

---

## 33. Currency Note Identification

**Situation:** User holds a banknote and wants to know the denomination.
**Modules:** VQA Engine (visual analysis), OCR Engine (text on note), TTS.
**Behavior:** VQA identifies note size and color patterns. OCR reads denomination text.
**User Cue:** "This appears to be a 20-dollar bill."

---

## 34. Playground Safety for Parent

**Situation:** Blind parent at a playground monitoring their child.
**Modules:** Face Engine (child's registered face), Face Tracker (continuous tracking), Action Engine (detecting play vs danger).
**Behavior:** Child's face tracked continuously. Action recognizer monitors for falling or distress.
**User Cue:** "Your child is playing on the swings. Everything looks safe."

---

## 35. Real-Time Translation of Foreign Sign

**Situation:** User travels abroad and encounters signs in another language.
**Modules:** OCR Engine (text extraction), VQA Engine (translation request), Memory Engine (store translation), TTS.
**Behavior:** OCR extracts foreign text. VQA provides translation. Stored for future reference.
**User Cue:** "The sign says 'Sortie' — that means 'Exit' in French."

---

## Summary Table

| # | Scenario | Primary Modules | Critical? |
|---|----------|-----------------|-----------|
| 1 | Street crossing | VQA, Audio, Priority | Yes |
| 2 | Person from behind | Audio SSL, Action | Yes |
| 3 | Known person greeting | Face, Social Cues | No |
| 4 | Car horn | Audio Event, SSL, Fusion | Yes |
| 5 | Braille reading | Braille Engine | No |
| 6 | QR medicine | QR Engine, Memory | No |
| 7 | Crowded sidewalk | Detection, Depth, Priority | Yes |
| 8 | Building entrance | OCR, Memory, Events | No |
| 9 | Emergency siren | Audio Event, SSL | Yes |
| 10 | Dog barking | Audio, SSL, Vision Fusion | Moderate |
| 11 | Cyclist | Action, Detection, Priority | Yes |
| 12 | Location recall | Memory RAG | No |
| 13 | Person falling | Action, Audio | Yes |
| 14 | Menu reading | OCR, Memory, VQA | No |
| 15 | Night navigation | Audio (primary), Freshness | Moderate |
| 16 | Elevator | Audio, OCR, Events | No |
| 17 | Face deletion | Face Embeddings, Consent | No |
| 18 | Cloud sync | Cloud Sync, Memory | No |
| 19 | Group photo | Face (multi), Tracker | No |
| 20 | Stairs | Detection, Depth, Events | Yes |
| 21 | Bus stop | OCR, QR, Memory | No |
| 22 | Tavus avatar | Tavus, VQA | No |
| 23 | ATM | OCR, Braille, QR | No |
| 24 | Package label | OCR, QR, Memory | No |
| 25 | Rainy day | VQA, Audio, Priority | Moderate |
| 26 | Supermarket aisle | OCR, Memory, Events | No |
| 27 | Stranger (no consent) | Face (detect only) | No |
| 28 | Alarm/smoke detector | Audio Event, SSL | Yes |
| 29 | Reaching gesture | Action, Social Cues | Moderate |
| 30 | Key recall | Memory RAG, Claude | No |
| 31 | Construction zone | Audio, Detection, Priority | Yes |
| 32 | Head nod/shake | Face Tracker, Social Cues | No |
| 33 | Currency ID | VQA, OCR | No |
| 34 | Playground monitoring | Face, Tracker, Action | Moderate |
| 35 | Foreign sign | OCR, VQA, Memory | No |
