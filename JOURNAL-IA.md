# 📓 Journal d'usage de l'IA — Équipe `[1]`

> **SAÉ 3.01 « Climat & Cultures »** — à tenir **au fil de l'eau**, versionné dans le dépôt Git, annexé au livrable final.
> Membres :
>
> \*`[Malik BOUSSAIDI]`
>
> \*`[Afnanmasud DHALI]`
>
> \*`[Amine EL AIDOUS]`
>
> \*`[Alaeddine ELGHOMARI--JABEUR]`
>
> \*`[Romaric LIN]`

## Rappel express des règles

- L'IA est un **copilote, pas un sous-traitant**. 🔑 _« Si tu ne peux pas l'expliquer, tu ne peux pas le rendre. »_
- **Tout outil est autorisé** (Claude fourni, ChatGPT, Gemini, Copilot…) — **à condition d'être déclaré**.
- **Une ligne par usage significatif** (code/requête/texte intégré, debug qui change la solution, choix orienté, tests, refactor).
- **Nominatif** : chaque ligne identifie son auteur.
- **Jamais** de données personnelles dans les prompts.
- La colonne **Justification** est le cœur : _pourquoi_ + ce que vous avez **vérifié / corrigé / testé**.

---

## ⌨️ Déclaration permanente — assistants ambiants

> **À remplir en J0, une fois pour toutes.** Un assistant d'autocomplétion (Copilot, Tabnine, IA intégrée à l'IDE…) produit des suggestions **en continu** : impossible de les journaliser une par une. On le déclare donc **globalement** ici.
> ⚠️ La règle d'or continue de s'appliquer : ce que vous intégrez, vous devez savoir l'expliquer.

| Équipier | Outil ambiant utilisé     | Où (IDE / éditeur) | Depuis quand |
| -------- | ------------------------- | ------------------ | ------------ |
| `[Tous]` | Prettier - CodeFormatteur | VSCode             | 13/09        |
|          |                           |                    |              |
|          |                           |                    |              |

_Aucun assistant ambiant utilisé ? Écrivez-le explicitement : « Aucun » — une case vide n'est pas une déclaration._

---

## Journal

| Date  | Équipier | Outil/modèle | Tâche / contexte    | Prompt (résumé)                                 | Sortie IA        | Gardé/modifié/rejeté | Justification (vérif. / correction / test)                                                | Tokens (≈) |
| ----- | -------- | ------------ | ------------------- | ----------------------------------------------- | ---------------- | -------------------- | ----------------------------------------------------------------------------------------- | ---------- |
| 12/10 | Léa      | Haiku 4.5    | requête SQL des GDD | « somme des T° > 10 °C par culture et commune » | requête proposée | **modifié**          | jointure fausse sur `Dim_Temps` corrigée ; index ajouté ; testée sur commune X → cohérent | ~1 900     |
|       |          |              |                     |                                                 |                  |                      |                                                                                           |            |
|       |          |              |                     |                                                 |                  |                      |                                                                                           |            |
|       |          |              |                     |                                                 |                  |                      |                                                                                           |            |

_(Ajoutez autant de lignes que nécessaire.)_

---

## 🌱 Synthèse environnementale (à compléter pour le rendu final)

> Méthode et exemple de calcul : voir `poc-empreinte-ia.py`. Manier avec **esprit critique** (forte incertitude).

- **Total tokens** sur le projet : `[…]` (entrée : `[…]` / sortie : `[…]`)
- **Énergie estimée** : `[…]` Wh
- **CO₂e estimé** : `[…]` g
- **Équivalence parlante** : ≈ `[…]` (ex. m/km en voiture, via facteur ADEME)
- **Hypothèses retenues** : `[Wh/1k tokens, intensité carbone du réseau, modèle…]`
- **Périmètre de la mesure** : `[quels usages ai-je pu compter, lesquels non ?]`
  > ℹ️ La colonne **Tokens** n'est renseignable que pour le compte API fourni. Un usage sur ChatGPT, Gemini ou Copilot n'expose pas ses tokens : **écrivez « non mesurable »** dans la colonne et dites-le ici. Annoncer ce qu'on n'a **pas** pu mesurer fait partie d'une mesure honnête — c'est valorisé, pas pénalisé.
- **Discussion de l'incertitude** : `[pourquoi ces chiffres varient d'un facteur ~10 ?]`
- **Regard coût/bénéfice** : `[cet usage de l'IA en valait-il la peine ? où aurait-on pu être plus sobre ?]`
