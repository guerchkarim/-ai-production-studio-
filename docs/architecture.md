# Architecture du socle

Le navigateur React appelle `/api/v1` à travers le proxy Vite. FastAPI porte les validations et l'authentification. SQLite est la source de vérité, les médias sont adressés par SHA-256 dans un dossier privé. Les UUID sont indépendants des noms de fichiers. Les métadonnées Unicode et dates UTC sont conservées.

Schéma v1 : projects, assets, characters, jobs, settings, sessions, audit. Les clés étrangères empêchent les références à un projet absent. Aucune suppression destructive n'est exposée. Les générations ne sont pas exécutées : le seul état initial de tâche est `blocked`, puis `canceled` à la demande. Les coûts réels restent nuls car il n'existe aucun adaptateur. Les plafonds sont validés côté API.

La frontière de calcul est volontairement absente du socle plutôt que simulée. Les prochains adaptateurs implémenteront probe/estimate/prepare/execute/cancel/cleanup. Une queue active, le budget réservé cumulé, l'idempotence et la reprise d'exécution ne devront être annoncés qu'après leur implémentation et leurs essais.

Les fichiers d'authentification et médias sont exclus des commits. Le script de sauvegarde vérifie l'intégrité et refuse tout écrasement. L'accès distant est hors périmètre du socle, pas simplement activable par ouverture d'un port.
