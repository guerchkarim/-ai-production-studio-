# Validation du socle · 21 octobre 2026

Environnement vérifié : Linux, Node 24.19.0, Python 3.12.14, Chromium système, CPU. Aucune clé fournisseur ni GPU.

- `npm ci` : installation depuis le verrou npm réussie.
- Installation Python depuis `requirements.lock.txt` : réussie.
- `npm run build` : typage TypeScript et bundle Vite réussis.
- `python -m unittest discover -s tests -v` : **9 tests passés**, couvrant authentification, origine, Unicode/persistance SQLite, budgets, annulation, upload/signature, déduplication/export, sauvegarde/restauration sans écrasement et corruption de média.
- `npm run test:e2e` : parcours Chromium desktop et mobile réussi, aucune erreur JavaScript : création d'accès propriétaire et projet, fiche arabe/française, média et aperçu, rejet d'un plafond trop élevé, tâche bloquée, rechargement des données, annulation, téléchargement ZIP et navigation mobile. Base temporaire et processus indépendants, nettoyés après le test.
- Aucun fichier suivi modifié dans le dépôt voisin de l'application d'arabe.

Les captures utilisent uniquement des données de test. Le studio livré n'est pas prérempli et son mot de passe propriétaire n'est pas défini.

Non vérifié : Windows physique, accès mobile distant, restauration d'une nouvelle machine cloud et exécution GitHub Actions. Pas de génération IA réelle : les tests GPU et les benchmarks de qualité restent à effectuer dans les phases suivantes.
