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

## Mise à jour 0.2

- 15 tests API, sauvegarde et migration : réussis. Les nouveaux cas vérifient les conflits de versions, la conservation des anciennes fiches, les références au bon projet, les doublons, l’export de l’historique et la mise à niveau répétée d’une vraie base v1 avec conservation des données d’authentification.
- Build TypeScript/Vite : réussi.
- Parcours navigateur étendu : édition du projet et du personnage, consultation des deux historiques, association d’une image approuvée. Les vérifications existantes desktop/mobile restent réussies, sans erreur JavaScript.
- Sauvegarde hors ligne de la base réelle effectuée avant migration dans /workspace/shared/studio-backups/pre-v02-20261021. La sauvegarde reste hors Git et ne contient pas les données temporaires des tests.
- Windows et accès mobile distant restent non testés. La génération IA est toujours indisponible.

## Version 0.3 — vérifications finales

- **29 tests passés, aucun ignoré** sur l'environnement Linux avec FFmpeg/FFprobe disponibles. Export H.264 720p avec audio et durée vérifiée ; reprise après média absent ; redémarrage de worker réutilisant les segments sans les recalculer ; import PDF/DOCX ; restauration ZIP et refus de corruption/traversée ; contrat Colab, jetons, doublons et provenance.
- Build TypeScript/Vite réussi. Dépendances Python verrouillées réinstallées avec succès. Code du lanceur et cellules du notebook compilés syntaxiquement.
- E2E Chromium réussi, aucune erreur JavaScript : parcours précédent + storyboard → montage → téléchargement d'un vrai MP4, restauration d'un projet ZIP, contrôles Colab, activation PWA et absence de cache API privé, navigation mobile.
- Le test du contrat Colab utilise des images synthétiques. **Il ne démontre pas une génération IA**. Le notebook n'a pas tourné sur le GPU du propriétaire.
- Serveur réel redémarré en version 0.3.0, santé OK, shell compilé servi en HTTP local, accès propriétaire non initialisé (le propriétaire choisira lui-même son mot de passe). Données de test séparées et supprimées après les tests.
- Sauvegarde hors ligne vérifiée conservée dans `/workspace/shared/studio-backups/pre-v03-offline-20261021` ; anciennes sauvegardes préservées. Le dépôt d'arabe reste sans modification.
- Windows physique, qualité/latence des trois modèles Colab, VRAM, film de 30 minutes, licences actuelles, accès mobile distant et restauration d'un nouveau snapshot cloud restent non validés.
