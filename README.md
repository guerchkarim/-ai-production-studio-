# AI Production Studio · 0.3

## Mise à jour 0.4 : casting vocal automatique

Les paquets de création Colab arrivent dans le casting **Voix** depuis un dossier surveillé sur le PC. WAV et JSON sont classés par profil/variante, restent candidats et peuvent être écoutés puis retenus. Une réplique peut rejoindre le projet sélectionné. Le Studio doit être ouvert et le navigateur doit télécharger ses paquets dans ce dossier, ou Drive doit les synchroniser localement. Aucun accès direct du Studio à votre Colab privé n’est installé.

Pour mettre à jour une installation Windows existante : fermer le serveur, télécharger/extracter les sources dans un nouveau dossier, lancer `Mettre-a-jour-Studio.cmd` et choisir le dossier habituel. Les données et l’ancien code sont sauvegardés avant copie ; le dépôt d’arabe est refusé. Voir [les instructions de casting](docs/casting-voix.md).


Atelier audiovisuel personnel, React/TypeScript + FastAPI + SQLite + FFmpeg. Dépôt indépendant de votre application d'évaluation d'arabe. Le serveur écoute uniquement en boucle locale. Aucune clé Gemini, carte bancaire ou souscription n'est nécessaire pour démarrer.

## Démarrer sur Windows

Installez Python 3.12+ et Node.js LTS 22+, puis double-cliquez sur **Lancer-Studio.cmd**. Le premier lancement installe les dépendances verrouillées, compile l'interface et ouvre votre navigateur. Créez votre mot de passe propriétaire au premier accès. Le serveur doit rester ouvert.

FFmpeg et FFprobe sont nécessaires aux exports MP4 (avec encodeurs libx264 et AAC). Sans eux, les projets, scénarios, médias et personnages restent disponibles. [Guide Windows](docs/installation-windows.md).

Les tests ont été exécutés sous Linux avec Node 24 et Python 3.12, pas sur votre PC Windows physique. L'accès mobile distant nécessite un déploiement HTTPS authentifié séparé ; publier l'environnement Codex n'héberge pas une application publique et ne l'installe pas sur votre PC.

## Fonctions disponibles

- Accès propriétaire par mot de passe, hash scrypt et session HttpOnly de 12 heures. Projets, budgets et personnages modifiables, avec historique et conflits de versions contrôlés.
- Import privé de médias, SHA-256, déduplication, signatures de formats, aperçu et téléchargement. Références de personnages par vue, avec approbation au moment de l'ajout.
- Scénarios FR/AR : saisie, import TXT/Markdown, extraction locale PDF/DOCX, découpage déterministe par paragraphes. Le PDF scanné nécessite un OCR non intégré.
- Storyboard : plans éditables, durées, médias associés et approbation humaine. Les durées de narration estimées restent indicatives.
- Montage séquentiel : images/vidéos, durée, point d'entrée vidéo, ordre des clips, bande sonore optionnelle. Les sources et les versions sauvegardées sont conservées ; le retrait d'un clip demande confirmation.
- **Export réel MP4 H.264 720p / 24 i/s sur CPU**, jusqu'à 200 clips et 30 minutes par montage. Aucun benchmark de film de 30 minutes n'a encore été réalisé. Le son des vidéos source est retiré ; la bande sonore choisie est complétée par du silence ou coupée à la durée du film. Pas de transitions complexes, sous-titres, overlays ou timeline multipiste dans cette version.
- File persistante de rendus, progression, annulation, reprise manuelle d'un export échoué/annulé. Après redémarrage, les rendus interrompus reprennent leur file et réutilisent les segments déjà vérifiés. Utiliser **un seul processus Uvicorn** avec ce worker intégré.
- ZIP portable par projet : médias, fiches, historique, scénario, storyboard, montage et provenance des générations. **Restauration en nouveau projet**, nouveaux UUID, contrôle des chemins et des checksums, sans écraser l'original. Les anciennes tâches ne sont jamais relancées automatiquement ; l'ancien manifeste est conservé en provenance de l'import.
- Interface responsive et shell PWA installable depuis une origine sécurisée ou localhost. Le service worker ne met en cache ni API, ni session, ni média privé. Sans liaison avec le serveur, les opérations privées sont indisponibles : pas de modification hors ligne du projet.

## Utiliser votre session Colab

Dans **Tâches**, enregistrez une demande image, vidéo ou voix. Choisissez **Exporter pour Colab**, puis téléchargez le notebook depuis la même page. Dans votre session Colab, importez le notebook et exécutez les cellules, puis importez le JSON de demande. Lisez la licence du modèle et approuvez l'utilisation de votre session avant le calcul. Réimportez le fichier `resultat-studio.zip` dans la tâche.

[Notebook fourni](notebooks/AI_Production_Studio_Worker.ipynb) · [Guide Colab](docs/colab.md).

L'échange par fichiers est implémenté et testé. **Le notebook n'a pas été exécuté sur GPU depuis Codex.** Les modèles sont des candidats à valider dans votre session : SDXL pour images, Wan 2.1 1.3B pour vidéo, MMS-TTS FR/AR (non commercial) pour voix. Le chargement est figé à une révision officielle au moment de l'exécution et utilise safetensors. La disponibilité des poids dans ce format, les licences actuelles, la compatibilité mémoire, la qualité et la latence doivent être confirmées par vos essais. Pas de garantie d'identité, de prononciation, de lip-sync ou de performance universelle.

Aucun port du studio n'est exposé à Colab, aucun fichier n'y est envoyé automatiquement, aucun GPU n'est loué. Le JSON et le ZIP contiennent des données de production et un jeton d'association : gardez-les privés. Le token est haché dans la base et exclu des exports de provenance. Le coût d'un éventuel abonnement Colab n'est pas mesuré ni limité automatiquement par le budget local. Aucun service de paiement n'est intégré.

## Installation manuelle / développement

```bash
npm ci
python -m venv .venv
.venv/bin/python -m pip install -r services/api/requirements.lock.txt
npm run build
.venv/bin/python -m uvicorn services.api.main:app --host 127.0.0.1 --port 8001
```

Le serveur API sert aussi l'interface compilée sur le port local 8001. Pour développer le frontend, lancez `npm run dev` dans un autre terminal : Vite sur 5174 transmet `/api` à 8001. Sur Windows, remplacez `.venv/bin/python` par `.venv\Scripts\python.exe`.

Données : `.studio-data/`, ignoré par Git. `STUDIO_DATA_DIR` permet de changer l'emplacement avant démarrage. `STUDIO_TRUSTED_ORIGINS` permet de définir les origines autorisées pour un proxy local ; ne pas utiliser de wildcard. Aucun secret fournisseur obligatoire.

## Vérifications

```bash
npm run build
.venv/bin/python -m unittest discover -s tests -v
npx playwright install chromium
npm run test:e2e
```

Le runner E2E utilise sa propre base temporaire et ses propres serveurs 5175/8002, qu'il arrête ensuite. Il couvre édition/historique, médias, tâches, storyboard, vrai MP4, restauration ZIP, confidentialité des caches PWA et navigation mobile. `PLAYWRIGHT_CHROMIUM_EXECUTABLE` sélectionne un Chromium installé. Artifacts : `.studio-test-output/`, ignoré par Git. Les tests Colab valident uniquement le contrat de fichiers avec des données synthétiques, pas les modèles IA.

Santé API : `/api/v1/health`. Contrats API : `/docs`. Les routes de données et de médias nécessitent une session.

## Sauvegarder sans perte

Arrêtez l'API avant sauvegarde ou restauration. Le dossier sauvegardé contient les médias, la base et le mot de passe haché : conservez-le en privé, chiffré si nécessaire. Le script vérifie SQLite et les SHA-256 et refuse tout écrasement ou copie dans le dossier source.

```bash
.venv/bin/python scripts/backup.py backup /chemin/prive/studio-backup
.venv/bin/python scripts/backup.py restore /chemin/prive/studio-backup --data /chemin/prive/studio-restaure
```

Redémarrez ensuite avec STUDIO_DATA_DIR pointant vers le dossier restauré. Les sessions sont invalidées, le mot de passe est conservé. La migration du schéma v1/v2 vers v4 ajoute les tables et préserve les données existantes. Le ZIP par projet reste une autre option de restauration, sans identifiants de connexion.

## Limites et prochains contrôles

Usage local personnel uniquement à ce stade. L'initialisation propriétaire doit rester en boucle locale ; ne publiez pas Vite ou l'API sur Internet. Un accès distant exige HTTPS, contrôle du bootstrap, limitation des connexions et reverse proxy de production. Pas de récupération de mot de passe dans l'UI.

Non implémentés : synchronisation Google Drive, GPU loué, adaptateur de modèle exécuté automatiquement en continu, benchmark réel de Character Lock, lip-sync, clonage de voix, montage professionnel multipiste, interface AR RTL complète, partage multi-utilisateur et automatisation IA de films longs sans supervision. Les modèles Colab restent expérimentaux jusqu'à vos tests GPU. La suppression et la restauration d'une ancienne version de fiche dans l'UI sont hors périmètre.

Les exports ZIP sont construits en mémoire : utilisez la sauvegarde hors ligne pour les projets très volumineux. Un import ZIP accepte 100 Mo compressés / 500 Mo décompressés et ne relance aucun ancien calcul. Les signatures médias constituent un contrôle de base, pas un antivirus. Les logs FFmpeg restent privés dans le dossier de rendu ; les segments de reprise occupent du disque et ne sont jamais purgés sans action explicite.

Voir [matrice de recette](docs/recette.md), [validation](docs/validation.md) et [architecture](docs/architecture.md).
