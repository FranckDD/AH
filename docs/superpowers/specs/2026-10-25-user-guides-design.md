# Per-role user guides (PDF, English): design

Date: 2026-10-25. Status: approved by the user in discussion. This is the "documentation d'utilisation par role" item of the pre-deployment backlog. It is written after the interface refonte and before chantier 8 (deployment).

## Purpose

Give every member of staff a short, professional guide for their own role, so the system stays usable when the people who built it are no longer around. The guides also serve the promoter as evidence of how each business action is performed in the application.

## Decisions (from the user)

- **Format**: PDF. English only. Product name in the header: **Glostone-Care**.
- **Style**: professional documentation. No AI-sounding writing: no em dashes or en dashes, no emojis or decorative symbols, no filler openers, no stacks of three adjectives, no "seamless/robust/leverage/streamline/ensure/utilize" vocabulary, no colon-subtitle patterns on every heading, no "Let us" or "In conclusion". Vary sentence structure and length. Prefer short paragraphs and numbered steps for procedures. Numbered callout markers on screenshots are the only decoration.
- **Volume**: one or two PDFs per role depending on how long or tedious the role's processes are (proposal below).
- **Images**: real screenshots taken by driving the real application in a browser, annotated with numbered markers and short instructions (for example "Select Save (3)"). The application is used in its English interface. Server messages that are still French (some report labels) stay as they are.
- **Environment**: the existing development environment and database (no copy). Demo accounts and demo data are created there. All data in it is test data. At the cleaning before go-live, some tables must NOT be wiped (the registered exams and their parameters, and others): the assistant will list them at that time.
- **Browser**: the assistant opens the browser itself and performs every action.

## Proposed PDFs (about 20)

| Role | PDFs |
|---|---|
| Administrator | 1. Getting started, accounts, catalogue and prices. 2. Oversight: approvals, cash register set-up, settings, logs |
| Promoter | 1. Reports and daily control. 2. Approvals and follow-up |
| Secretary | 1. Patients, appointments, invoicing. 2. Cash register, withdrawals, daily closure |
| Doctor | 1. Consultations and prescriptions. 2. Hospitalisation and follow-up |
| Nurse and head nurse | 1. Triage and care. 2. Shifts and hospitalisation |
| Laboratory technician | 1. Requests and results. 2. Laboratory stock and weekly count |
| Psychologist | 1 |
| Spiritual counsellor | 1 |
| Toxicology manager | 1. Admission, phases, evaluations. 2. Discharge, readmission, exports |
| Assistant | 1 (production lots and receipts) |
| Stock controller | 1. Receipt control and incidents. 2. Physical count |
| Production manager | 1. Inputs and purchases. 2. Batches, declared outputs, shipping |

The exact content of each guide follows what the role can really do in the application: read the router role lists and the menus, then walk every real process with the demo account of that role.

## Structure of a guide

Cover (name, role, version date, product), a one-page "before you start" (sign-in, language, offline behaviour in plain words, what the role can and cannot see), then one chapter per process. Each chapter opens with a short paragraph on what the process is for, gives the numbered steps with figures, and closes with the points where mistakes usually happen. A short glossary and a "when something goes wrong" page close the guide. Figures carry captions ("Figure 3. The invoice form") and numbered markers that the steps refer to.

## Tooling

A small, reusable kit under `docs/user-guides/tools/`: a Playwright helper (sign in as a role, switch the interface to English, open a route, find an element by selector or visible text, draw numbered markers and arrows around elements, save the annotated PNG), and a builder that turns a guide source (Markdown with a few conventions) into a PDF with WeasyPrint (cover, header "Glostone-Care", footer with page numbers, table of contents, figure captions, consistent typography, A4). Sources and images live next to the PDFs: `docs/user-guides/src/<role>/`, output in `docs/user-guides/en/`.

## Non-goals

No French version now. No video. No guide for the technician or for deployment (that is the operating manual of chantier 8). No redesign of any screen to make a screenshot easier.

## Quality checks

Every claim in a guide is exercised in the real application at least once. Each guide is re-read for the forbidden style traits (script check for em dashes, en dashes, emojis, middle dots, arrows, ellipsis characters) and for consistency with the interface labels. A pilot guide is produced first and approved by the user before the others.
