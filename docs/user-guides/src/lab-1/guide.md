---
title: Requests and results
role: Laboratory technician
subtitle: Receiving a laboratory request, entering the results parameter by parameter, flagging abnormal values, validating the file, printing the result sheet, finding past results and working when the connection drops.
version: 26 October 2026
output: lab-1-requests-results
---

## Before you start {.unnumbered}

This is the first guide for the laboratory technician. It follows one request from the moment a patient arrives at the laboratory to the moment the validated result sheet is available to the doctor. It covers the dashboard, the reception of a request, the bench where results are typed, the history, the PDF result sheet, the offline mode and your profile. The second guide covers the laboratory stock and the weekly count; nothing about stock is repeated here.

The screenshots come from a demonstration installation. The patients in the figures are invented. Numbers in red discs, such as {3}, match the numbered markers drawn on the figures.

### What the technician can see and do

Your menu has two entries: **Laboratory** and **Lab stock**. This guide covers the first one. Inside **Laboratory**, four tabs sit at the top right of the page: **Reception**, **Bench**, **History** and **Sync failures**. The **Dashboard** opens first and is reached again from the menu entry.

You register laboratory requests, type and validate results, and download result sheets. You do not see invoices, prices or the cash register, you cannot edit the list of exams or their parameters (that belongs to the administrator), and you cannot register a new patient file. Doctors and nurses read the validated results on their own **Exam Results** screen. They never see a result that is still in progress.

### Interface language

The application starts in French on a new computer. The language switch at the top right, next to the bell, has two buttons: select **EN** to work in English. The choice is kept on that computer.

> Note: Some things stay in French in English mode. The exam names are French (for example "Numération Formule Sanguine" and "Glycémie à jeun"). The **Sync failures** screen, the message that follows a new request and the printed result sheet are in French. This guide quotes each label as it appears and translates it the first time.

## Signing in and the dashboard

Each member of staff has a personal account. Every result carries the name of the technician who saved it.

![The sign-in form](figures/signin.png "small")

1. Open the address of the application in the browser (Chrome or Edge).
2. Type your user name in [[Username]] {1}.
3. Type your password in [[Password]] {2}.
4. Select [[Sign in]] {3}.

After several failed attempts in a short time, the server refuses new tries for a while. Wait a minute before trying again.

The application opens on the laboratory **Dashboard**.

![The laboratory dashboard](figures/dashboard.png)

The menu entry {1} brings you back here from any tab. The connection indicator {2} reads "Connected" when the computer is in contact with the server. The tabs {3} lead to the work screens. The buttons {4} choose the period used by the counters: **Today**, **This month** (the default) or **This year**.

The four counters read as follows. **Pending (Bench)** {5} counts the examinations waiting to be entered; it does not depend on the period, and selecting it opens the bench. **Completed (Period)** counts the cases finished in the period. **Pathological** {6} counts the cases with at least one abnormal value; selecting it opens the History, already filtered on abnormal cases of the same period. **Total Activity** counts the cases created in the period.

**Latest entries (Bench)** lists the most recent patients, with their examinations and a state for each one. [[Enter]] {7} opens that case directly on the bench. **Top Analyses** ranks the most requested exams of the period. The page refreshes by itself every five minutes.

> Note: The dashboard shows an external patient as "Patient Externe", without the name. Open the bench to see the name.

## Receiving a request

A request is one patient and one or more exams. You create it at **Reception**, and it then appears on the bench. Reception always asks who prescribed the exams, so have the doctor's name before you start.

Two situations exist. The patient has a file in the centre and a doctor wrote a lab order (the first case below), or the patient has no file or no order (the second case below).

### A patient with a doctor's lab order

![Searching a patient at Reception](figures/recep-search.png)

1. Select the **Reception** tab.
2. Keep [[Existing File]] {1} selected.
3. Type at least two letters of the name in [[Search a patient]] {2}. A line appears for each patient who has an active laboratory order.
4. Select the line {3}. It shows how many exams the doctor prescribed, and the patient code.

![A request filled from the doctor's order](figures/recep-filled.png)

The patient card {1} confirms the choice and says how many exams were imported from the prescription. The exams of the order are already in the list below, each with the blue label **Prescribed**.

1. Choose the prescriber in [[Prescribed by (doctor or nurse)]] {3}. The list shows the doctors of the centre. This field is required: without it, the button stays grey.
2. If the doctor also asked for an exam that is not in the list, choose it in the exam list {4} and select [[Add]].
3. Remove an exam that must not be done with [[Remove]] {5}.
4. Check the counter on [[Create request]] {6}, which shows the number of exams, then select it.

A browser message "Dossier enregistré avec succès !" (file saved successfully) appears. Select [[OK]]. A green line under the title adds that the exams are "enregistrés localement, en attente de synchronisation", which only means that the exams were saved on the computer and are being sent to the server. The form is cleared for the next patient. The patient now appears on the bench.

[[Change]] {2} returns to the search. The prescription of a patient who already had results can still be found at Reception: in the demonstration, a patient whose two exams were finished the same morning was still offered with "2 exams prescribed". Check the date of the order with the patient before you create the request again.

### A patient without a file or without an order

At the cash desk, the secretary can invoice a laboratory exam without any link to the laboratory, and the technician does not see invoices. Ask the patient for the doctor's note or for the receipt, and register the request yourself. If you search an internal patient who has no active order, the list says "No active prescription found." In that case, use the external mode.

![A request for an external patient](figures/recep-external.png)

1. At **Reception**, select [[External Patient]] {1}.
2. Type the name in [[Full name]] {2} and the age in years in [[Age]] {3}. Both are required.
3. Choose the sex in [[Gender]] {4}. The first choice is Male.
4. Choose the prescriber {5}. If the prescriber is outside the centre, choose a member of staff of the centre who refers the patient, as the help text under the list says.
5. Choose each exam in the list and select [[Add]] {6}. An exam added twice stays once.
6. Select [[Create request]] {7}.

The yellow warning says that this patient is not saved in the main database: the request is a laboratory record only, with no link to a patient file. Doctors can still read the validated result on their **Exam Results** screen, where it carries the label External. The code of an external request starts with EXT, for example EXT-1026-2062. The code of a patient with a file starts with LAB.

> Caution: Check the spelling of the name and the age before you select [[Create request]]. No laboratory screen edits an external request afterwards, and the sex and age decide which reference range the bench shows.

## Entering results at the bench

The **Bench** tab lists every case waiting for results. The newest cases come first. A case is one patient visit, with all the exams requested together.

![The bench list](figures/bench-list.png "small")

Select [[Refresh the list]] {1} to reload the list. Each card carries the patient name, the sex and the age, a label {2} for an external patient, and a progress line {3} such as "1 of 2 exams done". Each exam is a pill {4} that shows its state with a word and an icon: **Pending** (yellow clock), **In progress** (blue flask) or **Completed** (green check). A request that was just created at Reception starts as In progress.

> Note: The list does not always update the state of a pill at once after a validation. If a finished exam still reads "In progress", select [[Refresh the list]].

### Typing the values

1. Select the pill of the exam you want to enter. The form opens on the right.
2. Read the dark header: the exam, the file code, the patient, and the progress line "0 of 14 parameters entered".
3. Type each value in the box of its parameter. Only numbers are accepted for numeric parameters. Leave a box empty when the parameter is not measured.

![The entry form of a blood count](figures/bench-form.png)

The header {1} carries the code of the file. The progress line {2} counts the parameters that have a value. The result column shows, for each parameter, the value box {3}, the unit and the reference values {4}. A dash in the reference column means that no range is registered for the parameter: the application then cannot judge the value, and you read it against your own references. In the demonstration, only two parameters of the blood count (Erythrocytes and Hémoglobine) had a range.

The exam list is the same for everyone, but the number of parameters depends on the exam: a glycaemia has two, a blood count has fourteen.

### Flags and remarks

As soon as a box holds a value, a row of five choices appears under it, and an interpretation field.

| Choice | When to use it |
|---|---|
| No flag | Nothing to signal. The application may still judge the value alone when a range exists (see below). |
| High | The value is above the normal range. |
| Low | The value is below the normal range. |
| Normal | The value is normal. The result is shown in the usual style. |
| Abnormal | The value is outside the norm and you do not say in which direction. |

Choose the flag with {5} and, if needed, type a short remark in the interpretation field {6}. The remark is printed next to the value on the sheet.

When you leave a value without a flag and without a remark, the application compares it with the range of the patient's sex, if one exists. In the demonstration, a haemoglobin of 9.8 g/dL for a woman, with no flag chosen, was saved as "Bas" (low) and counted as abnormal. Where no range exists, nothing is judged for you. Choose a flag yourself for every value you consider abnormal: only flagged values count in the Pathological counter and in the "abnormal" label of the History.

> Caution: A flag chosen by hand takes the place of the automatic judgement. When you choose High, Low or Abnormal, add a remark if you want the sheet to say more than a star. In the demonstration, a platelet count of 480000 flagged High showed on the sheet as a red value with two stars and no word, and a flag "Normal" left no text at all.

### Saving, validating and printing

![The conclusion and the three buttons](figures/bench-actions.png)

Type a general conclusion in [[Overall Exam Conclusion]] {2} if the doctor must read one. The conclusion is printed at the bottom of the sheet, and it is shown to the doctor.

- [[Save Draft]] {3} keeps what you typed and leaves the exam open. Use it when the analyser has not finished or when you must stop. The exam stays on the bench, and its parameters reappear when you open it again.
- [[Validate & Close]] {4} completes the exam. The file leaves the bench and goes to the History as Completed. Doctors and nurses can read it from that moment.
- [[VALIDATE & PRINT]] {5} does the same and also asks for the PDF of the result sheet.

Both validation buttons stay grey until at least one value is typed. The application does not ask for confirmation, and it does not require every parameter to be filled. Validate only when the values are final.

> Caution: Save Draft gives no message. The only sign is that the progress line counts the typed values when you reopen the exam. After either validation, the form closes and the right-hand panel returns to "Select a case on the left." The counter of cases under analysis goes down by one. Neither action shows a success message, so look at the counter or open the History to check.

After a save, the order of the parameters changes: the empty parameters come first, and the parameters that hold a value move to the end of the table. This also holds for the result sheet. Do not take this for a loss of data.

A completed exam is not locked. While its case is still on the bench, the green pill reopens it and [[Validate & Close]] replaces the values. Use this only to correct a mistake, and warn the doctor if the earlier values were already read.

### Several exams for one patient

A patient who came for two exams has one card with two pills. Validate each exam on its own. The case leaves the list when all its exams are done. Both exams share the same laboratory code, such as LAB-1026-2060.

## The result sheet and the PDF

The result sheet is a PDF. It is available from the History in two forms: one per exam, and one for the whole file of a patient visit. The History chapter shows where the buttons are. This chapter describes what the sheet contains.

![A page of the result sheet of a visit](figures/pdf-sheet.png)

The sheet begins with a page that carries the name and the address of the centre, the patient, the laboratory code, the date of the sample, the prescriber and the list of exams. One section follows for each exam, with a table of parameters, results, units, reference values and interpretation, and the conclusion under the table. Values flagged abnormal are printed in red, with the remark between stars.

The sheet is written in French ("Informations Patient", "Valeurs de Réf.", "Conclusion / Note"). In the demonstration, the sex of the patient was printed as "X" on the first page for a woman, and the reference values were printed as a dash even where the bench had shown a range. Check these two points on a printed sheet before you hand it to a patient, and correct by hand if needed.

> Caution: In the demonstration, the buttons [[Download PDF]], [[Full file PDF]] and [[Print]] gave no file in the browser used for this guide: nothing was downloaded and no message appeared, although the server produced the PDF correctly when it was called directly. If a button does nothing on your computer, tell the administrator. Until it works, the result can be read on screen from [[View details]].

## History and search

The **History** tab keeps every case, finished or not, with the newest first. The cases are grouped by day.

![The history list](figures/history.png)

Type at least two letters of a patient name or a code in [[Search a file]] {1}; the list updates after a short pause. The list [[Status]] {2} has three choices: All statuses, Pending and Completed (Tech). [[Refresh]] {3} clears both the search and the status. Each day has a heading {4} such as "Today, Monday, October 26, 2026". A card shows the time, the patient, the exams, the state, and the number of abnormal parameters in red. A case that is not finished shows no PDF button.

The list shows fifteen cases per page, with [[Previous]] and [[Next]] at the bottom. A card for one exam has [[View details]] and [[Download PDF]]. A card for a visit with several exams has [[Show exams]] {5} and [[Full file PDF]] {6}.

> Note: The Pending choice of the status list keeps only the exams that nobody has started. A request created today at Reception is In progress, so it does not appear under Pending, although its card carries the label "Pending" in the list. To find it, search by name.

![A visit with its exams opened](figures/history-open.png)

[[Show exams]] changes to [[Hide exams]] {1} and lists each exam with its code and its own buttons. [[View details]] {2} opens the result on screen, and [[Download PDF]] {3} downloads the sheet of this exam only.

![The result of one exam on screen](figures/result-modal.png)

The window gives the state, the file number and the batch code, the patient and the prescriber, then the table {1} of the biological results with the value, the unit, the reference values {2} and the interpretation {3}. The conclusion {4} is at the bottom. [[Print]] {5} asks for the PDF. [[Close]] closes the window.

Values flagged by you appear in red with a label next to the value: Low, High or Abnormal. The interpretation column repeats the remark. A parameter that you flagged High or Low by hand shows the label Abnormal on screen, whatever the direction. Only a value judged by the application itself keeps the label Low or High.

You can also arrive at the History from the dashboard. The Pathological counter opens a list limited to abnormal cases, with a button "Abnormal cases, This month" that you select to see all cases again.

## Working without a connection

The laboratory screens keep working when the connection drops. The indicator turns yellow and reads "Offline (your entries are saved)". What you enter is kept on the computer and sent when the connection returns.

![The bench while the connection is down](figures/offline-bench.png)

The indicator {1} is yellow. The bench {2} still lists the cases from the copy kept on the computer, and you can open a case, type values and validate it. In the demonstration, a creatinine value typed offline and validated was sent to the server once the connection returned: the History showed "1 of 2 done" for the patient.

Some points change while you are offline.

- The list can differ slightly from the server: it counted 49 cases against 50, and a case created by a colleague may be missing.
- A patient with a file may lose the age and the sex on the bench ("-, - years"). Do not rely on the reference column for such a case; open it once the connection is back.
- The dashboard and the History need the server. Offline, the dashboard shows 0 in every counter and "No case waiting to be processed", and the History says "No exam found". Neither message means that the laboratory is empty. The counters come back when the connection returns.
- The PDF buttons need the server as well.
- Reception works offline. A patient with a lab order is found from the local copy ("2 exams prescribed" appeared as online). The list of prescribers is longer than online: it shows every member of staff with the word Doctor, including colleagues who are not doctors. Choose the name written on the order.

> Caution: Keep the computer on and the browser open until the indicator reads "Connected" again. Do not clear the browser data while the indicator is yellow and entries are waiting.

When the connection returns, the indicator turns green within a few seconds and the entries are sent. If the server refuses something typed offline, it is listed under **Sync failures** in your tabs. This screen is written in French ("Échecs de synchronisation"). When everything was accepted, it says "Aucun échec de synchronisation" (no synchronisation failure).

## Notifications and your profile

The bell at the top right opens your notifications. In the demonstration, the only message was a stock notice ("Lab: delivery from ets Test"), which belongs to the second laboratory guide.

The account icon next to the language switch opens **My Account**.

![The profile tab](figures/account-profile.png "small")

1. Select the account icon.
2. On the **Profile** tab {1}, correct the full name, the e-mail address or the phone number {3}.
3. Select [[Save]] {4}.

The user name and the role cannot be changed here. To change your password, open the **Password** tab {2}, type the current password, then the new one twice, and select [[Save]]. The application signs you out and you sign in again with the new password. Choose a password of at least 8 characters.

## Common mistakes

**Creating the request without the prescriber.** The button stays grey and nothing says why. Choose the prescriber first.

**Registering an internal patient as external.** The result then stays a laboratory record and does not reach the patient file. Use the external mode only when the patient has no file or no order.

**Validating too early.** The values go to the doctor at once. Use Save Draft until the values are final.

**Trusting the automatic judgement.** Without a range, the application says nothing about a value. Flag every abnormal value yourself.

**Expecting a message.** Save Draft and the two validation buttons do not confirm anything. Watch the case counter, or open the History.

**Entering a value for the wrong exam.** The pill you selected is the exam in the header. Read the header before you type.

**Counting on the Pending filter.** A request just received is In progress. Search by name.

## When something goes wrong {.unnumbered}

| What you see | What it means | What to do |
|---|---|---|
| Yellow "Offline" indicator | The computer cannot reach the server | Keep working. Entries are kept. Wait for "Connected". |
| [[Create request]] stays grey | The patient, the prescriber or an exam is missing | Fill the three parts of the form. |
| "No active prescription found." | The patient has no active lab order | Check the patient code. If there is no order, use External Patient. |
| "No exam selected" under the exam list | The request has no exam | Choose an exam and select Add. |
| Validate buttons stay grey | No value is typed | Type at least one value. |
| A finished exam still reads In progress | The list was not refreshed | Select Refresh the list. |
| A result cannot be found in History | The case is In progress, or the search is too short | Type at least two letters, or search by the code. |
| A PDF button does nothing | The browser did not receive the file | Tell the administrator. Read the result on screen meanwhile. |
| A case under Sync failures | The server refused an entry typed offline | Open it, read the reason, enter the data again. |
| Sign-in refused several times | Wrong password, or too many attempts | Wait a minute, then try again. Ask an administrator to reset the password. |

## Glossary {.unnumbered}

Bench
: The screen that lists the cases waiting for results. The word comes from the laboratory work surface.

Case
: One patient visit with all the exams requested together. It carries one laboratory code.

External patient
: A patient with no file in the centre, entered by name, age and sex at Reception. The result stays a laboratory record.

Flag
: The mark you choose for a value: High, Low, Normal or Abnormal. A flagged value is counted as abnormal, except Normal.

Laboratory code
: The code of a case, for example LAB-1026-2060 for a patient with a file and EXT-1026-2062 for an external patient.

Prescriber
: The doctor or nurse who ordered the exams. Reception requires one.

Reference values
: The normal range of a parameter, by sex. A dash means that none is registered.

Sync failures
: The screen that lists entries made offline that the server refused.
