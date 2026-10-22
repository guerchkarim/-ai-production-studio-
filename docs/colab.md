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

### Comparaison Chatterbox arabe sur L4

Le propriétaire a jugé FastPitch Arabic trop robotique malgré une prononciation correcte, et souhaite comparer d'autres moteurs avant les services Edge/Google. Le notebook autonome `notebooks/AI_Production_Studio_Essai_Chatterbox_AR.ipynb` teste **Chatterbox Multilingual V2**, bibliothèque `chatterbox-tts==0.1.7`, avec le même texte vocalisé et la voix fournie avec le modèle. Aucun audio personnel de référence, aucune API payante, aucune modification des précédents essais. Le WAV se réimporte par **Importer un média**, pas comme résultat d'une tâche MMS.

Python 3.11.17 et les 124 dépendances du fichier `scripts/colab/chatterbox-ar.requirements.txt` sont installés dans un environnement propre au notebook via uv 0.12.23. Le PyTorch du kernel Colab n'est pas remplacé. Le script vérifie la disponibilité CUDA et au moins 6 Go de VRAM libre (seuil préventif, pas garantie), puis télécharge seulement les fichiers nécessaires du dépôt officiel `ResembleAI/chatterbox`, à la révision obtenue et figée au début de l'essai. Il exige la voix intégrée, vérifie que les tokens distinguent trois paires vocalisées, conserve le filigrane Chatterbox et produit un WAV PCM16 avec un JSON de provenance. Les `.pt` de ce pipeline sont chargés par la bibliothèque en mode `weights_only=True` ; aucun chargement arbitraire ni contournement d'accès n'est ajouté.

Paramètres de départ : seed 42, arabe `ar`, exaggeration 0.5, température 0.8, CFG 0.0 suivant le conseil du mainteneur pour limiter le transfert d'accent depuis une référence dans une autre langue. Le texte n'est pas vocalisé automatiquement. Le moteur applique sa normalisation interne ; la distinction des tokens ne prouve pas la réalisation correcte des harakāt. Tester accent, naturel, répétitions, omissions, shadda et finales à l'écoute. Ce moteur multilingue n'est pas présenté comme un spécialiste de la prononciation arabe, ni comme validé ou équivalent à Edge/Google.

Validation du 22 octobre 2026 : installation complète réelle dans un environnement Linux Python 3.11.17 séparé et import de Chatterbox 0.1.7/PyTorch 2.6.0+cu124 réussis ; l'API déclare l'arabe pris en charge. Cellules et CLI compilées ; refus d'entrée invalide et d'absence de GPU vérifiés. **Poids Chatterbox non exécutés ici** : génération L4, utilisation mémoire réelle et qualité restent à évaluer dans Colab. Le coût des unités Colab n'est pas mesuré par le studio.

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
