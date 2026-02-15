# Scenario Analysis: RAG Memory for Visually Impaired Users

> How retrieval-augmented memory transforms everyday assistance for blind and low-vision users across **25 real-world scenarios**.

---

## 1. Indoor Room Navigation (Home)

**Environment:** Familiar apartment with furniture, rugs, low tables, charging cables on floor.

**How memory helps:**
- Stores spatial layout snapshots ("couch is 2m ahead, table to the right").
- Recalls furniture rearrangements ("Yesterday the chair was moved near the window").
- Alerts on new obstacles ("A box was not here last time you walked this path").

**What to store:** Scene-graph with object positions, obstacle distances, timestamp.

**Example dialogue:**
> **User:** "Has anything changed in the living room since this morning?"
> **Assistant:** "Yes — I see a backpack near the doorway that wasn't there at 8:15 AM. It's about 1.5 metres ahead on your left."

**Safety:** Always re-run live perception; memory is advisory only. Warn if memory is stale (>2 hours).

---

## 2. Crowded Sidewalks

**Environment:** Busy urban sidewalk, pedestrians, street vendors, e-scooters parked on path.

**How memory helps:**
- Learns recurring obstacles ("There's usually a food cart at this corner around noon").
- Recalls safest routes based on past experiences.
- Tracks moving hazards over short time windows.

**What to store:** Obstacle type + density summary, timestamp, GPS context (if available).

**Example dialogue:**
> **User:** "Is the sidewalk ahead clear?"
> **Assistant:** "Right now I see 3 people ahead. From past walks, this block tends to have a vendor cart on the right side around this time."

**Safety:** Never rely solely on memory for dynamic environments; always combine with live perception.

---

## 3. Public Transport — Bus Stops & Platforms

**Environment:** Bus stop with shelter, timetable sign, approaching vehicles.

**How memory helps:**
- Remembers bus stop layouts ("The bench is on the left, curb is 2 steps forward").
- Recalls bus numbers and schedules from past signage readings.
- Tracks which buses the user usually takes.

**What to store:** Signage OCR text, bus numbers sighted, platform layout summary.

**Example dialogue:**
> **User:** "Which bus did I take last Tuesday to the hospital?"
> **Assistant:** "You took Bus 42 from this stop at 9:22 AM last Tuesday."

**Safety:** Always confirm bus number with live perception before boarding.

---

## 4. Supermarket — Product Identification & Barcode

**Environment:** Grocery store aisles, shelves with products, price tags.

**How memory helps:**
- Remembers product locations ("Last time, oat milk was in aisle 3, second shelf").
- Stores barcode scan results for quick re-identification.
- Tracks purchase history ("You bought this brand of pasta two weeks ago").

**What to store:** Product name, barcode, aisle/location hint, price, timestamp.

**Example dialogue:**
> **User:** "Where did I find the peanut butter last time?"
> **Assistant:** "Last visit on February 3rd, you found peanut butter in aisle 5, about halfway down on the right, second shelf from the bottom."

**Safety:** Product placement may change; always confirm with live scan when possible.

---

## 5. Medication & Packaging Reading

**Environment:** Home medicine cabinet, pill bottles, blister packs.

**How memory helps:**
- Stores medication names, dosages, and schedules from label scans.
- Reminds about last dose taken ("You took your blood pressure medicine at 8 AM").
- Alerts on expiry dates.

**What to store:** Medication name, dosage, label OCR, timestamp of each scan/dose, expiry date.

**Example dialogue:**
> **User:** "When did I last take my allergy pill?"
> **Assistant:** "You last scanned and confirmed taking your cetirizine 10mg at 7:45 PM yesterday."

**Safety:** Always remind user to verify with a healthcare professional. Never provide medical advice.

---

## 6. Stairs & Escalators

**Environment:** Building entrance, subway station, shopping mall with stairs/escalators.

**How memory helps:**
- Recalls stair count ("This staircase has 14 steps, last confirmed 3 days ago").
- Remembers which side has the handrail.
- Notes escalator status ("The up escalator was out of service yesterday").

**What to store:** Stair count, handrail position, escalator direction/status, location context.

**Example dialogue:**
> **User:** "How many steps are in this staircase?"
> **Assistant:** "From your last visit, this staircase had 14 steps going down with a handrail on the right. Let me confirm with current perception — I can see the stairs ahead, consistent with 14 steps."

**Safety:** Always supplement memory with live depth estimation; stair conditions can change.

---

## 7. Road Crossings

**Environment:** Intersection, crosswalk, traffic lights, vehicle flow.

**How memory helps:**
- Recalls crossing signal patterns ("This light typically changes every 45 seconds").
- Remembers safest crossing points ("The audible signal is at the east corner").
- Notes construction or road changes.

**What to store:** Crossing location, signal timing patterns, audible signal presence, hazard notes.

**Example dialogue:**
> **User:** "Is it safe to cross here?"
> **Assistant:** "I'm checking live traffic now. From memory, this crossing has an audible signal on your right. I see the pedestrian signal is currently red — wait for the audible cue."

**Safety:** NEVER rely on memory alone for traffic safety. Always use real-time perception. If uncertain, advise waiting.

---

## 8. Social Interactions & Face Recognition

**Environment:** Office, social gathering, café meeting.

**How memory helps:**
- Associates voice patterns or described appearances with names (with consent).
- Recalls last interaction context ("You last met Sarah at the team lunch on Monday").
- Stores conversation context for continuity.

**What to store:** Name, voice description, context of meeting, timestamp. NO facial biometrics without explicit consent.

**Example dialogue:**
> **User:** "Who did I meet at the café yesterday?"
> **Assistant:** "Yesterday at 2:30 PM at the café, you had a conversation that you labelled 'meeting with David about project'. You asked me to remember that David mentioned the deadline is March 15th."

**Safety:** Strict consent required. Never store biometric data without explicit opt-in. Inform user what is stored.

---

## 9. Lost Item Retrieval

**Environment:** Home, office, or any familiar space.

**How memory helps:**
- Recalls where objects were last seen ("Your keys were on the kitchen counter at 7:12 AM").
- Tracks object movement patterns over time.
- Responds to "Where did I put my X?" queries instantly.

**What to store:** Object label, location description, scene-graph excerpt, timestamp.

**Example dialogue:**
> **User:** "Where are my keys?"
> **Assistant:** "The last time I detected your keys was at 7:12 AM today on the kitchen counter, near the coffee maker."

**Safety:** Advise that objects may have been moved since last observation.

---

## 10. Routine Reminders & Daily Patterns

**Environment:** Throughout daily life.

**How memory helps:**
- Learns daily patterns ("You usually leave for work at 8:30 AM").
- Provides proactive reminders ("You normally take your umbrella — it rained last time you forgot").
- Tracks deviations from routine.

**What to store:** Activity timestamps, pattern summaries, user-labelled reminders.

**Example dialogue:**
> **User:** "What's my usual morning routine?"
> **Assistant:** "Based on the last two weeks: you typically wake around 7 AM, take medication at 7:15, have breakfast by 7:45, and leave by 8:30. Today you're running about 15 minutes behind your usual schedule."

**Safety:** Patterns are suggestions, not mandates. Always respect user autonomy.

---

## 11. Emergency Events

**Environment:** Fire alarm, medical emergency, evacuation scenario.

**How memory helps:**
- Recalls nearest exit locations from prior scans.
- Provides building layout context from memory.
- Stores emergency contact information.

**What to store:** Exit locations, emergency routes, emergency contacts, building layout summaries.

**Example dialogue:**
> **User:** "I hear a fire alarm — where's the nearest exit?"
> **Assistant:** "Based on your last building scan, the nearest exit is behind you, about 10 metres. Turn around and go straight. There's a door on the left. I'm running live perception to guide you — clear path detected."

**Safety:** CRITICAL — always prioritize live perception over memory in emergencies. Memory provides initial direction only.

---

## 12. Battery & Charging Interruptions

**Environment:** Device running low on battery during navigation or assistance.

**How memory helps:**
- Saves current state (location, task, navigation progress) before shutdown.
- Resumes context after recharge ("Before battery died, you were heading to aisle 3 in the supermarket").
- Stores charging cable location.

**What to store:** Last known context/task, battery level events, charger location.

**Example dialogue:**
> **User (after restart):** "What was I doing before the battery died?"
> **Assistant:** "Before shutting down at 15% battery, you were navigating to the pharmacy on Main Street. You were approximately 200m away, heading east."

**Safety:** Always re-orient with live perception after restart; environment may have changed.

---

## 13. Elevator & Door Detection

**Environment:** Building lobby, elevator bank, automatic/manual doors.

**How memory helps:**
- Remembers elevator button positions ("The call button is at waist height on the right").
- Recalls which floor has which services ("Dentist is on floor 4").
- Notes door types (push/pull, automatic, revolving).

**What to store:** Button positions, floor directory, door type, accessibility features.

**Example dialogue:**
> **User:** "Which floor is the dentist on?"
> **Assistant:** "From your previous visit, the dentist office is on floor 4. The elevator call button should be on the right wall at about waist height."

**Safety:** Verify floor numbers with live signage reading when possible.

---

## 14. Public Signage Reading

**Environment:** Street signs, building directories, warning signs, information boards.

**How memory helps:**
- Stores OCR results from previously read signs.
- Recalls sign content without re-scanning ("The hours posted on that shop door say 9 AM to 6 PM").
- Tracks changes in posted information.

**What to store:** OCR text, sign location, sign type, timestamp.

**Example dialogue:**
> **User:** "What were the opening hours of that bakery we passed?"
> **Assistant:** "When you scanned the bakery sign on Oak Street last Saturday, the hours were Monday-Friday 7 AM to 4 PM, Saturday 8 AM to 2 PM, closed Sunday."

**Safety:** Business hours and signs can change. Note the date of last scan.

---

## 15. Restaurant & Menu Reading

**Environment:** Restaurant, café, food court with printed or posted menus.

**How memory helps:**
- Stores menu items and prices from previous visits.
- Recalls dietary preferences and past orders.
- Identifies allergens mentioned in previous scans.

**What to store:** Menu text (OCR), restaurant name, prices, allergen notes, past orders.

**Example dialogue:**
> **User:** "What did I order last time at this restaurant?"
> **Assistant:** "Last visit on January 20th, you ordered the grilled chicken sandwich with a side salad, no onions. It was $12.50."

**Safety:** Menus change. Always offer to re-scan current menu. For allergies, always recommend verifying with staff.

---

## 16. Clothing & Outfit Identification

**Environment:** Home wardrobe, getting dressed.

**How memory helps:**
- Stores clothing descriptions ("Blue striped shirt, khaki pants").
- Recalls outfit combinations and when they were last worn.
- Identifies items by colour and pattern from past scans.

**What to store:** Clothing item description, colour, pattern, location in wardrobe, last worn date.

**Example dialogue:**
> **User:** "When did I last wear my blue shirt?"
> **Assistant:** "You last wore the blue striped button-down shirt 4 days ago, on Thursday. You paired it with dark grey trousers."

**Safety:** Colour accuracy depends on lighting conditions during scan. Note confidence level.

---

## 17. Mail & Document Reading

**Environment:** Home mailbox, office desk, important documents.

**How memory helps:**
- Stores OCR text from scanned letters and documents.
- Tracks bills, appointments, and deadlines mentioned in mail.
- Recalls document locations ("Your insurance card scan is from January 15").

**What to store:** Document type, OCR key content, sender, date, action items.

**Example dialogue:**
> **User:** "Did I get any bills this week?"
> **Assistant:** "Yes, on Tuesday I scanned a utility bill from City Power for $87.50, due February 28th. And yesterday there was a credit card statement showing $342.18 due March 5th."

**Safety:** Sensitive financial data — encrypt at rest, require consent, enable easy deletion.

---

## 18. Park & Outdoor Recreation

**Environment:** Public park, trail, playground.

**How memory helps:**
- Remembers trail layouts and landmarks.
- Recalls bench locations for rest stops.
- Notes seasonal changes ("The path was muddy last time after rain").

**What to store:** Trail/path descriptions, landmark positions, surface conditions, bench locations.

**Example dialogue:**
> **User:** "Is there a bench coming up?"
> **Assistant:** "From your last visit, there's a bench about 30 metres ahead on the right side of the path, just past the large oak tree."

**Safety:** Outdoor environments change significantly. Always combine with live perception.

---

## 19. Hotel & Unfamiliar Building Navigation

**Environment:** Hotel room, lobby, conference centre.

**How memory helps:**
- Maps room layout on first exploration ("Bed is straight ahead, bathroom door on left").
- Remembers ice machine and vending locations.
- Stores room number and floor for wayfinding.

**What to store:** Room layout, key locations (bathroom, exits, light switches), floor/room number.

**Example dialogue:**
> **User:** "Where's the bathroom in this hotel room?"
> **Assistant:** "From when you first explored this room: the bathroom door is on your left, about 3 steps from the entrance. The light switch is on the wall inside, right side."

**Safety:** Verify layout with live perception on first use; hotel rooms vary between visits.

---

## 20. Workplace Navigation

**Environment:** Office building, meeting rooms, communal areas.

**How memory helps:**
- Stores office layout and meeting room locations.
- Remembers colleague desk positions.
- Tracks schedule-based occupancy ("Conference room B is usually free at 2 PM").

**What to store:** Office layout, room names/numbers, colleague locations, schedule patterns.

**Example dialogue:**
> **User:** "Where's Conference Room C?"
> **Assistant:** "Conference Room C is on this floor, past the kitchen area, second door on the right. Last time, the door had a sign at head height."

**Safety:** Office reconfigurations happen. Verify with live perception periodically.

---

## 21. ATM & Banking Kiosk Use

**Environment:** Bank ATM, self-service kiosks.

**How memory helps:**
- Remembers ATM button layout and screen sequence.
- Recalls accessible ATMs with audio guidance in the area.
- Stores which ATMs had issues previously.

**What to store:** ATM location, accessibility features (audio jack, braille keypad), last visit notes.

**Example dialogue:**
> **User:** "Is the ATM on High Street accessible?"
> **Assistant:** "From your last visit on January 12th, that ATM had an audio jack on the front panel and a braille keypad. The card slot is on the right side."

**Safety:** Never store PINs or account numbers. Warn about shoulder-surfing risk in public.

---

## 22. Pet Care & Veterinary Visits

**Environment:** Home with pets, veterinary clinic.

**How memory helps:**
- Tracks pet feeding times and amounts.
- Stores vet appointment notes and medication schedules.
- Recalls pet food brand and where it was last purchased.

**What to store:** Feeding logs, vet notes, medication schedules, pet food details.

**Example dialogue:**
> **User:** "When did I last feed the cat?"
> **Assistant:** "You noted feeding the cat at 7:30 AM today — about 5 hours ago. The usual evening feed is around 6 PM."

**Safety:** Pet health decisions should be verified with veterinarian. Memory aids routine tracking only.

---

## 23. Gym & Exercise Facility

**Environment:** Gym, fitness centre, pool.

**How memory helps:**
- Remembers equipment locations and layout.
- Tracks workout routines and progress.
- Recalls locker number and combination method.

**What to store:** Equipment layout, workout logs, locker info, facility layout.

**Example dialogue:**
> **User:** "Which treadmill did I use last time?"
> **Assistant:** "Last visit, you used the third treadmill from the entrance, which had the best audio feedback for speed and incline. You ran for 25 minutes at 6.5 km/h."

**Safety:** Always verify equipment condition with live perception before use. Gym layouts can change.

---

## 24. Laundry & Appliance Operation

**Environment:** Home laundry room, laundromat.

**How memory helps:**
- Remembers washer/dryer settings for different loads.
- Tracks when laundry was started ("Wash cycle started 45 minutes ago").
- Recalls detergent location and dosing.

**What to store:** Appliance settings, cycle start times, detergent info, sorting preferences.

**Example dialogue:**
> **User:** "How long has the washing machine been running?"
> **Assistant:** "You started the wash cycle about 38 minutes ago on the 'delicates' setting. It should be done in approximately 12 minutes based on the usual cycle time."

**Safety:** Appliance condition can change. If unusual sounds or behaviour are reported, advise caution.

---

## 25. Travel & Airport Navigation

**Environment:** Airport terminal, check-in counters, security, gates.

**How memory helps:**
- Stores terminal layout from previous flights.
- Recalls gate locations and walking times.
- Remembers accessible assistance points and restroom locations.

**What to store:** Terminal maps, gate assignments, walking time estimates, accessibility services, flight info.

**Example dialogue:**
> **User:** "How do I get to Gate B12 from here?"
> **Assistant:** "From your last flight through this terminal: Gate B12 is in Concourse B, about a 10-minute walk. Head straight, past the food court, then follow signs to Concourse B on the left. There's a moving walkway about halfway. I'll use live perception to guide you as we walk."

**Safety:** Airport layouts can change with construction. Always verify with live signage and/or airport staff. Security procedures should never be memorised or assumed.

---

## Summary Table

| # | Scenario | Primary Memory Use | Safety Level |
|---|----------|-------------------|--------------|
| 1 | Indoor Navigation | Layout recall, obstacle change detection | Medium |
| 2 | Crowded Sidewalks | Recurring obstacle patterns | High |
| 3 | Bus Stops | Schedule & layout recall | High |
| 4 | Supermarket | Product location, purchase history | Low |
| 5 | Medication | Dosage tracking, label recall | Critical |
| 6 | Stairs/Escalators | Step count, handrail position | High |
| 7 | Road Crossings | Signal patterns, crossing points | Critical |
| 8 | Social Interactions | Name-context association | Low |
| 9 | Lost Items | Last-seen location recall | Low |
| 10 | Daily Routines | Pattern learning, reminders | Low |
| 11 | Emergencies | Exit recall, emergency contacts | Critical |
| 12 | Battery Loss | Context preservation, resume | Medium |
| 13 | Elevators/Doors | Button positions, floor directory | Medium |
| 14 | Public Signs | OCR text recall | Low |
| 15 | Restaurant Menus | Past orders, allergen notes | Medium |
| 16 | Clothing | Outfit history, colour recall | Low |
| 17 | Mail/Documents | Bill tracking, deadline recall | Medium |
| 18 | Parks/Outdoor | Trail layout, bench locations | Medium |
| 19 | Hotels | Room layout mapping | Medium |
| 20 | Workplace | Office layout, meeting rooms | Low |
| 21 | ATM/Banking | Accessibility features, layout | High |
| 22 | Pet Care | Feeding & medication tracking | Medium |
| 23 | Gym | Equipment layout, workout logs | Low |
| 24 | Laundry | Cycle tracking, settings recall | Low |
| 25 | Airport/Travel | Terminal layout, gate navigation | High |

> **Key principle:** Memory always *supplements* real-time perception — it never *replaces* it, especially in safety-critical scenarios (road crossings, emergencies, stairs). The RAG system should explicitly state when it's drawing on memory vs live perception.
