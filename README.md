# 🤖 Bot Discord Communautaire

Bot Discord francophone avec modération, rôles par réaction, tickets et divertissement.

## 🚀 Hébergement

### Railway (Gratuit - Recommandé)
1. Allez sur [railway.app](https://railway.app)
2. "Deploy from GitHub repo" → Sélectionnez ce repository
3. Ajoutez les variables d'environnement :
   - `DISCORD_TOKEN` : Votre token Discord
   - `GUILD_ID` : ID de votre serveur (optionnel)
4. Railway déploie automatiquement !

### Render (Gratuit)
1. Allez sur [render.com](https://render.com)
2. "New Web Service" → Connectez votre repository
3. Configuration :
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python bot.py`
4. Ajoutez les variables d'environnement

## ⚙️ Configuration

Une fois déployé, configurez sur votre serveur Discord :

```
!welcome_setup #bienvenue
!setup_roles #choix-rôles
!setup_tickets #support
```

## 📋 Commandes

### 🎉 Bienvenue
- `!welcome_setup #canal` - Configure le canal de bienvenue
- `!welcome_message "message"` - Personnalise le message de bienvenue
- `!goodbye_setup #canal` - Configure le canal d'au revoir
- `!goodbye_message "message"` - Personnalise le message d'au revoir

### 🎭 Rôles
- `!setup_roles #canal` - Configure le système de sélection de rôles
- `!add_role @role emoji "desc"` - Ajoute un rôle sélectionnable
- `!remove_role @role` - Retire un rôle du système
- `!list_roles` - Liste tous les rôles configurés

### 🛡️ Modération
- `!kick @user [raison]` - Expulse un membre
- `!ban @user [raison]` - Bannit un membre
- `!unban user#1234` - Débannit un membre
- `!mute @user [durée]` - Rend muet un membre
- `!unmute @user` - Retire le mute
- `!clear [nombre]` - Supprime des messages (max 100)
- `!warn @user raison` - Avertit un membre
- `!warnings @user` - Voir les avertissements
- `!slowmode [secondes]` - Active le mode lent

### 🎫 Tickets
- `!setup_tickets #canal` - Configure le système de tickets
- `!ticket` - Crée un ticket de support
- `!add @user` - Ajoute un utilisateur au ticket
- `!remove @user` - Retire un utilisateur du ticket
- `!close` - Ferme un ticket (staff)

### 🔧 Utilitaires
- `!ping` - Teste la latence du bot
- `!serverinfo` - Infos sur le serveur
- `!userinfo [@user]` - Infos sur un utilisateur
- `!avatar [@user]` - Avatar d'un utilisateur
- `!say "message"` - Fait parler le bot
- `!embed "titre" "description"` - Crée un embed
- `!poll "question" "opt1" "opt2"` - Crée un sondage

### 🎮 Fun
- `!8ball question` - Boule magique 8
- `!flip` - Pile ou face
- `!dice [faces]` - Lance un dé
- `!joke` - Raconte une blague
- `!fact` - Fait aléatoire
- `!choose "opt1" "opt2" "opt3"` - Choix aléatoire
- `!reverse "texte"` - Inverse un texte
- `!mock "texte"` - TeXtE aLtErNé

### 📈 Niveaux/XP
- `!rank [@user]` - Voir son niveau
- `!leaderboard` - Top des niveaux
- `!setxp @user [amount]` - Définir XP (admin)
- `!addxp @user [amount]` - Ajouter XP (admin)
- `!rewards` - Récompenses par niveau

### 🎲 Mini-Jeux
- `!rps [pierre/papier/ciseaux]` - Pierre-papier-ciseaux
- `!guess [max]` - Devine le nombre
- `!trivia` - Questions culture générale
- `!hangman` - Jeu du pendu
- `!slots` - Machine à sous
- `!coinflip [pile/face]` - Pari pile ou face
- `!dice [faces] [count]` - Lance des dés

### ⚙️ Personnalisation
- `!color #hex` - Couleur des embeds
- `!prefix [nouveau]` - Changer le préfixe
- `!language [fr/en]` - Changer la langue
- `!timezone [zone]` - Fuseau horaire
- `!settings` - Voir les paramètres

## 🎭 Fonctionnalités

- ✅ Messages de bienvenue automatiques
- ✅ Rôles par réaction (persistants)
- ✅ Modération complète avec logs
- ✅ Système de tickets
- ✅ Commandes de divertissement
- ✅ Gestion d'erreurs en français
