import { createI18n } from 'vue-i18n';

// 1. Définition des traductions
const messages = {
  // 🇫🇷 FRANÇAIS
  fr: {
    common: {
      welcome: "Bienvenue",
      logout: "Déconnexion",
      dashboard: "Tableau de Bord",
      users: "Utilisateurs",
      loading: "Chargement...",
      cancel: 'Annuler',
      search_placeholder: 'Rechercher...',
      edit: "Modifier",
      delete: "Supprimer",
      save : "Enregistrer",
      none: "Aucun",
    },
    dashboard: {
      title: "Vue d'ensemble",
      subtitle: "Situation de la clinique au",
      table_title: "Dernières Activités Financières",
      stats: {
        income: "Recettes Totales",
        withdrawals: "Total Retraits",
        debt: "Reste à Payer",
        patients: "Patients Actifs",
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
        cancel: "Annuler",
        create: "Créer le compte",
        update: "Mettre à jour"
      },
      roles: {
        admin: "Administrateur",
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
      app_toxico_web: "Web Toxicomanie" // Si utilisé
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
      
      // Examens
      exams_title: "Tarification des Examens",
      exams_subtitle: "Définition des prix pour la facturation.",
      table_code: "Code",
      table_name: "Nom de l'Examen",
      table_category: "Catégorie",
      table_price: "Prix (FCFA)",
      add_exam: "Nouvel Examen",
      
      // Livres de Prières
      prayers_title: "Types de Livres de Prières",
      prayers_subtitle: "Liste des types de livres à disposition pour les patients.",
      table_type_code: "Code Type",
      table_label: "Libellé",
      
      // Boutons génériques
      save: "Enregistrer",
      cancel: "Annuler",
      edit: "Modifier",
      
      // NOUVELLES CLÉS
      general_title: "Paramètres Généraux & Maintenance",
      general_subtitle: "Options globales pour l'application, les sauvegardes et la performance.",

      db_backup: "Sauvegarde de la Base de Données",
      db_backup_subtitle: "Crée un fichier de sauvegarde (.sql ou .dump) de l'intégralité du système.",
      db_backup_button: "Lancer la Sauvegarde BDD",
      
      maintenance_mode: "Mode Maintenance",
      maintenance_mode_subtitle: "Activer pour bloquer l'accès aux utilisateurs non-administrateurs (sauf urgence).",
      maintenance_active: "Mode Maintenance ACTIF",
      maintenance_inactive: "Mode Maintenance INACTIF",
      
      // Clés des boutons
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
    // 🟢 CLÉ MEDICAL DÉPLACÉE AU NIVEAU RACINE DE 'fr'
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
      errors: {
        patient_not_found: "Patient introuvable"
      },
      spiritual: {
              new_note: "+ Nouvelle Note Spirituelle",
              prescriptions: "Prescriptions Spirituelles",
              psalm: "Psaume",
              no_history: "Aucun historique spirituel."
        }
    }
  },

  // 🇬🇧 ENGLISH
  en: {
    common: {
      welcome: "Welcome",
      logout: "Logout",
      dashboard: "Dashboard",
      users: "Users",
      loading: "Loading...",
      cancel: 'Cancel',
      search_placeholder: 'Search...',
      edit: "Edit",
      delete: "Delete",
      save : "Save",
      none: "None",
    },
    dashboard: {
      title: "Overview",
      subtitle: "Clinic status on",
      table_title: "Latest Financial Activities",
      stats: {
        income: "Total Revenue",
        withdrawals: "Total Withdrawals",
        debt: "Outstanding Debt",
        patients: "Active Patients",
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
        cancel: "Cancel",
        create: "Create Account",
        update: "Update"
      },
      roles: {
        admin: "Administrator",
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
    // 🟢 MODULE TOXICO CORRIGÉ (avec le bloc dossier)
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
      dossier: { // ⬅️ C'EST LE BLOC MANQUANT QUI CAUSAIT L'ERREUR
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
      
      // Examens
      exams_title: "Exam Pricing",
      exams_subtitle: "Defining prices for billing.",
      table_code: "Code",
      table_name: "Exam Name",
      table_category: "Category",
      table_price: "Price (FCFA)",
      add_exam: "New Exam",
      
      // Livres de Prières
      prayers_title: "Prayer Book Types",
      prayers_subtitle: "List of book types available to patients.",
      table_type_code: "Type Code",
      table_label: "Label",
      
      // Generic Buttons
      save: "Save",
      cancel: "Cancel",
      edit: "Edit",
      
      // NOUVELLES CLÉS
      general_title: "General Settings & Maintenance",
      general_subtitle: "Global options for the application, backups, and performance.",

      db_backup: "Database Backup",
      db_backup_subtitle: "Creates a backup file (.sql or .dump) of the entire system.",
      db_backup_button: "Launch DB Backup",
      
      maintenance_mode: "Maintenance Mode",
      maintenance_mode_subtitle: "Activate to block access for non-administrator users (except in emergencies).",
      maintenance_active: "Maintenance Mode ACTIVE",
      maintenance_inactive: "Maintenance Mode INACTIVE",
      
      // Clés des boutons
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
    // 🟢 CLÉ MEDICAL DÉPLACÉE AU NIVEAU RACINE DE 'en'
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
      errors: {
        patient_not_found: "Patient not found"
      },
      spiritual: {
              new_note: "+ New Spiritual Note",
              prescriptions: "Spiritual Prescriptions",
              psalm: "Psalm",
              no_history: "No spiritual history."
          }
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