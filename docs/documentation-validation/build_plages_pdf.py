# -*- coding: utf-8 -*-
"""Genere plages-reference-a-valider-laboratoire.pdf a partir du CSV de brouillon.
Usage : python build_plages_pdf.py   (depuis n'importe quel dossier)"""
import csv, html
from collections import OrderedDict
from pathlib import Path
from weasyprint import HTML

ROOT = Path(__file__).resolve().parents[2]
CSV = ROOT / ".superpowers/sdd/2026-10-28-chantier8-deploiement/reference_ranges_draft.csv"
OUT = Path(__file__).resolve().parent / "plages-reference-a-valider-laboratoire.pdf"
e = html.escape
BOX = '<span class="box"></span>'
CONF = {"high": "Élevée", "medium": "Moyenne", "low": "Faible"}

TITRES = {
 "ACIDE_URIQUE": "Acide urique", "ALAT": "ALAT", "ASAT": "ASAT", "ALBUMINE": "Albumine",
 "PROTEINES": "Protéines totales", "BIL_TOTAL": "Bilirubine totale", "BIL_DIRECT": "Bilirubine directe",
 "CREAT": "Créatinine", "UREE": "Urée", "CALCIUM": "Calcium ionisé", "IONO_EXT": "Ionogramme étendu",
 "MAGNESIUM": "Magnésium", "PHOSPHORE": "Phosphore", "IONO": "Ionogramme", "CRP": "CRP",
 "GLY_JEUN": "Glycémie à jeun", "GLY_PP": "Glycémie postprandiale", "HB1C": "HbA1c",
 "LIPIDES": "Bilan lipidique", "NFS": "NFS (numération formule sanguine)",
 "HB": "HB (taux d'hémoglobine simple)", "ELECTRO_HB": "Électrophorèse de l'hémoglobine",
 "SPERMOGRAMME": "Spermogramme", "TP_TCA": "TP / TCA", "VS": "Vitesse de sédimentation"}

REMARQUES = {
 "CREAT": "La plage de référence australienne n'est harmonisée que jusqu'à 60 ans. La fonction rénale s'interprète par le débit de filtration estimé (KDIGO), pas par la créatinine seule. La méthode (Jaffé ou enzymatique) change les valeurs.",
 "UREE": "Pour l'homme, aucune source n'a été trouvée : à renseigner. Voir « Points à trancher » : urée ou BUN.",
 "ALAT": "Valeurs sans phosphate de pyridoxal ; elles dépendent de la méthode et du réactif.",
 "ASAT": "Valeurs sans phosphate de pyridoxal ; elles dépendent de la méthode et du réactif.",
 "ACIDE_URIQUE": "Femme : valeur issue d'une seule source, donnée pour 18 à 50 ans. Au-delà de 50 ans, aucune plage n'est proposée.",
 "ALBUMINE": "Dépend de la méthode (vert ou pourpre de bromocrésol).",
 "GLY_JEUN": "Seuils de décision clinique. 1,00 à 1,25 g/L : prédiabète ; 1,26 g/L et plus : diabète. L'examen contient deux paramètres en doublon (voir « Points à trancher »).",
 "GLY_PP": "Seuil du test d'hyperglycémie provoquée (2 h) ; une glycémie postprandiale n'est pas ce test : confiance faible.",
 "HB1C": "Seuils de décision : normal moins de 5,7 % ; 5,7 à 6,4 % prédiabète ; 6,5 % et plus diabète. 0 = pas de limite basse. Méthode certifiée NGSP/IFCC requise.",
 "LIPIDES": "Seuils de décision clinique (NCEP ATP III), pas des intervalles statistiques. 999 = pas de limite haute (un HDL élevé n'est pas pathologique).",
 "NFS": "Désaccord principal sur les leucocytes : étude de Yaoundé 2,6 à 6,8 x10^9/L contre 3,5 à 11,0 en Australie. Proposition : limite basse locale, limite haute occidentale. Hémoglobine et indices (VGM, TCMH, CCMH) : seuils OMS ou occidentaux pour ne pas masquer une anémie ou une microcytose. La ligne existante id 5 (érythrocytes, M, 12 à 18 ans, 1,2 à 1,8) est fausse : voir « Corrections ».",
 "HB": "Femme enceinte : seuil OMS 11,0 g/dL, non gérable par l'application (pas de notion de grossesse). Moins d'un an : pas de plage (l'âge 0 est trop large). Pour les enfants, l'OMS ne donne qu'une limite basse : écrire le maximum dans la colonne « Valeur corrigée ».",
 "ELECTRO_HB": "Dépend de la méthode (CLHP ou électrophorèse capillaire). HbA2 de 4 % et plus : évoque une bêta-thalassémie.",
 "SPERMOGRAMME": "Limites basses OMS 2021 (5e percentile). 9999 = pas de limite haute.",
 "TP_TCA": "Sous anticoagulant (AVK), la cible INR est de 2 à 3, hors de cette plage.",
 "VS": "Hommes jusqu'à 50 ans seulement. Pour les femmes et les plus de 50 ans, aucune source : à renseigner (formule de Miller à vérifier).",
 "CRP": "0 = pas de limite basse. Autre source possible : moins de 3 mg/L.",
 "CALCIUM": "Calcium ionisé. Pour le calcium total, voir l'ionogramme étendu.",
 "IONO_EXT": "Calcium total ici ; si le laboratoire mesure le calcium ionisé, utiliser 1,15 à 1,30 mmol/L.",
 "PHOSPHORE": "Valeur convertie depuis 0,75 à 1,50 mmol/L.",
 "BIL_TOTAL": "Nouveau-né exclu.",
}
SANS_SOURCE = {
 "NFS": [("RDW", "%", "Aucune source trouvée.")],
 "ELECTRO_HB": [("HbA", "%", "Aucune source trouvée."), ("HbF", "%", "Aucune source trouvée.")],
 "TP_TCA": [("TP (%)", "%", "Aucune source trouvée. Pratique courante 70 à 100 %, non vérifiée.")],
}
KIT_DANS_EXAM = {
 "TP_TCA": [("TCA", "s", "Dépend du réactif ; rendre avec le temps du témoin. Indicatif seulement : 25 à 37 s (NSW).")],
}


def fmt(v):
    return v.replace(".", ",") if v else ""


def agecell(a, b):
    return a if a == b else f"{a} à {b}"


rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
exams = OrderedDict()
for r in rows:
    exams.setdefault(r["exam_code"], []).append(r)

HEAD = ("<tr><th class='p'>Paramètre</th><th>Unité</th><th>Sexe</th><th>Âge (ans)</th><th>Min</th><th>Max</th>"
        "<th>Source</th><th>Confiance</th><th class='c'>Validé</th><th class='c'>Modifié</th><th class='c'>Refusé</th>"
        "<th class='v'>Valeur corrigée</th></tr>")


def exam_block(code):
    t = []
    t.append(f"<section class='exam'><h2>{e(TITRES[code])} <span class='code'>({e(code)})</span></h2><table class='r'><thead>{HEAD}</thead><tbody>")
    for r in exams[code]:
        unit = r["unite"] if r["unite"] not in ("–", "-") else "sans unité"
        mx = fmt(r["valeur_max"]) or "<b>à fixer</b>"
        src = ", ".join(r["source_key"].split(";"))
        t.append(f"<tr><td class='p'>{e(r['nom_parametre'])}</td><td>{e(unit)}</td><td>{e(r['sexe'])}</td>"
                 f"<td>{agecell(r['age_min'], r['age_max'])}</td><td>{fmt(r['valeur_min'])}</td><td>{mx}</td>"
                 f"<td>{e(src)}</td><td>{CONF[r['confidence']]}</td><td class='c'>{BOX}</td><td class='c'>{BOX}</td>"
                 f"<td class='c'>{BOX}</td><td class='v'></td></tr>")
    for nom, u, txt in SANS_SOURCE.get(code, []):
        t.append(f"<tr class='nos'><td class='p'>{e(nom)}</td><td>{e(u)}</td><td colspan='7'><b>Sans source.</b> {e(txt)} Écrire la plage à utiliser, ou laisser sans plage :</td>"
                 f"<td class='c' colspan='3'>Min ____ Max ____</td><td class='v'></td></tr>")
    for nom, u, txt in KIT_DANS_EXAM.get(code, []):
        t.append(f"<tr class='nos'><td class='p'>{e(nom)}</td><td>{e(u)}</td><td colspan='7'><b>Selon le kit.</b> {e(txt)} Écrire la valeur de la notice :</td>"
                 f"<td class='c' colspan='3'>Min ____ Max ____</td><td class='v'></td></tr>")
    t.append("</tbody></table>")
    if code in REMARQUES:
        t.append(f"<p class='rem'><b>Remarques.</b> {e(REMARQUES[code])}</p>")
    t.append("<p class='sig'>Examen validé par : ____________________________ &nbsp; le : ____ / ____ / ________ &nbsp; Signature : ________________</p></section>")
    return "".join(t)


KITS = [
 ("ASLO", "Titre ASLO", "Souvent 200 UI/mL chez l'adulte ; aucune source vérifiée."),
 ("CHLAMYDIA", "IgM, IgG", "Seuil du kit."),
 ("HEPB_5EN1", "Anti-HBs", "10 UI/L et plus = protection après vaccination (S12)."),
 ("HEPB_5EN1", "Anti-HBc IgM, IgG", "Seuil du kit (index ou ratio)."),
 ("HEPC", "Anti-VHC", "Seuil du kit (ratio S/CO)."),
 ("HPYLORI", "Anti-H. pylori", "Seuil du kit."),
 ("RHUMATO", "Titre FR", "Seuil du kit."),
 ("RUBE", "IgM, IgG", "IgG de 10 UI/mL et plus souvent retenu comme immunité (S13)."),
 ("SYPHILIS", "TPHA, VDRL (titres)", "Toute réactivité est positive ; titre suivi dans le temps."),
 ("TOXO", "IgM, IgG", "Seuil du kit."),
 ("TYPHOIDE", "IgM, IgG", "Seuil du kit."),
]
kit_rows = "".join(
    f"<tr><td class='p'>{e(x)}</td><td class='p'>{e(p)}</td><td class='n'>{e(n)}</td><td>Min ______<br>Max ______</td></tr>"
    for x, p, n in KITS)

BIB = [
 "<b>S1</b> OMS. <i>Guideline on haemoglobin cutoffs to define anaemia in individuals and populations</i>. Genève, 2024. https://www.who.int/publications-detail-redirect/9789240088542",
 "<b>S2</b> American Diabetes Association. <i>Standards of Care in Diabetes, section 2 : Diagnosis and Classification of Diabetes</i> (éditions 2025-2026 ; seuils inchangés). Diabetes Care. Lire l'édition en vigueur sur https://diabetesjournals.org/care",
 "<b>S3</b> NHLBI. <i>Third Report of the NCEP Expert Panel (Adult Treatment Panel III)</i>. NIH, 2002. https://www.nhlbi.nih.gov/files/docs/resources/heart/atp3full.pdf",
 "<b>S4</b> Koerbin G, Tate JR (AACB). <i>Harmonising Adult Reference Intervals in Australia and New Zealand: the Continuing Story</i>. Clin Biochem Rev 2016;37(3):121-129. https://pmc.ncbi.nlm.nih.gov/articles/PMC5111244",
 "<b>S5</b> NSW Health Pathology. <i>Reference Ranges Adult</i>, 2019. https://www.seslhd.health.nsw.gov.au/sites/default/files/2019-04/NSWHP%20Reference%20Ranges%20Adult%202019.pdf",
 "<b>S6</b> Labcorp, catalogue des tests : Albumine 001081 https://www.labcorp.com/tests/001081/albumin ; Acide urique 001057 https://www.labcorp.com/tests/001057/uric-acid ; Bilirubine directe https://www.labcorp.com//test-menu/21101/bilirubin-direct",
 "<b>S7</b> PathWest (Western Australia). <i>iSTAT Age and Gender Reference Ranges POCT</i>, 2022. https://www.pathwest.health.wa.gov.au/~/media/PathWest/Documents/Health-Professionals/iSTAT-Age-and-Gender-Reference-Ranges-POCT-2022-07.pdf",
 "<b>S8</b> Oloume ME et al. <i>Haematological values in a healthy adult population in Yaounde, Cameroon</i>. Afr J Lab Med 2019;8(1):852. doi:10.4102/ajlm.v8i1.852. https://pmc.ncbi.nlm.nih.gov/articles/PMC6852616 (n = 294, 18 à 55 ans, donneurs de sang)",
 "<b>S9</b> OMS. <i>WHO laboratory manual for the examination and processing of human semen</i>, 6e édition, 2021. https://www.who.int/publications/i/item/9789240030787",
 "<b>S10</b> Étude kenyane sur les intervalles locaux d'HbA2, Egyptian Journal of Internal Medicine 2022. https://ejim.springeropen.com/articles/10.1186/s43162-022-00187-9",
 "<b>S11</b> Revue sur le diagnostic de la bêta-thalassémie et les seuils d'HbA2 (PMC10542033). https://pmc.ncbi.nlm.nih.gov/articles/PMC10542033 ; voir aussi BSH 2023, <i>Significant haemoglobinopathies</i>, https://cms-bsh-u9.b-s-h.org.uk/media/dkrlxdg2/2023-04-19-significant-haemoglobinopathies-a-guideline-for-screening-and-diagnosis.pdf",
 "<b>S12</b> OMS. <i>Hepatitis B vaccines: WHO position paper</i>, Weekly Epidemiological Record 2017;92(27):369-392 (anti-HBs 10 mUI/mL et plus).",
 "<b>S13</b> Skendzel LP. <i>Rubella immunity: defining the level of protective antibody</i>. Am J Clin Pathol 1996;106:170-174.",
]

CSS = """
@page { size: A4 portrait; margin: 22mm 18mm 20mm 18mm;
  @top-left { content: "Plages de référence du laboratoire : proposition à valider"; font-size: 10pt; color:#444; }
  @top-right { content: "BROUILLON, ne pas utiliser avant validation"; font-size: 10pt; color:#444; }
  @bottom-right { content: "Page " counter(page) " / " counter(pages); font-size: 10pt; color:#444; } }
@page wide { size: A4 landscape; margin: 22mm 14mm 18mm 14mm; }
@page cover { margin: 25mm 20mm; @top-left{content:none} @top-right{content:none} @bottom-right{content:none} }
html { font-family: "Arial", "DejaVu Sans", sans-serif; font-size: 11pt; color:#111; line-height:1.4; }
h1 { font-size: 20pt; margin: 0 0 6mm; } h2 { font-size: 13pt; margin: 6mm 0 2mm; break-after: avoid; }
h2 .code { font-weight: normal; color:#444; font-size: 11pt; }
.cover { page: cover; padding-top: 35mm; }
.cover h1 { font-size: 28pt; line-height:1.2; }
.cover .for { font-size: 15pt; margin: 14mm 0 4mm; }
.cover table { border-collapse: collapse; margin-top: 10mm; font-size: 12pt; width:auto; }
.cover td { border:none; padding: 2mm 6mm 2mm 0; vertical-align: top; font-size: 12pt; }
.status { margin-top: 16mm; border: 2px solid #000; padding: 5mm; font-weight: bold; font-size: 14pt; }
.text { break-before: page; }
.wide { page: wide; break-before: page; }
ul, ol { margin: 1mm 0 2mm 5mm; padding-left: 5mm; } li { margin-bottom: 1.2mm; }
table { border-collapse: collapse; width: 100%; table-layout: fixed; }
table, th, td { box-sizing: border-box; }
th, td { border: 0.7pt solid #333; padding: 1.4mm 1.6mm; font-size: 11pt; vertical-align: middle; overflow-wrap: break-word; }
th { background: #e8e8e8; text-align: left; }
tr { break-inside: avoid; }
table.r th:nth-child(1){width:36mm} table.r th:nth-child(2){width:20mm} table.r th:nth-child(3){width:14mm}
table.r th:nth-child(4){width:20mm} table.r th:nth-child(5){width:18mm} table.r th:nth-child(6){width:19mm}
table.r th:nth-child(7){width:20mm} table.r th:nth-child(8){width:25mm}
table.r th:nth-child(9),table.r th:nth-child(10),table.r th:nth-child(11){width:18mm} table.r th:nth-child(12){width:40mm}
td.c, th.c { text-align:center; } td.v { height: 8mm; }
tr.nos td { background:#f4f4f4; }
.box { display:inline-block; width:4.2mm; height:4.2mm; border:0.9pt solid #000; vertical-align:middle; }
.exam { break-inside: avoid-page; margin-bottom: 4mm; }
.rem { font-size: 11pt; margin: 2mm 0 1mm; }
.sig { margin: 3mm 0 0; font-size: 11pt; }
.q { border:0.8pt solid #333; padding:3mm 4mm; margin: 0 0 3.5mm; break-inside: avoid; }
.q p { margin: 0 0 1.5mm; } .q .opt { margin: 0 0 1mm 0; }
.line { border-bottom: 0.7pt solid #333; height: 8mm; }
.bib ul { padding-left:0; margin-left:0; }
.bib li { list-style:none; margin-bottom: 2.2mm; overflow-wrap: anywhere; }
.sign td { height: 14mm; }
"""


def q(num, titre, texte, opts):
    o = "".join(f"<p class='opt'>{BOX} {x}</p>" for x in opts)
    return f"<div class='q'><p><b>{num}. {titre}</b></p><p>{texte}</p>{o}<p>Réponse ou précision : ___________________________________</p></div>"


QS = "".join([
 q(1, "Urée ou BUN", "L'automate rend-il l'urée ou l'azote uréique (BUN) ? La plage proposée (18 à 42 mg/dL, femme 18 à 49 ans) est exprimée en urée. Le BUN, multiplié par 2,14, donne l'urée.", ["L'automate rend l'urée : plage utilisable", "L'automate rend le BUN : plage à convertir ou à remplacer"]),
 q(2, "Calcium total ou ionisé dans l'ionogramme étendu", "L'examen CALCIUM est proposé en calcium ionisé (1,15 à 1,30 mmol/L). L'ionogramme étendu (IONO_EXT) est proposé en calcium total (2,10 à 2,60 mmol/L). Que mesure réellement le laboratoire dans l'ionogramme étendu ?", ["Calcium total : garder 2,10 à 2,60", "Calcium ionisé : utiliser 1,15 à 1,30"]),
 q(3, "Glycémie à jeun : deux paramètres en doublon", "L'examen GLY_JEUN contient deux paramètres identiques : « Glucose » et « Glucose à jeun », avec la même plage (0,63 à 0,99 g/L). Lequel garder ?", ["Garder « Glucose »", "Garder « Glucose à jeun »", "Garder les deux"]),
 q(4, "Hémoglobine de l'enfant : limite haute manquante", "L'OMS ne donne qu'une limite basse pour l'enfant. Les lignes enfant de l'examen HB (1 an, 2 à 4 ans, 5 à 11 ans, 12 à 14 ans) n'ont donc pas de maximum et ne peuvent pas être importées telles quelles.", ["J'écris le maximum de chaque tranche dans l'examen HB", "Je préfère ne pas définir de plage pour l'enfant"]),
 q(5, "Paramètres sans aucune source", "Aucune source n'a été trouvée pour : RDW, HbA, HbF, TP (%). Le TP est couramment lu entre 70 et 100 %, mais cela n'est pas vérifié.", ["J'écris les plages dans les lignes concernées", "Je laisse ces paramètres sans plage"]),
 q(6, "Leucocytes, neutrophiles, plaquettes : valeurs locales ou occidentales", "La population de Yaoundé a en moyenne ces valeurs plus basses. Utiliser des limites basses occidentales signalerait à tort beaucoup de sujets sains. Proposition : limite basse de l'étude de Yaoundé, limite haute occidentale (une hyperleucocytose reste pathologique).", ["D'accord avec la proposition", "Étude de Yaoundé en entier", "Valeurs occidentales"]),
 q(7, "Lipides, glycémie, HbA1c : seuils de décision", "Ces lignes sont des seuils de décision clinique (ADA, NCEP ATP III), et non des intervalles de référence statistiques de la population locale.", ["J'accepte ces seuils", "Je préfère d'autres valeurs (à écrire dans les lignes)"]),
])

COMMENT = """
<h1>Comment valider</h1>
<p><b>À quoi servent ces plages.</b> Dans l'application, quand un résultat chiffré est saisi, l'écran le compare à la plage de référence de l'examen. Si la valeur est en dessous du minimum, elle est signalée « basse » ; au-dessus du maximum, « haute ». Les plages proposées ici sont donc celles qui feront apparaître ces signalements.</p>
<p><b>Rien n'est utilisé avant votre signature.</b> Ce document est un brouillon préparé par l'équipe logicielle à partir de sources publiées (liste en fin de document). Ce ne sont pas des vérités médicales validées. Aucune valeur n'entrera dans l'application tant que vous n'aurez pas signé.</p>
<p><b>Comparez avec votre laboratoire.</b> Chaque valeur doit être comparée avec la notice des réactifs et de l'automate que vous utilisez, et avec votre expérience locale. La notice prime sur ce document. Les enzymes, la créatinine, l'albumine, l'HbA2 et le TCA changent selon la méthode.</p>
<p><b>Pour chaque ligne, cochez une seule case :</b></p>
<ul>
<li><b>Validé</b> : la ligne convient telle quelle.</li>
<li><b>Modifié</b> : écrivez la nouvelle valeur (minimum et maximum) dans la colonne « Valeur corrigée ».</li>
<li><b>Refusé</b> : la ligne ne doit pas être utilisée.</li>
</ul>
<p><b>Niveau de confiance.</b> <b>Élevée</b> : plusieurs sources concordantes ou seuil officiel. <b>Moyenne</b> : une source solide, ou une adaptation (conversion d'unité, choix local ou occidental). <b>Faible</b> : source unique, indirecte ou à vérifier ; regardez ces lignes en priorité.</p>
<p><b>« Selon le kit ».</b> Pour les sérologies et le TCA, la valeur vient de la notice du réactif. Nous ne proposons pas de chiffre : c'est à vous de l'écrire (minimum et maximum). Quand un chiffre couramment publié existe, il est indiqué à titre indicatif seulement.</p>
<p><b>Limites du système à connaître.</b></p>
<ul>
<li>L'âge est un nombre entier d'années. L'âge 0 regroupe tous les enfants de moins d'un an : pas de distinction entre nouveau-né et nourrisson.</li>
<li>Il n'y a pas de notion de grossesse.</li>
<li>Une ligne par sexe et par tranche d'âge, sans chevauchement. Sexe : M, F, ou X (X = valable pour les deux sexes). Un patient de sexe inconnu ne reçoit que les plages X.</li>
<li>Les bornes sont incluses. Une limite ouverte s'écrit 0 en bas, ou 999 ou 9999 en haut (indiqué dans les remarques).</li>
<li>Les unités sont celles de l'application et ne peuvent pas être changées ici. Les conversions déjà faites sont indiquées.</li>
</ul>
<p><b>Ordre conseillé.</b> Répondez d'abord aux points de la page suivante, puis parcourez les examens, puis signez à la dernière page.</p>
"""

FINAL = """
<h1>Validation générale</h1>
<p>Je soussignée, responsable du laboratoire, déclare avoir examiné les plages de référence de ce document, avec les modifications et refus que j'ai notés. <b>Je les valide pour utilisation dans l'application</b> de A Hand to Humanity (A.H2) Medical Center, Yaoundé, dans les limites indiquées.</p>
<table class="sign">
<tr><td style="width:45mm"><b>Nom</b></td><td></td></tr>
<tr><td><b>Fonction</b></td><td></td></tr>
<tr><td><b>Date</b></td><td></td></tr>
<tr><td><b>Signature</b></td><td></td></tr>
<tr><td style="height:30mm"><b>Cachet</b></td><td></td></tr>
</table>
<h2>Commentaires</h2>
<div class="line"></div><div class="line"></div><div class="line"></div><div class="line"></div><div class="line"></div><div class="line"></div><div class="line"></div><div class="line"></div>
"""

blocks_exam = "".join(exam_block(c) for c in exams)

body = f"""
<div class="cover">
<h1>Plages de référence du laboratoire : proposition à valider</h1>
<p class="for">Pour : Ernestine, cheffe du laboratoire</p>
<p style="font-size:13pt">A Hand to Humanity (A.H2) Medical Center, Yaoundé</p>
<table><tr><td>Date</td><td>2026-10-28</td></tr><tr><td>Préparé par</td><td>L'équipe logicielle</td></tr></table>
<div class="status">BROUILLON : ne pas utiliser avant validation</div>
</div>

<div class="text">{COMMENT}</div>

<div class="text"><h1>Points à trancher en premier</h1>
<p>Ces points ont été relevés pendant la préparation. Vos réponses guideront la lecture des tableaux.</p>{QS}</div>

<div class="wide"><h1>Examens : plages proposées</h1>
<p>Sexe : M, F, X (X = les deux). Source : numéro dans la bibliographie en fin de document. Cochez une case par ligne.</p>
{blocks_exam}</div>

<div class="wide"><h1>Examens dont la valeur dépend du kit</h1>
<p>Aucune plage n'est proposée : écrivez le minimum et le maximum de la notice du réactif. La colonne « Repère indicatif » donne une valeur couramment publiée, à titre indicatif seulement.</p>
<table><tr><th style="width:36mm">Examen</th><th style="width:48mm">Paramètre</th><th>Repère indicatif</th><th style="width:48mm">Valeur de la notice</th></tr>{kit_rows}</table>
<p class="sig">Examens validés par : ____________________________ &nbsp; le : ____ / ____ / ________ &nbsp; Signature : ________________</p>
<h2>Paramètres sans plage nécessaire</h2>
<p>Bandelette urinaire (saisie en texte), coprologie, crachats BAAR, cultures (germe, antibiogramme, Gram), ECBU, hémoculture, spermoculture, prélèvement gorge ou pus, groupe ABO et Rhésus, hémoparasites, VIH, VIH oral, HBsAg, test Scotch, skin snip. <b>Goutte épaisse (parasites/µL)</b> : numérique, mais tout parasite est un résultat positif, une plage n'a pas de sens. D'accord qu'aucune plage ne soit définie pour ces examens ? {BOX} Oui &nbsp; {BOX} Non : ______________</p>
<h2>Corrections de lignes déjà présentes dans l'application</h2>
<table><tr><th style="width:24mm">Ligne</th><th>Constat</th><th class="c" style="width:20mm">Validé</th><th class="c" style="width:20mm">Modifié</th><th class="c" style="width:20mm">Refusé</th></tr>
<tr><td>id 5</td><td>Érythrocytes, M, 12 à 18 ans, 1,2 à 1,8 x10^12/L : valeur erronée, à supprimer ou corriger.</td><td class="c">{BOX}</td><td class="c">{BOX}</td><td class="c">{BOX}</td></tr>
<tr><td>id 1 et 2</td><td>Hémoglobine 18 à 65 ans : étendre à 120 ans pour couvrir les plus de 65 ans.</td><td class="c">{BOX}</td><td class="c">{BOX}</td><td class="c">{BOX}</td></tr>
<tr><td>id 310</td><td>Paramètre 979 (Hemoglobin, M, 18 à 120 ans, 13 à 17) : appartient vraisemblablement à un examen de test, à vérifier.</td><td class="c">{BOX}</td><td class="c">{BOX}</td><td class="c">{BOX}</td></tr></table>
</div>

<div class="text">{FINAL}</div>

<div class="text"><h1>Bibliographie</h1><div class="bib"><ul>{"".join(f"<li>{b}</li>" for b in BIB)}</ul></div>
<p>Autres études camerounaises repérées, non utilisées : Fondoh et al., Bamenda, Afr J Lab Med 2020 (https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7756783/) ; Bamenda 2021 (https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7932772/). Les références françaises (SFBC, Eurofins Biomnis) n'ont pas pu être consultées en ligne : à ajouter par le laboratoire s'il les possède.</p></div>
"""

doc = f"<!doctype html><html lang='fr'><head><meta charset='utf-8'><title>Plages de référence du laboratoire : proposition à valider</title><style>{CSS}</style></head><body>{body}</body></html>"
(Path(__file__).resolve().parent / "plages-reference.html").write_text(doc, encoding="utf-8")
HTML(string=doc).write_pdf(str(OUT))
print("ok", OUT)
