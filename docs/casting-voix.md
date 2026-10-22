# Casting vocal personnel FR / AR

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

Ouvrir `AI_Production_Studio_Casting_Voix_FR_AR.ipynb` dans la session L4 existante. L'installation utilise deux environnements Python séparés. Aucun abonnement supplémentaire ni clé API n'est nécessaire ; la session consomme toujours ses unités Colab. Le notebook génère un candidat à la fois, sans boucle sur tout le catalogue.

1. Choisir un profil et une variante. Qwen3-TTS VoiceDesign génère une référence **fictive en français**, sans demander l'enregistrement d'une personne réelle. Qwen ne prend pas directement en charge l'arabe.
2. Écouter la référence. Pour auditionner un autre candidat, changer la variante ; conserver les fichiers du candidat retenu.
3. Chatterbox réutilise cette même référence pour une réplique FR ou AR. Passer d'une langue à l'autre avec LANGUE, sans recréer la référence. Comparer naturel, âge perçu, identité, accent, harakat et intégralité des phrases. Le transfert FR→AR peut modifier identité et accent ; il reste expérimental.
4. Télécharger `voix-fictive.zip` après audition. Il conserve la référence WAV, son empreinte, l'intention de timbre, la variante, la révision Qwen, puis la révision Chatterbox et les empreintes des auditions. Les états restent « À écouter » : la génération ne vaut pas approbation.
5. Aux sessions suivantes, choisir « Réutiliser une voix sauvegardée » et téléverser ce ZIP. Le notebook ne régénère pas le timbre ; il vérifie l'empreinte et réutilise la révision Chatterbox enregistrée. La seed seule n'est pas un verrou d'identité.

Dans le studio actuel, importer les WAV de répliques comme médias. Le champ de voix de la fiche personnage peut conserver le code et la variante retenus ; conserver également le ZIP de référence. **Le sélecteur de casting, l'association structurée d'une référence à un personnage et l'envoi direct à Colab ne sont pas encore intégrés à l'interface.** Le ZIP de voix sert à ce notebook, pas à « Restaurer un projet ZIP » ni à l'import de résultat MMS. Il n'entre pas automatiquement dans les sauvegardes du studio.

## Validation et limites

Le 22 octobre 2026 : installations et imports réels de Qwen 0.1.1 et Chatterbox 0.1.7 réussis sous Python 3.11.17 séparés ; attention SDPA reconnue par le code Qwen, aucun FlashAttention ajouté. Cellules compilées. Tests des archives : conservation exacte du WAV et de la révision, refus de corruption, fichier factice et chemins inattendus, non-écrasement ; textes FR/AR conservés et langues invalides refusées.

La création Qwen sur L4, la variation des 16 timbres et leur transfert FR/AR **ne sont pas validés par ces tests**. Il faut commencer par une référence. Même référence, seed et révision ne garantissent pas une identité parfaite entre textes et langues. Aucune promesse de diction parfaite, d'âge exact ou de stabilité absolue. Les vérifications de tokens Chatterbox ne prouvent pas la bonne réalisation des voyelles.

Les poids Qwen sont téléchargés depuis leur dépôt officiel à une révision figée, avec fichiers safetensors et configuration ; Chatterbox conserve ses chargements `weights_only=True` et son filigrane natif. La référence originale est toujours conservée. Les archives sont limitées et leurs chemins ne sont pas extraits librement. Aucun GPU n'est loué par le code, aucun port public n'est ouvert et aucune application voisine n'est modifiée.
