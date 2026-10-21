# Utiliser votre studio personnel sur Windows

1. Installez **Python 3.12 ou plus récent** depuis python.org (cochez l'ajout au PATH) et **Node.js LTS 22 ou plus récent** depuis nodejs.org.
2. Récupérez votre dépôt GitHub privé `guerchkarim/-ai-production-studio-` (Code → Download ZIP, ou clone Git), puis décompressez-le dans un dossier privé stable, par exemple Documents/AI-Production-Studio.
3. Pour les exports vidéo, installez **FFmpeg et FFprobe** depuis une distribution Windows référencée par ffmpeg.org, puis ajoutez leur dossier bin au PATH. Sans eux, l'organisation reste utilisable et le bouton de rendu est désactivé.
4. Double-cliquez sur **Lancer-Studio.cmd**. Le premier lancement installe les dépendances verrouillées et construit l'interface. Il nécessite Internet pour les gestionnaires de paquets. Le navigateur s'ouvre ensuite automatiquement.
5. Créez votre mot de passe personnel. Aucune clé IA ni carte bancaire n'est demandée.
6. Créez un projet, importez vos médias, préparez le scénario dans Storyboard, approuvez les plans avec médias, puis ouvrez Montage et exportez votre MP4.

Gardez la fenêtre du serveur ouverte. Ctrl+C permet un arrêt propre. Ne déplacez ou n'effacez pas `.studio-data` : ce dossier contient vos créations. Les mises à jour ne doivent pas écraser ce dossier. Sauvegardez-le avant mise à jour suivant le README.

Le serveur écoute uniquement sur votre PC. « Publier l'environnement » dans Codex n'installe pas l'application sur Windows et ne fournit pas une adresse d'application accessible à votre téléphone. L'accès mobile distant demande un déploiement HTTPS authentifié à organiser séparément.

Le lanceur est livré et sa logique portable est vérifiée par lecture et compilation Python ; l'exécution sur votre Windows physique reste à tester. Le script `scripts/windows/Diagnostic-PC.ps1` produit un inventaire sans lire vos fichiers personnels ni vos secrets et sans envoyer de données sur Internet. Il permettra de choisir les moteurs compatibles.
