# Architecture du socle

Le navigateur React appelle `/api/v1` à travers le proxy Vite. FastAPI porte les validations et l'authentification. SQLite est la source de vérité, les médias sont adressés par SHA-256 dans un dossier privé. Les UUID sont indépendants des noms de fichiers. Les métadonnées Unicode et dates UTC sont conservées.

Schéma v1 : projects, assets, characters, jobs, settings, sessions, audit. Les clés étrangères empêchent les références à un projet absent. Aucune suppression destructive n'est exposée. Les générations ne sont pas exécutées : le seul état initial de tâche est `blocked`, puis `canceled` à la demande. Les coûts réels restent nuls car il n'existe aucun adaptateur. Les plafonds sont validés côté API.

La frontière de calcul est volontairement absente du socle plutôt que simulée. Les prochains adaptateurs implémenteront probe/estimate/prepare/execute/cancel/cleanup. Une queue active, le budget réservé cumulé, l'idempotence et la reprise d'exécution ne devront être annoncés qu'après leur implémentation et leurs essais.

Les fichiers d'authentification et médias sont exclus des commits. Le script de sauvegarde vérifie l'intégrité et refuse tout écrasement. L'accès distant est hors périmètre du socle, pas simplement activable par ouverture d'un port.

## Évolution 0.2

Migration transactionnelle et idempotente vers le schéma 2 : version des projets/personnages, table revisions avec snapshots JSON immuables et table character_references. Les fiches v1 sont conservées avec version 1 et historique initial. Chaque PUT attend la version lue par le client ; une version périmée renvoie 409 et ne modifie rien. Les opérations d’édition sont sérialisées par transaction SQLite BEGIN IMMEDIATE.

Les références visuelles sont uniquement des images du même projet que le personnage. L’ajout est idempotent par personnage/image/vue. L’approbation éditoriale est enregistrée à l’ajout ; une tentative de changer cette approbation par réajout renvoie 409. Aucun modèle n’utilise encore ces références. L’export ZIP v2 inclut fiches, historique, références et médias.

Le budget d’un projet ne peut pas descendre sous les dépenses constatées ou le plus grand plafond de ses demandes actives. Ce contrôle ne constitue pas un mécanisme de réservation cumulée : toutes les tâches restent bloquées sans adaptateur.

## Production locale et Colab · 0.3

Schéma v3 : scripts, shots, timelines, production_history et renders. Le worker CPU intégré utilise un seul thread et un seul processus Uvicorn. Les modifications de scénario, plan et montage conservent des snapshots et contrôlent les versions. Les tâches de rendu conservent les médias/checksums au moment de leur soumission. Le serveur réinscrit les rendus interrompus dans la file au démarrage ; FFprobe vérifie chaque segment avant sa réutilisation. L'annulation est contrôlée pendant FFmpeg et avant la publication atomique du résultat dans SQLite.

FFmpeg s'exécute sans shell, avec chemins internes, protocoles file/pipe uniquement, options fixes et limites de temps. La résolution est explicitement 1280×720 / 24 i/s dans ce premier montage. L'audio source des clips est retiré ; une piste de bande sonore peut être ajoutée. Il ne s'agit pas d'un NLE multipiste complet. Le disque des caches ne se nettoie pas automatiquement, afin de ne supprimer aucun média ou checkpoint sans décision explicite.

Le restore ZIP vérifie chemins, liens, noms, tailles, types et SHA-256 avant la transaction de création. Il génère de nouveaux UUID et réassocie les références, plans et clips. Les médias identiques restent dédupliqués. Il ne restaure pas de session d'authentification ni de file d'exécution automatique. Le manifeste original reste en provenance privée de l'import. Les gros projets doivent préférer la sauvegarde hors ligne.

Schéma v4 : remote_runs. L'échange Colab est volontairement manuel et sans serveur public : paquet JSON exporté par le propriétaire, notebook exécuté dans sa session, résultat ZIP importé dans une tâche. Le jeton d'association est haché au repos ; le modèle déclaré, la révision, le type, le checksum et l'état de la tâche sont contrôlés. L'import identique est idempotent. La provenance déclarée du worker n'est pas une attestation d'exécution distante ; une revue humaine et un benchmark GPU restent requis.

Le notebook utilise uniquement des poids safetensors depuis les sources officielles, fixe une révision au moment de l'exécution et demande une validation de licence/session. Aucun pipeline n'a encore été exécuté sur GPU depuis Codex. Les métriques de temps sont renvoyées au studio, le coût propre à un abonnement Colab ne l'est pas. Aucun connecteur de location GPU n'est actif.

Le frontend compilé peut être servi par FastAPI sur le même port local. La PWA ne cache que le shell et les bundles, jamais les API, les sessions ou les médias. L'accès mobile distant exige une topologie HTTPS et un durcissement du bootstrap, pas seulement un manifeste PWA.
