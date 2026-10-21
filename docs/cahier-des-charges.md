# AI PRODUCTION STUDIO

**Cahier des charges fonctionnel et technique — Version 1.0 — 20 octobre 2026**

**Statut :** document de conception destiné à tout programmeur ; choix des modèles et performances à confirmer par essais.

## 1. Objet, périmètre et principes

Produit : AI Production Studio (nom provisoire). Application personnelle de création audiovisuelle IA, orientée production professionnelle et pédagogique, exploitable depuis Windows et téléphone. Objectifs : créer tout style d'image, enregistrer des personnages cohérents, animer des plans, synthétiser voix/dialogues AR/FR, réaliser montage, automatiser des films jusqu'à 30 minutes et plus par assemblage de plans, contrôler qualité, coûts et temps.

Contraintes confirmées : PC de bureau principal sans GPU dédié ; GPU intégré éventuellement disponible à diagnostiquer ; calcul lourd sur Colab si disponible ou GPU loué avec accord préalable ; stockage local et synchronisation optionnelle Google Drive ; éviter abonnements et dépenses inutiles. L'application reste fonctionnelle pour organiser, prévisualiser et monter légèrement sans GPU distant. L'usage depuis téléphone requiert serveur joignable et authentifié ; Google Drive n'héberge pas un serveur.

Non-objectifs initiaux : reproduire immédiatement toutes les fonctionnalités de DaVinci Resolve, garantir la continuité parfaite d'identité, rendre Colab disponible 24h/24, garantir 30 minutes d'animation générative continue à faible coût, ou promettre tous les modèles sous licence libre.

## 2. Utilisateurs, cas d’usage et exigences

Profils : propriétaire/administrateur, éditeur, opérateur (extensible). Cas d'usage UC01 créer un projet depuis script/PDF/texte ; UC02 créer image de tout style ; UC03 enregistrer personnage et déclinaisons ; UC04 modifier image par masque et références ; UC05 générer vidéo image-to-video/text-to-video ; UC06 générer voix arabe/française et assigner aux personnages ; UC07 synchroniser lèvres et dialogues ; UC08 storyboard et plans ; UC09 montage multipiste ; UC10 lancer film long automatisé ; UC11 reprendre tâches après panne ; UC12 exporter projet et médias ; UC13 lancer calcul sur backend local/Colab/location ; UC14 accès mobile ; UC15 sauvegarde/restauration ; UC16 mesurer coût réel.

Priorités : P0 données conservées, application fonctionnelle sans GPU dédié, traitement distant, contrôle dépenses, génération d'image, gestion des personnages, orchestration et reprise ; P1 vidéo, TTS, montage, automatisation longue ; P2 multi-utilisateurs, modèles additionnels, plugins, publication directe.

## 3. Architecture logique et déploiement

Architecture en couches : (A) client React/TypeScript responsive, PWA installable ; (B) serveur FastAPI Python avec authentification, API REST, WebSocket/SSE événements ; (C) services métier Projects, Assets, Character Registry, Model Registry, Jobs, Workflow, Cost & GPU Manager, Timeline, QC, Export ; (D) file de tâches persistante et workers CPU/GPU ; (E) adaptateurs de modèles IA interchangeables ; (F) stockage fichiers et base relationnelle.

Déploiement local : Windows héberge UI/backend, SQLite au départ puis PostgreSQL possible, dossiers projets sur disque. Workers GPU distants exécutent les tâches lourdes et renvoient résultats ; communication sécurisée sortante ou tunnel authentifié, pas de port public non protégé. Déploiement optionnel serveur distant pour accès continu quand PC éteint. PWA pour mobile ; Tauri optionnel plus tard pour bureau, pas obligatoire pour MVP.

Séparer plan de contrôle et plan de calcul : API d'orchestration indépendante de ComfyUI, de Colab et du fournisseur GPU. Utiliser conteneurs Linux sur machines GPU quand possible ; sur Windows, environnement natif/WSL selon contraintes. Prévoir adaptation des chemins et formats. Une seule source de vérité pour états des tâches et médias.

## 4. Modules communs et données

Project : id, nom, langue, résolution, fps, durée cible, budget, date, version. Asset : id, type, checksum SHA256, chemin local, URI distante optionnelle, licence, provenance, version, métadonnées techniques. Character : id, fiche descriptive, images multi-vues, tenues, palette, contraintes négatives, voix associée, adaptateurs d'identité/LoRA, autorisations et versions. Scene : id, script, personnages, durée, plans, transitions, dépendances. Shot : id, image de référence, vidéo, prompt, seed, modèle, paramètres, version et score QC. VoiceProfile : id, langue, style, moteur, référence autorisée, conditions de consentement. Job : id, type, statut, dépendances, tentatives, horodatages, backend, VRAM estimée, coût estimé/réel, logs et artefacts. Model : id, version, poids, licence, compatibilité, VRAM, qualité mesurée, statut d'installation.

Utiliser UUID, migrations de schéma, versionnement non destructif et manifeste de projet JSON exportable. Ne jamais dépendre uniquement d'un nom de fichier ; conserver provenance complète des générations. Stockage volumineux dédupliqué et politique de nettoyage explicite. Toute opération destructrice doit être confirmée.

## 5. Atelier A — Création et retouche d’images

Fonctions : text-to-image, image-to-image, inpainting/outpainting, détourage, suppression d'objet, variation, composition multi-références, contrôle de pose/profondeur/contours, changement de style, lots, seeds, comparaison côte à côte, upscale, export PNG/JPEG/WebP/TIFF selon support. Styles : photographie, cinéma, dessin, peinture, manga, bande dessinée, 2D/3D, isométrie, architecture, produit, affiche, tableau blanc, illustrations éducatives. Gabarits 16:9, 9:16, 1:1, A4, résolutions personnalisées.

Candidats moteurs à benchmarker : FLUX (versions/licences à vérifier), Qwen-Image/Edit, SDXL avec ControlNet, autres modèles ouverts compatibles ; ne pas figer un seul moteur. L'interface expose capacités réelles du modèle (références, édition, résolution, VRAM). Les écritures arabes vocalisées et textes critiques seront superposés par moteur typographique fiable, pas confiés exclusivement au rendu génératif.

Entrées : prompt, références, masques, personnage, style, paramètres. Sorties : images, miniatures, métadonnées, rapport qualité, variantes. Tests : 20 prompts multi-styles, images avec texte AR/FR, édition localisée, répétabilité, comparaison qualité/coût/temps.

## 6. Atelier B — Identité et continuité des personnages

Character Lock : fiche d'identité visuelle persistante (face, profil, trois-quarts, corps entier, expressions, vêtements, proportions, signes distinctifs), voix et consignes. Générer planches de références, approuver images maîtresses, créer variantes contrôlées, historique des changements, versions et verrouillage d'éléments.

Méthodes interchangeables : multi-références, adaptateurs d'identité compatibles, ControlNet pose/profondeur, entraînement LoRA autorisé si utile. Attention : compatibilité IP-Adapter/PuLID/LoRA varie selon modèle ; aucune garantie universelle. Pour vidéo, utiliser images-clés et références du personnage ; contrôler dérive entre plans et régénérer les plans problématiques.

Mesure qualité : revue humaine obligatoire pour plans clés, comparaison automatisée indicative de visage, tenue, silhouette, palette et accessoires ; seuils réglables, journal des écarts. Identité et consentement : uniquement personnages originaux ou personnes pour lesquelles les droits et autorisations nécessaires sont obtenus. Test d'acceptation : même personnage dans 10 scènes, 3 angles, 2 tenues autorisées, 2 éclairages, puis 3 plans animés ; noter cohérence et corrections nécessaires.

## 7. Atelier C — Vidéo et animation

Fonctions : text-to-video, image-to-video, first/last frame si moteur compatible, vidéo-to-vidéo, mouvement par vidéo de référence si supporté, camera motion, extension de clip, stabilisation, interpolation, upscaling, lip-sync par module séparé, extraction de frames. Moteurs candidats : Wan (famille et variantes adaptées), LTX, HunyuanVideo, CogVideoX, autres compatibles ; choix final après tests VRAM/licence/vitesse.

Chaque plan dispose d'un contrat : durée, fps, résolution, personnages, références, mouvement attendu, voix, seed, tolérance de dérive. Prévisualisation basse résolution puis rendu final. Gestion de clips courts et assemblage, pas de promesse de générer 30 minutes d'un seul tenant. Contrôle visuel des mains, visage, mouvements, sauts temporels, clignotements, artefacts. Rendu distribué seulement si les workers ont modèles et assets compatibles.

Sorties : MP4/WebM selon encodeur, séquences images et fichiers intermédiaires ; encodage FFmpeg ; métadonnées et coûts conservés.

## 8. Atelier D — Voix, audio et langues

Fonctions : TTS texte-vers-voix, narration longue segmentée, voix AR/FR, voix masculines/féminines et voix synthétiques enfantines, réglage débit, pauses, expressivité, prosodie, dictionnaire de prononciation, échantillons de validation, voix associées aux personnages, nettoyage audio, normalisation, sous-titres synchronisés, diarisation/transcription si utile. Clonage uniquement avec consentement documenté et garde-fous d'accès. Ne pas imiter une personne sans autorisation.

Moteurs candidats à comparer selon qualité/licence/support arabe : XTTS-v2, modèles Fish Speech, Chatterbox et autres moteurs multilingues ; valider concrètement phonèmes arabes, voyelles, noms propres, français, stabilité et temps de démarrage. Les modèles ne prennent pas tous en charge les deux langues ni les mêmes droits d'usage.

Pipeline : préparation linguistique -> segmentation -> génération -> écoute/QC -> assemblage -> synchronisation -> WAV maître + pistes compressées. Critère impératif : un test de phrase de 2 secondes ne doit pas attendre des heures ; mesurer latence de démarrage et latence à chaud séparément.

## 9. Atelier E — Réalisation, scénarios et storyboards

Importer texte, Markdown, DOCX/PDF si extractible, notes et audio transcrit. Définir sujet, audience, durée, langue, ton, charte visuelle et contraintes. Produire structure en actes/chapitres/scènes/plans, storyboard illustré, liste des assets, voix, durée estimée et budget avant génération. Éditeur humain pour modifier chaque plan, verrouiller personnages et approuver les scènes. Planification des dialogues et de l'ordre des prises ; bibliothèque de templates pédagogiques, documentaire, fiction, publicité, tutoriel.

La génération automatique de scripts est une aide éditoriale ; validation humaine requise pour faits, citations, contenu religieux/éducatif, prononciation et droits. Les estimations de durée tiennent compte du débit de narration, des silences et des transitions.

## 10. Atelier F — Montage, son et export

Timeline multipiste vidéo, audio, sous-titres et overlays ; coupe, trim, ripple, transitions, vitesse, cadrage, titres, fondus, mixage, normalisation, égalisation basique, colorimétrie élémentaire, preview proxy et rendu final. Format interne timeline JSON versionné, EDL/OTIO éventuel pour interopérabilité ; export projet avec assets. Moteur de rendu FFmpeg, contrôles résolution/fps/bitrate, MP4 H.264 par défaut, autres codecs selon environnement et licences.

Sans GPU dédié, le montage lourd et l'export 4K peuvent être lents ; prévoir proxies et, si nécessaire, encodage distant. Autosave, undo/redo, versions, sauvegarde avant export. Le périmètre MVP n'inclut pas l'équivalent complet d'un NLE professionnel ; extension par étapes.

## 11. Atelier G — Automatisation des productions longues

Orchestrateur DAG de tâches : import -> script -> storyboard -> personnages -> voix -> images -> QC -> clips -> QC -> timeline -> mixage -> export -> rapport. Chaque tâche idempotente si possible, dépendances explicites, cache basé sur hash des entrées, reprise sur panne, retries limités, checkpoint par scène, annulation et pause. États : draft, queued, blocked, running, review, failed, completed, canceled. Une validation humaine peut constituer une porte obligatoire.

Modes assisté, semi-auto, automatique avec plafond de dépenses. Les productions de 30 minutes combinent voix, images fixes animées par caméra, animations courtes et séquences réutilisables. Budget par projet, plafond par scène et par tâche, alerte avant dépassement ; régénération limitée par nombre de tentatives. Ne jamais louer ou maintenir un GPU facturé sans confirmation explicite préalable.

Planificateur : exécution en lot, priorités, dépendances, estimations, reprise après redémarrage, notifications dans l'application ; accès distant mobile possible selon déploiement. Rapports : réussite par scène, durée totale, temps GPU, coût, éléments à revoir. Essais progressifs 30 secondes, 3 minutes, 5 minutes, 15 minutes, 30 minutes.

## 12. Atelier H — Gestionnaire GPU et modèles

Backend types : CPU local, GPU local futur, Colab expérimental, GPU loué à la demande. Capabilities : VRAM, RAM, accélération CUDA/ROCm/DirectML si compatible, versions pilotes, codecs, modèle chargé, disponibilité, tarif, vitesse mesurée. Sélection par règles : compatibilité dure -> capacité -> latence -> coût -> préférence utilisateur. Pas de supposition sur GPU intégré ; diagnostic à domicile.

Colab : sessions éphémères, limites de durée et disponibilité, déconnexions ; ne pas traiter comme infrastructure fiable 24/7 ni promettre automatisation non supervisée. Connecteur uniquement conforme aux conditions du service. Location : démarrage explicite, confirmation tarif, synchronisation sécurisée des assets, exécution, récupération des résultats, arrêt automatique vérifié ; provision pour temps de chargement et stockage facturable. Prévoir tableau de bord dépenses réelles et alertes.

Model Registry : téléchargement depuis sources officielles, checksum, licence, révision, taille, VRAM, exigences, benchmark, compatibilité avec plugins et moteur. Installer/désinstaller/versionner sans altérer projets anciens. Adaptateurs standards pour les moteurs, pas d'hypothèse que tous acceptent la même API.

## 13. Interface, navigation et mobile

Navigation : Tableau de bord ; Projets ; Images ; Personnages ; Vidéo ; Voix ; Storyboard ; Montage ; Automatisation ; Bibliothèque ; Modèles/GPU ; Budget ; Paramètres. Recherche globale par personnage/projet/tag. Interface responsive avec actions lourdes accessibles depuis mobile ; montage précis de préférence sur écran large. Notifications progression, files de tâches, coût, échec, validations. Accessibilité clavier, contrastes, textes lisibles, états explicites. Localisation FR initiale, AR RTL complète et EN en option ; respect des signes diacritiques arabes.

UX : aucun bouton factice ; toute action affiche disponibilité réelle du modèle, backend, coût estimé, temps estimé, paramètres et statut. Prévisualisation/proxy avant haute qualité. Workflow novice avec assistants, workflow expert avec paramètres avancés.

## 14. API et contrats techniques

API REST versionnée /api/v1 : POST /projects ; GET /projects/{id} ; POST /assets/upload ; POST /characters ; POST /characters/{id}/references ; GET /models ; POST /jobs ; GET /jobs/{id} ; POST /jobs/{id}/cancel ; POST /workflows ; POST /workflows/{id}/run ; GET /budgets/{projectId} ; POST /exports. SSE ou WebSocket pour job.progress, job.completed, job.failed, review.required, budget.warning.

JobRequest schéma : project_id, task_type, input_asset_ids, character_ids, model_id, model_version, backend_preference, parameters, max_cost, idempotency_key. JobResult : job_id, status, output_asset_ids, model_version, runtime_sec, gpu_sec, actual_cost, warnings, logs_ref. Auth par session sécurisée ou jetons de courte durée ; validation stricte des entrées, limites de taille et anti-traversée de chemins. Les adaptateurs GPU implémentent probe(), estimate(), prepare(), execute(), cancel(), cleanup().

## 15. Sécurité, confidentialité et droits

Accès authentifié, TLS pour accès distant, chiffrement des secrets au repos, gestion des clés fournisseur, droits par projet, journal d'audit, protection contre uploads malveillants, limites fichiers, séparation workers, validation des commandes FFmpeg, mises à jour dépendances. Les fichiers locaux restent privés par défaut. Synchronisation Google Drive avec OAuth et permissions minimales ; consentement utilisateur avant envoi d'images, voix ou documents vers GPU tiers.

Respect des licences des modèles et de leurs poids ; vérifier usage commercial, attribution, restrictions géographiques, données d'entraînement et distribution. Gestion des autorisations de voix et visages réels. Politique de rétention, suppression et export des données. Sauvegardes chiffrées si sensibles, tests de restauration.

## 16. Performance, qualité, coûts et observabilité

Mesures obligatoires : latence premier résultat, latence à chaud, durée totale, temps de chargement modèle, temps de transfert, coût par génération, taux de succès, taux de régénération, scores de cohérence, consommation mémoire. Cibles initiales indicatives à confirmer par benchmark : voix courte quelques secondes à chaud ; image aperçu en dizaines de secondes sur GPU adapté ; vidéo courte en minutes sur GPU adapté. Aucun SLA chiffré universel avant choix matériel/modèle.

Définir budget maximum projet/session, budget prévisionnel avant lancement, réserve pour échecs et interruptions, alertes 50/80/100 %, arrêt automatique des GPU loués avec confirmation de l'état réel. Tableau comparatif qualité/temps/coût par moteur. Logs structurés sans contenu sensible en clair, métriques, traces et export diagnostic. Benchmarks reproductibles avec même seed, même prompt, même GPU et version de modèle.

## 17. Tests et critères de recette

Tests unitaires : modèles de données, transitions de statuts, plafonds budget, calcul dépendances, permissions. Intégration : création projet, upload, génération réelle, réception asset, reprise, annulation, export. E2E : parcours navigateur desktop/mobile. Robustesse : coupure réseau, Colab déconnecté, GPU indisponible, disque plein, modèle absent, mauvaise licence, export interrompu, redémarrage serveur. Sécurité : accès non autorisé, upload malveillant, exposition clés, API sans TLS.

Recette R01 : application démarre sur Windows sans GPU dédié. R02 : projet créé, sauvegardé, restauré et synchronisé si activé. R03 : génération image réelle sur worker distant et import du résultat. R04 : personnage identifiable sur série de 10 images évaluées humainement. R05 : animation de 5 secondes et contrôle identité. R06 : TTS arabe/français et écoute validée. R07 : timeline exporte MP4 lisible. R08 : workflow 3-5 min reprend après interruption sans refaire tâches réussies. R09 : dépassement budget bloqué sans accord. R10 : GPU loué s'arrête après tâche et coût tracé. R11 : accès mobile sécurisé. R12 : aucune action UI annoncée comme fonctionnelle si moteur absent.

## 18. Phasage, livrables et gouvernance du développement

Phase 0 — cadrage/inventaire : diagnostic PC, choix stockage, limites budgétaires, licences, benchmark de 2 moteurs images et 1 moteur TTS ; livrable matrice de décision et architecture validée. Phase 1 — socle : repo, backend, UI, base, projets/assets, authentification, tâches, journal, tests CI, sauvegardes. Phase 2 — images/personnages : moteurs et Character Lock, QC et benchmark. Phase 3 — voix/vidéo : TTS AR/FR, animation courte, lip-sync si validé. Phase 4 — storyboard/montage : timeline, FFmpeg, exports. Phase 5 — orchestration longue : workflows, reprise, budget, vidéo 3-5 min puis 15/30 min. Phase 6 — mobilité et durcissement : PWA, accès sécurisé, backups, documentation.

Livrables à chaque phase : code source versionné, instructions d'installation, migrations, tests automatisés, démonstration de génération réelle, captures, manuel utilisateur, liste dépendances/licences, mesures qualité/temps/coût, problèmes connus, procédure de rollback. Revue humaine avant chaque phase suivante. Ne pas engager location GPU avant estimation et autorisation.

## 19. Structure de dépôt proposée

apps/web/ (React PWA) ; apps/desktop/ (Tauri éventuel) ; services/api/ (FastAPI) ; services/orchestrator/ ; services/workers/ ; packages/contracts/ ; packages/ui/ ; adapters/image/ ; adapters/video/ ; adapters/tts/ ; adapters/gpu/ ; workflows/templates/ ; infra/local/ ; infra/remote/ ; migrations/ ; tests/unit/ ; tests/integration/ ; tests/e2e/ ; docs/architecture/ ; docs/operations/ ; scripts/diagnostics/.

Qualité code : formatters, lint, typage statique, revue PR, CI, tests sur mocks puis GPU réel, verrouillage dépendances, SBOM si possible. Toute intégration de modèle doit avoir adapter, test de fumée, documentation licence/VRAM et profil benchmark.

## 20. Décisions ouvertes et annexes de réalisation

À confirmer : CPU/RAM/stockage/OS exact du PC de bureau, présence et type de circuit graphique intégré, débit Internet montant/descendant, budget mensuel maximal, espace Google Drive, accès mobile uniquement sur réseau domestique ou partout, qualité cible 1080p/4K, priorité arabe/français, droits de voix/personnages, usage commercial éventuel. Ces inconnues ne bloquent pas la conception modulaire.

Annexe A — Definition of Done : code testé, démonstration réelle, métriques mesurées, coûts expliqués, gestion erreurs, documentation et procédure de retour arrière. Annexe B — Politique de modèles : source officielle, licence vérifiée, version figée, compatibilité prouvée, coût benchmarké, fallback défini. Annexe C — Règle produit : qualité, identité, vitesse et coût doivent être évalués ensemble ; aucun moteur ne devient défaut sur simple réputation.

