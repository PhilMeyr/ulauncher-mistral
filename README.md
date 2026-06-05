# ulauncher-mistral

Extension [Ulauncher](https://ulauncher.io) pour interroger [Mistral AI](https://mistral.ai) directement depuis le launcher.

> ⚠️ Cette extension cible **Ulauncher v6 (bêta) / Extension API v3** uniquement. Elle ne fonctionne pas avec Ulauncher 5.x.

## Fonctionnalités

- **`ai <question>`** — pose une question à Mistral. Appuie sur Entrée sur « Demander à Mistral » pour envoyer (aucun appel API pendant la frappe). La réponse s'affiche ligne par ligne dans Ulauncher (liste scrollable) ; Entrée sur n'importe quelle ligne copie la réponse complète dans le presse-papiers ; les URLs présentes dans la réponse apparaissent comme items 🔗 cliquables.
- **`ai model`** — liste les modèles disponibles (récupérés en direct via `GET /v1/models`) et persiste ton choix. Le modèle choisi prime sur la préférence « Modèle par défaut ».
- **`ai reset`** — vide l'historique de conversation.
- **Conversation multi-tours** — les N derniers échanges (configurable) sont renvoyés comme contexte à chaque question.
- **Zéro dépendance** — l'API Mistral est appelée via la stdlib (`urllib`), aucun `pip install` requis.

## Installation

1. Installer Ulauncher v6 (bêta) : télécharger le `.deb` sur la [page des releases](https://github.com/Ulauncher/Ulauncher/releases) puis `sudo apt install ./ulauncher_6.0.0.betaXX_all.deb gir1.2-gtklayershell-0.1`.
2. Installer l'extension :
   ```bash
   ln -s /chemin/vers/ulauncher-mistral \
     ~/.local/share/ulauncher/extensions/com.github.philmeyr.ulauncher-mistral
   ```
   puis redémarrer Ulauncher.
3. Créer une clé API sur <https://console.mistral.ai/api-keys> et la renseigner dans les préférences de l'extension.

## Préférences

| Préférence | Défaut | Description |
|---|---|---|
| Clé API Mistral | — | Obligatoire |
| Modèle par défaut | `mistral-small-latest` | Surchargé par `ai model` |
| System prompt | « Réponds de façon concise. » | Instructions de base |
| Taille de l'historique | 4 | Échanges gardés en contexte (0 = désactivé) |
| Tokens max par réponse | 1024 | |
| Timeout API | 30 s | |

## Limitations connues

- **Pas de streaming de la réponse** : l'architecture événementielle d'Ulauncher (y compris v6 beta31) n'autorise qu'une seule réponse rendue par activation — le callback côté app est consommé après le premier rendu (`extension_mode.py`). Le client (`mistral/client.py`) expose déjà `chat_stream()` (SSE), prêt à être branché le jour où Ulauncher permettra le rendu progressif.
- Chaque item est limité à une ligne : les réponses longues sont découpées (~90 caractères/ligne) et la liste est scrollable.
- Les liens ne sont pas cliquables *dans* le texte : ils sont extraits et affichés comme items dédiés.

## Architecture

```
main.py              # MistralExtension : routage des callbacks Ulauncher (SRP)
ui/commands.py       # Registre de commandes ask/model/reset (OCP) + contexte injecté (DIP)
ui/results.py        # Fabriques de Result (DRY)
mistral/client.py    # Client REST Mistral (urllib) : chat, chat_stream, list_models
mistral/conversation.py  # Fenêtre glissante d'échanges
mistral/state.py     # Persistance JSON atomique (XDG_DATA_HOME)
mistral/formatter.py # Découpage en lignes + extraction d'URLs
mistral/errors.py    # Exceptions typées avec message utilisateur
```

La logique métier (`mistral/`) n'importe jamais Ulauncher ; les commandes dépendent du protocole `ChatProvider`, pas du client concret.

## Développement

```bash
ruff check . && ruff format .
# Tester sans installer :
ulauncher preview /chemin/vers/ulauncher-mistral
```
