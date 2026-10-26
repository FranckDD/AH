---
title: Triage and care
role: Nurse and head nurse
subtitle: Registering a new patient, taking the measurements, writing the nursing consultation, sending the patient to a doctor, handling appointments, reading laboratory results and following the patients who stay in the centre.
version: 26 October 2026
output: nurse-1-triage-care
---

## Before you start {.unnumbered}

This is the first guide for nurses. It follows the day of a nurse at the front of the clinic: a patient arrives, you register the patient if the file does not exist, you measure and write the first notes, and you decide whether a doctor must see the patient. It also covers appointments, the laboratory results you can read, the patients who stay in the centre, the notification bell, the offline mode and your profile.

The second nurse guide covers the shift calendar and the planning work of the head nurse. A head nurse works exactly as described here, with the extra rights described in that second guide. Nothing about shifts is repeated here.

The screenshots come from a demonstration installation. The patients in the figures are invented. Numbers in red discs, such as {3}, match the numbered markers drawn on the figures.

### What the nurse can see and do

Your menu has three groups. Under **Activity** you find Appointments, Patients, Hospitalized Patients and Nurse Schedule. Under **Medical** you find Prescriptions, Consultations and Exam Results. Under **Follow-up** you find the Dashboard. A Sync failures entry appears only when something you entered offline was refused by the server.

You work on clinical patients and clinical data. You can register a patient, write consultations, book appointments, read laboratory results and record the progress of inpatients. You do not see invoices or the cash register, and you cannot enter or change a laboratory result: that belongs to the laboratory technician. For a patient who is also followed in toxicology or spiritual care, the file tells you that another service follows the patient but does not show the details.

### Interface language

The application starts in French on a new computer. The language switch sits at the top right of every screen, next to the bell: select **EN** to work in English. The choice is kept on that computer.

> Note: Some labels stay in French in English mode. The patient list and the registration form use "Ajouter un patient" (add a patient), "Créer" (create), "Annuler" (cancel), "Voir Dossier" (open the file), "Modifier" (edit) and "Supprimer" (delete). In the patient file you will meet "Prescrire" (prescribe), "Tension" (blood pressure), "Poids" (weight) and "Fermer" (close). This guide quotes each label as it appears and gives the English meaning the first time.

## Signing in and the dashboard

Each member of staff has a personal account. Every consultation carries the name of the person who saved it.

![The sign-in form](figures/signin.png "small")

1. Open the address of the application in the browser (Chrome or Edge).
2. Type your user name in [[Username]] {1}.
3. Type your password in [[Password]] {2}.
4. Select [[Sign in]] {3}.

After several failed attempts in a short time, the server refuses new tries for a while. Wait a minute before trying again.

The application opens on your **Dashboard**.

![The nurse dashboard](figures/dashboard.png)

The menu {1} gives access to every screen of your role. The connection indicator {2} reads "Connected" when the computer is in contact with the server. The block **Patients awaiting review** {3} lists the patients whom a nurse has measured and who wait for a doctor. **Quick access** {4} opens Appointments, Current stays (the inpatients, chapter 8) and Patients. **Statistics for the period** {5} counts your consultations and the stays in the centre between the two dates at the top right.

The waiting list is for information. A nurse sees no [[Take in charge]] button, because only a doctor takes a patient in charge. The list also shows only the patients sent to the shared queue (chapter 4). A patient sent to one named doctor does not appear in your list, although that doctor sees the patient.

## Registering a new patient

A patient who has never come to the centre has no file. You create it before anything else, and the application then leads you straight to the first measurements. The patient code is built by the server and you cannot choose it.

1. In the menu, select **Patients**.
2. Select [[Ajouter un patient]] {1}.

![The patient list](figures/patients-list.png)

The list shows the patients of the centre. Use the search box {2} to look for a name or a code before you create a file: a patient who is already known must not be registered twice. The tabs {3} count **All Patients** and **Clinical Care**. The **Type** column shows NEW for a patient who has no follow-up yet, CLINIQUE for a clinical patient, and TOXICO or SPIRITUEL for a patient of another service. [[Voir Dossier]] {4} opens the file.

![The registration form](figures/newpat-form.png "small")

3. Type the first name in [[Prénom]] {1} and the last name in [[Nom]]. Both are required.
4. Choose the birth date in [[Date de naissance]] {2}. It is required.
5. Choose [[Genre]] {3}: Non précisé, Masculin, Féminin or Autre.
6. Type the national identity number if the patient has one. The telephone {4}, the residence, the insurance and the names of the parents are optional but useful.
7. Select [[Créer]] {5}.

A window **Patient registered** opens.

![The patient code window](figures/newpat-code.png)

8. Read the patient code {1}, for example AH2-690509EX. [[Copy]] {2} copies it.
9. Write the code in the patient's paper notebook, then select [[OK]] {3}.

The patient will give this code at the next visit, which is why it goes in the notebook before you continue.

The form of the first measurements opens at once (chapter 3). In the demonstration, the Type column of the list kept reading NEW for such a patient after the measurements were saved, while the header of the file read CLINIQUE. Trust the file.

> Caution: Do not create a second file for a patient who already has one. The Sync failures screen explains that a patient created offline can be refused by the server, for example when the national identity number is already used by another patient.

## Measurements and the nursing consultation

A nursing consultation records one visit: the reason, the vitals, the history and allergies, the symptoms and your notes. You reach the same form in three ways.

- Right after registering a patient, as described in chapter 2. The form carries the title **New consultation**, the patient is filled in, and the switch **Refer to doctor** is already on.
- From a patient file: [[New consultation]] on the **Medical Record** tab. The patient is filled in and the switch is off.
- From the **Consultations** screen: [[New consultation]] at the top right, where you type the patient code yourself.

![The measurements form of a new patient (the empty Diagnosis and Treatment sections are left out of the picture)](figures/vitals-form.png)

The form is a panel with these parts, from top to bottom.

**Consultation** {1}. The date is today. The reason is required: choose it from the list (consultation, gratuite, hospitalisation, rendez-vous, suivi_prénatal, urgence). The severity is Low, Medium or High and colours the line in the consultation list.

**Vitals** {2}{3}. Blood pressure is typed as 120/80. The form refuses a temperature outside 30 to 45 degrees, a weight outside 0 to 1000 kg and a height outside 30 to 250 cm.

**History and allergies** {4}. Write the allergies that apply to this patient, even if the answer is "none known". The allergies written in the most recent consultation feed the red allergy card of the file.

**Examination and symptoms**, **Diagnosis and treatment** and **Clinical Notes**. Write what the patient tells you and what you find. The diagnosis and the treatment belong to the doctor: leave them empty unless a doctor told you what to write.

**Doctor referral** {5}{6}. This part decides what happens to the patient next (chapter 4).

Select [[Save]] {7} when the form is complete. After a registration, the message "Measurements saved." appears at the top right. After a consultation started from a file, the file shows the new consultation at once and a green banner offers "Add a prescription for this consultation?" with the buttons [[No]] and [[Yes, prescribe]].

> Note: Right after saving a new consultation, the author may show as "Inconnu" (unknown) and the cards of the file may show a dash. Reload the file: your name and the values appear.

### The patient file

![The patient file](figures/dossier.png)

The header {1} gives the name, the patient code, the age and a badge for each service that follows the patient. The cards show the last blood pressure {2}, the weight and the temperature, and the known allergies {3}, in red. The **Medical Record** tab lists the consultations, the newest first. [[New consultation]] {4} opens an empty form. [[Modifier]] {5} changes the consultation and [[Prescrire]] {6} writes a prescription for it. The other tabs are **Exams** (chapter 7), **Treatments** and **Hospitalization** (chapter 8).

### Correcting a consultation

[[Modifier]] opens the same form with the saved values. The section **Doctor referral** does not appear in a form that you edit: the referral is decided when the consultation is created. Change the text, then select [[Save]]. The change shows in the file at once.

### Only the latest consultation can be changed

As soon as a newer consultation exists for the same patient, the older one becomes read-only. Its buttons are replaced by the grey label "Consultation closed: a more recent consultation exists", and the prescriptions linked to it become read-only as well.

> Caution: Complete the visit in the consultation you already started, with [[Modifier]]. A second [[New consultation]] on the same visit closes the first one, and its measurements stay behind in a record that nobody can edit.

### The Consultations screen

**Consultations** in the menu lists the consultations of every patient with the date, the reason, the severity, the diagnosis and the treatment.

[[New consultation]] at the top right opens the form, the search box finds a patient by name or code, and the filters narrow the list by reason, severity and dates. [[Edit]] changes a consultation that is still the latest one.

## Sending the patient to a doctor

A consultation that stays between nurses is a nursing note. A consultation that needs a doctor is referred. The switch **Refer to doctor** at the bottom of the form makes the difference.

![Referral switched on, with a named doctor](figures/refer-named.png)

When the switch is on {1}, the list **Doctor** {2} appears. There are two choices.

- A named doctor. The patient waits in the list of that doctor only.
- "Shared queue (any doctor)". Every doctor sees the patient, and the first doctor who selects [[Take in charge]] keeps the patient. Choose it when you do not know yet which doctor will be free.

Both choices put the patient in the **Patients awaiting review** block of the doctor's dashboard, with your name ("flagged by Demo Nurse") and a badge for the waiting time. In the demonstration, a patient referred to Dr Paul Essomba appeared on his dashboard but not on the nurse's one, while a shared queue patient appeared on both.

When the switch is off, the form says "Unchecked = a regular nursing note, won't appear on any doctor's dashboard." The consultation is saved in the file and no doctor is warned. Use it for a dressing, a routine measurement or any visit that does not need a doctor.

In the registration flow the switch starts on, because a new patient is expected to see a doctor. In a consultation started from a file, it starts off. Check it before you save.

> Caution: Nothing in the application warns a doctor when you leave the switch off, and a consultation already saved cannot be referred afterwards from the edit form. If you forgot the switch, create a new consultation with the switch on and a short note. This closes the earlier one, which is acceptable because the measurements are repeated in the new one.

The doctor then takes the patient in charge, completes your consultation and writes the prescription. The first doctor guide describes that side.

## Prescriptions

The application also lets a nurse open the prescription form, from [[Prescrire]] under a consultation, from [[Yes, prescribe]] or from the **Prescriptions** screen. Use it only for what a doctor has told you to give.

1. Leave [[This is a lab order]] unticked for a medicine.
2. Type the medicine in [[Medication]], then the [[Dosage]] and the [[Frequency]].
3. Type the [[Duration]]. Dosage, frequency and duration are required.
4. Check the start date, add an end date if the treatment must be followed for renewal, and add a note if needed.
5. Select [[Save]].

The prescription is saved under your user name, and it appears on the **Prescriptions** screen with your name in the Prescriber column. A prescription of a consultation that has been closed by a newer one is read-only.

## Appointments

The **Appointments** screen shows the appointments of the whole centre: the patient, the telephone number, the doctor, the date and time, the reason and the status. You can book, change, complete and cancel them like a doctor.

![The appointments list](figures/appointments-list.png)

Use the search box {1} and the filters on the right to narrow by status (Pending, Cancelled, Completed) and by date. [[Calendar view]] {2} switches to a month calendar, and [[Book Appointment]] {3} opens the booking form. A pending line carries five buttons, and [[Start consultation]] {4} is the first.

### Booking an appointment

1. Select [[Book Appointment]].
2. Type the patient code in [[Patient Code]], then press Tab. The patient name appears under the field when the code is recognised.
3. Choose a specialty, then the doctor. "Unassigned" leaves the appointment without a doctor.
4. Choose the date and a time slot.
5. Type the reason of the visit.
6. Select [[Save]].

The new line shows "Pending".

### Working an appointment

- [[Start consultation]] opens the patient file, where you select [[New consultation]].
- [[Complete]] marks the appointment as done. The status turns to "Completed" and only [[Edit]] remains.
- [[View record]] opens the patient file without changing anything.
- [[Edit]] changes the date, the time, the doctor or the reason. In the demonstration, moving an appointment from 10:00 to 11:00 showed at once in the list.
- [[Reject]] cancels the appointment. There is no confirmation question: the status turns to "Cancelled" immediately.

Saving a consultation does not complete the appointment by itself. Select [[Complete]] after the visit.

> Caution: Select [[Complete]] or [[Reject]] only after checking the line. A completed or cancelled appointment keeps only [[Edit]], and the way to undo a rejection is to book a new appointment.

## Laboratory results

The **Exam Results** screen shows the results that the laboratory has completed. You read them, you cannot enter or change them. An exam still in progress is not visible: the list then reads "No completed exam found".

![The completed results of a patient](figures/results-list.png)

1. Select **Exam Results** in the menu.
2. Type a patient name or code in the search box {1}.
3. Select [[Refresh]] {2} to reload the list.
4. Select [[View details]] {3} to read a result, or [[Download PDF]] {4} to save it.

A patient who had several exams in one visit has one line per exam. The detail opens in a panel.

![One result in detail](figures/result-detail.png)

The panel shows the result table {1}: the parameter, the value, the unit, the reference values {2} and the interpretation {3}. A value outside the reference range carries the label High or Low, and the interpretation column says "Haut" or "Bas". A dash in the reference column means that the parameter has no range for this patient, so the value has no automatic flag: read it against your own references. The note of the technician appears at the bottom as "Conclusion / General notes".

The same results appear in the patient file, on the **Exams** tab, with a status label per exam and a red label such as "2 abnormal" when values are out of range. [[View Results]] opens the same sheet.

## Patients who stay in the centre

A patient who must stay for treatment is hospitalised. The nurse and the doctor use the same screens and can do the same four things: admit, record the progress, discharge and download the discharge letter. The second doctor guide describes the discharge, the letter and the readmission in full. This chapter covers what a nurse does most often.

**Hospitalized Patients** in the menu lists every patient who is in the centre now, whoever admitted the patient.

The columns give the admission date and time, the number of days, the current status and the person who admitted the patient. [[View record]] opens the patient file. The status column shows the latest entry of each stay.

### Admitting a patient

1. Open the patient file and select the **Hospitalization** tab.
2. Select [[Admit]].
3. Type the reason in [[Admission reason]]. The field is optional, but it is the only place where the reason is recorded.
4. Select [[Confirm]].

The card now shows "Hospitalized since", the date and time, the number of days and your name under "Admitted by".

### Recording the progress

Each time you see the patient, add an entry. The status is Improving, Stable or Worsening.

![Adding a progress entry](figures/status-form.png)

1. On the **Hospitalization** tab, select [[Update status]] {1}.
2. Choose the status {2}.
3. Write the measurements and what you did in the note {3}.
4. Select [[Confirm]] {4}.

![The card of a stay in progress](figures/hosp-card.png)

**Latest update** {1} shows the status of the last entry, and **Current stay's clinical updates** {2} lists every entry with its author and its note. [[Update status]] {3} adds an entry and [[Discharge]] {4} closes the stay. Entries cannot be changed or deleted. If one is wrong, add a new entry that corrects it.

> Caution: A Worsening entry is meant to send a notification to the other doctors and nurses, but in the demonstration none arrived: a doctor saved a Worsening entry on an inpatient, and the nurse's bell stayed empty. The status Worsening shows in the Hospitalized Patients list. Tell the doctor on duty yourself, and do not rely on the bell.

## Notifications

The bell at the top right of every screen opens the list of your notifications.

Select the bell. The list reads "No notifications." when nothing is waiting. In the demonstration installation, the nurse account received no notification during the tests, so keep the habit of telling colleagues directly about anything urgent.

## Working without a connection

The application keeps working when the internet connection drops. What you save while offline is kept on the computer and sent to the server when the connection returns.

![A consultation saved while the connection was down](figures/offline-saved.png)

When the network is lost, the indicator {1} turns yellow and reads "Offline (your entries are saved)". The patient list and the patient files still open from the copy on the computer, and a new consultation {2} is accepted. After a consultation saved offline, the author may show as "Inconnu" until the file is reloaded online.

Some things need the server and do not work offline.

- The **Dashboard** shows "Unable to load the statistics. Try again" and an empty waiting list ("No patient waiting"). The list is not empty, it is simply not readable.
- In the patient list, the totals and the counters of the tabs show 0.

### Registering a patient offline

You can register a patient while offline, but the code does not exist yet.

![The code window while offline](figures/offline-code.png)

The window **Patient registered** says "The code is assigned at synchronization and will appear in the list." The patient shows in the list as "CODE EN ATTENTE". Select [[OK]] {2}.

The measurements form opens, but its patient code reads "Code en attente" and the message "Patient not found" appears. In the demonstration, [[Save]] did nothing, and the measurements typed there were lost. A file opened from the list in the same state refused a new consultation in the same way. Until the connection returns, write the measurements on paper. When the indicator is green again, the patient receives a code shortly afterwards. Open the file from the list and enter the measurements with [[New consultation]].

> Caution: Do not trust the measurements form that opens after an offline registration. Check in the patient file that the consultation exists before you send the patient away.

When the connection returns, the indicator goes back to "Connected" within a few seconds and your entries are sent. Check that each entry you made offline is in the file. If the server refuses an entry, it is listed under **Sync failures** in the menu, with the text you typed so that you can enter it again.

> Caution: Do not clear the browser data, uninstall the browser or switch off the computer for good while the indicator reads "Offline" and entries are waiting. Keep the computer on until it shows "Connected".

## Your profile and password

The account icon at the top right, next to the language switch, opens **My Account**.

![The profile tab](figures/account-profile.png "small")

1. Select the account icon.
2. On the **Profile** tab {1}, correct the full name, the e-mail address or the phone number {3}.
3. Select [[Save]] {4}. The message "Profile updated successfully." confirms the change.

The user name and the role cannot be changed here. To change your password, open the **Password** tab {2}, type the current password, then the new one twice, and select [[Save]]. When the change succeeds, the application signs you out and you sign in again with the new password. Choose a password of at least 8 characters.

## Common mistakes

**Creating a second file for a known patient.** Search the list first, by name and by code.

**Forgetting the Refer to doctor switch.** From a patient file the switch starts off. A patient who needs a doctor but was saved without the switch appears on no doctor's dashboard.

**Opening a new consultation to finish the visit.** The first consultation is closed and read-only. Use [[Modifier]] to add to it.

**Trusting the dashboard offline.** An empty waiting list while the indicator reads "Offline" says nothing about the patients.

**Typing measurements offline for a patient registered offline.** They are lost. Write them on paper and enter them once the patient has a code.

**Waiting for a notification of a worsening.** Tell the doctor yourself.

**Selecting Reject by accident.** The appointment is cancelled at once, without a question.

## When something goes wrong {.unnumbered}

| What you see | What it means | What to do |
|---|---|---|
| Yellow "Offline" indicator | The computer cannot reach the server | Your entries are kept. Wait for "Connected"; tell the administrator if it lasts. |
| "CODE EN ATTENTE" in the list | A patient registered offline has no code yet | Wait for "Connected". The code appears in the list. |
| "Patient not found" in the form | The patient has no code yet | Close the form, wait for the code, then enter the consultation from the file. |
| "Consultation closed: a more recent consultation exists" | A newer consultation exists for this patient | Work in the newest consultation. Ask an administrator to correct an older one. |
| "Unable to load the statistics. Try again" | The dashboard could not reach the server | Select Try again, or check the connection. |
| "No completed exam found" | No result is complete, or the computer is offline | Select Refresh when the indicator is green, or ask the laboratory. |
| A red message when saving a consultation | A required field is missing or a vital is out of range | Check the reason, the temperature (30 to 45), the weight and the height. |
| An entry listed under Sync failures | The server refused something entered offline | Open Sync failures, read the reason, enter the text again. |
| Sign-in refused several times | Wrong password, or too many attempts | Wait a minute, then try again. Ask an administrator to reset the password. |

## Glossary {.unnumbered}

Closed consultation
: A consultation that has a more recent one for the same patient. It becomes read-only, with its prescriptions.

Nursing note
: A consultation saved with the Refer to doctor switch off. No doctor is warned.

Patient code
: The code given by the server to every patient file, for example AH2-690509EX. It is written in the patient's notebook.

Refer to doctor
: The switch on the consultation form that sends the patient to the doctors' waiting list.

Shared queue
: The waiting list that every doctor sees, used when the nurse does not name a doctor.

Sync failures
: The screen that lists entries made offline that the server refused.
