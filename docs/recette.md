# État réel de la recette 0.3

| Critère | État | Preuve / limite |
|---|---|---|
| R01 Démarrage sans GPU | Validé Linux, Windows à tester | Serveur CPU et tests ; lanceur Windows fourni |
| R02 Données sauvegardées/restaurées | Validé localement | SQLite, sauvegarde hors ligne et ZIP en nouveau projet ; Drive absent |
| R03 Image distante réelle | À exécuter dans votre Colab | Échange JSON/ZIP testé sur fixtures, notebook SDXL candidat fourni |
| R04 Cohérence personnage 10 images | Non validé | Fiches, références et approbations disponibles, pas de benchmark GPU |
| R05 Animation 5 secondes | Non validé sur GPU | Pipeline Colab Wan candidat, export CPU réel de médias importés validé |
| R06 Voix AR/FR | Auditions de base appréciées par le propriétaire ; casting non validé | Kokoro FR et Chatterbox AR essayés ; FastPitch Arabic jugé robotique. Le nouveau casting fictif par âge/timbre et le transfert FR/AR restent à tester ; voir casting-voix.md |
| R07 MP4 lisible | Validé | H.264 1280×720 + audio, durée inspectée avec FFprobe |
| R08 Reprise après interruption | Validé pour rendu CPU | Redémarrage et réutilisation des segments vérifiés ; pas de DAG génératif complet |
| R09 Budget | Gardes locaux validés | Plafonds de tâches/projets ; coût d'abonnement Colab non mesuré |
| R10 Arrêt GPU loué | Hors périmètre | Aucune location GPU intégrée ou engagée |
| R11 Mobile sécurisé | Interface/PWA validées, hébergement à faire | Test responsive et caches ; pas d'accès distant configuré |
| R12 Disponibilité honnête | Appliquée | Moteurs locaux absents signalés, notebook expérimental explicite |

Cette version n'est pas la totalité du cahier des charges. Elle termine les fonctions locales de production réalisables dans l'environnement actuel et prépare l'essai distant sans service payant nouveau. Les résultats GPU, le matériel Windows et l'accès mobile distant restent des validations externes indispensables.
