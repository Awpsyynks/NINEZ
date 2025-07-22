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

### Modération
- `!ban @user [raison]` - Bannir
- `!kick @user [raison]` - Expulser
- `!mute @user [minutes] [raison]` - Muter
- `!clear [nombre]` - Supprimer messages
- `!warn @user [raison]` - Avertir

### Utilitaires
- `!help` - Aide
- `!ping` - Latence
- `!userinfo [@user]` - Info utilisateur
- `!serverinfo` - Info serveur

### Fun
- `!joke` - Blague
- `!8ball <question>` - Boule magique
- `!poll <question>` - Sondage
- `!trivia` - Culture générale

### Tickets
- `!ticket` - Créer un ticket
- `!close` - Fermer un ticket (staff)

## 🎭 Fonctionnalités

- ✅ Messages de bienvenue automatiques
- ✅ Rôles par réaction (persistants)
- ✅ Modération complète avec logs
- ✅ Système de tickets
- ✅ Commandes de divertissement
- ✅ Gestion d'erreurs en français
