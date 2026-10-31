---
title: Training and pilot plan
subtitle: Moving the centre from paper to the information system
---

## 1. Objectives

- Every member of staff uses the system for the daily work of their role, with confidence.
- No loss of patient data, sales or stock during the change.
- Paper is stopped service by service, on a date decided with evidence, not on a hope.
- Staff feel supported, not watched.

## 2. Roles

| Role | Who | What they do |
|---|---|---|
| Rollout lead | [NAME] | Owns the plan and the dates. Runs the weekly review. Decides go or no-go with the promoter. |
| Champion | One per service: [NAME] per service | First helper for colleagues. Collects problems. Shows good practice. |
| Trainers | [NAME], [NAME] | Give the 45-minute sessions. Stay at the elbow in the first days. |
| Support person | [NAME] [PHONE] | Answers calls. Fills the issues log. Escalates to the admin or the developer. |
| Admin | [NAME] | Creates and removes accounts, unlocks accounts, keeps the training accounts. |
| Promoter | [NAME] | Announces, decides, recognises the champions. |

## 3. Schedule (template, in weeks)

| Week | What happens | Dates |
|---|---|---|
| Week 0 | Preparation: accounts, computers, scanners, printers, paper outage forms, outage sheets stuck near each workstation, announcement sent, champions named. | [DATE] to [DATE] |
| Week 1 | Training of the pilot service(s): [SERVICE]. Then go live in the pilot, paper and system in parallel. | [DATE] |
| Weeks 1 to [N] | Pilot with paper and system in parallel for [N] weeks. The pilot ends on [END DATE]. Weekly 15-minute review each [DAY] at [TIME]. | [DATE] to [END DATE] |
| End of pilot | Go or no-go with the criteria in section 7. | [END DATE] |
| Then | Extension service by service, in this order: [SERVICE 1], [SERVICE 2], [SERVICE 3]. Each service has its own parallel period of [N] weeks and its own go or no-go. | [DATE] |
| Paper stop | Paper is stopped for a service when its go or no-go is Yes. Outage forms are kept. | [DATE] per service |

The weekly 15-minute review: look at the tracking sheet, read the issues log, choose the top 3 fixes, thank one person.

## 4. Training sessions

Each role has one session of 45 minutes. Small groups, at a computer, with real cases from that service. Use training accounts, never real accounts, for the exercises.

Session plan: 5 minutes why and what changes, 30 minutes hands-on, 10 minutes questions and the checklist. Give the role's one-page sheet to each person.

At the elbow: a trainer or the champion stays in the service during the first [3] working days of go-live.

| Role | Skills to demonstrate (tick in the Training attendance sheet) |
|---|---|
| Secretary and cash desk | Register a patient. Find a patient. Make an invoice with a scanned product. Add an instalment. Record a withdrawal. Do the cash closing. Read the offline indicator. |
| Nurse | Register a patient. Save a consultation. Check that it appears. Send a patient to the doctor. Read a result. Find Sync failures. |
| Doctor | Take a patient in charge. Write a consultation. Prescribe. Order an exam and read the result. Know what not to do offline. |
| Laboratory | Receive a request. Enter and validate results. Print a result sheet. Correct a result with a reason. Do the weekly count. Head of laboratory: edit the catalogue. |
| Pharmacy and stock | Validate or reject a receipt. Enter a delivery. Do a blind count. Print labels. |
| Production | Record a purchase. Create and start a batch. Declare an output. Ship a batch. |
| Toxicology team | Admit a patient without duplicates. Record an evaluation. Discharge or transfer. Print a file. |
| Spiritual counsellor | Write, edit and delete a note. Know who reads the notes. |
| Promoter | Read the daily check. Decide a discount request. Read a cash closing. Export a report. |
| Admin | Create an account. Reset a password. Unlock an account. Read the audit log. Create and delete training accounts. |

## 5. Training accounts

Training accounts are to be created by the admin before the sessions, one per role, with the data of the training environment only. They are deleted before go-live. No password is written in this plan. Passwords are given in person and changed at first use. Check that no training account stays active after the deletion date [DATE].

## 6. Risks and answers

| Risk | Answer |
|---|---|
| Resistance, "paper is faster" | Keep paper in parallel at first. Let the champion show the gain. Measure the time of a standard task and share it. Ask the sceptics to test and report. |
| Fear of surveillance | Be honest: an audit log records who did what for safety and traceability, not for punishment. Say who can read it. |
| Fear of job loss | The promoter states clearly that the system removes copying and adding up, not jobs [promoter to confirm]. |
| Fear of outages | Outage sheet near every workstation. Paper forms ready. One outage drill during week 0. Offline mode for reception, nursing, medical and laboratory results. |
| Data quality (duplicates, wrong entries) | Search before creating. Weekly check of duplicates by the champion. Sync failures read every day. Correction is always possible and recorded. |
| Key person absent | Each service has a deputy champion [NAME]. |
| Overload during the pilot | Pilot services limited to [N]. Double entry measured and reduced week by week. |

## 7. Go or no-go criteria (end of pilot and each extension)

The same list is in the tracking workbook, sheet "Go-No-go". Decision: go only if every line is Yes.

1. At least [X] percent of the service staff are trained.
2. At least [X] percent of the service staff use the system every day.
3. Records still on paper only are at most [X] percent of the week's records.
4. Sales or entries entered twice are at most [X] per week.
5. No critical issue is open (no data loss, no wrong money total).
6. Average time of a standard task is at most [X] minutes.
7. Average satisfaction is at least [X] out of 5.
8. The outage drill was done and the outage sheet is in place.
9. Cash closing is done every working day for [X] days, with no unexplained difference (reception only).
10. The support person and the deputy champion are confirmed for the next step.

## 8. Communication plan

- **Announcement** by the promoter before week 0 (see announcement-message.md), followed by the short message and the reminder before each session.
- **Weekly note** every [DAY]: three lines. What works, what we fixed, what comes next. Signed by the rollout lead.
- **Recognition**: name the champions and the best helpers in the weekly note and at the staff meeting. Small thanks, [GESTURE], at the end of each pilot.
- **Feedback**: issues log, champion, and the weekly review.

## 9. What to measure

Use adoption-tracking.xlsx. Each service fills one line per week: staff trained, staff using the system daily, records created in the system, records still on paper only, double entries, incidents, average time of a standard task, satisfaction (1 to 5). The issues log and the training attendance sheet are in the same file. The rollout lead reads it at the weekly review and updates the Go-No-go sheet.

## 10. Points to confirm before the pilot

- Which screen the admin uses to unlock an account after the login lock.
- Whether pregnancy fields can be saved without network.
- Whether the laboratory result sheet printing and catalogue editing need the network in your set-up.
- The exact standard task chosen for the time measure in each service: [TASK].
