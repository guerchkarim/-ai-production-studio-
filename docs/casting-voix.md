# Casting vocal personnel FR / AR

## Utilisation entièrement dans Colab

Pour créer les voix sans installation Windows, utiliser `notebooks/AI_Production_Studio_Colab.ipynb` : choisir la L4, exécuter les trois cellules et connecter Drive, puis utiliser le panneau **Mon studio de voix** en bas. Choisir le profil, la variante (1 puis 2 pour votre sélection actuelle), les langues et cliquer **Créer et enregistrer**. Les lecteurs apparaissent et le dossier Drive reçoit automatiquement WAV, JSON, référence réutilisable et catalogue, sans téléchargement manuel. Les références déjà sauvegardées pour le profil/numéro sont réutilisées ; si plusieurs existent, la dernière sauvegardée est indiquée et reprise. Rien n’est envoyé automatiquement à cette conversation ou au logiciel Windows.

Validation : cellules compilées ; simulation du bouton avec deux variantes FR/AR, réutilisation de référence et inventaire Drive simulé réussie, sans modèles ni GPU. Widgets, connexion Drive et génération dans cette interface restent à valider dans Colab. Les moteurs de base ont été essayés dans les notebooks précédents. La session doit rester active pendant le calcul ; le programme ne peut pas créer de voix après arrêt de Colab.

## Import automatique dans AI Production Studio 0.4

L'écran **Voix** contient un casting indépendant des projets : profil, variante, références et répliques FR/AR, lecteurs audio, fiches JSON et choix « Retenir cette voix ». Une réplique peut ensuite être ajoutée au projet sélectionné pour le montage. Les anciens médias audio restent accessibles et les voix entrent comme candidates, sans sélection automatique.

La première fois, régler le dossier d'arrivée dans cet écran. Deux possibilités :

- Dans Chrome, **Paramètres → Téléchargements**, choisir comme destination le dossier affiché par le Studio ; activer les téléchargements automatiques de Colab. Le notebook de casting 0.4 produit des ZIP `Studio-Voix-...zip`, importés pendant que le logiciel reste ouvert.
- Avec Google Drive pour ordinateur déjà configuré, sélectionner la copie **locale** de `AI Production Studio/Voix` comme dossier surveillé. Un dossier qui existe seulement dans le Drive monté par Colab n'est pas accessible directement au PC.

Le ZIP arrive au navigateur ou via la synchronisation. Le Studio ne contrôle ni Colab, ni le navigateur, ni Drive à distance. Si le Studio est fermé, les paquets attendent dans ce dossier et sont traités au redémarrage. Les fichiers en cours de copie attendent deux observations stables, les `.crdownload` sont ignorés et les paquets déjà classés ne créent pas de doublons. Les anciens WAV ne sont pas remplacés. Les paquets erronés restent dans le dossier ; leur erreur est visible dans l'écran Voix.

Les références, métadonnées, répliques et paquets source sont conservés dans `.studio-data`. La sauvegarde complète hors ligne les inclut ; un export ZIP de projet inclut seulement les répliques ajoutées à ce projet. Les anciennes copies manuelles dans cette conversation ne deviennent pas automatiquement des voix de ce casting : elles restent conservées séparément.

### Appliquer la mise à jour Windows une seule fois

Fermer la fenêtre serveur du Studio avec Ctrl+C. Télécharger puis extraire le ZIP source de la dernière version GitHub dans un **nouveau dossier**. Dans ce nouveau dossier, ouvrir `Mettre-a-jour-Studio.cmd`, puis choisir le dossier habituel du Studio, celui qui contient `package.json` et `Lancer-Studio.cmd`. L'assistant vérifie qu'il s'agit bien de `ai-production-studio`, sauvegarde les données et les anciens fichiers de code avant copie, préserve `.studio-data`, `.env`, les projets et le mot de passe. Il refuse le dépôt d'évaluation d'arabe et un serveur encore ouvert. Relancer ensuite `Lancer-Studio.cmd` dans le dossier habituel. Le lanceur sauvegarde avant la migration additive du schéma 4 vers 5 et reconstruit l'interface.

Télécharger ensuite le notebook compatible depuis l'écran Voix et l'importer dans Colab : une copie déjà présente dans Drive ne se met pas à jour automatiquement depuis GitHub. Une fois le dossier d'arrivée réglé et Colab connecté, chaque nouvelle création/téléchargement compatible arrive au casting sans envoi de WAV et JSON un par un dans cette conversation.

Le besoin est double : auditionner plusieurs timbres/âges et conserver une identité vocale réutilisable par personnage. Les essais déjà appréciés sont Kokoro pour une voix française et Chatterbox pour une voix arabe. Ils ne constituent pas un catalogue d'enfants/adultes/seniors.

Le fichier `catalogue-voix-cibles.json` décrit **16 profils à créer**, chacun à auditionner en français et en arabe. Aucun profil n'est déclaré disponible ou validé sans audio. Chaque profil peut avoir plusieurs variantes.

| Intention d'âge perçu | Timbre féminin | Timbre masculin |
|---|---|---|
| Petite enfance, environ 5 ans | F-petit | M-petit |
| Enfant, environ 10 ans | F-enfant | M-enfant |
| Adolescent, environ 15 ans | F-ado | M-ado |
| Jeune adulte, environ 20 ans | F-20 | M-20 |
| Adulte, environ 30 ans | F-30 | M-30 |
| Adulte, environ 40 ans | F-40 | M-40 |
| Adulte, environ 50 ans | F-50 | M-50 |
| Senior, environ 70 ans | F-senior | M-senior |

Ces âges sont des descriptions de timbre, pas des âges exacts garantis. Le timbre ne prouve ni l'âge ni le genre d'une personne. Modifier uniquement la hauteur d'une même voix ne remplit pas ce besoin.

## Essai dans Colab

### Rangement automatique

La version du 23 octobre sauvegarde automatiquement chaque création et chaque réplique dans **Mon Drive / AI Production Studio / Voix**. Google Colab demande l'autorisation de connecter Drive au premier lancement. Une fois connecté, aucun téléchargement manuel n'est nécessaire. Chaque dossier porte le profil, la variante et une courte empreinte de référence pour éviter de mélanger deux créations : `M-petit_var1_ab12cd34ef56`. WAV et JSON sont nommés ensemble ; les répliques FR/AR et leurs prises sont numérotées, sans remplacer les anciens WAV. Le catalogue `catalogue_voix.json` est actualisé à chaque sauvegarde. Le sous-fichier `voix-fictive.zip` reste utilisable pour retrouver ce timbre.

`TELECHARGER_AUTOMATIQUEMENT`, activé par défaut en 0.4, ajoute un téléchargement ZIP du dossier à chaque étape. Chrome choisit sa destination selon ses réglages ; un notebook ne peut pas créer ou remplir librement un dossier Windows. Si Drive est désactivé, la copie locale Colab est éphémère et il faut conserver les ZIP. L'assistant n'a pas d'accès automatique à votre Drive ni aux fichiers créés dans une autre session : l'archivage est effectué par le notebook, pas par une surveillance de cette conversation. L’import dans Windows nécessite le dossier d’arrivée configuré comme décrit plus haut.

Tests locaux : nommage des WAV/JSON, ZIP de référence réutilisable, répétition sans doublon, conservation des anciennes prises, index FR/AR, refus de checksum incorrect et de profil traversant les chemins. La connexion effective Drive et les téléchargements du navigateur restent à tester dans la session Colab du propriétaire.

Ouvrir `AI_Production_Studio_Casting_Voix_FR_AR.ipynb` dans la session L4 existante. L'installation utilise deux environnements Python séparés. Aucun abonnement supplémentaire ni clé API n'est nécessaire ; la session consomme toujours ses unités Colab. Le notebook génère un candidat à la fois, sans boucle sur tout le catalogue.

1. Choisir un profil et une variante. Qwen3-TTS VoiceDesign génère une référence **fictive en français**, sans demander l'enregistrement d'une personne réelle. Qwen ne prend pas directement en charge l'arabe.
2. Écouter la référence. Pour auditionner un autre candidat, changer la variante ; conserver les fichiers du candidat retenu.
3. Chatterbox réutilise cette même référence pour une réplique FR ou AR. Passer d'une langue à l'autre avec LANGUE, sans recréer la référence. Comparer naturel, âge perçu, identité, accent, harakat et intégralité des phrases. Le transfert FR→AR peut modifier identité et accent ; il reste expérimental.
4. Télécharger `voix-fictive.zip` après audition. Il conserve la référence WAV, son empreinte, l'intention de timbre, la variante, la révision Qwen, puis la révision Chatterbox et les empreintes des auditions. Les états restent « À écouter » : la génération ne vaut pas approbation.
5. Aux sessions suivantes, choisir « Réutiliser une voix sauvegardée » et téléverser ce ZIP. Le notebook ne régénère pas le timbre ; il vérifie l'empreinte et réutilise la révision Chatterbox enregistrée. La seed seule n'est pas un verrou d'identité.

Dans le studio 0.3, importer les WAV de répliques comme médias. En 0.4, les paquets compatibles sont classés dans le casting et leurs répliques peuvent être ajoutées au projet sélectionné. Le champ de voix de la fiche personnage peut conserver le code et la variante retenus ; conserver également le ZIP de référence. **L'association structurée d'une référence à un personnage et l'envoi direct à Colab ne sont pas encore intégrés à l'interface.** Le sous-ZIP voix-fictive.zip sert à ce notebook ; le paquet Studio-Voix est importable dans le casting 0.4, pas dans « Restaurer un projet ZIP » ni dans l’import de résultat MMS. Les paquets importés dans le casting entrent dans la sauvegarde complète du studio.

## Validation et limites

Le 22 octobre 2026 : installations et imports réels de Qwen 0.1.1 et Chatterbox 0.1.7 réussis sous Python 3.11.17 séparés ; attention SDPA reconnue par le code Qwen, aucun FlashAttention ajouté. Cellules compilées. Tests des archives : conservation exacte du WAV et de la révision, refus de corruption, fichier factice et chemins inattendus, non-écrasement ; textes FR/AR conservés et langues invalides refusées.

La création Qwen sur L4, la variation des 16 timbres et leur transfert FR/AR **ne sont pas validés par ces tests**. Il faut commencer par une référence. Même référence, seed et révision ne garantissent pas une identité parfaite entre textes et langues. Aucune promesse de diction parfaite, d'âge exact ou de stabilité absolue. Les vérifications de tokens Chatterbox ne prouvent pas la bonne réalisation des voyelles.

Les poids Qwen sont téléchargés depuis leur dépôt officiel à une révision figée, avec fichiers safetensors et configuration ; Chatterbox conserve ses chargements `weights_only=True` et son filigrane natif. La référence originale est toujours conservée. Les archives sont limitées et leurs chemins ne sont pas extraits librement. Aucun GPU n'est loué par le code, aucun port public n'est ouvert et aucune application voisine n'est modifiée.
