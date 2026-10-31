# Fiches de resultats du laboratoire : examens, familles et valeurs normales

Document versionne, SANS donnee patient. Source : les fiches fournies par le laboratoire (`docs/laboratory/`, jamais versionnees), lues seulement pour les titres, libelles, unites, ordre, methodes et valeurs normales.
La source de verite du chargement est `scripts/data/lab_catalogue.json` (script `scripts/seed_lab_catalogue.py`) ; ce document en est la lecture. La cheffe du laboratoire valide ou corrige ensuite chaque valeur depuis l'ecran du catalogue.

## Regles appliquees

- Plusieurs unites pour un meme parametre : **mg/dl** (decision du proprietaire). Les autres variantes sont dans la colonne Variantes.
- Plusieurs valeurs pour un meme parametre : la valeur imprimee le plus souvent ; a egalite, la plus recente ; les autres dans Variantes.
- Serologies : resultat POSITIF / NEGATIF (`pos_neg`) ; un taux numerique est garde seulement quand la fiche en imprime un (toxoplasmose, rubeole), avec des min-max standards (ils dependent du reactif).
- Ages des plages, en jours : nouveau-ne 0 a 28, enfant 29 a 1825 (moins de 5 ans), adulte des 1826 ; sexe M, F ou X (tous).
- `reference_ranges` ne stocke que des nombres (min et max obligatoires) : `< X` est stocke 0 - X. Le texte de norme tel qu'imprime par la fiche (`H: 4,0 - 5,5   F: 4,0 - 5,0`, `VN > 20 M/ml`, paliers, `>= 70`) est garde tel quel dans `parametres.norm_text` (colonne Norme imprimee) et, plage par plage, dans `reference_ranges.display_text` (zeros de precision conserves, ex. `4,0 - 5,5`).
- La fiche imprime TOUTES les normes definies par le laboratoire pour un parametre (les deux sexes, adulte et enfant), comme les fiches papier ; la valeur est signalee selon la norme choisie pour le patient. Sans `norm_text`, les normes sont recomposees depuis les plages (prefixes `H:`, `F:`, `Adulte:`, `Enfant:`, `Nouveau-ne:`).
- Sous-titres de la fiche (NUMERATION GLOBULAIRE, FORMULE SANGUINE, ECBU, hemostase, spermogramme) : `parametres.group_label`, affiche entre crochets dans la colonne Libelle imprime ; les parametres consecutifs de meme sous-titre sont regroupes.
- Textes fixes d'un examen (zones therapeutiques de l'INR, seuil de la CRP, NB de la typhoide, INFORMATIONS de la toxoplasmose, interpretation des Chlamydiae...) : `examens.fixed_notes`, liste ordonnee de blocs `{position, text, style}` (position `before_body`, `after_body` ou `after_conclusion` ; style `normal`, `bold` ou `italic`), 12 au plus, 1000 caracteres chacun. Ils sont modifiables dans l'ecran du catalogue (cheffe du laboratoire et administrateur) et copies dans la copie figee (version 2) de chaque resultat valide.
- Conclusion et NB : deux champs libres du laborantin (jamais de phrase automatique). En-tete et pied de page : configuration de l'etablissement (numero d'agrement, texte du pied de page, signature par defaut).
- Titres : les fautes d'origine sont corrigees (COPOROLOGIE, SYPHILYTIQUES, ALBUINE, PILORI) et signalees en note.

## Familles de mise en page

| Code | Famille | Exemples |
|---|---|---|
| `table` | tableau | NFS, PROLACTINE, CRACHAT_BAAR, HEPB_5EN1, TOXICO_UR, SPERMOGRAMME |
| `three_columns` | trois colonnes | HB, VS, GLY_JEUN, GLY_PP, HB1C, UREE, CREAT, ASAT, ALAT, IONO, IONO_EXT, CALCIUM, MAGNESIUM, PHOSPHORE, ACIDE_URIQUE, ALBUMINE, LIPIDES, BIL_TOTAL, BIL_DIRECT, PROTEINES, AMYLASE, PAL, GGT, AFP, PSA |
| `label_value` | lignes libelle : valeur | GR_ABO_RH, TP_TCA, G_TEST, BANDE_UR, ALB_SUCRE_UR, GE, TDR_PALU, HEMOPARA, MICROFIL, SKIN_SNIP, SCOTCH, TYPHOIDE, ASLO, RHUMATO, CRP, HEPB_AGHBS, HEPC, SYPHILIS, TOXO, RUBE, HPYLORI, HIV, HIV_ORAL, HIV_SYPH |
| `narrative` | compte rendu narratif | ELECTRO_HB, ECBU, CULOT_UR, PCV, PU, CULT_SIMPLE, CULT_ATB, SPH_PUS, PLAIE_ATB, OEIL_ATB, HEMOCULTURE, SPERMOCULTURE, ECBC_CRACHATS, ECBC_CRACHATS_ATB, MYCOPLASMES, COPRO, COPROCULTURE, FCU, CYTO_SANG |
| `boxed` | formulaire en cases | CHLAMYDIA |

Defaut pour un nouvel examen : `label_value`. Types de resultat : `numeric`, `text`, `choice` (liste `choices`), `pos_neg` (POSITIF / NEGATIF).

## Examens (75)

| Ordre | Code | Catalogue avant | Section | Titre imprime | Famille | Signature |
|---|---|---|---|---|---|---|
| 10 | `NFS` | oui | HEMATOLOGIE | HEMOGRAMME | table | Le Biologiste |
| 20 | `HB` | oui | LABORATOIRE D'HEMATOLOGIE | TAUX D'HEMOGLOBINE | three_columns | Le Biologiste |
| 30 | `VS` | oui | HEMATOLOGIE | VITESSE DE SEDIMENTATION (VS) | three_columns | Le Biologiste |
| 40 | `ELECTRO_HB` | oui | HEMATOLOGIE | ELECTROPHORESE DE L'HEMOGLOBINE | narrative | LE RESPONSABLE DE LABORATOIRE |
| 50 | `GR_ABO_RH` | oui | HEMATOLOGIE | GROUPAGE SANGUIN | label_value | LE RESPONSABLE DE LABORATOIRE |
| 60 | `TP_TCA` | oui | - | HEMOSTASE-COAGULATION | label_value | LE RESPONSABLE DE LABORATOIRE |
| 70 | `GLY_JEUN` | oui | BIOCHIMIE SANGUINE | GLYCEMIE A JEUN | three_columns | Le Biologiste |
| 80 | `GLY_PP` | oui | BIOCHIMIE SANGUINE | GLYCEMIE POST PRANDIALE | three_columns | Le Biologiste |
| 90 | `HB1C` | oui | BIOCHIMIE SANGUINE | HEMOGLOBINE GLYQUEE (HbA1c) | three_columns | Le Biologiste |
| 100 | `UREE` | oui | BIOCHIMIE SANGUINE | AZOTEMIE | three_columns | Le Biologiste |
| 110 | `CREAT` | oui | BIOCHIMIE SANGUINE | AZOTEMIE | three_columns | Le Biologiste |
| 120 | `ASAT` | oui | BIOCHIMIE SANGUINE | LES TRANSAMINASES | three_columns | Le Biologiste |
| 130 | `ALAT` | oui | BIOCHIMIE SANGUINE | LES TRANSAMINASES | three_columns | Le Biologiste |
| 140 | `IONO` | oui | BIOCHIMIE SANGUINE | IONOGRAMME SIMPLE | three_columns | Le Biologiste |
| 150 | `IONO_EXT` | oui | BIOCHIMIE SANGUINE | IONOGRAMME COMPLET | three_columns | Le Biologiste |
| 160 | `CALCIUM` | oui | BIOCHIMIE SANGUINE | CALCEMIE | three_columns | Le Biologiste |
| 170 | `MAGNESIUM` | oui | BIOCHIMIE SANGUINE | MAGNESEMIE | three_columns | Le Biologiste |
| 180 | `PHOSPHORE` | oui | BIOCHIMIE SANGUINE | PHOSPHORE | three_columns | Le Biologiste |
| 190 | `ACIDE_URIQUE` | oui | BIOCHIMIE SANGUINE | ACIDE URIQUE | three_columns | Le Biologiste |
| 200 | `ALBUMINE` | oui | BIOCHIMIE SANGUINE | ALBUMINEMIE | three_columns | Le Biologiste |
| 210 | `LIPIDES` | oui | BIOCHIMIE SANGUINE | PROFILE LIPIDIQUE | three_columns | Le Biologiste |
| 220 | `BIL_TOTAL` | oui | BIOCHIMIE SANGUINE | BILIRUBINE TOTALE | three_columns | Le Biologiste |
| 230 | `BIL_DIRECT` | oui | BIOCHIMIE SANGUINE | BILIRUBINE DIRECTE | three_columns | Le Biologiste |
| 240 | `PROTEINES` | oui | BIOCHIMIE SANGUINE | PROTEINES TOTALES | three_columns | Le Biologiste |
| 250 | `G_TEST` | **nouveau** | BIOCHIMIE SANGUINE | G-TEST | label_value | Le Biologiste |
| 260 | `AMYLASE` | **nouveau** | BIOCHIMIE SANGUINE | AMYLASEMIE | three_columns | Le Biologiste |
| 270 | `PAL` | **nouveau** | BIOCHIMIE SANGUINE | PHOSPHATASES ALCALINES | three_columns | Le Biologiste |
| 280 | `GGT` | **nouveau** | BIOCHIMIE SANGUINE | GAMMA GT | three_columns | Le Biologiste |
| 290 | `AFP` | **nouveau** | BIOCHIMIE SANGUINE | ALPHA FOETOPROTEINE | three_columns | Le Biologiste |
| 300 | `PSA` | **nouveau** | DOSAGE D'HORMONES | RECHERCHE DE L'ANTIGENE PROSTATIQUE SPECIFIQUE | three_columns | LE RESPONSABLE DU LABORATOIRE |
| 310 | `PROLACTINE` | **nouveau** | - | DOSAGE D'HORMONE | table | LE RESPONSABLE DU LABORATOIRE |
| 320 | `BANDE_UR` | oui | - | CHIMIE URINAIRE (URS 11) | label_value | Le Biologiste |
| 330 | `ALB_SUCRE_UR` | **nouveau** | BIOCHIMIE URINAIRE | EXAMEN: ALBUMINE/SUCRE | label_value | Le Biologiste |
| 340 | `ECBU` | oui | LABORATOIRE DE BACTERIOLOGIE | EXAMEN CYTOBACTERIOLOGIQUE DES URINES / ATB | narrative | LE RESPONSABLE DE LABORATOIRE |
| 350 | `CULOT_UR` | **nouveau** | LABORATOIRE DE BACTERIOLOGIE | EXAMEN : CULOT URINAIRE | narrative | LE RESPONSABLE DE LABORATOIRE |
| 360 | `PCV` | **nouveau** | LABORATOIRE DE BACTERIOLOGIE | EXAMEN : PRELEVEMENT CERVICO-VAGINAL (PCV + ATB) | narrative | LE RESPONSABLE DE LABORATOIRE |
| 370 | `PU` | **nouveau** | LABORATOIRE DE BACTERIOLOGIE | PRELEVEMENT URETHRAL (PU) + ANTIBIOGRAMME (ATB) | narrative | LE RESPONSABLE DE LABORATOIRE |
| 380 | `CULT_SIMPLE` | oui | LABORATOIRE DE BACTERIOLOGIE | PRELEVEMENT ET ANALYSE CYTOBACTERIOLOGIQUE | narrative | LE RESPONSABLE DE LABORATOIRE |
| 390 | `CULT_ATB` | oui | LABORATOIRE DE BACTERIOLOGIE | PRELEVEMENT ET ANALYSE CYTOBACTERIOLOGIQUE PLUS ATB | narrative | LE RESPONSABLE DE LABORATOIRE |
| 400 | `SPH_PUS` | oui | LABORATOIRE DE BACTERIOLOGIE | PUS / ATB | narrative | LE RESPONSABLE DE LABORATOIRE |
| 410 | `PLAIE_ATB` | **nouveau** | LABORATOIRE DE BACTERIOLOGIE | ECOUVILLONAGE ET CULTURE DE BLESSURE | narrative | LE RESPONSABLE DE LABORATOIRE |
| 420 | `OEIL_ATB` | **nouveau** | LABORATOIRE DE BACTERIOLOGIE | ECOULEMENT DES YEUX / ATB | narrative | LE RESPONSABLE DE LABORATOIRE |
| 430 | `HEMOCULTURE` | oui | LABORATOIRE DE BACTERIOLOGIE | HEMOCULTURE + ATB | narrative | LE RESPONSABLE DE LABORATOIRE |
| 440 | `SPERMOCULTURE` | oui | LABORATOIRE DE BACTERIOLOGIE | SPERMOCULTURE + ANTIBIOGRAMME (ATB) | narrative | LE RESPONSABLE DE LABORATOIRE |
| 450 | `CRACHAT_BAAR` | oui | LABORATOIRE DE BACTERIOLOGIE | CRACHATS - BAAR | table | LE RESPONSABLE DE LABORATOIRE |
| 455 | `ECBC_CRACHATS` | **nouveau** | LABORATOIRE DE BACTERIOLOGIE | EXAMEN CYTOBACTERIOLOGIQUE DES CRACHATS | narrative | LE RESPONSABLE DE LABORATOIRE |
| 457 | `ECBC_CRACHATS_ATB` | **nouveau** | LABORATOIRE DE BACTERIOLOGIE | EXAMEN CYTOBACTERIOLOGIQUE DES CRACHATS + ATB | narrative | LE RESPONSABLE DE LABORATOIRE |
| 460 | `MYCOPLASMES` | **nouveau** | - | RECHERCHE DE MYCOPLASMES Uro-Génitaux | narrative | LE RESPONSABLE DE LABORATOIRE |
| 470 | `COPRO` | oui | - | COPROLOGIE / KOAP (Kystes Oeufs Amibes Parasites) | narrative | LE RESPONSABLE DE LABORATOIRE |
| 480 | `COPROCULTURE` | **nouveau** | COPROCULTURE / COPROLOGIE | COPROCULTURE | narrative | LE RESPONSABLE DE LABORATOIRE |
| 490 | `GE` | oui | LABORATOIRE DE PARASITOLOGIE | GE (GOUTTE EPAISSE, Paludisme) | label_value | LE RESPONSABLE DE LABORATOIRE |
| 500 | `TDR_PALU` | **nouveau** | LABORATOIRE DE PARASITOLOGIE | TDR (Paludisme) | label_value | LE RESPONSABLE DE LABORATOIRE |
| 510 | `HEMOPARA` | oui | LABORATOIRE DE PARASITOLOGIE | EXAMEN: RECHERCHE D'HEMOPARASITES | label_value | LE RESPONSABLE DE LABORATOIRE |
| 520 | `MICROFIL` | **nouveau** | LABORATOIRE DE PARASITOLOGIE | RECHERCHE DES MICROFILAIRES SANGUICOLES | label_value | LE RESPONSABLE DE LABORATOIRE |
| 530 | `SKIN_SNIP` | oui | LABORATOIRE DE PARASITOLOGIE | SKIN SNIP TEST | label_value | LE RESPONSABLE DE LABORATOIRE |
| 540 | `SCOTCH` | oui | LABORATOIRE DE PARASITOLOGIE | TEST SCOTCH ANAL | label_value | LE RESPONSABLE DE LABORATOIRE |
| 550 | `TYPHOIDE` | oui | IMMUNO-SEROLOGIE | DIAGNOSTIC DE TYPHOIDE : ANTICORPS IgG/IgM | label_value | LE RESPONSABLE DU LABORATOIRE |
| 560 | `ASLO` | oui | IMMUNO-SEROLOGIE | A.S.L.O (Antistreptolysine O) | label_value | LE RESPONSABLE DU LABORATOIRE |
| 570 | `RHUMATO` | oui | IMMUNO-SEROLOGIE | FR (Facteur Rhumatoïde) | label_value | LE RESPONSABLE DU LABORATOIRE |
| 580 | `CRP` | oui | IMMUNO-SEROLOGIE | DOSAGE DE LA C.R.P : Protéine C-Réactive | label_value | LE RESPONSABLE DU LABORATOIRE |
| 590 | `HEPB_AGHBS` | **nouveau** | SEROLOGIE VIRALE | HEPATITE VIRALE B | label_value | LE RESPONSABLE DU LABORATOIRE |
| 600 | `HEPC` | oui | SEROLOGIE VIRALE | HEPATITE VIRALE C | label_value | LE RESPONSABLE DU LABORATOIRE |
| 610 | `HEPB_5EN1` | oui | IMMUNO-SEROLOGIE | HBV 5-IN-1 HEPATITIS B VIRUS MARKERS RAPID TEST | table | LE RESPONSABLE DU LABORATOIRE |
| 620 | `SYPHILIS` | oui | IMMUNO-SEROLOGIE | SEROLOGIES SYPHILITIQUES | label_value | LE RESPONSABLE DU LABORATOIRE |
| 630 | `TOXO` | oui | IMMUNO-SEROLOGIE | EXAMEN: TOXOPLASMOSE | label_value | LE RESPONSABLE DU LABORATOIRE |
| 640 | `RUBE` | oui | IMMUNO-SEROLOGIE | EXAMEN: RUBEOLE | label_value | LE RESPONSABLE DU LABORATOIRE |
| 650 | `HPYLORI` | oui | LABORATOIRE D'IMMUNO-SEROLOGIE | HELICOBACTER PYLORI | label_value | LE RESPONSABLE DU LABORATOIRE |
| 660 | `CHLAMYDIA` | oui | - | SERODIAGNOSTIC DES CHLAMYDIAE | boxed | LE RESPONSABLE DE LABORATOIRE |
| 670 | `HIV` | oui | - | SEROLOGIE HIV | label_value | LE RESPONSABLE DU LABORATOIRE |
| 680 | `HIV_ORAL` | oui | - | SEROLOGIE HIV | label_value | LE RESPONSABLE DU LABORATOIRE |
| 690 | `HIV_SYPH` | **nouveau** | - | SEROLOGIE HIV | label_value | LE RESPONSABLE DU LABORATOIRE |
| 700 | `TOXICO_UR` | **nouveau** | - | RECHERCHE DES DROGUES (TOXICOLOGIE URINAIRE) | table | LE RESPONSABLE DU LABORATOIRE |
| 710 | `SPERMOGRAMME` | oui | - | COMPTE RENDU D'EXAMEN D'HISTO-CYTO-PATHOLOGIE DU SPERMOGRAMME | table | LE RESPONSABLE DE LABORATOIRE |
| 720 | `FCU` | **nouveau** | LABORATOIRE D'ANATOMIE PATHOLOGIE | FROTTIS CERVICO-UTERIN (TEST DE PAPANICOLAOU) | narrative | LE RESPONSABLE DE LABORATOIRE |
| 730 | `CYTO_SANG` | **nouveau** | - | EXAMEN CYTOLOGIE DU SANG | narrative | LE RESPONSABLE DE LABORATOIRE |

### NFS - HEMOGRAMME

- Catalogue : existant ; categorie `Hematologie` ; section : HEMATOLOGIE ; famille : `table` ; signature : Le Biologiste
- Parametres desactives (gardes pour les anciens resultats) : RDW
- Textes fixes (1) :
  - avant les resultats, gras : NUMERATION FORMULE SANGUINE (N.F.S)

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | - Globules rouges (RBC) *[NUMERATION GLOBULAIRE]* | x10^6/mm3 | numeric | H: 4,0 - 5,5 F: 4,0 - 5,0 | M tous ages: 4 - 5,5; F tous ages: 4 - 5 | - |
| 2 | - Globules blancs (WBC) *[NUMERATION GLOBULAIRE]* | x10^3/mm3 | numeric | ADULTE: 5,0 - 10,0 / ENFT < 5ans: 5,0 - 15,0 | X adulte (>= 1826 j): 5 - 10; X < 5 ans (0-1825 j): 5 - 15 | - |
| 3 | - Taux d'HB (Hb) *[NUMERATION GLOBULAIRE]* | g/dl | numeric | H: 12 - 17 F: 12 - 15 / Nouveau-né: 16 - 21,5 | M tous ages: 12 - 17; F tous ages: 12 - 15; X nouveau-ne (0-28 j): 16 - 21,5 | une fiche imprime g/L (erreur), retenu g/dl |
| 4 | - Taux de Réticulocytes (RC) *[NUMERATION GLOBULAIRE]* | % | numeric | ADULT: 0,5 - 2,5 / Nouveau-né: 2 - 6 | X adulte (>= 1826 j): 0,5 - 2,5; X nouveau-ne (0-28 j): 2 - 6 | position apres l'hematocrite sur certaines fiches |
| 5 | - Hématocrite (HTC) *[NUMERATION GLOBULAIRE]* | % | numeric | H: 40 - 54 F: 36 - 52 | M tous ages: 40 - 54; F tous ages: 36 - 52 | H: 40 - 50 (fiche Hb 2021) |
| 6 | - T.C.M.H. (MCH) *[NUMERATION GLOBULAIRE]* | pg | numeric | 27 - 32 | X tous ages: 27 - 32 | - |
| 7 | - V.G.M. (MCV) *[NUMERATION GLOBULAIRE]* | fl | numeric | H: 76 - 96 F: 76 - 100 | M tous ages: 76 - 96; F tous ages: 76 - 100 | - |
| 8 | - C.C.M.H. (MCHC) *[NUMERATION GLOBULAIRE]* | g/100ml | numeric | 30 - 35 | X tous ages: 30 - 35 | - |
| 9 | - Plaquettes (Platelets) *[NUMERATION GLOBULAIRE]* | x10^3/mm3 | numeric | 150 - 400 | X tous ages: 150 - 400 | - |
| 10 | - PN Neutrophiles *[FORMULE SANGUINE (Coloration MGG)]* | % | numeric | 40 - 74 | X tous ages: 40 - 74 | - |
| 11 | V.A.M. PN Neutrophiles *[FORMULE SANGUINE (Coloration MGG)]* | /mm3 | numeric | 1800 - 7000 | X tous ages: 1800 - 7000 | valeur absolue = % x GB |
| 12 | - PN Eosinophiles *[FORMULE SANGUINE (Coloration MGG)]* | % | numeric | 1 - 4 | X tous ages: 1 - 4 | - |
| 13 | V.A.M. PN Eosinophiles *[FORMULE SANGUINE (Coloration MGG)]* | /mm3 | numeric | < 500 | X tous ages: 0 - 500 | - |
| 14 | - PN Basophiles *[FORMULE SANGUINE (Coloration MGG)]* | % | numeric | 0 - 2 | X tous ages: 0 - 2 | - |
| 15 | V.A.M. PN Basophiles *[FORMULE SANGUINE (Coloration MGG)]* | /mm3 | numeric | < 100 | X tous ages: 0 - 100 | - |
| 16 | - Lymphocytes *[FORMULE SANGUINE (Coloration MGG)]* | % | numeric | 19 - 48 | X tous ages: 19 - 48 | - |
| 17 | V.A.M. Lymphocytes *[FORMULE SANGUINE (Coloration MGG)]* | /mm3 | numeric | 1500 - 4000 | X tous ages: 1500 - 4000 | - |
| 18 | - Monocytes *[FORMULE SANGUINE (Coloration MGG)]* | % | numeric | 2 - 10 | X tous ages: 2 - 10 | - |
| 19 | V.A.M. Monocytes *[FORMULE SANGUINE (Coloration MGG)]* | /mm3 | numeric | 100 - 1000 | X tous ages: 100 - 1000 | - |

### HB - TAUX D'HEMOGLOBINE

- Catalogue : existant ; categorie `Hematologie` ; section : LABORATOIRE D'HEMATOLOGIE ; famille : `three_columns` ; signature : Le Biologiste

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | TAUX d'HEMOGLOBINE | g/dl | numeric | 12 - 17 g/dl | X tous ages: 12 - 17 | fiche 2021: Homme 12-17, Femme 12-15, Nouveau-né 16-21,5 (g/L imprime par erreur) |
| 2 | HEMATOCRITE | % | numeric | F 36 - 52% / M 40 - 54% | M tous ages: 40 - 54; F tous ages: 36 - 52 | fiche 2021: Homme 40-50% |

### VS - VITESSE DE SEDIMENTATION (VS)

- Catalogue : existant ; categorie `Hematologie` ; section : HEMATOLOGIE ; famille : `three_columns` ; signature : Le Biologiste

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | 1ER Heure | mm | numeric | < 15mm | X tous ages: 0 - 15 | - |
| 2 | 2E Heure | mm | numeric | < 20mm | X tous ages: 0 - 20 | - |

### ELECTRO_HB - ELECTROPHORESE DE L'HEMOGLOBINE

- Catalogue : existant ; categorie `Hematologie` ; section : HEMATOLOGIE ; famille : `narrative` ; signature : LE RESPONSABLE DE LABORATOIRE
- Methode : Méthode utilisée: Technique de migration des hémoglobines sur plaque d'acétate de cellulose dans la cuve électrolytique, de la cathode vers l'anode. / Appareillage : / - Générateur de tension titan plus de type helena (marque OSI Labo), Electrophoresis power supply / - Cuve électrolytique Helena (Zip-Zone chamber) / - Applicateur de type Helena / - Plaque d'acétate de cellulose.
- Parametres desactives (gardes pour les anciens resultats) : HbA (%), HbA2 (%), HbF (%)

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | HEMOGLOBINE | - | choice (AA, AS, SS, SC, AC, MONOZYGOTE AA) | - | - | texte libre sur les fiches (AA, AS, MONOZYGOTE AA) |

### GR_ABO_RH - GROUPAGE SANGUIN

- Catalogue : existant ; categorie `Hematologie` ; section : HEMATOLOGIE ; famille : `label_value` ; signature : LE RESPONSABLE DE LABORATOIRE

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | GS | - | choice (A, B, AB, O) | - | - | - |
| 2 | Rhésus | - | pos_neg | - | - | - |

### TP_TCA - HEMOSTASE-COAGULATION

- Catalogue : existant ; categorie `Hematologie` ; section : aucune ; famille : `label_value` ; signature : LE RESPONSABLE DE LABORATOIRE
- Methode : Méthode utilisée : Système de détection basé sur les capteurs électromagnétiques. / Appareillage : Coagulomètre DIAGNOSTICA ST4 STAGO à quatre canaux compacts / Réactifs : Gamme complète STAGO (STAGO TP, STAGO TCK, STAGO TT)
- Textes fixes (6) :
  - apres les resultats, gras : Zones thérapeutiques :
  - apres les resultats, normal : Prévention de thromboses veineuses : 2,0 - 3,0
  - apres les resultats, normal : Prévention de thromboses récidivantes : 2,0 - 4,0
  - apres les resultats, normal : Phlébites, embolies pulmonaire : 2,0 - 4,0
  - apres les resultats, normal : Prophylaxie artérielle, valve cardiaque : 3,0 - 4,5
  - apres les resultats, normal : Valeurs usuelles : Temps du témoin + ou - 10s

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | Temps du témoin *[TAUX DE PROTHROMBINE / TEMPS DE QUICK]* | s | numeric | - | - | - |
| 2 | Temps du Sujet *[TAUX DE PROTHROMBINE / TEMPS DE QUICK]* | s | numeric | - | - | - |
| 3 | Taux de Prothrombine | % | numeric | VN >/= 70% | X tous ages: 70 - 100 | borne haute 100 ajoutee (la fiche n'imprime que >= 70) |
| 4 | INR | - | numeric | VN 0,8 - 1,2 | X tous ages: 0,8 - 1,2 | zones therapeutiques fixes: 2,0-3,0 / 2,0-4,0 / 2,0-4,0 / 3,0-4,5 |
| 5 | Temps du témoin *[TEMPS DE CEPHALINE ACTIVEE]* | s | numeric | - | - | - |
| 6 | Temps du sujet *[TEMPS DE CEPHALINE ACTIVEE]* | s | numeric | VN 27,1 - 36,6 | X tous ages: 27,1 - 36,6 | Valeurs usuelles: témoin + ou - 10s (une fiche: +/- 5) |

### GLY_JEUN - GLYCEMIE A JEUN

- Catalogue : existant ; categorie `Biochimie` ; section : BIOCHIMIE SANGUINE ; famille : `three_columns` ; signature : Le Biologiste
- Parametres desactives (gardes pour les anciens resultats) : Glucose

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | GLYCEMIE A JEUN | g/l | numeric | 0,60 - 1,2 g/L | X tous ages: 0,6 - 1,2 | 0,60 - 1,10 g/l (liste maitresse) |

### GLY_PP - GLYCEMIE POST PRANDIALE

- Catalogue : existant ; categorie `Biochimie` ; section : BIOCHIMIE SANGUINE ; famille : `three_columns` ; signature : Le Biologiste

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | GLYCEMIE POST PRANDIALE | g/l | numeric | 0,90 - 1,4 g/L | X tous ages: 0,9 - 1,4 | - |

### HB1C - HEMOGLOBINE GLYQUEE (HbA1c)

- Catalogue : existant ; categorie `Biochimie` ; section : BIOCHIMIE SANGUINE ; famille : `three_columns` ; signature : Le Biologiste
- Methode : Méthode Utilisée : Ion - exchange High Performance Liquid Chromatography (HPLC)

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | HbA1c % | % | numeric | 4,5 - 7,0 % | X tous ages: 4,5 - 7 | ancienne grille: non diabetique 6-8%, diabetique 7,5-9%, critique 9-10%, non stabilise > 10% |
| 2 | HbA1c mmol/mol | mmol/mol | numeric | 35 - 48 mmol/mol | X tous ages: 35 - 48 | - |

### UREE - AZOTEMIE

- Catalogue : existant ; categorie `Biochimie` ; section : BIOCHIMIE SANGUINE ; famille : `three_columns` ; signature : Le Biologiste

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | UREE | mg/dl | numeric | 10 - 50 mg/dl | X tous ages: 10 - 50 | 0,10 - 0,50 g/l (liste maitresse) ; regle mg/dl |

### CREAT - AZOTEMIE

- Catalogue : existant ; categorie `Biochimie` ; section : BIOCHIMIE SANGUINE ; famille : `three_columns` ; signature : Le Biologiste

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | CREAT | mg/dl | numeric | 0,6 - 1,3 mg/dl | X tous ages: 0,6 - 1,3 | 0,9 - 1,3 mg/dl (1 fiche) ; 5 - 14 mg/l (liste maitresse) ; regle mg/dl |
| 2 | DFG (GFR) | ml/mn | numeric | 90 - 120 (+/-20ml/mn) | X tous ages: 90 - 120 | valeur calculee |
| 3 | BUN RATIO | - | numeric | 10:1 - 20:1 | X tous ages: 10 - 20 | rapport, stocke 10 - 20 |

### ASAT - LES TRANSAMINASES

- Catalogue : existant ; categorie `Biochimie` ; section : BIOCHIMIE SANGUINE ; famille : `three_columns` ; signature : Le Biologiste

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | ASAT (SGOT) | UI/l | numeric | 10 - 40 UI/l | X tous ages: 10 - 40 | 10 - 35 ; 1 - 37 UI/l |

### ALAT - LES TRANSAMINASES

- Catalogue : existant ; categorie `Biochimie` ; section : BIOCHIMIE SANGUINE ; famille : `three_columns` ; signature : Le Biologiste

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | ALAT (SGPT) | UI/l | numeric | 10 - 35 UI/l | X tous ages: 10 - 35 | 10 - 40 ; 8 - 41 ; 1 - 40 UI/l |

### IONO - IONOGRAMME SIMPLE

- Catalogue : existant ; categorie `Biochimie` ; section : BIOCHIMIE SANGUINE ; famille : `three_columns` ; signature : Le Biologiste

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | CHLORIDE | mmol/l | numeric | 98 - 110 mmol/L | X tous ages: 98 - 110 | 98 - 107 mE/l (liste maitresse) |
| 2 | SODIUM | mmol/l | numeric | 135 - 155 mmol/L | X tous ages: 135 - 155 | 135 - 148 mE/l (liste maitresse) |
| 3 | POTASSIUM | mmol/l | numeric | 3,6 - 5,5 mmol/L | X tous ages: 3,6 - 5,5 | 3,5 - 5,3 mE/l (liste maitresse) |

### IONO_EXT - IONOGRAMME COMPLET

- Catalogue : existant ; categorie `Biochimie` ; section : BIOCHIMIE SANGUINE ; famille : `three_columns` ; signature : Le Biologiste

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | CHLORIDE | mmol/l | numeric | 98 - 110 | X tous ages: 98 - 110 | unite imprimee mg/dl par erreur dans l'iono complet |
| 2 | SODIUM | mmol/l | numeric | 135 - 155 mmol/L | X tous ages: 135 - 155 | - |
| 3 | KALIEMIE | mmol/l | numeric | 3,6 - 5,5 mmol/L | X tous ages: 3,6 - 5,5 | - |
| 4 | CALCEMIE | mg/dl | numeric | 8,0 - 10,5 mg/dl | X tous ages: 8 - 10,5 | 8,5 - 10,5 mg/dl ; 80 - 105 mg/l |
| 5 | MAGNESEMIE | mg/dl | numeric | 1,9 - 2,5 mg/dl | X tous ages: 1,9 - 2,5 | 15 - 26 mg/l (liste maitresse) |
| 6 | PHOSPHORE | mg/dl | numeric | 2,5 - 5,0 mg/dl | X tous ages: 2,5 - 5 | 20 - 50 mg/l |

### CALCIUM - CALCEMIE

- Catalogue : existant ; categorie `Biochimie` ; section : BIOCHIMIE SANGUINE ; famille : `three_columns` ; signature : Le Biologiste

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | CALCEMIE | mg/dl | numeric | 8,0 - 10,5 mg/dl | X tous ages: 8 - 10,5 | 8,5 - 10,5 mg/dl ; 80 - 105 mg/l ; le catalogue avait le calcium ionise en mmol/L |

### MAGNESIUM - MAGNESEMIE

- Catalogue : existant ; categorie `Biochimie` ; section : BIOCHIMIE SANGUINE ; famille : `three_columns` ; signature : Le Biologiste

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | MAGNESEMIE | mg/dl | numeric | 1,9 - 2,5 mg/dl | X tous ages: 1,9 - 2,5 | 15 - 26 mg/l |

### PHOSPHORE - PHOSPHORE

- Catalogue : existant ; categorie `Biochimie` ; section : BIOCHIMIE SANGUINE ; famille : `three_columns` ; signature : Le Biologiste

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | PHOSPHORE | mg/dl | numeric | 2,5 - 5,0 mg/dl | X tous ages: 2,5 - 5 | 20 - 50 mg/l |

### ACIDE_URIQUE - ACIDE URIQUE

- Catalogue : existant ; categorie `Biochimie` ; section : BIOCHIMIE SANGUINE ; famille : `three_columns` ; signature : Le Biologiste

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | Acide Urique | mg/dl | numeric | 3,4 - 7,0 mg/dl | X tous ages: 3,4 - 7 | 30 - 70 mg/l ; le catalogue etait en umol/L |

### ALBUMINE - ALBUMINEMIE

- Catalogue : existant ; categorie `Biochimie` ; section : BIOCHIMIE SANGUINE ; famille : `three_columns` ; signature : Le Biologiste

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | Albuminémie | g/l | numeric | 38 - 48 g/L | X tous ages: 38 - 48 | 38,1 - 46,5 g/l (liste maitresse) ; le catalogue etait en g/dL |

### LIPIDES - PROFILE LIPIDIQUE

- Catalogue : existant ; categorie `Biochimie` ; section : BIOCHIMIE SANGUINE ; famille : `three_columns` ; signature : Le Biologiste

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | CHOLESTEROL | mg/dl | numeric | < 200 mg/dl | X tous ages: 0 - 200 | 140 - 265 mg/dl (autant de fiches) ; 135 - 250 mg/dl (2023) ; 1,4 - 2,7 g/l |
| 2 | HDL | mg/dl | numeric | 50 - 82 mg/dl | X tous ages: 50 - 82 | > 55 normal / 35 - 55 risque modere / < 35 risque eleve (autant de fiches) ; 40 - 82 ; 42 - 65 mg/dl ; 0,3 - 0,8 g/l |
| 3 | LDL | mg/dl | numeric | < 100 mg/dl | X tous ages: 0 - 100 | 100 - 150 mg/dl ; 1 - 1,9 g/l |
| 4 | TRIGLICERIDES | mg/dl | numeric | 45 - 175 mg/dl | X tous ages: 45 - 175 | 40 - 140 mg/dl ; 35 - 140 mg/dl ; 0,5 - 1,5 g/l |

### BIL_TOTAL - BILIRUBINE TOTALE

- Catalogue : existant ; categorie `Biochimie` ; section : BIOCHIMIE SANGUINE ; famille : `three_columns` ; signature : Le Biologiste

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | BILIRUBINE TOTALE | mg/dl | numeric | Up to 1,2 mg/dl | X tous ages: 0 - 1,2 | 1 - 15 mg/l (liste maitresse) |

### BIL_DIRECT - BILIRUBINE DIRECTE

- Catalogue : existant ; categorie `Biochimie` ; section : BIOCHIMIE SANGUINE ; famille : `three_columns` ; signature : Le Biologiste

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | BILIRUBINE DIRECTE | mg/dl | numeric | Up to 0,35 mg/dl | X tous ages: 0 - 0,35 | 1 - 5 mg/l (liste maitresse) |

### PROTEINES - PROTEINES TOTALES

- Catalogue : existant ; categorie `Biochimie` ; section : BIOCHIMIE SANGUINE ; famille : `three_columns` ; signature : Le Biologiste
- Note : aucune fiche : examen du catalogue seulement

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | PROTEINES TOTALES | g/dL | numeric | - | - | - |

### G_TEST - G-TEST

- Catalogue : nouvel examen (prix 0, fixe par l'admin) ; categorie `Biochimie` ; section : BIOCHIMIE SANGUINE ; famille : `label_value` ; signature : Le Biologiste

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | G-TEST | - | pos_neg | - | - | - |

### AMYLASE - AMYLASEMIE

- Catalogue : nouvel examen (prix 0, fixe par l'admin) ; categorie `Biochimie` ; section : BIOCHIMIE SANGUINE ; famille : `three_columns` ; signature : Le Biologiste

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | AMYLASEMIE | UI/ml | numeric | 7 - 80 UI/ml | X tous ages: 7 - 80 | unite imprimee UI/ml, a verifier (UI/l ?) |

### PAL - PHOSPHATASES ALCALINES

- Catalogue : nouvel examen (prix 0, fixe par l'admin) ; categorie `Biochimie` ; section : BIOCHIMIE SANGUINE ; famille : `three_columns` ; signature : Le Biologiste

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | Phosphatases alcalines | UI/l | numeric | 30 - 280 UI/l | X tous ages: 30 - 280 | - |

### GGT - GAMMA GT

- Catalogue : nouvel examen (prix 0, fixe par l'admin) ; categorie `Biochimie` ; section : BIOCHIMIE SANGUINE ; famille : `three_columns` ; signature : Le Biologiste

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | GAMA GT | UI/l | numeric | 7 - 60 UI/l | X tous ages: 7 - 60 | - |

### AFP - ALPHA FOETOPROTEINE

- Catalogue : nouvel examen (prix 0, fixe par l'admin) ; categorie `Biochimie` ; section : BIOCHIMIE SANGUINE ; famille : `three_columns` ; signature : Le Biologiste

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | ALPHA FOETOPROTEINE | UI/ml | numeric | < 10 UI/ml | X tous ages: 0 - 10 | - |

### PSA - RECHERCHE DE L'ANTIGENE PROSTATIQUE SPECIFIQUE

- Catalogue : nouvel examen (prix 0, fixe par l'admin) ; categorie `Biochimie` ; section : DOSAGE D'HORMONES ; famille : `three_columns` ; signature : LE RESPONSABLE DU LABORATOIRE
- Methode : Taux de PSA TOTALE (Electrochimiluminescence (Cobas E411 Roche))
- Textes fixes (3) :
  - apres les resultats, gras : Interprétations :
  - apres les resultats, normal : > 50 ans : 4,0 ng/ml
  - apres les resultats, normal : < 50 ans : 2,5 ng/ml

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | PSA T | ng/ml | numeric | Valeurs normal < 4ng/ml | M 0-18249 j: 0 - 2,5; M 18250- j: 0 - 4 | - |

### PROLACTINE - DOSAGE D'HORMONE

- Catalogue : nouvel examen (prix 0, fixe par l'admin) ; categorie `Biochimie` ; section : aucune ; famille : `table` ; signature : LE RESPONSABLE DU LABORATOIRE
- Note : A confirmer par la cheffe du laboratoire: phase de 2-20 et 2-15

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | PROLACTINE | ng/ml | numeric | HOMME 2 - 15 / FEMME 2 - 20 | M tous ages: 2 - 15; F tous ages: 2 - 20 | grille FEMME par phase (folliculaire, pic ovulation, luteale, post menopause) : 2 - 20 entre folliculaire et ovulation, 2 - 15 entre luteale et post menopause (position mesuree sur la fiche, phase a confirmer) |

### BANDE_UR - CHIMIE URINAIRE (URS 11)

- Catalogue : existant ; categorie `Biochimie` ; section : aucune ; famille : `label_value` ; signature : Le Biologiste
- Note : valeurs: Negatif, Normal, Positif (intensite) ; Ketones parfois en 2e position
- Parametres desactives (gardes pour les anciens resultats) : Corps cétoniques

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | Aspect | - | text | - | - | - |
| 2 | Hématies | - | text | - | - | - |
| 3 | Urobilinogène | - | text | - | - | - |
| 4 | Bilirubine | - | text | - | - | - |
| 5 | Sucres (glucose) | - | text | - | - | - |
| 6 | Protéine | - | text | - | - | - |
| 7 | Nitrites | - | text | - | - | - |
| 8 | Acide ascorbique | - | text | - | - | - |
| 9 | Leucocytes | - | text | - | - | - |
| 10 | PH | - | text | - | - | - |
| 11 | Densité | - | text | - | - | - |
| 12 | Ketones | - | text | - | - | - |

### ALB_SUCRE_UR - EXAMEN: ALBUMINE/SUCRE

- Catalogue : nouvel examen (prix 0, fixe par l'admin) ; categorie `Biochimie` ; section : BIOCHIMIE URINAIRE ; famille : `label_value` ; signature : Le Biologiste
- Note : normale imprimee NEGATIF ; titre d'origine ALBUINE/SUCRE (faute)

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | Albumine | - | text | - | - | - |
| 2 | Sucre | - | text | - | - | - |

### ECBU - EXAMEN CYTOBACTERIOLOGIQUE DES URINES / ATB

- Catalogue : existant ; categorie `Bacteriologie` ; section : LABORATOIRE DE BACTERIOLOGIE ; famille : `narrative` ; signature : LE RESPONSABLE DE LABORATOIRE
- Note : variante de titre: EXAMEN : ECBU + ATB (Examen Cytobactériologique des Urines + Antibiogramme)

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | ASPECT | - | text | - | - | - |
| 2 | PH | - | text | - | - | - |
| 3 | Hématies *[CYTOLOGIE]* | /mm3 | numeric | - | - | - |
| 4 | Leucocytes *[CYTOLOGIE]* | /mm3 | numeric | - | - | - |
| 5 | Cellules épithéliales *[CYTOLOGIE]* | /mm3 | text | - | - | - |
| 6 | CYTOLOGIE *[CYTOLOGIE]* | - | text | - | - | - |
| 7 | EXAMEN GRAM | - | text | - | - | - |
| 8 | CULTURE | - | text | - | - | - |
| 9 | BACTERIURIE QUANTITATIVE | - | text | - | - | - |
| 10 | GERME ISOLE | - | text | - | - | - |
| 11 | Sensible à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 12 | Intermédiaire à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 13 | Résistant à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |

### CULOT_UR - EXAMEN : CULOT URINAIRE

- Catalogue : nouvel examen (prix 0, fixe par l'admin) ; categorie `Bacteriologie` ; section : LABORATOIRE DE BACTERIOLOGIE ; famille : `narrative` ; signature : LE RESPONSABLE DE LABORATOIRE

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | ASPECT | - | text | - | - | - |
| 2 | PH | - | text | - | - | - |
| 3 | Hématies | /mm3 | numeric | - | - | - |
| 4 | Leucocytes | /mm3 | numeric | - | - | - |
| 5 | Cellules épithéliales | /mm3 | text | - | - | - |
| 6 | Levures | /mm3 | numeric | - | - | - |
| 7 | CYTOLOGIE | - | text | - | - | - |
| 8 | BACTERIURIE QUANTITATIVE | - | text | - | - | - |

### PCV - EXAMEN : PRELEVEMENT CERVICO-VAGINAL (PCV + ATB)

- Catalogue : nouvel examen (prix 0, fixe par l'admin) ; categorie `Bacteriologie` ; section : LABORATOIRE DE BACTERIOLOGIE ; famille : `narrative` ; signature : LE RESPONSABLE DE LABORATOIRE
- Note : variante PCV SIMPLE (sans ATB)

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | ASPECT *[EXAMEN MACROSCOPIQUE]* | - | text | - | - | - |
| 2 | EXAMEN MICROSCOPIQUE *[EXAMEN MICROSCOPIQUE]* | - | text | - | - | - |
| 3 | EXAMEN GRAM *[EXAMEN GRAM]* | - | text | - | - | - |
| 4 | Flore *[EXAMEN GRAM]* | - | text | - | - | - |
| 5 | CULTURE *[CULTURE]* | - | text | - | - | - |
| 6 | GERME(S) ISOLE(S) *[CULTURE]* | - | text | - | - | - |
| 7 | Sensible à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 8 | Intermédiaire à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 9 | Résistant à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 10 | ANTIFONGIGRAMME (AFG) | - | text | - | - | - |

### PU - PRELEVEMENT URETHRAL (PU) + ANTIBIOGRAMME (ATB)

- Catalogue : nouvel examen (prix 0, fixe par l'admin) ; categorie `Bacteriologie` ; section : LABORATOIRE DE BACTERIOLOGIE ; famille : `narrative` ; signature : LE RESPONSABLE DE LABORATOIRE

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | ASPECT *[EXAMEN MACROSCOPIQUE]* | - | text | - | - | - |
| 2 | EXAMEN MICROSCOPIQUE *[EXAMEN MICROSCOPIQUE]* | - | text | - | - | - |
| 3 | EXAMEN GRAM *[EXAMEN GRAM]* | - | text | - | - | - |
| 4 | CULTURE *[CULTURE]* | - | text | - | - | - |
| 5 | GERME(S) ISOLE(S) *[CULTURE]* | - | text | - | - | - |
| 6 | Sensible à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 7 | Intermédiaire à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 8 | Résistant à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 9 | ANTIFONGIGRAMME (AFG) | - | text | - | - | - |

### CULT_SIMPLE - PRELEVEMENT ET ANALYSE CYTOBACTERIOLOGIQUE

- Catalogue : existant ; categorie `Bacteriologie` ; section : LABORATOIRE DE BACTERIOLOGIE ; famille : `narrative` ; signature : LE RESPONSABLE DE LABORATOIRE

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | ASPECT *[EXAMEN MACROSCOPIQUE]* | - | text | - | - | - |
| 2 | EXAMEN MICROSCOPIQUE | - | text | - | - | - |
| 3 | EXAMEN GRAM | - | text | - | - | - |
| 4 | CULTURE | - | text | - | - | - |
| 5 | GERME(S) ISOLE(S) | - | text | - | - | - |

### CULT_ATB - PRELEVEMENT ET ANALYSE CYTOBACTERIOLOGIQUE PLUS ATB

- Catalogue : existant ; categorie `Bacteriologie` ; section : LABORATOIRE DE BACTERIOLOGIE ; famille : `narrative` ; signature : LE RESPONSABLE DE LABORATOIRE
- Note : aussi CULTURE DES CRACHATS

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | ASPECT *[EXAMEN MACROSCOPIQUE]* | - | text | - | - | - |
| 2 | EXAMEN MICROSCOPIQUE *[EXAMEN MICROSCOPIQUE]* | - | text | - | - | - |
| 3 | Hématies *[CYTOLOGIE]* | /mm3 | text | - | - | - |
| 4 | Leucocytes *[CYTOLOGIE]* | /mm3 | text | - | - | - |
| 5 | Cellules épithéliales *[CYTOLOGIE]* | /mm3 | text | - | - | - |
| 6 | EXAMEN GRAM *[EXAMEN GRAM]* | - | text | - | - | - |
| 7 | CULTURE *[CULTURE]* | - | text | - | - | - |
| 8 | GERME(S) ISOLE(S) *[CULTURE]* | - | text | - | - | - |
| 9 | Sensible à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 10 | Intermédiaire à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 11 | Résistant à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 12 | ANTIFONGIGRAMME (AFG) | - | text | - | - | - |

### SPH_PUS - PUS / ATB

- Catalogue : existant ; categorie `Bacteriologie` ; section : LABORATOIRE DE BACTERIOLOGIE ; famille : `narrative` ; signature : LE RESPONSABLE DE LABORATOIRE

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | ASPECT *[EXAMEN MACROSCOPIQUE]* | - | text | - | - | - |
| 2 | EXAMEN MICROSCOPIQUE *[EXAMEN MICROSCOPIQUE]* | - | text | - | - | - |
| 3 | Pyocytes *[CYTOLOGIE]* | /mm3 | text | - | - | - |
| 4 | Leucocytes *[CYTOLOGIE]* | /mm3 | text | - | - | - |
| 5 | EXAMEN GRAM *[EXAMEN GRAM]* | - | text | - | - | - |
| 6 | CULTURE *[CULTURE]* | - | text | - | - | - |
| 7 | GERME(S) ISOLE(S) *[CULTURE]* | - | text | - | - | - |
| 8 | Sensible à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 9 | Intermédiaire à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 10 | Résistant à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 11 | ANTIFONGIGRAMME (AFG) | - | text | - | - | - |

### PLAIE_ATB - ECOUVILLONAGE ET CULTURE DE BLESSURE

- Catalogue : nouvel examen (prix 0, fixe par l'admin) ; categorie `Bacteriologie` ; section : LABORATOIRE DE BACTERIOLOGIE ; famille : `narrative` ; signature : LE RESPONSABLE DE LABORATOIRE

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | ASPECT *[EXAMEN MACROSCOPIQUE]* | - | text | - | - | - |
| 2 | EXAMEN MICROSCOPIQUE *[EXAMEN MICROSCOPIQUE]* | - | text | - | - | - |
| 3 | EXAMEN GRAM *[EXAMEN GRAM]* | - | text | - | - | - |
| 4 | CULTURE *[CULTURE]* | - | text | - | - | - |
| 5 | GERME(S) ISOLE(S) *[CULTURE]* | - | text | - | - | - |
| 6 | Sensible à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 7 | Intermédiaire à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 8 | Résistant à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 9 | ANTIFONGIGRAMME (AFG) | - | text | - | - | - |

### OEIL_ATB - ECOULEMENT DES YEUX / ATB

- Catalogue : nouvel examen (prix 0, fixe par l'admin) ; categorie `Bacteriologie` ; section : LABORATOIRE DE BACTERIOLOGIE ; famille : `narrative` ; signature : LE RESPONSABLE DE LABORATOIRE

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | ASPECT *[EXAMEN MACROSCOPIQUE]* | - | text | - | - | - |
| 2 | EXAMEN MICROSCOPIQUE *[EXAMEN MICROSCOPIQUE]* | - | text | - | - | - |
| 3 | EXAMEN GRAM *[EXAMEN GRAM]* | - | text | - | - | - |
| 4 | CULTURE *[CULTURE]* | - | text | - | - | - |
| 5 | GERME(S) ISOLE(S) *[CULTURE]* | - | text | - | - | - |
| 6 | Sensible à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 7 | Intermédiaire à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 8 | Résistant à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 9 | ANTIFONGIGRAMME (AFG) | - | text | - | - | - |

### HEMOCULTURE - HEMOCULTURE + ATB

- Catalogue : existant ; categorie `Bacteriologie` ; section : LABORATOIRE DE BACTERIOLOGIE ; famille : `narrative` ; signature : LE RESPONSABLE DE LABORATOIRE
- Note : ligne fixe: Sang veineux prélevé sur bouillon castaneda.

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | PRELEVEMENT | - | text | - | - | - |
| 2 | RESULTATS | - | choice (RESULTATS PRELIMINAIRES, RESULTATS DEFINITIFS) | - | - | - |
| 3 | ASPECT *[EXAMEN MACROSCOPIQUE]* | - | text | - | - | - |
| 4 | EXAMEN MICROSCOPIQUE *[EXAMEN MICROSCOPIQUE]* | - | text | - | - | - |
| 5 | EXAMEN GRAM *[EXAMEN GRAM]* | - | text | - | - | - |
| 6 | CULTURE *[CULTURE]* | - | text | - | - | - |
| 7 | GERME(S) ISOLE(S) *[CULTURE]* | - | text | - | - | - |
| 8 | Sensible à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 9 | Intermédiaire à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 10 | Résistant à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 11 | ANTIFONGIGRAMME (AFG) | - | text | - | - | - |

### SPERMOCULTURE - SPERMOCULTURE + ANTIBIOGRAMME (ATB)

- Catalogue : existant ; categorie `Bacteriologie` ; section : LABORATOIRE DE BACTERIOLOGIE ; famille : `narrative` ; signature : LE RESPONSABLE DE LABORATOIRE

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | ASPECT *[EXAMEN MACROSCOPIQUE]* | - | text | - | - | - |
| 2 | EXAMEN MICROSCOPIQUE *[EXAMEN MICROSCOPIQUE]* | - | text | - | - | - |
| 3 | EXAMEN GRAM *[EXAMEN GRAM]* | - | text | - | - | - |
| 4 | CULTURE *[CULTURE]* | - | text | - | - | - |
| 5 | GERME(S) ISOLE(S) *[CULTURE]* | - | text | - | - | - |
| 6 | Sensible à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 7 | Intermédiaire à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 8 | Résistant à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 9 | ANTIFONGIGRAMME (AFG) | - | text | - | - | - |

### CRACHAT_BAAR - CRACHATS - BAAR

- Catalogue : existant ; categorie `Bacteriologie` ; section : LABORATOIRE DE BACTERIOLOGIE ; famille : `table` ; signature : LE RESPONSABLE DE LABORATOIRE
- Methode : METHODE UTILISEE : COLORATION ZIEHL NEELSEN

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | DATE *[ECHANTILLON 1]* | - | text | - | - | - |
| 2 | ASPECT *[ECHANTILLON 1]* | - | text | - | - | - |
| 3 | RESULTATS *[ECHANTILLON 1]* | - | choice (NEG, 1 - 9, +, ++, +++) | - | - | - |
| 4 | DATE *[ECHANTILLON 2]* | - | text | - | - | - |
| 5 | ASPECT *[ECHANTILLON 2]* | - | text | - | - | - |
| 6 | RESULTATS *[ECHANTILLON 2]* | - | choice (NEG, 1 - 9, +, ++, +++) | - | - | - |
| 7 | DATE *[ECHANTILLON 3]* | - | text | - | - | - |
| 8 | ASPECT *[ECHANTILLON 3]* | - | text | - | - | - |
| 9 | RESULTATS *[ECHANTILLON 3]* | - | choice (NEG, 1 - 9, +, ++, +++) | - | - | - |

### MYCOPLASMES - RECHERCHE DE MYCOPLASMES Uro-Génitaux

- Catalogue : nouvel examen (prix 0, fixe par l'admin) ; categorie `Bacteriologie` ; section : aucune ; famille : `narrative` ; signature : LE RESPONSABLE DE LABORATOIRE
- Methode : METHODE UTILISEE: Mycoplasma IST BIOMERIEUX (Diagnostic, Culture, Identification, Numération et antibiogramme des Mycoplasmes urogénitaux)

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | Recherche de Mycoplasmes | - | pos_neg | NEGATIF | - | - |
| 2 | Ureaplasma urealyticum | - | pos_neg | NEGATIF | - | - |
| 3 | Mycoplasma hominis | - | pos_neg | NEGATIF | - | - |
| 4 | Sensible à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 5 | Intermédiaire à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 6 | Résistant à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |

### COPRO - COPROLOGIE / KOAP (Kystes Oeufs Amibes Parasites)

- Catalogue : existant ; categorie `Parasitologie` ; section : aucune ; famille : `narrative` ; signature : LE RESPONSABLE DE LABORATOIRE
- Note : titre d'origine COPOROLOGIE (faute) ; bloc patient: Examen prescrit Par

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | Consistance *[EXAMEN MACROSCOPIQUE]* | - | text | - | - | - |
| 2 | EXAMEN MICROSCOPIQUE DIRECT | - | text | - | - | - |

### COPROCULTURE - COPROCULTURE

- Catalogue : nouvel examen (prix 0, fixe par l'admin) ; categorie `Bacteriologie` ; section : COPROCULTURE / COPROLOGIE ; famille : `narrative` ; signature : LE RESPONSABLE DE LABORATOIRE

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | - Consistance *[EXAMEN MACROSCOPIQUE]* | - | text | - | - | - |
| 2 | - Couleur *[EXAMEN MACROSCOPIQUE]* | - | text | - | - | - |
| 3 | EXAMEN MICROSCOPIQUE DIRECT | - | text | - | - | - |
| 4 | Bacilles gram positif *[GRAM]* | % | numeric | - | - | - |
| 5 | Bacilles gram négatif *[GRAM]* | % | numeric | - | - | - |
| 6 | Cocci gram positif *[GRAM]* | % | numeric | - | - | - |
| 7 | CULTURE | - | text | - | - | - |
| 8 | GERMES ISOLES | - | text | - | - | - |
| 9 | Sensible à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 10 | Intermédiaire à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 11 | Résistant à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 12 | ANTIFONGIGRAMME | - | text | - | - | - |

### GE - GE (GOUTTE EPAISSE, Paludisme)

- Catalogue : existant ; categorie `Parasitologie` ; section : LABORATOIRE DE PARASITOLOGIE ; famille : `label_value` ; signature : LE RESPONSABLE DE LABORATOIRE
- Note : variantes de titre: GE : (Paludisme) ; EXAMEN: RECHERCHE D'HEMOPARASITES (GE)

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | RESULTAT | - | text | - | - | - |
| 2 | Parasitemie | - | text | - | - | - |

### TDR_PALU - TDR (Paludisme)

- Catalogue : nouvel examen (prix 0, fixe par l'admin) ; categorie `Parasitologie` ; section : LABORATOIRE DE PARASITOLOGIE ; famille : `label_value` ; signature : LE RESPONSABLE DE LABORATOIRE

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | RESULTAT | - | pos_neg | NEGATIF | - | - |
| 2 | Parasitemie | - | text | - | - | - |

### HEMOPARA - EXAMEN: RECHERCHE D'HEMOPARASITES

- Catalogue : existant ; categorie `Parasitologie` ; section : LABORATOIRE DE PARASITOLOGIE ; famille : `label_value` ; signature : LE RESPONSABLE DE LABORATOIRE

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | RESULTAT | - | text | - | - | - |
| 2 | Parasitemie | - | text | - | - | - |

### MICROFIL - RECHERCHE DES MICROFILAIRES SANGUICOLES

- Catalogue : nouvel examen (prix 0, fixe par l'admin) ; categorie `Parasitologie` ; section : LABORATOIRE DE PARASITOLOGIE ; famille : `label_value` ; signature : LE RESPONSABLE DE LABORATOIRE

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | RESULTAT | - | text | - | - | - |
| 2 | PARASITEMIE | - | text | - | - | - |

### SKIN_SNIP - SKIN SNIP TEST

- Catalogue : existant ; categorie `Parasitologie` ; section : LABORATOIRE DE PARASITOLOGIE ; famille : `label_value` ; signature : LE RESPONSABLE DE LABORATOIRE
- Note : parasitemie en microfilaires /cm2, /ul ou 1-3/ch

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | RESULTAT | - | text | - | - | - |
| 2 | PARASITEMIE | - | text | - | - | - |

### SCOTCH - TEST SCOTCH ANAL

- Catalogue : existant ; categorie `Parasitologie` ; section : LABORATOIRE DE PARASITOLOGIE ; famille : `label_value` ; signature : LE RESPONSABLE DE LABORATOIRE
- Note : aucune fiche : examen du catalogue seulement

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | Oeufs d'oxyures | - | text | - | - | - |

### TYPHOIDE - DIAGNOSTIC DE TYPHOIDE : ANTICORPS IgG/IgM

- Catalogue : existant ; categorie `Serologie` ; section : IMMUNO-SEROLOGIE ; famille : `label_value` ; signature : LE RESPONSABLE DU LABORATOIRE
- Methode : METHODE UTILISEE : Technique rapide par immunochromatographie.
- Note : NB toujours imprime: Une réaction positive peut correspondre à une infection récente ou ancienne.
- Textes fixes (1) :
  - apres la conclusion, normal : NB : Une réaction positive peut correspondre à une infection récente ou ancienne.

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | Anticorps Typhoide IgG | - | pos_neg | NEGATIF | - | - |
| 2 | Anticorps Typhoide IgM | - | pos_neg | NEGATIF | - | - |

### ASLO - A.S.L.O (Antistreptolysine O)

- Catalogue : existant ; categorie `Serologie` ; section : IMMUNO-SEROLOGIE ; famille : `label_value` ; signature : LE RESPONSABLE DU LABORATOIRE

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | Valeur du malade | UI/ml | numeric | (V.N. <= 200 UI/mL) | X tous ages: 0 - 200 | unites imprimees mg/l, IU/ml, UI/L |

### RHUMATO - FR (Facteur Rhumatoïde)

- Catalogue : existant ; categorie `Serologie` ; section : IMMUNO-SEROLOGIE ; famille : `label_value` ; signature : LE RESPONSABLE DU LABORATOIRE

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | Valeur du malade | UI/ml | numeric | (V.N. <= 8 IU/l) ou (< 08 IU/ml) | X tous ages: 0 - 8 | - |

### CRP - DOSAGE DE LA C.R.P : Protéine C-Réactive

- Catalogue : existant ; categorie `Serologie` ; section : IMMUNO-SEROLOGIE ; famille : `label_value` ; signature : LE RESPONSABLE DU LABORATOIRE
- Methode : TECHNIQUE UTILISEE : Agglutination sur latex
- Textes fixes (3) :
  - avant les resultats, normal : C.R.P (Protéine C - Réactive)
  - avant les resultats, normal : Valeur Seuil = 6 mg/l
  - avant les resultats, normal : Valeur à 20 mg/l si syndrome inflammatoire

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | Valeur du malade | mg/l | numeric | (V.N. <= 6 mg/L) | X tous ages: 0 - 6 | resultat parfois rendu < 6 |

### HEPB_AGHBS - HEPATITE VIRALE B

- Catalogue : nouvel examen (prix 0, fixe par l'admin) ; categorie `Serologie` ; section : SEROLOGIE VIRALE ; famille : `label_value` ; signature : LE RESPONSABLE DU LABORATOIRE

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | AgHBs | - | pos_neg | NEGATIF | - | - |

### HEPC - HEPATITE VIRALE C

- Catalogue : existant ; categorie `Serologie` ; section : SEROLOGIE VIRALE ; famille : `label_value` ; signature : LE RESPONSABLE DU LABORATOIRE

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | AcHCV | - | pos_neg | NEGATIF | - | - |

### HEPB_5EN1 - HBV 5-IN-1 HEPATITIS B VIRUS MARKERS RAPID TEST

- Catalogue : existant ; categorie `Serologie` ; section : IMMUNO-SEROLOGIE ; famille : `table` ; signature : LE RESPONSABLE DU LABORATOIRE
- Methode : TECHNIQUE UTILISEE: Double Antibody Sandwich and Gold Immuno-chromatography Assay
- Parametres desactives (gardes pour les anciens resultats) : Anti-HBc IgM

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | HBs Ag | - | pos_neg | NEGATIF | - | - |
| 2 | HBs Ab | - | pos_neg | NEGATIF | - | - |
| 3 | HBe Ag | - | pos_neg | NEGATIF | - | - |
| 4 | HBe Ab | - | pos_neg | NEGATIF | - | - |
| 5 | HBc Ab | - | pos_neg | NEGATIF | - | - |

### SYPHILIS - SEROLOGIES SYPHILITIQUES

- Catalogue : existant ; categorie `Serologie` ; section : IMMUNO-SEROLOGIE ; famille : `label_value` ; signature : LE RESPONSABLE DU LABORATOIRE
- Note : titre d'origine SYPHILYTIQUES (faute)

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | T.P.H.A | - | pos_neg | NEGATIF | - | - |
| 2 | V.D.R.L | - | pos_neg | NEGATIF | - | - |

### TOXO - EXAMEN: TOXOPLASMOSE

- Catalogue : existant ; categorie `Serologie` ; section : IMMUNO-SEROLOGIE ; famille : `label_value` ; signature : LE RESPONSABLE DU LABORATOIRE
- Methode : Méthode utilisée : Immunocomb
- Note : texte fixe INFORMATIONS (3 paragraphes) apres la signature
- Textes fixes (4) :
  - apres la conclusion, gras : INFORMATIONS
  - apres la conclusion, normal : La Toxoplasmose est une maladie systémique causée par le protozoaire Toxoplasma gondii. Ce parasite est capable d'infecter l'homme, plus fréquemment dans les zones tropicales. Les moyens de transmission sont soit par voie orale, soit par voie congénitale, soit par contact avec le sang contaminé. Les manifestations cliniques sont généralement une simple lymphadénopathie et une fièvre auto-limitante. Par contre, l'infection chez le malade immunodéprimé ou chez le fœtus peut avoir les conséquences sévères telles les encéphalites, les pneumonies, les myocardies. L'infection peut se propager vers le système nerveux central. Elle peut provoquer des fausses couches, des accouchements prématurés chez les femmes enceintes.
  - apres la conclusion, normal : La détermination quantitative des anticorps IgG peut fournir une détermination du statut immunitaire chez la femme enceinte et le nouveau-né.
  - apres la conclusion, normal : Du fait de la persistance des anticorps anti-toxo IgG tout au long de la vie, seule une augmentation du titre au delà de quatre fois supérieure au titre précédant peut permettre de diagnostiquer une infection active.

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | IgG | - | pos_neg | NEGATIF | - | - |
| 2 | IgM | - | pos_neg | NEGATIF | - | - |
| 3 | Taux d'anticorps IgG | UI/ml | numeric | < 10 UI/ml | X tous ages: 0 - 10 | norme standard du reactif (min-max serologie) |
| 4 | Taux d'anticorps IgM | UI/ml | numeric | < 10 UI/ml | X tous ages: 0 - 10 | - |

### RUBE - EXAMEN: RUBEOLE

- Catalogue : existant ; categorie `Serologie` ; section : IMMUNO-SEROLOGIE ; famille : `label_value` ; signature : LE RESPONSABLE DU LABORATOIRE
- Methode : Méthode utilisée : Immunocomb

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | IgG | - | pos_neg | NEGATIF | - | - |
| 2 | IgM | - | pos_neg | NEGATIF | - | - |
| 3 | Taux d'anticorps IgG | UI/ml | numeric | Vn : <= 10 UI/ml | X tous ages: 0 - 10 | - |
| 4 | Taux d'anticorps IgM | UI/ml | numeric | Vn : <= 10 UI/ml | X tous ages: 0 - 10 | - |

### HPYLORI - HELICOBACTER PYLORI

- Catalogue : existant ; categorie `Serologie` ; section : LABORATOIRE D'IMMUNO-SEROLOGIE ; famille : `label_value` ; signature : LE RESPONSABLE DU LABORATOIRE
- Methode : METHODE UTILISEE: IMMUNOCHROMATOGRAPHIE (BIOLINE)
- Note : rendu REACTION POSITIVE / NEGATIVE

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | HELICOBACTER PYLORI | - | pos_neg | NEGATIF | - | - |

### CHLAMYDIA - SERODIAGNOSTIC DES CHLAMYDIAE

- Catalogue : existant ; categorie `Serologie` ; section : aucune ; famille : `boxed` ; signature : LE RESPONSABLE DE LABORATOIRE
- Methode : METHODE UTILISEE: IMMUNOPEROXIDASE INDIRECTE (IPAzyme)
- Note : titre de page RESULTAT D'ANALYSE DE BIOLOGIE CLINIQUE ; interpretation fixe: < 8 negative, 8-63 faiblement positive, 64-255 moyennement positive
- Textes fixes (5) :
  - apres les resultats, gras : INTERPRETATION
  - apres les resultats, normal : Titre < 8 ou immuno peroxydase négative : Sérologie négative.
  - apres les resultats, normal : Titre compris entre 8 et 63 ou immuno peroxydase+ : Sérologie faiblement positif.
  - apres les resultats, normal : Titre compris entre 64 et 255 ou immuno peroxydase++ : sérologie moyennement positive. Cette valeur peut correspondre à une infection active ou une cicatrice sérologique. Faire pratiquer un 2ème examen deux à quatre semaines plus tard.
  - apres les resultats, normal : N.B : Les anticorps ainsi décelés peuvent persister longtemps, même après la guérison.

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | N° de l'examen antérieur | - | text | - | - | - |
| 2 | Titre en IgG | - | text | - | - | - |
| 3 | Titre en IgM | - | text | - | - | - |
| 4 | Titre en IgA | - | text | - | - | - |
| 5 | Validation | - | choice (Sérologie négative, Sérologie faiblement positive, Sérologie moyennement positive) | - | - | - |

### HIV - SEROLOGIE HIV

- Catalogue : existant ; categorie `Serologie` ; section : aucune ; famille : `label_value` ; signature : LE RESPONSABLE DU LABORATOIRE
- Methode : Dépistage des anticorps anti-HIV1 et anti-HIV2 dans le sérum ou le plasma
- Note : kits: HIV1 et 2 (Abbott Determine), First Response CARD TEST Version 2.0

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | Renseignements cliniques *[EXAMEN CLINIQUE]* | - | text | - | - | - |
| 2 | Manifestations cliniques *[EXAMEN CLINIQUE]* | - | text | - | - | - |
| 3 | METHODES UTILISEES | - | text | - | - | - |
| 4 | Validation | - | choice (NEGATIF, POSITIF, NON REACTIVE, REACTIVE) | - | - | - |

### HIV_ORAL - SEROLOGIE HIV

- Catalogue : existant ; categorie `Biochimie` ; section : aucune ; famille : `label_value` ; signature : LE RESPONSABLE DU LABORATOIRE
- Methode : Dépistage des anticorps anti-HIV1 et anti-HIV2 dans le fluide oral (OraQuick)

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | Renseignements cliniques *[EXAMEN CLINIQUE]* | - | text | - | - | - |
| 2 | Manifestations cliniques *[EXAMEN CLINIQUE]* | - | text | - | - | - |
| 3 | METHODES UTILISEES | - | text | - | - | - |
| 4 | Validation | - | choice (NEGATIF, POSITIF, NON REACTIVE, REACTIVE) | - | - | - |

### HIV_SYPH - SEROLOGIE HIV

- Catalogue : nouvel examen (prix 0, fixe par l'admin) ; categorie `Serologie` ; section : aucune ; famille : `label_value` ; signature : LE RESPONSABLE DU LABORATOIRE
- Methode : METHODES UTILISEES : HIV1 et 2 / SYPHILIS Combo Card Test (FIRST RESPONSE)

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | Renseignements cliniques *[EXAMEN CLINIQUE]* | - | text | - | - | - |
| 2 | Manifestations cliniques *[EXAMEN CLINIQUE]* | - | text | - | - | - |
| 3 | HIV 1 et 2 | - | choice (NEGATIF, POSITIF, NON REACTIVE, REACTIVE) | - | - | - |
| 4 | SYPHILIS | - | choice (NEGATIF, POSITIF, NON REACTIVE, REACTIVE) | - | - | - |

### TOXICO_UR - RECHERCHE DES DROGUES (TOXICOLOGIE URINAIRE)

- Catalogue : nouvel examen (prix 0, fixe par l'admin) ; categorie `Toxicologie` ; section : aucune ; famille : `table` ; signature : LE RESPONSABLE DU LABORATOIRE
- Methode : Technique utilisée : Immunochromatographie
- Note : TRAMADOL present sur une seule fiche

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | CANNABIS (THC) | - | pos_neg | Négatif | - | - |
| 2 | TRAMADOL (TRA) | - | pos_neg | Négatif | - | - |
| 3 | BENZODIAZEPINE (BZO) | - | pos_neg | Négatif | - | - |
| 4 | METAPHETAMINE (MAMP) | - | pos_neg | Négatif | - | - |
| 5 | AMPHETAMINE (AMP) | - | pos_neg | Négatif | - | - |
| 6 | COCAINE (COC) | - | pos_neg | Négatif | - | - |
| 7 | BARBITURATE (BAR) | - | pos_neg | Négatif | - | - |
| 8 | COTININE (COT) | - | pos_neg | Négatif | - | - |
| 9 | KETAMINE (KET) | - | pos_neg | Négatif | - | - |
| 10 | OPIATES/ MORPHINE/ HEROINE (MOP) | - | pos_neg | Négatif | - | - |
| 11 | OPIATES II (OPI 2000) | - | pos_neg | Négatif | - | - |
| 12 | PHENCYCLIDINE (PCP) | - | pos_neg | Négatif | - | - |
| 13 | TRICYCLIC ANTIDEPRESSANTS (TCA) | - | pos_neg | Négatif | - | - |

### SPERMOGRAMME - COMPTE RENDU D'EXAMEN D'HISTO-CYTO-PATHOLOGIE DU SPERMOGRAMME

- Catalogue : existant ; categorie `Bacteriologie` ; section : aucune ; famille : `table` ; signature : LE RESPONSABLE DE LABORATOIRE

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | Motif *[RENSEIGNEMENTS GENERAUX]* | - | text | - | - | - |
| 2 | Nombre d'enfants *[RENSEIGNEMENTS GENERAUX]* | - | numeric | - | - | - |
| 3 | Délai d'abstinence *[RENSEIGNEMENTS GENERAUX]* | - | text | - | - | - |
| 4 | Temps entre éjaculation et début Analyses *[RENSEIGNEMENTS GENERAUX]* | - | text | - | - | - |
| 5 | -Viscosité *[II) ETUDE PHYSICO - CHIMIQUE]* | - | text | - | - | - |
| 6 | -Couleur *[II) ETUDE PHYSICO - CHIMIQUE]* | - | text | - | - | - |
| 7 | -Liquéfaction *[II) ETUDE PHYSICO - CHIMIQUE]* | - | text | - | - | - |
| 8 | -Volume *[II) ETUDE PHYSICO - CHIMIQUE]* | ml | numeric | - | - | - |
| 9 | -PH *[II) ETUDE PHYSICO - CHIMIQUE]* | - | numeric | - | - | - |
| 10 | Immobiles 0H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 11 | Immobiles 1H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 12 | Immobiles 2H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 13 | Immobiles 6H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 14 | Immobiles 12H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 15 | Immobiles 24H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 16 | Rapide progressive 0H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 17 | Rapide progressive 1H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 18 | Rapide progressive 2H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 19 | Rapide progressive 6H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 20 | Rapide progressive 12H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 21 | Rapide progressive 24H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 22 | Lente progressive 0H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 23 | Lente progressive 1H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 24 | Lente progressive 2H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 25 | Lente progressive 6H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 26 | Lente progressive 12H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 27 | Lente progressive 24H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 28 | Mobilité non progressive 0H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 29 | Mobilité non progressive 1H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 30 | Mobilité non progressive 2H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 31 | Mobilité non progressive 6H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 32 | Mobilité non progressive 12H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 33 | Mobilité non progressive 24H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 34 | Total mobiles 0H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 35 | Total mobiles 1H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 36 | Total mobiles 2H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 37 | Total mobiles 6H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 38 | Total mobiles 12H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 39 | Total mobiles 24H *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 40 | Vitalité vivants *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 41 | morts *[III) ETUDE DYNAMIQUE]* | % | numeric | - | - | - |
| 42 | Agglutination *[III) ETUDE DYNAMIQUE]* | - | text | - | - | - |
| 43 | Formes normales *[IV) CYTOLOGIE - Morphologie des spermatozoïdes]* | % | numeric | - | - | - |
| 44 | Anomalie tête *[IV) CYTOLOGIE - Morphologie des spermatozoïdes]* | % | numeric | - | - | - |
| 45 | Macrocéphales *[IV) CYTOLOGIE - Morphologie des spermatozoïdes]* | % | numeric | - | - | - |
| 46 | Sans tête *[IV) CYTOLOGIE - Morphologie des spermatozoïdes]* | % | numeric | - | - | - |
| 47 | Têtes effilées *[IV) CYTOLOGIE - Morphologie des spermatozoïdes]* | % | numeric | - | - | - |
| 48 | Têtes dupliquées *[IV) CYTOLOGIE - Morphologie des spermatozoïdes]* | % | numeric | - | - | - |
| 49 | Microcéphales *[IV) CYTOLOGIE - Morphologie des spermatozoïdes]* | % | numeric | - | - | - |
| 50 | Anomalie pièce intermédiaire *[IV) CYTOLOGIE - Morphologie des spermatozoïdes]* | % | numeric | - | - | - |
| 51 | Anomalie flagelle *[IV) CYTOLOGIE - Morphologie des spermatozoïdes]* | % | numeric | - | - | - |
| 52 | Double flagelle *[IV) CYTOLOGIE - Morphologie des spermatozoïdes]* | % | numeric | - | - | - |
| 53 | Sans flagelle *[IV) CYTOLOGIE - Morphologie des spermatozoïdes]* | % | numeric | - | - | - |
| 54 | Cellules rondes *[IV) CYTOLOGIE]* | - | text | - | - | - |
| 55 | Leucocytes *[IV) CYTOLOGIE]* | - | text | - | - | - |
| 56 | Hématies *[IV) CYTOLOGIE]* | - | text | - | - | - |
| 57 | Polynucléaires *[IV) CYTOLOGIE]* | - | text | - | - | - |
| 58 | Cellules épithéliales *[IV) CYTOLOGIE]* | - | text | - | - | - |
| 59 | Lymphocytes *[IV) CYTOLOGIE]* | - | text | - | - | - |
| 60 | V) CONCENTRATION | million/ml | numeric | VN > 20 M/ml | - | borne basse seule : non stockee en plage (valeur_max obligatoire) |
| 61 | VI) INDICE DE FERTILITE SPERMATIQUE | - | numeric | VN : 1 - 7 | X tous ages: 1 - 7 | - |

### FCU - FROTTIS CERVICO-UTERIN (TEST DE PAPANICOLAOU)

- Catalogue : nouvel examen (prix 0, fixe par l'admin) ; categorie `Anatomie pathologique` ; section : LABORATOIRE D'ANATOMIE PATHOLOGIE ; famille : `narrative` ; signature : LE RESPONSABLE DE LABORATOIRE

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | Echantillon | - | text | - | - | - |
| 2 | Résultats microscopiques | - | text | - | - | - |

### CYTO_SANG - EXAMEN CYTOLOGIE DU SANG

- Catalogue : nouvel examen (prix 0, fixe par l'admin) ; categorie `Hematologie` ; section : aucune ; famille : `narrative` ; signature : LE RESPONSABLE DE LABORATOIRE
- Methode : COLORATION: May Grunwald Giemsa (MGG)

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | CYTOLOGIE | - | text | - | - | - |
| 2 | Hématies | /mm3 | numeric | - | - | - |
| 3 | Leucocytes | /mm3 | numeric | - | - | - |
| 4 | GRAM | - | text | - | - | - |

### ECBC_CRACHATS - EXAMEN CYTOBACTERIOLOGIQUE DES CRACHATS

- Catalogue : nouvel examen (prix 0, fixe par l'admin) ; categorie `Bacteriologie` ; section : LABORATOIRE DE BACTERIOLOGIE ; famille : `narrative` ; signature : LE RESPONSABLE DE LABORATOIRE
- Note : titre d'origine EXAMEN CYTOBACTERIOLOGQUE (faute) ; NB libre = champ NB de la fiche ; lignes Culture, ATB et antifongigramme seulement dans la version + ATB

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | Aspect | - | text | - | - | - |
| 2 | Cytologie | - | text | - | - | - |
| 3 | Gram | - | text | - | - | - |

### ECBC_CRACHATS_ATB - EXAMEN CYTOBACTERIOLOGIQUE DES CRACHATS + ATB

- Catalogue : nouvel examen (prix 0, fixe par l'admin) ; categorie `Bacteriologie` ; section : LABORATOIRE DE BACTERIOLOGIE ; famille : `narrative` ; signature : LE RESPONSABLE DE LABORATOIRE
- Note : titre d'origine EXAMEN CYTOBACTERIOLOGQUE (faute) ; NB libre = champ NB de la fiche ; lignes Culture, ATB et antifongigramme seulement dans la version + ATB

| # | Libelle imprime | Unite | Type | Norme imprimee | Plages chargees | Variantes |
|---|---|---|---|---|---|---|
| 1 | Aspect | - | text | - | - | - |
| 2 | Cytologie | - | text | - | - | - |
| 3 | Gram | - | text | - | - | - |
| 4 | Culture sur milieux usuels | - | text | - | - | - |
| 5 | Sensible à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 6 | Intermédiaire à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 7 | Résistant à *[ANTIBIOGRAMME (ATB)]* | - | text | - | - | - |
| 8 | ANTIFONGIGRAMME (AFG) | - | text | - | - | - |

## Examens de test du catalogue

`DEMO_TEST` et `VERIFX` ne sont pas dans les fiches : non touches par le chargement, exclus de l'export de production.
