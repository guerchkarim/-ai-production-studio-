# Votre session Google Colab

## Comparer une autre voix française après MMS

Le notebook indépendant `notebooks/AI_Production_Studio_Essai_Voix_FR.ipynb` propose Kokoro-82M, voix `ff_siwis`, via `kokoro-onnx==0.6.1` (Python 3.10 à 3.13). Il ne remplace pas le worker MMS : écouter le même texte avant de choisir. Exécuter ses trois cellules dans l'ordre, écouter le lecteur puis conserver le WAV et son JSON de provenance. Réimporter le WAV par **Importer un média**, pas par l'import de résultat d'une tâche MMS, qui vérifie l'identité du moteur.

Calcul CPU, aucune clé API ; une session Colab GPU connectée continue néanmoins à consommer ses unités. Poids Kokoro Apache 2.0, bibliothèque de conversion MIT ; consulter les sources liées dans le notebook. Les deux fichiers de la release officielle du mainteneur ONNX sont vérifiés par SHA-256 avant chargement. Ce moteur ne propose ici que le français, pas l'arabe. Aucun audio du propriétaire n'est envoyé à un service de synthèse.

Validation du 22 octobre 2026 : génération réelle CPU de « Bonjour, bienvenue dans notre atelier. », WAV PCM 16 bits à 24 kHz, échantillons finis et non silencieux. Les cellules ont été compilées. Le naturel, la prononciation et l'exécution de ce notebook dans la session Colab Python 3.13 du propriétaire restent à évaluer. Cette vérification ne prouve aucune supériorité sur MMS. Le dépôt d'évaluation d'arabe reste inchangé.

## Worker de tâches existant

### Essai spécialisé arabe vocalisé

`notebooks/AI_Production_Studio_Essai_Voix_AR.ipynb` teste FastPitch Arabic + HiFi-GAN avec le phonémiseur arabe de `nipponjo/tts_arabic`, révision `eae130c8b94ebf88d3fa727db63c740859106327`. Le notebook ne touche ni Kokoro français, ni les tâches MMS, ni les données du studio. Il produit un WAV réimportable par **Importer un média**, accompagné de la provenance JSON.

Les harakāt saisis restent dans le texte ; `vowelizer=None` désactive la réécriture automatique. L'utilisateur doit relire la vocalisation avant synthèse. Le contrôle CPU des tokens distingue réellement `عَلِمَ`/`عُلِمَ`, `دَرَسَ`/`دَرَّسَ` et `قَلَمٌ`/`قَلَمٍ`. Cela ne valide ni l'acoustique, ni les règles de pause, ni une prononciation parfaite. Cette livraison n'a pas exécuté les poids arabes : l'audio et le fonctionnement dans Colab restent à valider. Le modèle n'est pas un moteur de tajwid.

Les modèles ONNX viennent des liens Google Drive publiés dans le dépôt du mainteneur. Le JSON enregistre leurs empreintes observées, sans les présenter comme vérifiées contre un manifeste signé. Les notices de tiers sont liées dans le notebook ; la révision choisie n'a pas de fichier LICENSE racine, donc ne pas en déduire une licence globale ou une autorisation de redistribution. Le chargement CPU évite de modifier PyTorch et n'exige aucune clé fournisseur. La session Colab connectée peut néanmoins continuer à consommer ses unités GPU.

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
