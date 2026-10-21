# Profil photographique natif

Le premier essai réel du propriétaire a produit une image SDXL sur Tesla T4 : chargement rapporté 342,37 s, génération 15,27 s, 512×512, 20 étapes. L'import Windows a réussi. Le rendu du jardin, visible sur la capture, est stylisé et ses textures ne satisfont pas l'objectif photographique du propriétaire. Ce test de connexion ne valide pas la qualité finale.

Le nouveau notebook distingue Photo native 1024, Création native 1024 (sans négatif photographique pour préserver les autres styles), et Aperçu technique 512. Les profils natifs utilisent 35 étapes, CFG 5,5 et DPM++/Karras. Ils conservent les paramètres dans le PNG et le manifeste. Les nouveaux paquets image demandent 1024 par défaut. Le notebook applique explicitement son profil même si un ancien paquet mentionne encore 512.

Il n'y a ni agrandissement ni refiner automatique. La qualité photoréaliste supérieure reste à vérifier sur un nouvel essai GPU ; résolution plus élevée et davantage d'étapes ne garantissent pas une image indiscernable d'une photo. Le profil photo n'est pas adapté à tous les styles.

Pour tester dans la session Colab déjà chargée sans réinstaller ni télécharger d'autres poids : ajouter une nouvelle cellule, copier le contenu de `scripts/colab/essai_photo_1024.py`, exécuter. Le résultat distinct `essai-photo-1024.png` ne remplace ni l'image précédente ni le ZIP déjà importé. La cellule affiche l'image et mesure uniquement ce nouvel essai. Comparer les textures, feuilles, éclairage, artefacts et composition en taille réelle.

Pour importer ce simple essai dans l'application, télécharger le PNG puis utiliser Importer un média. Pour une génération avec association complète à une tâche, créer une NOUVELLE demande et utiliser le notebook mis à jour ; un ZIP différent ne peut pas remplacer un résultat déjà validé. Les résultats antérieurs sont conservés.

Si le profil reste insuffisant, il faudra benchmarker un autre modèle sur le même sujet et le même matériel, avec licence et contraintes mémoire vérifiées. Aucun modèle n'est promu « qualité extrême » sans revue humaine.
