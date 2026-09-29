import { createI18n } from 'vue-i18n';

// 1. Définition des traductions
const messages = {
  // 🇫🇷 FRANÇAIS
  fr: {
    common: {
      welcome: "Bienvenue",
      logout: "Déconnexion",
      my_account: "Mon compte",
      dashboard: "Tableau de Bord",
      users: "Utilisateurs",
      loading: "Chargement...",
      cancel: 'Annuler',
      search_placeholder: 'Rechercher...',
      edit: "Modifier",
      delete: "Supprimer",
      save : "Enregistrer",
      none: "Aucun",
      page: "Page",
      ok: "OK",
    },
    account: {
      title: "Mon compte",
      tab_profile: "Profil",
      tab_password: "Mot de passe",
      full_name: "Nom complet",
      email: "Email",
      contact: "Téléphone",
      old_password: "Mot de passe actuel",
      new_password: "Nouveau mot de passe",
      confirm_password: "Confirmer le nouveau mot de passe",
      password_mismatch: "Les nouveaux mots de passe ne correspondent pas.",
      profile_saved: "Profil mis à jour avec succès.",
      password_saved: "Mot de passe mis à jour avec succès. Toutes vos sessions ont été déconnectées, y compris celle-ci — reconnexion en cours...",
      save: "Enregistrer",
      saving: "Enregistrement...",
    },
    dashboard: {
      title: "Vue d'ensemble",
      subtitle: "Situation de la clinique au",
      table_title: "Dernières Activités Financières",
      stats: {
        income: "Recettes Totales",
        withdrawals: "Total Retraits",
        debt: "Reste à Payer",
        patients: "Admissions Toxico (Mois)",
        users_online: "Utilisateurs en ligne",
        alerts: "Alertes Système",
        bed_occupancy: "Occupation Lits"
      },
      filters: {
        start_date: "Date Début",
        end_date: "Date Fin",
        apply: "Filtrer"
      },
      actions: {
        refresh: "Actualiser",
        report: "Rapport Complet",
        manage_staff: "Gérer le Personnel",
        new_admission: "Nouvelle Admission",
        payment: "Encaisser Paiement"
      }
    },
    users: {
      title: "Gestion du Personnel",
      subtitle: "Liste des comptes du personnel et des administrateurs.",
      search_placeholder: "Rechercher par nom, email ou rôle...",
      add_new: "Nouveau Compte",
      table: {
        employee: "Employé",
        role: "Rôle",
        contact: "Contact",
        status: "Statut",
        actions: "Actions",
        active: "Actif",
        inactive: "Inactif",
        no_results: "Aucun utilisateur ne correspond à votre recherche",
        active_accounts: "comptes actifs"
      },
      modal: {
        new_title: "Nouvel Utilisateur",
        edit_title: "Modifier l'utilisateur",
        firstname: "Prénom",
        lastname: "Nom",
        email: "Email",
        phone: "Téléphone",
        role: "Rôle",
        is_active: "Compte actif (autorisé à se connecter)",
        is_head_nurse: "Chef infirmier/infirmière",
        cancel: "Annuler",
        create: "Créer le compte",
        update: "Mettre à jour"
      },
      roles: {
        admin: "Administrateur",
        promoteur: "Promoteur",
        medecin: "Médecin",
        nurse: "Infirmier(ère)",
        secretaire: "Secrétaire",
        laborantin: "Laborantin",
        Psychologist: "Psychologue",
        SpiritualCounsellor: "Conseiller Spirituel",
        ToxicoManager: "Responsable Toxicologie",
        Assistant: "Assistant (Finance)"
      },
      groups: {
        label: "Groupe de Sécurité",
        app_admin: "Administration & Direction",
        app_medical: "Service Médical",
        app_secretaire: "Secrétariat",
        app_laborantin: "Laboratoire",
        app_toxico_web: "Web Toxicomanie"
      },
      specialty: {
        label: "Spécialité Médicale",
        placeholder: "— Choisir une spécialité —"
      }
    },
    patients: {
      title: "Dossiers Patients",
      search_placeholder: "Rechercher par nom ou code...",
      tabs: {
        all: "Tous les patients",
        clinical: "Soins Cliniques",
        toxico: "Toxicologie",
        spiritual: "Soins Spirituels"
      },
      types: {
        clinique: "Clinique",
        toxico: "Toxicologie",
        spirituel: "Spirituel",
      }
    }, 
    appointments: {
      title: "Rendez-vous",
      subtitle: "Planning des consultations",
      new_appointment: "Prendre RDV",
      search_label: "Recherche",
      search_placeholder: "Rechercher code ou nom patient...",
      status_label: "Statut",
      status_all: "Tous",
      status_pending: "En attente",
      status_completed: "Terminé",
      status_cancelled: "Annulé",
      date_label: "Date",
      date_all: "Toutes",
      date_today: "Aujourd'hui",
      date_custom: "Personnalisée",
      results_count: "rendez-vous trouvés",
      empty: "Aucun rendez-vous trouvé pour ces critères.",
      pending_sync: "En attente de synchronisation",
      table: {
        patient: "Patient",
        phone: "Téléphone",
        doctor: "Médecin",
        date: "Date",
        time: "Heure",
        reason: "Raison",
        status: "Statut",
        actions: "Actions"
      },
      actions: {
        complete: "Compléter",
        cancel: "Refuser",
        edit: "Éditer",
        view_dossier: "Voir dossier",
        start_consultation: "Démarrer consultation"
      },
      modal: {
        title_new: "Nouveau Rendez-vous",
        title_edit: "Modifier le Rendez-vous",
        patient_code: "Code Patient",
        specialty: "Spécialité",
        specialty_none: "-- Aucune --",
        date: "Date",
        time: "Heure",
        reason: "Motif",
        cancel: "Annuler",
        save: "Enregistrer",
        patient_not_found: "Patient introuvable",
        patient_lookup_error: "Erreur lors de la recherche locale du patient."
      },
      view_list: "Vue liste",
      view_calendar: "Vue calendrier",
      calendar: {
        today: "Aujourd'hui",
        weekdays_short: ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"],
        more: "de plus",
        day_panel_empty: "Aucun rendez-vous ce jour.",
        day_panel_title: "Rendez-vous du"
      }
    },
    hospitalization: {
      title: "Patients hospitalisés",
      subtitle: "Séjours en cours",
      card_title: "Hospitalisation",
      not_hospitalized: "Ce patient n'est pas actuellement hospitalisé.",
      admit_button: "Admettre",
      update_status_button: "Mettre à jour l'état",
      discharge_button: "Sortir",
      admission_reason: "Motif d'admission",
      admitted_since: "Hospitalisé depuis",
      days_count: "jour(s)",
      current_status: "Dernière évolution",
      no_status_yet: "Aucune mise à jour depuis l'admission.",
      history_title: "Historique",
      evolution_title: "Évolution du séjour en cours",
      admitted_by: "Admis par",
      discharged_by: "Sortie prononcée par",
      recorded_by: "par",
      unknown_user: "Utilisateur inconnu",
      download_letter: "Télécharger la lettre de sortie",
      status: {
        AMELIORATION: "Amélioration",
        STABLE: "Stable",
        AGGRAVATION: "Aggravation"
      },
      disposition: {
        GUERI: "Guéri",
        TRANSFERE: "Transféré",
        SORTIE_CONTRE_AVIS_MEDICAL: "Sortie contre avis médical",
        DECES: "Décès"
      },
      status_note: "Note",
      discharge_note: "Note de sortie",
      discharge_disposition_label: "Type de sortie",
      confirm: "Confirmer",
      cancel: "Annuler",
      empty_list: "Aucun patient actuellement hospitalisé.",
      table: {
        patient: "Patient",
        admitted_since: "Hospitalisé depuis",
        days: "Jours",
        current_status: "État actuel",
        admitted_by: "Admis par"
      }
    },
    nurseShift: {
      title: "Planning infirmiers",
      subtitle: "Rotation de l'équipe (matin / après-midi / nuit)",
      today: "Aujourd'hui",
      shift: {
        MATIN: "Matin",
        APRES_MIDI: "Après-midi",
        NUIT: "Nuit"
      },
      day_panel_title: "Planning du",
      add_nurse: "Ajouter un infirmier",
      select_nurse: "Choisir un infirmier",
      remove: "Retirer",
      no_assignment: "Aucun infirmier assigné.",
      read_only_note: "Seuls le médecin ou le chef infirmier/infirmière peuvent modifier ce planning.",
      head_nurse_badge: "Chef infirmier/infirmière"
    },
    prescriptions: {
      title: "Prescriptions",
      subtitle: "Ordonnances et bons d'examen",
      new_prescription: "Nouvelle Prescription",
      search_label: "Recherche",
      search_placeholder: "Rechercher code patient ou médicament...",
      date_from: "Du",
      date_to: "Au",
      results_count: "prescriptions trouvées",
      empty: "Aucune prescription trouvée pour ces critères.",
      confirm_delete: "Supprimer cette prescription ?",
      table: {
        patient: "Patient",
        content: "Prescription",
        duration: "Durée",
        start_date: "Début",
        end_date: "Fin",
        prescriber: "Prescripteur",
        actions: "Actions",
        lab_order_badge: "Bon d'examen"
      },
      actions: {
        edit: "Éditer",
        delete: "Supprimer"
      },
      modal: {
        title_new: "Nouvelle Prescription",
        title_edit: "Modifier la Prescription",
        patient_code: "Code Patient",
        is_lab_order: "Ceci est une demande d'examen (Laboratoire)",
        medication: "Médicament",
        dosage: "Dosage",
        frequency: "Fréquence",
        duration: "Durée",
        start_date: "Date de début",
        end_date: "Date de fin",
        exams: "Examens",
        exams_filter: "Filtrer les examens...",
        exams_empty: "Aucun examen disponible.",
        notes: "Notes",
        cancel: "Annuler",
        save: "Enregistrer",
        patient_not_found: "Patient introuvable",
        medication_required: "Le nom du médicament est requis.",
        exams_required: "Sélectionnez au moins un examen.",
        date_order_error: "La date de fin doit être postérieure ou égale à la date de début."
      }
    },
    medicalRecords: {
      title: "Dossier Médical",
      subtitle: "Consultations et paramètres cliniques",
      new_record: "Nouvelle Consultation",
      search_label: "Recherche",
      search_placeholder: "Rechercher code patient ou nom...",
      date_from: "Du",
      date_to: "Au",
      motif_label: "Motif",
      motif_all: "Tous",
      severity_label: "Gravité",
      severity_all: "Toutes",
      severity_low: "Faible",
      severity_medium: "Moyen",
      severity_high: "Élevé",
      results_count: "consultations trouvées",
      empty: "Aucune consultation trouvée pour ces critères.",
      confirm_delete: "Supprimer cette consultation ?",
      table: {
        patient: "Patient",
        date: "Date",
        motif: "Motif",
        severity: "Gravité",
        diagnosis: "Diagnostic",
        treatment: "Traitement",
        actions: "Actions"
      },
      actions: {
        edit: "Éditer",
        delete: "Supprimer"
      },
      modal: {
        title_new: "Nouvelle Consultation",
        title_edit: "Modifier la Consultation",
        patient_code: "Code Patient",
        patient_not_found: "Patient introuvable",
        section_consultation: "Consultation",
        consultation_date: "Date de consultation",
        motif: "Motif",
        motif_none: "-- Sélectionner un motif --",
        marital_status: "État civil",
        severity: "Gravité",
        section_vitals: "Signes Vitaux",
        bp: "Tension artérielle",
        temperature: "Température (°C)",
        weight: "Poids (kg)",
        height: "Taille (cm)",
        section_notes: "Notes Cliniques",
        medical_history: "Antécédents médicaux",
        allergies: "Allergies",
        symptoms: "Symptômes",
        diagnosis: "Diagnostic",
        treatment: "Traitement",
        notes: "Notes",
        section_triage: "Transmission au médecin",
        needs_doctor_review: "À transmettre au médecin",
        assign_doctor: "Médecin",
        assign_doctor_pool: "File d'attente (tout médecin)",
        cancel: "Annuler",
        save: "Enregistrer",
        motif_required: "Veuillez sélectionner un motif.",
        temperature_range: "La température doit être comprise entre 30 et 45°C.",
        weight_range: "Le poids doit être compris entre 0 et 1000 kg.",
        height_range: "La taille doit être comprise entre 30 et 250 cm.",
        marital_single: "Célibataire",
        marital_married: "Marié(e)",
        marital_divorced: "Divorcé(e)",
        marital_widowed: "Veuf(ve)"
      }
    },
    doctorKpi: {
      title: "Médecins",
      subtitle: "Mes statistiques d'activité",
      period_from: "Du",
      period_to: "Au",
      total_appointments: "Rendez-vous (période)",
      distinct_patients: "Patients distincts (période)",
      medical_records_total: "Consultations réalisées (période)",
      medical_records_note: "Détail par motif ci-dessous.",
      by_status: "Rendez-vous par statut",
      by_motif: "Dossiers médicaux par motif",
      no_data: "Aucune donnée pour cette période.",
      prescriptions_total: "Prescriptions (période)",
      hospitalizations_current: "Séjours en cours (établissement)"
    },
    secretariat: {
      title: "Secrétariat",
      nav: {
        home: "Accueil",
        patients: "Patients",
        stock: "Stock",
        caisse: "Caisse",
        retrait: "Retraits",
        consultations: "Consultations",
        sync_failures: "Échecs de synchronisation",
        discount_history: "Historique des réductions"
      },
      home: {
        title: "Vue d'ensemble",
        period_from: "Du",
        period_to: "Au",
        total_paid: "Total Encaissé",
        total_withdrawn: "Total Retraits",
        balance: "Solde Net",
        remaining_due: "Reste à Recouvrer",
        critical_stock: "Stock Critique",
        expiring_stock: "Péremptions Proches (30j)",
        consultations_period: "Consultations (200 dernières)",
        critical_stock_table_title: "Produits en stock critique",
        critical_stock_table_error: "Impossible de charger les alertes de stock.",
        critical_stock_table_empty: "Aucune alerte de stock critique.",
        critical_stock_table: {
          product: "Produit",
          category: "Catégorie",
          quantity: "Quantité",
          threshold: "Seuil",
          status: "Statut",
          out_of_stock: "Rupture",
          low_stock: "Stock bas"
        }
      }
    },
    consultations: {
      title: "Consultations Spirituelles",
      subtitle: "Suivi des consultations et accompagnements",
      search_placeholder: "Rechercher code patient ou nom...",
      new_consultation: "Nouvelle Consultation",
      empty: "Aucune consultation trouvée.",
      confirm_delete: "Supprimer cette consultation ?",
      table: {
        patient: "Patient",
        type: "Type",
        date: "Date",
        actions: "Actions"
      },
      actions: {
        edit: "Éditer",
        delete: "Supprimer"
      },
      type_spiritual: "Spirituelle",
      type_family_restoration: "Restauration Familiale",
      modal: {
        title_new: "Nouvelle Consultation",
        title_edit: "Modifier la Consultation",
        patient_code: "Code Patient",
        patient_not_found: "Patient introuvable",
        type_label: "Type de consultation",
        consultation_date: "Date de consultation",
        section_spiritual: "Détails Spirituels",
        prayer_book_type: "Type de livre de prière",
        prayer_book_none: "-- Sélectionner --",
        psaume: "Psaume",
        section_family_restoration: "Restauration Familiale",
        fr_registered_at: "Date d'inscription",
        fr_appointment_at: "Date de rendez-vous",
        fr_amount_paid: "Montant payé",
        fr_observation: "Observation",
        section_common: "Informations complémentaires",
        presc_generic: "Prescriptions générales",
        presc_med_spirituel: "Prescriptions médico-spirituelles",
        notes: "Notes",
        cancel: "Annuler",
        save: "Enregistrer",
        type_required: "Veuillez sélectionner un type de consultation."
      }
    },
    finance: {
      title: "Gestion Financière",
      income: "Recettes",
      expense: "Dépenses",
      balance: "Solde Caisse",
      new_transaction: "Nouvelle Transaction",
      search_placeholder: "Rechercher une transaction...",
      table: {
        date: "Date",
        desc: "Description",
        category: "Catégorie",
        amount: "Montant",
        method: "Moyen de paiement",
        status: "Statut",
        type: "Type"
      },
      types: {
        income: "Entrée",
        expense: "Sortie"
      },
      modal: {
        title_new: "Nouvelle Transaction",
        type: "Type de transaction",
        amount: "Montant (FCFA)",
        date: "Date de la transaction",
        category: "Catégorie",
        desc: "Description / Motif",
        method: "Moyen de Paiement",
        cancel: "Annuler",
        save: "Enregistrer la transaction"
      },
      categories: {
        consultation: "Consultation",
        pharmacy: "Pharmacie",
        hospitalization: "Hospitalisation",
        lab: "Laboratoire",
        salary: "Salaires",
        supplies: "Achat Médicaments/Matériel",
        maintenance: "Maintenance/Réparations",
        bills: "Factures (Eau/Électricité)",
        detox: "Desintoxification",
        other: "Autre"
      },
      payment_methods: {
        cash: "Espèces",
        mobile: "Mobile Money",
        check: "Chèque",
        transfer: "Virement"
      },
    },
    caisse: {
      title: "Caisse",
      new_invoice: "Nouvelle facture",
      search_placeholder: "Rechercher une transaction...",
      table: {
        date: "Date",
        patient: "Patient",
        type: "Type",
        total: "Total",
        paid: "Payé",
        due: "Reste dû",
        status: "Statut",
        actions: "Actions",
      },
      status: {
        active: "Active",
        cancelled: "Annulée",
        refunded: "Remboursée",
        pending_approval: "En attente de validation",
        all: "Toutes",
      },
      pending_banner: "{count} facture(s) en attente de validation d'une réduction.",
      actions: {
        view: "Voir le détail",
        add_payment: "Ajouter un versement",
        settle: "Solder",
        cancel: "Annuler",
        download: "Télécharger la facture",
        reprint_ticket: "Réimprimer le ticket",
      },
      cancel_modal: {
        title: "Annuler la transaction",
        justification: "Justification",
        justification_placeholder: "Motif de l'annulation...",
        cancel: "Retour",
        confirm: "Confirmer l'annulation",
        saving: "Annulation...",
      },
      invoice_modal: {
        title: "Nouvelle facture",
        section_patient: "Patient",
        section_items: "Lignes de facture",
        patient_search_placeholder: "Rechercher un patient existant...",
        or: "ou",
        patient_label_placeholder: "Nom du patient de passage (sans dossier)...",
        change_patient: "Changer",
        line_type_pharmacy: "Pharmacie",
        line_type_consultation: "Consultation spirituelle",
        line_type_exam: "Examen",
        line_type_service: "Service libre",
        no_lines: "Aucune ligne ajoutée. Utilisez les boutons ci-dessus.",
        search_product_placeholder: "Rechercher un médicament ou carnet...",
        search_consultation_placeholder: "Rechercher une consultation...",
        search_exam_placeholder: "Rechercher un examen...",
        in_stock: "en stock",
        service_label_placeholder: "Description du service (ex: Hospitalisation 3 jours)...",
        quantity: "Quantité",
        unit_price: "Prix unitaire",
        line_total: "Total ligne",
        advance_amount: "Avance initiale",
        total: "Total facture",
        discount_recipient: "Demander une réduction à",
        discount_select_placeholder: "Sélectionner un responsable...",
        pending_approval: "Demande de réduction envoyée à {name}, en attente d'approbation.",
        cancel_reassign: "Annuler et réassigner",
        request_discount: "Demander une réduction",
        requesting: "Envoi...",
      },
      installment_modal: {
        title: "Ajouter un versement",
        remaining_due: "Reste dû",
      },
    },
    retrait: {
      title: "Retraits de caisse",
      new_retrait: "Nouveau retrait",
      search_placeholder: "Rechercher un retrait...",
      table: {
        date: "Date",
        amount: "Montant",
        justification: "Justification",
        category: "Catégorie",
        method: "Moyen de paiement",
        status: "Statut",
        actions: "Actions",
      },
      modal: {
        title: "Nouveau retrait",
        amount: "Montant (FCFA)",
        category: "Catégorie",
        justification: "Justification",
        justification_placeholder: "Motif du retrait...",
      },
    },
    toxico: {
      title: "Suivi Toxicologique",
      new_admission: "Nouvelle Admission Toxico",
      phases: {
        1: "Phase 1 : Sevrage",
        2: "Phase 2 : Désintoxication",
        3: "Phase 3 : Réinsertion",
        4: "Phase 4 : Suivi Post-Cure"
      },
      table: {
        patient: "Patient / Code",
        substance: "Substance",
        phase: "Phase Actuelle",
        psy: "Psychologue",
        last_eval: "Dernière Éval.",
        actions: "Actions"
      },
      actions: {
        evaluate: "Évaluer",
        change_phase: "Changer Phase",
        discharge: "Sortie",
        admission: "Admission"
      },
      modal: {
        eval_title: "Évaluation Clinique & Comportementale",
        decision_label: "Décision d'évolution",
        maintain: "Maintenir la phase",
        progress: "Progression",
        regress: "Régression / Rechute",
        observations: "Observations Cliniques",
        recommendations: "Recommandations / Prescriptions",
        validate_eval: "Valider l'Évaluation"
      },
      dossier: {
        tabs: {
          overview: "Vue d'ensemble",
          history: "Historique Toxico",
          medical: "Dossier Médical",
          prescriptions: "Prescriptions"
        },
        timeline: {
          phase: "Phase",
          duration: "Période",
          status: "Statut",
          comments: "Commentaire"
        },
        medical: {
          diagnosis: "Diagnostic / Examen",
          type: "Type",
          treated_by: "Traité par",
          result: "Résultat / Statut"
        },
        drugs: {
          drug: "Médicament",
          dosage: "Dosage",
          duration: "Durée",
          prescribed_by: "Signataire"
        }
      },
      admission: {
        title: "Formulaire d'Admission",
        firstname: "Prénom du Patient",
        lastname: "Nom du Patient",
        date: "Date d'entrée",
        substance: "Substance Principale",
        psychologist: "Psychologue Référent",
        referring_doctor: "Médecin Prescripteur (Optionnel)",
        notes: "Note d'admission",
        cancel: "Annuler",
        submit: "Valider l'Admission",
        section_patient: "Information Patient",
        section_guardian: "Garant / Accompagnateur",
        address: "Lieu de résidence",
        guardian_name: "Nom du Garant",
        guardian_contact: "Contact du Garant",
        guardian_relation: "Lien de parenté",
        consent_file: "Engagement signé (PDF/IMG)",
        upload_placeholder: "Cliquer pour uploader le document",
        dob: "Date de Naissance",
        mothers_name: "Nom de la Mère",
        contact: "Numéro patient [optionel]"
      },
      substances: {
        alcohol: "Alcool",
        cannabis: "Cannabis",
        opioids: "Opioïdes / Tramadol",
        cocaine: "Cocaïne",
        tobacco: "Tabac",
        poly: "Polytoxicomanie"
      },
      dashboard: {
        title: "Tableau de Bord Toxicologie",
        subtitle: "Monitoring clinique et statistiques",
        active_patients: "Patients Actifs",
        relapse_rate: "Taux de Rechute",
        new_this_month: "Admissions (Mois)",
        phase_dist: "Répartition par Phase",
        substance_dist: "Répartition par Substance",
        psy_workload: "Charge Psychologues",
        alerts: "Alertes Cliniques"
      },
    },
    config: {
      title: "Configuration Système",
      subtitle: "Paramètres globaux, tarifs et listes de référence.",
      
      exams_title: "Tarification des Examens",
      exams_subtitle: "Définition des prix pour la facturation.",
      table_code: "Code",
      table_name: "Nom de l'Examen",
      table_category: "Catégorie",
      table_price: "Prix (FCFA)",
      add_exam: "Nouvel Examen",
      
      prayers_title: "Types de Livres de Prières",
      prayers_subtitle: "Liste des types de livres à disposition pour les patients.",
      table_type_code: "Code Type",
      table_label: "Libellé",
      
      save: "Enregistrer",
      cancel: "Annuler",
      edit: "Modifier",
      
      general_title: "Paramètres Généraux & Maintenance",
      general_subtitle: "Options globales pour l'application, les sauvegardes et la performance.",

      db_backup: "Sauvegarde de la Base de Données",
      db_backup_subtitle: "Crée un fichier de sauvegarde (.sql ou .dump) de l'intégralité du système.",
      db_backup_button: "Lancer la Sauvegarde BDD",
      
      maintenance_mode: "Mode Maintenance",
      maintenance_mode_subtitle: "Activer pour bloquer l'accès aux utilisateurs non-administrateurs (sauf urgence).",
      maintenance_active: "Mode Maintenance ACTIF",
      maintenance_inactive: "Mode Maintenance INACTIF",
      
      launch_backup: "Lancer la Sauvegarde",
      activate: "Activer",
      deactivate: "Désactiver"
    },
    tech: {
      title: "Audit & Sécurité",
      subtitle: "Journaux d'accès et traçabilité des actions.",
      tabs: {
        access: "Historique des Connexions",
        actions: "Audit des Actions"
      },
      table: {
        user: "Utilisateur",
        action: "Action / Événement",
        resource: "Ressource",
        ip: "Adresse IP",
        date: "Horodatage",
        details: "Détails"
      },
      resources: {
        all: "Toutes les ressources",
        TOXICO: "Toxicologie",
        PHARMACY: "Pharmacie/Stock",
        CAISSE: "Caisse & Facturation",
        MEDICAL_RECORD: "Dossier Médical",
        LAB: "Laboratoire",
        SPIRITUEL: "Spirituel",
        USER: "Utilisateurs/Admin",
        PRESCRIPTION: "Prescriptions",
        PATIENT: "État Civil Patient"
      }
    },
    stock: {
      title: "Gestion du Stock",
      subtitle: "Inventaire des produits pharmaceutiques et naturels.",
      add_product: "Nouveau Produit",
      kpi: {
        total_value: "Valeur du Stock",
        pharma_items: "Produits Pharma",
        natural_items: "Produits Naturels",
        low_stock: "Alertes Stock Bas"
      },
      table: {
        product: "Produit",
        category: "Catégorie",
        qty: "Quantité",
        price: "Prix Unitaire",
        status: "État",
        expiry: "Péremption"
      },
      categories: {
        PHARMA: "Pharmaceutique",
        NATUREL: "Naturel / Traditionnel",
        MATERIEL: "Matériel Médical",
        AUTRE: "Autre"
      },
      modal: {
        add_title: "Ajouter un Produit",
        edit_title: "Modifier le Produit",
        name: "Nom du produit",
        category: "Catégorie",
        qty: "Quantité actuelle",
        threshold: "Seuil d'alerte (Min)",
        price: "Prix de vente",
        expiry: "Date de péremption"
      },
      expiry_status: {
        valid: "Valide",
        soon: "Bientôt périmé",
        expired: "PÉRIMÉ"
      },
      actions: {
        dispose: "Sortir du stock (Destruction/Péremption)"
      },
      forms: {
        tablet: "Comprimé",
        syrup: "Sirop",
        injection: "Injection",
        ointment: "Pommade",
        capsule: "Gélule",
        sachet: "Sachet",
        other: "Autre",
        save : "Enregistrer"
      }
    },
    medical: {
      vitals: {
        bp: "Tension",
        weight: "Poids",
        temperature: "Température"
      },
      alerts: {
        allergies_title: "Allergies Connues"
      },
      tabs: {
        medical_record: "Dossier Médical",
        lab_exams: "Examens & Labo",
        treatments: "Traitements",
        toxico_followup: "Suivi Toxicologie",
        spiritual_followup: "Suivi Spirituel"
      },
      history: {
        title: "Historique des Consultations"
      },
      lab: {
        results_title: "Résultats d'Examens"
      },
      pharma: {
        history_title: "Historique des Traitements"
      },
      actions: {
        new_consultation: "+ Nouvelle Consultation",
        prescribe_exam: "+ Prescrire Examen",
        new_prescription: "+ Nouvelle Ordonnance"
      },
      consultation_flow: {
        offer_prescription: "Ajouter une prescription pour cette consultation ?",
        decline: "Non",
        accept: "Oui, prescrire",
        appointment_complete_failed: "Le dossier a été enregistré, mais le rendez-vous n'a pas pu être marqué terminé automatiquement. Utilisez le bouton \"Terminer\" sur la liste des rendez-vous."
      },
      errors: {
        patient_not_found: "Patient introuvable"
      },
      spiritual: {
          new_note: "+ Nouvelle Note Spirituelle",
          prescriptions: "Prescriptions Spirituelles",
          psalm: "Psaume",
          no_history: "Aucun historique spirituel."
        }
    },
    // 🟢 MISE À JOUR : SECTION LABO COMPLÉTÉE
    lab: {
      title: "Laboratoire",
      nav: {
        dashboard: "Tableau de Bord",
        entry: "Saisie Résultats",
        history: "Historique",
        medical_results: "Résultats d'examens",
        config: "Configuration"
      },
      stats: {
        pending: "Échantillons en attente",
        completed: "Réalisés ce jour",
        critical: "Alertes / Pathologiques",
        revenue: "Recettes Labo (Mois)",
        productivity: "Productivité",
        action_required: "À traiter prioritairement",
        validation_required: "Validation médecin requise"
      },
      entry: {
        title: "Saisie des résultats",
        subtitle: "Enregistrement des analyses biologiques",
        step1: "Identifier le Patient",
        step2: "Saisir les résultats",
        search_placeholder: "Rechercher par nom ou code (ex: P-001)...",
        change_patient: "Changer de patient",
        add_exam: "Ajouter un examen",
        select_exam: "Sélectionner un examen...",
        columns: {
          param: "Examen / Paramètre",
          value: "Valeur",
          unit: "Unité",
          norms: "Normes",
          action: "Action"
        },
        empty_search: "Aucun patient trouvé.",
        empty_rows: "Cliquez sur 'Ajouter un examen' pour commencer.",
        success: "Résultats enregistrés avec succès !"
      },
      history: {
        filter_title: "Filtres avancés",
        search_ph: "Rechercher patient, examen...",
        table: {
            date: "Date",
            patient: "Patient",
            exam: "Examen",
            result: "Résultat",
            status: "Statut",
            action: "Action"
        },
        status_normal: "Normal",
        status_critical: "Pathologique"
      },
      // 🆕 NOUVELLE SECTION RÉCEPTION (AJOUTÉE)
      reception: {
        title: "Nouvelle Demande Labo",
        subtitle: "Réception & Enregistrement",
        success_message: "Demande enregistrée avec succès !",
        section1_title: "1. Identification du Patient",
        mode_internal: "Dossier Existant",
        mode_external: "Patient Externe",
        search_placeholder: "Rechercher (Nom, Code)...",
        no_results: "Aucune prescription active trouvée.",
        searching: "Recherche en cours...",
        patient_internal_label: "Patient Interne",
        change_patient: "Changer",
        ext_name_label: "NOM COMPLET",
        ext_age_label: "ÂGE",
        ext_gender_label: "SEXE",
        ext_warning: "Ce patient ne sera pas enregistré dans la base principale (Dossier Labo uniquement).",
        section2_title: "2. Choix des Examens",
        select_exam_placeholder: "-- Choisir un examen --",
        add_btn: "Ajouter",
        cart_exam_col: "Examen",
        cart_action_col: "Action",
        cart_empty: "Aucun examen sélectionné",
        submit_btn: "CRÉER LA DEMANDE",
        prescribed_exams_found: "Examens prescrits détectés :"
      },
      gender: {
        m: "Masculin",
        f: "Féminin"
      }
    },
    export: {
      format_label: "Format",
      period_label: "Période",
      preset_day: "Aujourd'hui",
      preset_week: "7 derniers jours",
      preset_month: "30 derniers jours",
      cancel: "Annuler",
      confirm: "Exporter",
      exporting: "Export en cours...",
      error: "Échec de l'export. Veuillez réessayer.",
    },
    notifications: {
      title: "Notifications",
      empty: "Aucune notification.",
    },
    discount_review: {
      title: "Demandes de remise en attente",
      empty: "Aucune demande de remise en attente.",
      echelonne_deadline: "Échéance (paiement échelonné)",
      password_confirm: "Confirmez avec votre mot de passe",
      approve: "Approuver",
      refuse: "Refuser",
      unknown_patient: "Patient non renseigné",
      requested_by: "Demandé par {name}",
    },
    discount_history: {
      title: "Historique des réductions",
      results: "résultat(s)",
      from: "Du",
      to: "Au",
      empty: "Aucune demande sur cette période.",
      preset: {
        week: "Cette semaine",
        month: "Ce mois",
        custom: "Personnalisé",
      },
      kpi: {
        approved: "Acceptées",
        refused: "Refusées",
        pending: "En attente",
        total_reduced: "Montant total réduit",
      },
      status: {
        approved: "Acceptée",
        refused: "Refusée",
        pending: "En attente",
        cancelled: "Annulée",
      },
      table: {
        date: "Date",
        requested_by: "Demandé par",
        decided_by: "Décidé par",
        invoice_amount: "Montant facture",
        reduced_amount: "Montant réduit",
      },
    }
  },

  // 🇬🇧 ENGLISH
  en: {
    common: {
      welcome: "Welcome",
      logout: "Logout",
      my_account: "My Account",
      dashboard: "Dashboard",
      users: "Users",
      loading: "Loading...",
      cancel: 'Cancel',
      search_placeholder: 'Search...',
      edit: "Edit",
      delete: "Delete",
      save : "Save",
      none: "None",
      page: "Page",
      ok: "OK",
    },
    account: {
      title: "My Account",
      tab_profile: "Profile",
      tab_password: "Password",
      full_name: "Full Name",
      email: "Email",
      contact: "Phone",
      old_password: "Current Password",
      new_password: "New Password",
      confirm_password: "Confirm New Password",
      password_mismatch: "The new passwords do not match.",
      profile_saved: "Profile updated successfully.",
      password_saved: "Password updated successfully. All your sessions have been signed out, including this one — logging you out...",
      save: "Save",
      saving: "Saving...",
    },
    dashboard: {
      title: "Overview",
      subtitle: "Clinic status on",
      table_title: "Latest Financial Activities",
      stats: {
        income: "Total Revenue",
        withdrawals: "Total Withdrawals",
        debt: "Outstanding Debt",
        patients: "Toxicology Admissions (Month)",
        users_online: "Users Online",
        alerts: "System Alerts",
        bed_occupancy: "Bed Occupancy"
      },
      filters: {
        start_date: "Start Date",
        end_date: "End Date",
        apply: "Filter"
      },
      actions: {
        refresh: "Refresh",
        report: "Full Report",
        manage_staff: "Manage Staff",
        new_admission: "New Admission",
        payment: "Receive Payment"
      }
    },
    users: {
      title: "Staff Management",
      subtitle: "List of staff and administrator accounts.",
      search_placeholder: "Search by name, email, or role...",
      add_new: "New Account",
      table: {
        employee: "Employee",
        role: "Role",
        contact: "Contact",
        status: "Status",
        actions: "Actions",
        active: "Active",
        inactive: "Inactive",
        no_results: "No user matches your search",
        active_accounts: "active accounts"
      },
      modal: {
        new_title: "New User",
        edit_title: "Edit User",
        firstname: "First Name",
        lastname: "Last Name",
        email: "Email",
        phone: "Phone",
        role: "Role",
        is_active: "Active account (allowed to log in)",
        is_head_nurse: "Head nurse",
        cancel: "Cancel",
        create: "Create Account",
        update: "Update"
      },
      roles: {
        admin: "Administrator",
        promoteur: "Owner",
        medecin: "Doctor",
        nurse: "Nurse",
        secretaire: "Secretary",
        laborantin: "Lab Technician",
        Psychologist: "Psychologist",
        SpiritualCounsellor: "Spiritual Counsellor",
        ToxicoManager: "Toxicology Manager",
        Assistant: "Assistant (Finance)"
      },
      groups: {
        label: "Security Group",
        app_admin: "Administration & Management",
        app_medical: "Medical Service",
        app_secretaire: "Secretariat",
        app_laborantin: "Laboratory",
        app_toxico_web: "Toxico Web"
      },
      specialty: {
        label: "Medical Specialty",
        placeholder: "— Choose a specialty —"
      }
    },
    patients: {
      title: "Patient Files",
      search_placeholder: "Search by name or code...",
      tabs: {
        all: "All Patients",
        clinical: "Clinical Care",
        toxico: "Toxicology",
        spiritual: "Spiritual Care"
      },
      types: {
        clinique: "Clinical",
        toxico: "Toxicology",
        spirituel: "Spiritual"
      }
    }, 
    appointments: {
      title: "Appointments",
      subtitle: "Consultation schedule",
      new_appointment: "Book Appointment",
      search_label: "Search",
      search_placeholder: "Search patient code or name...",
      status_label: "Status",
      status_all: "All",
      status_pending: "Pending",
      status_completed: "Completed",
      status_cancelled: "Cancelled",
      date_label: "Date",
      date_all: "All",
      date_today: "Today",
      date_custom: "Custom",
      results_count: "appointments found",
      empty: "No appointments found for these criteria.",
      pending_sync: "Awaiting sync",
      table: {
        patient: "Patient",
        phone: "Phone",
        doctor: "Doctor",
        date: "Date",
        time: "Time",
        reason: "Reason",
        status: "Status",
        actions: "Actions"
      },
      actions: {
        complete: "Complete",
        cancel: "Reject",
        edit: "Edit",
        view_dossier: "View record",
        start_consultation: "Start consultation"
      },
      modal: {
        title_new: "New Appointment",
        title_edit: "Edit Appointment",
        patient_code: "Patient Code",
        specialty: "Specialty",
        specialty_none: "-- None --",
        date: "Date",
        time: "Time",
        reason: "Reason",
        cancel: "Cancel",
        save: "Save",
        patient_not_found: "Patient not found",
        patient_lookup_error: "Local patient lookup failed."
      },
      view_list: "List view",
      view_calendar: "Calendar view",
      calendar: {
        today: "Today",
        weekdays_short: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        more: "more",
        day_panel_empty: "No appointments this day.",
        day_panel_title: "Appointments for"
      }
    },
    hospitalization: {
      title: "Hospitalized Patients",
      subtitle: "Current stays",
      card_title: "Hospitalization",
      not_hospitalized: "This patient is not currently hospitalized.",
      admit_button: "Admit",
      update_status_button: "Update status",
      discharge_button: "Discharge",
      admission_reason: "Admission reason",
      admitted_since: "Hospitalized since",
      days_count: "day(s)",
      current_status: "Latest update",
      no_status_yet: "No update since admission.",
      history_title: "History",
      evolution_title: "Current stay's clinical updates",
      admitted_by: "Admitted by",
      discharged_by: "Discharge recorded by",
      recorded_by: "by",
      unknown_user: "Unknown user",
      download_letter: "Download discharge letter",
      status: {
        AMELIORATION: "Improving",
        STABLE: "Stable",
        AGGRAVATION: "Worsening"
      },
      disposition: {
        GUERI: "Recovered",
        TRANSFERE: "Transferred",
        SORTIE_CONTRE_AVIS_MEDICAL: "Left against medical advice",
        DECES: "Deceased"
      },
      status_note: "Note",
      discharge_note: "Discharge note",
      discharge_disposition_label: "Discharge type",
      confirm: "Confirm",
      cancel: "Cancel",
      empty_list: "No patient currently hospitalized.",
      table: {
        patient: "Patient",
        admitted_since: "Hospitalized since",
        days: "Days",
        current_status: "Current status",
        admitted_by: "Admitted by"
      }
    },
    nurseShift: {
      title: "Nurse Schedule",
      subtitle: "Team rotation (morning / afternoon / night)",
      today: "Today",
      shift: {
        MATIN: "Morning",
        APRES_MIDI: "Afternoon",
        NUIT: "Night"
      },
      day_panel_title: "Schedule for",
      add_nurse: "Add a nurse",
      select_nurse: "Select a nurse",
      remove: "Remove",
      no_assignment: "No nurse assigned.",
      read_only_note: "Only the physician or the head nurse can edit this schedule.",
      head_nurse_badge: "Head nurse"
    },
    prescriptions: {
      title: "Prescriptions",
      subtitle: "Prescriptions and lab orders",
      new_prescription: "New Prescription",
      search_label: "Search",
      search_placeholder: "Search patient code or medication...",
      date_from: "From",
      date_to: "To",
      results_count: "prescriptions found",
      empty: "No prescriptions found for these criteria.",
      confirm_delete: "Delete this prescription?",
      table: {
        patient: "Patient",
        content: "Prescription",
        duration: "Duration",
        start_date: "Start",
        end_date: "End",
        prescriber: "Prescriber",
        actions: "Actions",
        lab_order_badge: "Lab order"
      },
      actions: {
        edit: "Edit",
        delete: "Delete"
      },
      modal: {
        title_new: "New Prescription",
        title_edit: "Edit Prescription",
        patient_code: "Patient Code",
        is_lab_order: "This is a lab order",
        medication: "Medication",
        dosage: "Dosage",
        frequency: "Frequency",
        duration: "Duration",
        start_date: "Start date",
        end_date: "End date",
        exams: "Exams",
        exams_filter: "Filter exams...",
        exams_empty: "No exams available.",
        notes: "Notes",
        cancel: "Cancel",
        save: "Save",
        patient_not_found: "Patient not found",
        medication_required: "Medication name is required.",
        exams_required: "Select at least one exam.",
        date_order_error: "End date must be on or after start date."
      }
    },
    medicalRecords: {
      title: "Medical Record",
      subtitle: "Consultations and clinical vitals",
      new_record: "New Consultation",
      search_label: "Search",
      search_placeholder: "Search patient code or name...",
      date_from: "From",
      date_to: "To",
      motif_label: "Reason",
      motif_all: "All",
      severity_label: "Severity",
      severity_all: "All",
      severity_low: "Low",
      severity_medium: "Medium",
      severity_high: "High",
      results_count: "consultations found",
      empty: "No consultations found for these criteria.",
      confirm_delete: "Delete this consultation?",
      table: {
        patient: "Patient",
        date: "Date",
        motif: "Reason",
        severity: "Severity",
        diagnosis: "Diagnosis",
        treatment: "Treatment",
        actions: "Actions"
      },
      actions: {
        edit: "Edit",
        delete: "Delete"
      },
      modal: {
        title_new: "New Consultation",
        title_edit: "Edit Consultation",
        patient_code: "Patient Code",
        patient_not_found: "Patient not found",
        section_consultation: "Consultation",
        consultation_date: "Consultation date",
        motif: "Reason",
        motif_none: "-- Select a reason --",
        marital_status: "Marital status",
        severity: "Severity",
        section_vitals: "Vitals",
        bp: "Blood pressure",
        temperature: "Temperature (°C)",
        weight: "Weight (kg)",
        height: "Height (cm)",
        section_notes: "Clinical Notes",
        medical_history: "Medical history",
        allergies: "Allergies",
        symptoms: "Symptoms",
        diagnosis: "Diagnosis",
        treatment: "Treatment",
        notes: "Notes",
        section_triage: "Doctor referral",
        needs_doctor_review: "Refer to doctor",
        assign_doctor: "Doctor",
        assign_doctor_pool: "Shared queue (any doctor)",
        cancel: "Cancel",
        save: "Save",
        motif_required: "Please select a reason.",
        temperature_range: "Temperature must be between 30 and 45°C.",
        weight_range: "Weight must be between 0 and 1000 kg.",
        height_range: "Height must be between 30 and 250 cm.",
        marital_single: "Single",
        marital_married: "Married",
        marital_divorced: "Divorced",
        marital_widowed: "Widowed"
      }
    },
    doctorKpi: {
      title: "Doctors",
      subtitle: "My activity statistics",
      period_from: "From",
      period_to: "To",
      total_appointments: "Appointments (period)",
      distinct_patients: "Distinct patients (period)",
      medical_records_total: "Consultations performed (period)",
      medical_records_note: "Breakdown by reason below.",
      by_status: "Appointments by status",
      by_motif: "Medical records by reason",
      no_data: "No data for this period.",
      prescriptions_total: "Prescriptions (period)",
      hospitalizations_current: "Current stays (establishment)"
    },
    secretariat: {
      title: "Secretary",
      nav: {
        home: "Home",
        patients: "Patients",
        stock: "Stock",
        caisse: "Cashier",
        retrait: "Withdrawals",
        consultations: "Consultations",
        sync_failures: "Sync failures",
        discount_history: "Discount history"
      },
      home: {
        title: "Overview",
        period_from: "From",
        period_to: "To",
        total_paid: "Total Paid",
        total_withdrawn: "Total Withdrawn",
        balance: "Net Balance",
        remaining_due: "Remaining Due",
        critical_stock: "Critical Stock",
        expiring_stock: "Expiring Soon (30d)",
        consultations_period: "Consultations (last 200)",
        critical_stock_table_title: "Products in critical stock",
        critical_stock_table_error: "Unable to load stock alerts.",
        critical_stock_table_empty: "No critical stock alerts.",
        critical_stock_table: {
          product: "Product",
          category: "Category",
          quantity: "Quantity",
          threshold: "Threshold",
          status: "Status",
          out_of_stock: "Out of stock",
          low_stock: "Low stock"
        }
      }
    },
    consultations: {
      title: "Spiritual Consultations",
      subtitle: "Consultation and support tracking",
      search_placeholder: "Search patient code or name...",
      new_consultation: "New Consultation",
      empty: "No consultations found.",
      confirm_delete: "Delete this consultation?",
      table: {
        patient: "Patient",
        type: "Type",
        date: "Date",
        actions: "Actions"
      },
      actions: {
        edit: "Edit",
        delete: "Delete"
      },
      type_spiritual: "Spiritual",
      type_family_restoration: "Family Restoration",
      modal: {
        title_new: "New Consultation",
        title_edit: "Edit Consultation",
        patient_code: "Patient Code",
        patient_not_found: "Patient not found",
        type_label: "Consultation type",
        consultation_date: "Consultation date",
        section_spiritual: "Spiritual Details",
        prayer_book_type: "Prayer book type",
        prayer_book_none: "-- Select --",
        psaume: "Psalm",
        section_family_restoration: "Family Restoration",
        fr_registered_at: "Registration date",
        fr_appointment_at: "Appointment date",
        fr_amount_paid: "Amount paid",
        fr_observation: "Observation",
        section_common: "Additional information",
        presc_generic: "General prescriptions",
        presc_med_spirituel: "Medico-spiritual prescriptions",
        notes: "Notes",
        cancel: "Cancel",
        save: "Save",
        type_required: "Please select a consultation type."
      }
    },
    finance: {
      title: "Financial Management",
      income: "Income",
      expense: "Expenses",
      balance: "Cash Balance",
      new_transaction: "New Transaction",
      search_placeholder: "Search transaction...",
      table: {
        date: "Date",
        desc: "Description",
        category: "Category",
        amount: "Amount",
        method: "Payment Method",
        status: "Status",
        type: "Type"
      },
      types: {
        income: "Income",
        expense: "Expense"
      },
      modal: {
        title_new: "New Transaction",
        type: "Transaction Type",
        amount: "Amount (XAF)",
        date: "Transaction Date",
        category: "Category",
        desc: "Description / Reason",
        method: "Payment Method",
        cancel: "Cancel",
        save: "Save Transaction"
      },
      categories: {
        consultation: "Consultation",
        pharmacy: "Pharmacy",
        hospitalization: "Hospitalization",
        lab: "Laboratory",
        salary: "Salaries",
        supplies: "Supplies/Medicine Purchase",
        maintenance: "Maintenance/Repairs",
        bills: "Utility Bills",
        detox: "Detox",
        other: "Other"
      },
      payment_methods: {
        cash: "Cash",
        mobile: "Mobile Money",
        check: "Check",
        transfer: "Bank Transfer"
      },
    },
    caisse: {
      title: "Cash Desk",
      new_invoice: "New Invoice",
      search_placeholder: "Search a transaction...",
      table: {
        date: "Date",
        patient: "Patient",
        type: "Type",
        total: "Total",
        paid: "Paid",
        due: "Balance Due",
        status: "Status",
        actions: "Actions",
      },
      status: {
        active: "Active",
        cancelled: "Cancelled",
        refunded: "Refunded",
        pending_approval: "Awaiting approval",
        all: "All",
      },
      pending_banner: "{count} invoice(s) awaiting discount approval.",
      actions: {
        view: "View Details",
        add_payment: "Add Payment",
        settle: "Settle",
        cancel: "Cancel",
        download: "Download Invoice",
        reprint_ticket: "Reprint ticket",
      },
      cancel_modal: {
        title: "Cancel Transaction",
        justification: "Justification",
        justification_placeholder: "Reason for cancellation...",
        cancel: "Back",
        confirm: "Confirm Cancellation",
        saving: "Cancelling...",
      },
      invoice_modal: {
        title: "New Invoice",
        section_patient: "Patient",
        section_items: "Invoice Lines",
        patient_search_placeholder: "Search an existing patient...",
        or: "or",
        patient_label_placeholder: "Walk-in patient name (no file)...",
        change_patient: "Change",
        line_type_pharmacy: "Pharmacy",
        line_type_consultation: "Spiritual Consultation",
        line_type_exam: "Lab Exam",
        line_type_service: "Free-form Service",
        no_lines: "No line added yet. Use the buttons above.",
        search_product_placeholder: "Search a medication or booklet...",
        search_consultation_placeholder: "Search a consultation...",
        search_exam_placeholder: "Search a lab exam...",
        in_stock: "in stock",
        service_label_placeholder: "Service description (e.g. 3-day hospitalization)...",
        quantity: "Quantity",
        unit_price: "Unit Price",
        line_total: "Line Total",
        advance_amount: "Initial Advance",
        total: "Invoice Total",
        discount_recipient: "Request a discount from",
        discount_select_placeholder: "Select a manager...",
        pending_approval: "Discount request sent to {name}, awaiting approval.",
        cancel_reassign: "Cancel and reassign",
        request_discount: "Request a discount",
        requesting: "Sending...",
      },
      installment_modal: {
        title: "Add a Payment",
        remaining_due: "Balance Due",
      },
    },
    retrait: {
      title: "Cash Withdrawals",
      new_retrait: "New Withdrawal",
      search_placeholder: "Search a withdrawal...",
      table: {
        date: "Date",
        amount: "Amount",
        justification: "Justification",
        category: "Category",
        method: "Payment Method",
        status: "Status",
        actions: "Actions",
      },
      modal: {
        title: "New Withdrawal",
        amount: "Amount (FCFA)",
        category: "Category",
        justification: "Justification",
        justification_placeholder: "Reason for withdrawal...",
      },
    },
    toxico: {
      title: "Toxicology Monitoring",
      new_admission: "New Toxico Admission",
      phases: {
        1: "Phase 1: Withdrawal",
        2: "Phase 2: Detox",
        3: "Phase 3: Reintegration",
        4: "Phase 4: Aftercare"
      },
      table: {
        patient: "Patient / Code",
        substance: "Substance",
        phase: "Current Phase",
        psy: "Psychologist",
        last_eval: "Last Eval.",
        actions: "Actions"
      },
      actions: {
        evaluate: "Evaluate",
        change_phase: "Change Phase",
        discharge: "Discharge",
        admission: "Admission"
      },
      modal: {
        eval_title: "Clinical & Behavioral Evaluation",
        decision_label: "Evolution Decision",
        maintain: "Maintain Phase",
        progress: "Progression",
        regress: "Regression / Relapse",
        observations: "Clinical Observations",
        recommendations: "Recommendations / Prescriptions",
        validate_eval: "Submit Evaluation"
      },
      dossier: {
        tabs: {
          overview: "Overview",
          history: "Toxico History",
          medical: "Medical Record",
          prescriptions: "Prescriptions"
        },
        timeline: {
          phase: "Phase",
          duration: "Period",
          status: "Status",
          comments: "Comment"
        },
        medical: {
          diagnosis: "Diagnosis / Examination",
          type: "Type",
          treated_by: "Treated By",
          result: "Result / Status"
        },
        drugs: {
          drug: "Drug",
          dosage: "Dosage",
          duration: "Duration",
          prescribed_by: "Prescriber"
        }
      },
      admission: {
        title: "Admission Form",
        firstname: "Patient First Name",
        lastname: "Patient Last Name",
        date: "Admission Date",
        substance: "Primary Substance",
        psychologist: "Referral Psychologist",
        referring_doctor: "Prescribing Doctor (Optional)",
        notes: "Admission Note",
        cancel: "Cancel",
        submit: "Validate Admission",
        section_patient: "Patient Information",
        section_guardian: "Guardian / Sponsor",
        address: "Place of Residence",
        guardian_name: "Guardian Name",
        guardian_contact: "Guardian Contact",
        guardian_relation: "Relationship",
        consent_file: "Signed Consent (PDF/IMG)",
        upload_placeholder: "Click to upload document",
        dob: "Date of Birth",
        mothers_name: "Mother's Name",
        contact: "patient phone [optional]"
      },
      substances: {
        alcohol: "Alcohol",
        cannabis: "Cannabis",
        opioids: "Opioids / Tramadol",
        cocaine: "Cocaine",
        tobacco: "Tobacco",
        poly: "Polysubstance Abuse"
      },
      dashboard: {
        title: "Toxicology Dashboard",
        subtitle: "Clinical monitoring and statistics",
        active_patients: "Active Patients",
        relapse_rate: "Relapse Rate",
        new_this_month: "Admissions (Month)",
        phase_dist: "Distribution by Phase",
        substance_dist: "Distribution by Substance",
        psy_workload: "Psychologist Workload",
        alerts: "Clinical Alerts"
      }
    },
    config: {
      title: "System Configuration",
      subtitle: "Global settings, pricing, and reference lists.",
      
      exams_title: "Exam Pricing",
      exams_subtitle: "Defining prices for billing.",
      table_code: "Code",
      table_name: "Exam Name",
      table_category: "Category",
      table_price: "Price (FCFA)",
      add_exam: "New Exam",
      
      prayers_title: "Prayer Book Types",
      prayers_subtitle: "List of book types available to patients.",
      table_type_code: "Type Code",
      table_label: "Label",
      
      save: "Save",
      cancel: "Cancel",
      edit: "Edit",
      
      general_title: "General Settings & Maintenance",
      general_subtitle: "Global options for the application, backups, and performance.",

      db_backup: "Database Backup",
      db_backup_subtitle: "Creates a backup file (.sql or .dump) of the entire system.",
      db_backup_button: "Launch DB Backup",
      
      maintenance_mode: "Maintenance Mode",
      maintenance_mode_subtitle: "Activate to block access for non-administrator users (except in emergencies).",
      maintenance_active: "Maintenance Mode ACTIVE",
      maintenance_inactive: "Maintenance Mode INACTIVE",
      
      launch_backup: "Launch Backup",
      activate: "Activate",
      deactivate: "Deactivate"
    },
    tech: {
      title: "Audit & Security",
      subtitle: "Access logs and action traceability.",
      tabs: {
        access: "Connection History",
        actions: "Action Audit"
      },
      table: {
        user: "User",
        action: "Action / Event",
        resource: "Resource",
        ip: "IP Address",
        date: "Timestamp",
        details: "Details"
      },
      resources: {
        all: "All Resources",
        TOXICO: "Toxicology",
        PHARMACY: "Pharmacy/Stock",
        CAISSE: "Cashier & Billing",
        MEDICAL_RECORD: "Medical Record",
        LAB: "Laboratory",
        SPIRITUEL: "Spiritual",
        USER: "Users/Admin",
        PRESCRIPTION: "Prescriptions",
        PATIENT: "Patient Info"
      }
    },
    stock: {
      title: "Stock Management",
      subtitle: "Inventory of pharmaceutical and natural products.",
      add_product: "New Product",
      kpi: {
        total_value: "Stock Value",
        pharma_items: "Pharma Items",
        natural_items: "Natural Items",
        low_stock: "Low Stock Alerts"
      },
      table: {
        product: "Product",
        category: "Category",
        qty: "Quantity",
        price: "Unit Price",
        status: "Status",
        expiry: "Expiry"
      },
      categories: {
        PHARMA: "Pharmaceutical",
        NATUREL: "Natural / Traditional",
        MATERIEL: "Medical Equipment",
        AUTRE: "Other"
      },
      modal: {
        add_title: "Add Product",
        edit_title: "Edit Product",
        name: "Product Name",
        category: "Category",
        qty: "Current Quantity",
        threshold: "Alert Threshold (Min)",
        price: "Selling Price",
        expiry: "Expiry Date"
      },
      expiry_status: {
        valid: "Valid",
        soon: "Soon Expiring",
        expired: "EXPIRED"
      },
      actions: {
        dispose: "Remove from Stock (Destruction/Expiry)"
      },
      forms: {
        tablet: "Tablet",
        syrup: "Syrup",
        injection: "Injection",
        ointment: "Ointment",
        capsule: "Capsule",
        sachet: "Sachet",
        other: "Other",
        save : "Save"
      }
    },
    medical: {
      vitals: {
        bp: "Blood Pressure",
        weight: "Weight",
        temperature: "Temperature"
      },
      alerts: {
        allergies_title: "Known Allergies"
      },
      tabs: {
        medical_record: "Medical Record",
        lab_exams: "Labs & Exams",
        treatments: "Treatments",
        toxico_followup: "Toxicology Follow-up",
        spiritual_followup: "Spiritual Follow-up"
      },
      history: {
        title: "Consultation History"
      },
      lab: {
        results_title: "Lab Results"
      },
      pharma: {
        history_title: "Treatment History"
      },
      actions: {
        new_consultation: "+ New Consultation",
        prescribe_exam: "+ Order Lab Test",
        new_prescription: "+ New Prescription"
      },
      consultation_flow: {
        offer_prescription: "Add a prescription for this consultation?",
        decline: "No",
        accept: "Yes, prescribe",
        appointment_complete_failed: "The record was saved, but the appointment could not be marked as completed automatically. Use the \"Complete\" button on the appointments list."
      },
      errors: {
        patient_not_found: "Patient not found"
      },
      spiritual: {
          new_note: "+ New Spiritual Note",
          prescriptions: "Spiritual Prescriptions",
          psalm: "Psalm",
          no_history: "No spiritual history."
        }
    },
    // 🟢 UPDATED LAB SECTION
    lab: {
      title: "Laboratory",
      nav: {
        dashboard: "Dashboard",
        entry: "Result Entry",
        history: "History",
        medical_results: "Exam Results",
        config: "Configuration"
      },
      stats: {
        pending: "Pending Samples",
        completed: "Completed Today",
        critical: "Alerts / Critical",
        revenue: "Lab Revenue (Month)",
        productivity: "Productivity",
        action_required: "Priority processing",
        validation_required: "Doctor validation required"
      },
      entry: {
        title: "Result Entry",
        subtitle: "Recording biological analysis",
        step1: "Identify Patient",
        step2: "Enter Results",
        search_placeholder: "Search by name or code (e.g. P-001)...",
        change_patient: "Change Patient",
        add_exam: "Add Exam",
        select_exam: "Select exam...",
        columns: {
          param: "Exam / Parameter",
          value: "Value",
          unit: "Unit",
          norms: "Ranges",
          action: "Action"
        },
        empty_search: "No patient found.",
        empty_rows: "Click 'Add Exam' to start.",
        success: "Results saved successfully!"
      },
      history: {
        filter_title: "Advanced Filters",
        search_ph: "Search patient, exam...",
        table: {
            date: "Date",
            patient: "Patient",
            exam: "Exam",
            result: "Result",
            status: "Status",
            action: "Action"
        },
        status_normal: "Normal",
        status_critical: "Critical"
      },
      // 🆕 NEW RECEPTION SECTION (ADDED)
      reception: {
        title: "New Lab Request",
        subtitle: "Reception & Registration",
        success_message: "Request successfully registered!",
        section1_title: "1. Patient Identification",
        mode_internal: "Existing File",
        mode_external: "External Patient",
        search_placeholder: "Search (Name, Code)...",
        no_results: "No active prescription found.",
        searching: "Searching...",
        patient_internal_label: "Internal Patient",
        change_patient: "Change",
        ext_name_label: "FULL NAME",
        ext_age_label: "AGE",
        ext_gender_label: "GENDER",
        ext_warning: "This patient will not be saved in the main database (Lab record only).",
        section2_title: "2. Exam Selection",
        select_exam_placeholder: "-- Select an exam --",
        add_btn: "Add",
        cart_exam_col: "Exam",
        cart_action_col: "Action",
        cart_empty: "No exam selected",
        submit_btn: "CREATE REQUEST",
        prescribed_exams_found: "Prescribed exams found:"
      },
      gender: {
        m: "Male",
        f: "Female"
      }
    },
    export: {
      format_label: "Format",
      period_label: "Period",
      preset_day: "Today",
      preset_week: "Last 7 days",
      preset_month: "Last 30 days",
      cancel: "Cancel",
      confirm: "Export",
      exporting: "Exporting...",
      error: "Export failed. Please try again.",
    },
    notifications: {
      title: "Notifications",
      empty: "No notifications.",
    },
    discount_review: {
      title: "Pending discount requests",
      empty: "No pending discount requests.",
      echelonne_deadline: "Deadline (installment plan)",
      password_confirm: "Confirm with your password",
      approve: "Approve",
      refuse: "Refuse",
      unknown_patient: "No patient specified",
      requested_by: "Requested by {name}",
    },
    discount_history: {
      title: "Discount history",
      results: "result(s)",
      from: "From",
      to: "To",
      empty: "No requests in this period.",
      preset: {
        week: "This week",
        month: "This month",
        custom: "Custom",
      },
      kpi: {
        approved: "Approved",
        refused: "Refused",
        pending: "Pending",
        total_reduced: "Total reduced amount",
      },
      status: {
        approved: "Approved",
        refused: "Refused",
        pending: "Pending",
        cancelled: "Cancelled",
      },
      table: {
        date: "Date",
        requested_by: "Requested by",
        decided_by: "Decided by",
        invoice_amount: "Invoice amount",
        reduced_amount: "Reduced amount",
      },
    }
  }
};

// 2. Création de l'instance i18n
const i18n = createI18n({
  legacy: false, 
  locale: localStorage.getItem('lang') || 'fr', 
  fallbackLocale: 'en',
  globalInjection: true, 
  messages,
});

export default i18n;