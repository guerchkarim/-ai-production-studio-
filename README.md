# AI Production Studio · Socle 0.1

Atelier personnel audiovisuel, en français. React/TypeScript + FastAPI + SQLite.
Ce dépôt est indépendant de `guerchkarim/-_-`. Aucune clé Gemini, autre clé API, carte bancaire ou GPU n'est nécessaire pour démarrer.

## Fonctionnalités de ce jalon

- Accès propriétaire par mot de passe (10 caractères minimum), hash scrypt, session HttpOnly de 12 heures.
- Projets persistants : langue, résolution, cadence et budget plafond.
- Import, recherche, filtrage, aperçu et téléchargement de médias (50 Mo maximum).
- SHA-256, déduplication des fichiers et contrôle des signatures PNG/JPEG/WebP/MP4/WebM/WAV/MP3/OGG.
- Fiches personnages en Unicode, avec description et intention de voix.
- Demandes image/vidéo/voix persistantes, explicitement **bloquées** sans moteur. Annulation disponible. Budget de tâche supérieur au projet refusé.
- Export ZIP de projet (manifeste JSON versionné + médias), audit de création/annulation et sauvegarde/restauration complète hors ligne.
- Interface responsive et statistiques issues des données réelles, sans données de démonstration.

## Installation et démarrage

Prérequis : Node.js 22+ et Python 3.12. Testé ici sous Linux avec Node 24 et Python 3.12. Les instructions Windows restent à valider sur le PC cible.

```bash
npm ci
python -m venv .venv
# Linux / macOS
.venv/bin/python -m pip install -r services/api/requirements.lock.txt
.venv/bin/python -m uvicorn services.api.main:app --host 127.0.0.1 --port 8001
```

Dans un deuxième terminal :

```bash
npm run dev -- --host 127.0.0.1
```

Ouvrir le port local **5174** dans son navigateur. Créer le mot de passe propriétaire au premier lancement. Aucune variable d'environnement obligatoire. Le proxy Vite transmet `/api` à l'API sur le port 8001.

Windows PowerShell : remplacer `.venv/bin/python` par `.venv\Scripts\python.exe`. Le chemin Python fonctionne indépendamment de l'activation du venv.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r services/api/requirements.lock.txt
.venv\Scripts\python.exe -m uvicorn services.api.main:app --host 127.0.0.1 --port 8001
# Deuxième terminal
npm ci
npm run dev -- --host 127.0.0.1
```

Les données se trouvent dans `.studio-data/` (ignoré par Git). `STUDIO_DATA_DIR` permet de changer cet emplacement avant de lancer l'API. Garder cet emplacement stable entre les lancements. La création du schéma v1 est idempotente ; les futures évolutions nécessiteront de nouvelles migrations.

## Vérification

```bash
npm run build
.venv/bin/python -m unittest discover -s tests -v
```

Tests navigateur (Chromium système ou navigateur Playwright) :

```bash
npx playwright install chromium
npm run test:e2e
```

Le runner démarre ses propres serveurs sur 5175/8002, utilise une base temporaire, puis arrête ces processus. Il vérifie le parcours projet/personnage/média/tâche, les plafonds, l’export ZIP, la persistance après rechargement et la navigation mobile. Les captures et le ZIP de test sont dans `.studio-test-output/` (ignoré par Git). `PLAYWRIGHT_CHROMIUM_EXECUTABLE` permet de choisir un Chromium installé. Aucun jeu de données de test n’est écrit dans votre studio.

API de santé : `GET /api/v1/health`. Données : `GET /api/v1/studio` (session nécessaire). Contrats interactifs FastAPI : `/docs` sur le serveur API.

## Sauvegarde et restauration

**Arrêter l'API avant copie.** Une sauvegarde contient les médias, le mot de passe haché, les projets et l'audit. La conserver dans un emplacement privé, chiffré si nécessaire. Ne jamais la committer.

```bash
.venv/bin/python scripts/backup.py backup /chemin/prive/studio-backup
# Restauration dans un nouveau répertoire uniquement, sans écrasement :
.venv/bin/python scripts/backup.py restore /chemin/prive/studio-backup --data /chemin/prive/studio-restaure
# Puis démarrer l'API avec STUDIO_DATA_DIR pointant vers ce répertoire.
```

Le script vérifie SQLite et les SHA-256. Les sessions sont supprimées à la restauration ; le mot de passe existant est conservé. L'export ZIP par projet est portable et ne contient pas les identifiants. L'import/restauration de ce ZIP dans l'UI n'est pas encore implémenté.

## Limites explicites

Aucun moteur IA, fournisseur GPU ou service payant n'est intégré. Aucune image, voix ou vidéo n'est générée. Les demandes bloquées ne démarrent pas automatiquement. Le registre de modèles montre des candidats à évaluer, pas des modèles installés. Les personnages n'ont pas encore de références multi-vues, de versions éditables ni de Character Lock. Les fiches/projets sont créables et consultables ; modification et suppression ne font pas partie de ce jalon.

Pas encore de timeline, montage, export MP4, workflow DAG, synchronisation Drive, connexion Colab, PWA, multi-utilisateurs ou interface RTL complète. Ce jalon ne revendique pas les recettes GPU R03–R10 du cahier des charges.

**Usage local uniquement à ce stade.** Ne pas exposer Vite ou l'API sur Internet. L'initialisation du propriétaire s'effectue sans compte préalable : elle doit rester en boucle locale. Le déploiement distant nécessitera HTTPS, contrôle du bootstrap, limitation des tentatives de connexion et reverse proxy de production. Pas de mécanisme de récupération de mot de passe dans l'UI.

L’interface utilise les polices système, sans CDN ni requête de police externe. Aucun fichier utilisateur n’est envoyé à un moteur IA.

Le ZIP d'export est construit en mémoire : utiliser la sauvegarde hors ligne pour les projets volumineux. Les signatures médias sont une protection de base, pas une analyse antivirus ni une validation complète de décodage.

## Suite proposée

Valider ce socle avec le propriétaire. Ensuite : diagnostic du PC, choix du stockage et des budgets, références personnages, adaptateur image distant et benchmark réel avec contrôle licence/coût. Aucune location GPU sans autorisation explicite.
