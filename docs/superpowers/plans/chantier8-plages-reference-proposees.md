# Plages de reference du laboratoire : PROJET a valider

> **BROUILLON. NE PAS IMPORTER.** Le fichier `.superpowers/sdd/2026-10-28-chantier8-deploiement/reference_ranges_draft.csv` n'est a importer par personne tant que le responsable du laboratoire (biologiste, technicien superieur ou medecin) n'a pas signe la liste de controle en bas de page. Ces valeurs ne sont pas une verite medicale validee.

## Resume (15 lignes)

1. Il n'existe pas de « reglementation officielle » unique fixant des valeurs normales chiffrees : elles dependent de la methode, de l'automate, du reactif et de la population.
2. Ce document propose un projet sourcé pour les 69 parametres numeriques du catalogue (hors examens de test 5163 et 5188).
3. 46 parametres recoivent au moins une plage proposee, 18 sont « selon le kit » (serologies, TCA), 4 restent sans source (RDW, HbA, HbF, TP %), 1 n'a pas besoin de plage (goutte epaisse).
4. Les unites de la base sont conservees ; chaque conversion est indiquee.
5. Biochimie : plages harmonisees AACB (Australie/Nouvelle-Zelande, 2016) et liste NSW Health Pathology (2019), completees par Labcorp.
6. Glycemie et HbA1c : seuils ADA ; lipides : NCEP ATP III ; spermogramme : manuel OMS 2021.
7. Hemoglobine : seuils d'anemie OMS 2024 comme limite basse.
8. Leucocytes, neutrophiles, plaquettes : limite basse de l'etude locale de Yaounde (Oloume 2019), limite haute occidentale (neutropenie ethnique benigne).
9. Lymphocytes, monocytes, eosinophiles, basophiles, erythrocytes : etude de Yaounde.
10. VGM/TCMH/CCMH : valeurs occidentales, pour ne pas masquer les microcytoses (carence martiale, thalassemie).
11. Les enfants ne sont couverts que pour l'hemoglobine (seuils OMS, limite haute a fixer par le labo).
12. Anomalie a corriger : la ligne existante id=5 (Erythrocytes, M, 12-18 ans, 1,2-1,8 x10^12/L) est fausse.
13. Les lignes existantes Hb 18-65 ans laissent les plus de 65 ans sans plage : proposer 18-120.
14. Le texte de la base est bien en UTF-8 (verifie en hexadecimal) ; les « ? » venaient seulement de la console Windows.
15. Chaque examen doit etre coche et signe par le responsable du laboratoire avant import.

## Methodologie et avertissements

- **Statut** : projet de travail. Le responsable du laboratoire valide, modifie ou rejette chaque ligne. Idealement, il verifie les plages fournies dans la notice des reactifs et de l'automate utilises, qui priment sur ce document.
- **Dependance a la methode** : enzymes (ALAT/ASAT avec ou sans phosphate de pyridoxal), creatinine (Jaffe ou enzymatique), albumine (vert ou pourpre de bromocresol), HbA2 (CLHP ou electrophorese capillaire), TCA (reactif) : les valeurs changent selon la technique.
- **Unites** : on garde l'unite deja en base. Facteurs utilises : creatinine µmol/L / 88,4 = mg/dL ; bilirubine µmol/L / 17,1 = mg/dL ; acide urique mg/dL x 59,48 = µmol/L ; phosphate mmol/L x 3,097 = mg/dL ; uree mmol/L x 6,006 = mg/dL d'uree (et pas de BUN : BUN x 2,14 = uree) ; glucose mmol/L x 0,1802 = g/L ; g/L / 10 = g/dL ; 10^9/L x 1000 = /mm^3.
- **Regles du moteur** (`utils/lab_reference.py`, `select_range`) :
  - `sexe` vaut `M`, `F` ou `X`. `X` = valable pour les deux sexes. Le moteur prend d'abord la plage du sexe du patient, sinon la plage `X`. Un patient de sexe inconnu ne recoit que les plages `X`.
  - L'age est un entier en **annees** (age 0 = moins d'un an : impossible de distinguer nouveau-ne et nourrisson). Bornes incluses (`age_min <= age <= age_max`, `valeur_min <= valeur <= valeur_max`).
  - Les quatre colonnes sont NOT NULL. Une limite ouverte se code par une sentinelle : 0 en bas, 999 ou 9999 en haut (indique en note).
  - Si deux lignes se chevauchent pour le meme sexe et le meme age, la premiere trouvee gagne, sans ordre garanti : **eviter tout chevauchement**.
- **Choix local ou occidental** : la population de Yaounde a en moyenne des leucocytes, neutrophiles et plaquettes plus bas (trait genetique). Utiliser des limites basses occidentales signalerait a tort beaucoup de sujets sains. En revanche, l'echantillon local inclut probablement des carences martiales et des porteurs d'hemoglobinopathie (Hb basse a 11 g/dL chez l'homme) : pour l'hemoglobine et les indices erythrocytaires, on garde les seuils OMS ou occidentaux pour ne pas « normaliser » une anemie.

## Tableaux par examen

Colonnes : sexe, age (ans), min, max, unite, source. Le CSV donne le niveau de confiance et la note complete.

### NFS (Numeration Formule Sanguine)
| Parametre | Sexe | Age | Min | Max | Unite | Source |
|---|---|---|---|---|---|---|
| Erythrocytes | M | 18-120 | 4,00 | 5,90 | 10^12/L | S8 |
| Erythrocytes | F | 18-120 | 3,40 | 5,30 | 10^12/L | S8 |
| Hemoglobine | M | 18-120 | 13,0 | 17,0 | g/dL | S1 (min), S5 (max) |
| Hemoglobine | F | 18-120 | 12,0 | 15,5 | g/dL | S1 (min), max = ligne existante non sourcee |
| Hematocrite | M | 18-120 | 40 | 54 | % | S5 (alternative locale 34,6-47,6) |
| Hematocrite | F | 18-120 | 29,7 | 42,0 | % | S8 (faible) |
| VGM | X | 12-120 | 80 | 100 | fL | S5 (alternative locale 70-97) |
| TCMH | X | 12-120 | 26,5 | 33,0 | pg | S5 |
| CCMH | X | 12-120 | 31,0 | 36,0 | g/100ml | S5 (310-360 g/L) |
| RDW | - | - | - | - | % | aucune source trouvee |
| Leucocytes | M | 18-120 | 2600 | 11000 | /mm^3 | S8 (min), S5 (max) |
| Leucocytes | F | 18-120 | 2800 | 11000 | /mm^3 | S8, S5 |
| Plaquettes | M | 18-120 | 133000 | 450000 | /mm^3 | S8, S5 |
| Plaquettes | F | 18-120 | 143000 | 450000 | /mm^3 | S8, S5 |
| Neutrophiles | M / F | 18-120 | 0,92 / 1,01 | 7,0 | 10^9/L | S8, S5 |
| Lymphocytes | M / F | 18-120 | 1,03 / 1,06 | 3,13 / 2,90 | 10^9/L | S8 (alt. S5 : 1,5-4,0) |
| Monocytes | M / F | 18-120 | 0,11 / 0,14 | 0,54 / 0,65 | 10^9/L | S8 (alt. S5 : 0,1-0,8) |
| Eosinophiles | M / F | 18-120 | 0,05 / 0,12 | 0,98 / 0,42 | 10^9/L | S8 (alt. S5 : 0,04-0,44) |
| Basophiles | M / F | 18-120 | 0,03 / 0,03 | 0,22 / 0,29 | 10^9/L | S8 (alt. S5 : 0-0,2) |

Desaccord principal : leucocytes. Etude locale 2,6-6,8 x10^9/L contre NSW 3,5-11,0. Recommandation : limite basse locale, limite haute occidentale (une hyperleucocytose reste pathologique). A defaut, le labo peut prendre l'etude locale entiere.

### HB (Taux d'hemoglobine simple)
| Sexe | Age | Min | Max | Source |
|---|---|---|---|---|
| M | 15-120 | 13,0 | 17,0 | S1, S5 |
| F | 15-120 | 12,0 | 15,5 | S1 |
| X | 1 | 10,5 | a fixer | S1 (6-23 mois) |
| X | 2-4 | 11,0 | a fixer | S1 (24-59 mois) |
| X | 5-11 | 11,5 | a fixer | S1 |
| X | 12-14 | 12,0 | a fixer | S1 |

Femme enceinte : seuil OMS 11,0 g/dL, non gerable par le moteur (pas de notion de grossesse). Moins d'un an : pas de plage (age 0 trop large).

### Biochimie
| Examen | Parametre | Sexe | Age | Min | Max | Unite | Source (conversion) |
|---|---|---|---|---|---|---|---|
| ACIDE_URIQUE | Acide urique | M | 18-120 | 200 | 420 | µmol/L | S5 (0,20-0,42 mmol/L) |
| ACIDE_URIQUE | Acide urique | F | 18-50 | 155 | 369 | µmol/L | S6 (2,6-6,2 mg/dL) |
| ALAT | ALAT | M / F | 18-120 | 5 | 40 / 35 | U/L | S4 |
| ASAT | ASAT | M / F | 18-120 | 5 | 35 / 30 | U/L | S4 |
| ALBUMINE | Albumine | X | 1-120 | 3,3 | 4,8 | g/dL | S5 (33-48 g/L) |
| PROTEINES | Proteines totales | X | 18-120 | 6,0 | 8,0 | g/dL | S4 (60-80 g/L) |
| BIL_TOTAL | Bilirubine totale | X | 1-120 | 0,1 | 1,2 | mg/dL | S4 (1-20 µmol/L) |
| BIL_DIRECT | Bilirubine directe | X | 1-120 | 0,0 | 0,4 | mg/dL | S6 (alt. S5 <10 µmol/L = 0,58) |
| CREAT | Creatinine | M | 18-120 | 0,68 | 1,24 | mg/dL | S4 (60-110 µmol/L) |
| CREAT | Creatinine | F | 18-120 | 0,51 | 1,02 | mg/dL | S4 (45-90 µmol/L) |
| UREE | Uree sanguine | F | 18-49 | 18 | 42 | mg/dL | S5 (3,0-7,0 mmol/L) ; homme : aucune source extraite |
| CALCIUM | Calcium ionise | X | 18-120 | 1,15 | 1,30 | mmol/L | S5 |
| IONO_EXT | Calcium (total) | X | 18-120 | 2,10 | 2,60 | mmol/L | S4 |
| IONO_EXT / MAGNESIUM | Magnesium | X | 18-120 | 0,70 | 1,10 | mmol/L | S4 |
| PHOSPHORE | Phosphore | X | 20-120 | 2,3 | 4,6 | mg/dL | S4 (0,75-1,50 mmol/L) |
| IONO | Sodium | X | 18-120 | 135 | 145 | mmol/L | S4 |
| IONO | Potassium | X | 18-120 | 3,5 | 5,2 | mmol/L | S4 |
| IONO | Chlorures | X | 18-120 | 95 | 110 | mmol/L | S4 |
| CRP | CRP | X | 0-120 | 0 | 5 | mg/L | S7 (alt. S5 <3) |

Creatinine : la plage AACB n'est harmonisee que jusqu'a 60 ans ; interpreter la fonction renale par le DFG estime (KDIGO), pas par la seule creatinine. Uree : verifier si l'automate rend l'uree ou le BUN (facteur 2,14).

### Glycemie, HbA1c, lipides
| Examen | Parametre | Sexe | Age | Min | Max | Unite | Source |
|---|---|---|---|---|---|---|---|
| GLY_JEUN | Glucose / Glucose a jeun | X | 18-120 | 0,63 | 0,99 | g/L | S2 (max), S5 (min) |
| GLY_PP | Glucose postprandial | X | 18-120 | 0,63 | 1,39 | g/L | S2 (seuil HGPO 2 h, faible) |
| HB1C | HbA1c | X | 18-120 | 0 | 5,6 | % | S2 |
| LIPIDES | Cholesterol total | X | 18-120 | 0 | 199 | mg/dL | S3 |
| LIPIDES | HDL | X | 18-120 | 40 | 999 | mg/dL | S3 |
| LIPIDES | LDL | X | 18-120 | 0 | 129 | mg/dL | S3 |
| LIPIDES | Triglycerides | X | 18-120 | 0 | 149 | mg/dL | S3 |

Ce sont des seuils de decision clinique, pas des intervalles de reference statistiques. GLY_JEUN contient deux parametres en doublon (Glucose et Glucose a jeun).

### Autres
| Examen | Parametre | Sexe | Age | Min | Max | Unite | Source |
|---|---|---|---|---|---|---|---|
| ELECTRO_HB | HbA2 | X | 1-120 | 1,5 | 3,5 | % | S10 (faible) ; >= 4 % evoque une beta-thalassemie (S11) |
| ELECTRO_HB | HbA, HbF | - | - | - | - | % | aucune source trouvee |
| SPERMOGRAMME | Numeration | M | 18-120 | 16 | 9999 | 10^6/mL | S9 |
| SPERMOGRAMME | Mobilite totale | M | 18-120 | 42 | 100 | % | S9 |
| SPERMOGRAMME | Morphologie normale | M | 18-120 | 4 | 100 | % | S9 |
| TP_TCA | INR | X | 17-120 | 0,8 | 1,1 | - | S5 (hors anticoagulant) |
| TP_TCA | TP (%) | - | - | - | - | % | aucune source trouvee (pratique courante 70-100 %, non verifiee) |
| VS | VS a 1 h | M | 17-50 | 0 | 10 | mm | S5 ; femmes et plus de 50 ans : aucune source extraite (formule de Miller a verifier) |

## Parametres sans plage necessaire

Bandelette urinaire (pH, proteines, glucose, corps cetoniques, sang, bilirubine, cetones, densite, urobilinogene, nitrites, leucocytes : saisis en texte), Coprologie, Crachats BAAR, Cultures (germe, antibiogramme, Gram), ECBU, Hemoculture, Spermoculture, Prelevement gorge/pus, Groupe ABO et Rhesus, Hemoparasites, VIH, VIH oral, HBsAg, Test Scotch, Skin snip, et **Goutte epaisse (parasites/µL)** : numerique mais tout parasite est un resultat positif ; une plage n'a pas de sens.

## Parametres « selon le kit » (prendre la valeur dans la notice du reactif)

| Examen | Parametre | Note (valeur couramment publiee, a titre indicatif seulement) |
|---|---|---|
| ASLO | Titre ASLO | souvent 200 UI/mL chez l'adulte, aucune source verifiee |
| CHLAMYDIA | IgM, IgG | seuil du kit |
| HEPB_5EN1 | Anti-HBs | >= 10 UI/L = protection post-vaccinale (S12) |
| HEPB_5EN1 | Anti-HBc IgM, IgG | seuil du kit (index ou ratio) |
| HEPC | Anti-VHC | seuil du kit (ratio S/CO) |
| HPYLORI | Anti-H. pylori | seuil du kit |
| RHUMATO | Titre FR | seuil du kit |
| RUBE | IgM, IgG | IgG >= 10 UI/mL souvent retenue comme immunite (S13) |
| SYPHILIS | TPHA, VDRL titres | toute reactivite est positive ; titre suivi dans le temps |
| TOXO | IgM, IgG | seuil du kit |
| TYPHOIDE | IgM, IgG | seuil du kit |
| TP_TCA | TCA (s) | depend du reactif ; rendre avec le temps du temoin (NSW : 25-37 s, a titre indicatif) |

## Corrections des lignes existantes

- id=5 : Erythrocytes, M, 12-18 ans, 1,2-1,8 x10^12/L : **valeur erronee**, a supprimer ou corriger.
- id=1 et id=2 : Hemoglobine 18-65 ans : etendre a 120 ans.
- id=310 : parametre 979 (Hemoglobin, M 18-120, 13-17) : appartient vraisemblablement a un examen de test ; a verifier.

## Bibliographie

- **S1** OMS. *Guideline on haemoglobin cutoffs to define anaemia in individuals and populations*. Geneve, 2024. https://www.who.int/publications-detail-redirect/9789240088542
- **S2** American Diabetes Association. *Standards of Care in Diabetes, section 2 : Diagnosis and Classification of Diabetes* (editions 2025-2026 ; seuils inchanges). Diabetes Care. Lire l'edition en vigueur sur https://diabetesjournals.org/care
- **S3** NHLBI. *Third Report of the NCEP Expert Panel (Adult Treatment Panel III)*. NIH, 2002. https://www.nhlbi.nih.gov/files/docs/resources/heart/atp3full.pdf
- **S4** Koerbin G, Tate JR (AACB). *Harmonising Adult Reference Intervals in Australia and New Zealand: the Continuing Story*. Clin Biochem Rev 2016;37(3):121-129. https://pmc.ncbi.nlm.nih.gov/articles/PMC5111244
- **S5** NSW Health Pathology. *Reference Ranges Adult*, 2019. https://www.seslhd.health.nsw.gov.au/sites/default/files/2019-04/NSWHP%20Reference%20Ranges%20Adult%202019.pdf
- **S6** Labcorp, catalogue des tests : Albumine 001081 https://www.labcorp.com/tests/001081/albumin ; Acide urique 001057 https://www.labcorp.com/tests/001057/uric-acid ; Bilirubine directe https://www.labcorp.com//test-menu/21101/bilirubin-direct
- **S7** PathWest (Western Australia). *iSTAT Age and Gender Reference Ranges POCT*, 2022. https://www.pathwest.health.wa.gov.au/~/media/PathWest/Documents/Health-Professionals/iSTAT-Age-and-Gender-Reference-Ranges-POCT-2022-07.pdf
- **S8** Oloume ME et al. *Haematological values in a healthy adult population in Yaounde, Cameroon*. Afr J Lab Med 2019;8(1):852. doi:10.4102/ajlm.v8i1.852. https://pmc.ncbi.nlm.nih.gov/articles/PMC6852616 (n = 294, 18-55 ans, donneurs de sang)
- **S9** OMS. *WHO laboratory manual for the examination and processing of human semen*, 6e edition, 2021. https://www.who.int/publications/i/item/9789240030787
- **S10** Etude kenyane sur les intervalles locaux d'HbA2, Egyptian Journal of Internal Medicine 2022. https://ejim.springeropen.com/articles/10.1186/s43162-022-00187-9
- **S11** Revue sur le diagnostic de la beta-thalassemie et les seuils d'HbA2 (PMC10542033). https://pmc.ncbi.nlm.nih.gov/articles/PMC10542033 ; voir aussi BSH 2023 *Significant haemoglobinopathies*, https://cms-bsh-u9.b-s-h.org.uk/media/dkrlxdg2/2023-04-19-significant-haemoglobinopathies-a-guideline-for-screening-and-diagnosis.pdf
- **S12** OMS. *Hepatitis B vaccines: WHO position paper*, Weekly Epidemiological Record 2017;92(27):369-392 (anti-HBs >= 10 mUI/mL).
- **S13** Skendzel LP. *Rubella immunity: defining the level of protective antibody*. Am J Clin Pathol 1996;106:170-174.

Autres etudes camerounaises reperees, non utilisees : Fondoh et al., Bamenda, Afr J Lab Med 2020 (https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7756783/) ; Bamenda 2021 (https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7932772/). Les references francaises (SFBC, Eurofins Biomnis) n'ont pas pu etre consultees en ligne : a ajouter par le labo s'il les possede.

## Liste de controle du responsable du laboratoire

Pour chaque examen : plages comparees a la notice du reactif et de l'automate, unites verifiees, regles sexe/age verifiees.

| Examen | Valide tel quel | Modifie | Rejete | Nom, date, signature |
|---|---|---|---|---|
| NFS | [ ] | [ ] | [ ] | |
| HB | [ ] | [ ] | [ ] | |
| ACIDE_URIQUE | [ ] | [ ] | [ ] | |
| ALAT / ASAT | [ ] | [ ] | [ ] | |
| ALBUMINE / PROTEINES | [ ] | [ ] | [ ] | |
| BIL_TOTAL / BIL_DIRECT | [ ] | [ ] | [ ] | |
| CREAT / UREE | [ ] | [ ] | [ ] | |
| CALCIUM / IONO / IONO_EXT / MAGNESIUM / PHOSPHORE | [ ] | [ ] | [ ] | |
| CRP | [ ] | [ ] | [ ] | |
| GLY_JEUN / GLY_PP / HB1C | [ ] | [ ] | [ ] | |
| LIPIDES | [ ] | [ ] | [ ] | |
| ELECTRO_HB | [ ] | [ ] | [ ] | |
| SPERMOGRAMME | [ ] | [ ] | [ ] | |
| TP_TCA | [ ] | [ ] | [ ] | |
| VS | [ ] | [ ] | [ ] | |
| Serologies (seuils des notices saisis) | [ ] | [ ] | [ ] | |
| Corrections des lignes id 1, 2, 5, 310 | [ ] | [ ] | [ ] | |
