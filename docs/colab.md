# Votre session Google Colab

L'application fonctionne sans Colab. Le notebook sert uniquement à vos calculs lourds ponctuels dans une session existante, sans connexion publique au studio.

1. Créer une demande dans **Tâches**, choisir Image/Vidéo/Voix et rédiger le prompt ou le texte. Fixer le plafond local.
2. Cliquer sur **Exporter pour Colab** et conserver le JSON en privé. Cliquer sur **Télécharger le notebook**.
3. Dans Google Colab, choisir **Fichier → Importer un notebook** et sélectionner `AI_Production_Studio_Worker.ipynb`. Pour image/vidéo, sélectionner votre session GPU disponible. Le code ne souscrit pas d'abonnement et ne réserve pas de GPU facturé.
4. Exécuter les cellules dans l'ordre, importer le JSON avec le sélecteur proposé, consulter les conditions du modèle. Cocher `APPROUVER_LICENCE_ET_SESSION` uniquement après vérification. Pour la voix, choisir FR ou AR.
5. Le notebook télécharge les poids depuis la source officielle à une révision figée, puis génère un fichier. Cette étape peut durer et échouer selon mémoire, disponibilité, licence ou format des poids. Les trois pipelines sont expérimentaux tant qu'ils n'ont pas tourné dans votre session.
6. Télécharger `resultat-studio.zip`. Revenir dans la tâche, choisir **Importer le résultat Colab** et sélectionner ce ZIP.
7. L'image/vidéo/voix devient un média du projet. Vérifier visuellement ou écouter le résultat. La provenance (modèle, révision, paramètres, temps et avertissements) est incluse dans l'export du projet.
8. Arrêter votre session Colab quand elle n'est plus nécessaire. Les sessions et leurs fichiers sont éphémères ; ne comptez pas sur un service 24h/24.

Le budget de l'application ne mesure pas un abonnement Colab ou ses unités de calcul. Le worker n'utilise pas de fournisseur payant externe, ne clone aucune voix et n'entraîne aucun visage. MMS-TTS est un candidat non commercial avec une seule voix par langue. Le texte vocal est limité à 2000 caractères par essai dans ce notebook ; vérifier les règles et la prononciation avant production.

Validation encore nécessaire : premier chargement, latence à chaud, qualité AR/FR, identité, artefacts vidéo, licence actuelle, poids safetensors disponibles et VRAM réelle. Aucun résultat GPU n'a été observé depuis Codex : les tests automatisés utilisent des fixtures et ne prouvent pas les performances des moteurs.

Si une cellule échoue, conserver le message d'erreur sans publier de token ni d'archive privée. Ne pas contourner TLS, safetensors ou les restrictions d'accès. L'échec d'un modèle n'empêche pas l'organisation, le montage ou les exports CPU du studio.
