# Architecture du socle

Le navigateur React appelle `/api/v1` à travers le proxy Vite. FastAPI porte les validations et l'authentification. SQLite est la source de vérité, les médias sont adressés par SHA-256 dans un dossier privé. Les UUID sont indépendants des noms de fichiers. Les métadonnées Unicode et dates UTC sont conservées.

Schéma v1 : projects, assets, characters, jobs, settings, sessions, audit. Les clés étrangères empêchent les références à un projet absent. Aucune suppression destructive n'est exposée. Les générations ne sont pas exécutées : le seul état initial de tâche est `blocked`, puis `canceled` à la demande. Les coûts réels restent nuls car il n'existe aucun adaptateur. Les plafonds sont validés côté API.

La frontière de calcul est volontairement absente du socle plutôt que simulée. Les prochains adaptateurs implémenteront probe/estimate/prepare/execute/cancel/cleanup. Une queue active, le budget réservé cumulé, l'idempotence et la reprise d'exécution ne devront être annoncés qu'après leur implémentation et leurs essais.

Les fichiers d'authentification et médias sont exclus des commits. Le script de sauvegarde vérifie l'intégrité et refuse tout écrasement. L'accès distant est hors périmètre du socle, pas simplement activable par ouverture d'un port.

## Évolution 0.2

Migration transactionnelle et idempotente vers le schéma 2 : version des projets/personnages, table revisions avec snapshots JSON immuables et table character_references. Les fiches v1 sont conservées avec version 1 et historique initial. Chaque PUT attend la version lue par le client ; une version périmée renvoie 409 et ne modifie rien. Les opérations d’édition sont sérialisées par transaction SQLite BEGIN IMMEDIATE.

Les références visuelles sont uniquement des images du même projet que le personnage. L’ajout est idempotent par personnage/image/vue. L’approbation éditoriale est enregistrée à l’ajout ; une tentative de changer cette approbation par réajout renvoie 409. Aucun modèle n’utilise encore ces références. L’export ZIP v2 inclut fiches, historique, références et médias.

Le budget d’un projet ne peut pas descendre sous les dépenses constatées ou le plus grand plafond de ses demandes actives. Ce contrôle ne constitue pas un mécanisme de réservation cumulée : toutes les tâches restent bloquées sans adaptateur.
