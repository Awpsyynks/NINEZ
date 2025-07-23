import discord
from discord.ext import commands
import json
import logging
import os
import asyncio
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

# Configuration du logging
log_level = logging.DEBUG if os.getenv('DEBUG', 'False').lower() == 'true' else logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('discord_bot')

class CommunityBot(commands.Bot):
    def __init__(self):
        # Chargement de la configuration
        with open('config.json', 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        # Configuration des intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.reactions = True
        intents.guilds = True
        
        super().__init__(
            command_prefix=self.config['prefix'],
            intents=intents,
            help_command=None  # On va créer notre propre commande help
        )
        
        # Variables pour stocker les données persistantes
        self.warnings = {}  # {user_id: count}
        self.muted_users = set()
        
    async def setup_hook(self):
        """Appelé quand le bot démarre"""
        logger.info("Chargement des cogs...")
        
        # Liste des cogs à charger
        cogs = [
            'cogs.welcome',
            'cogs.role_selection',
            'cogs.moderation',
            'cogs.tickets',
            'cogs.utilities',
            'cogs.fun',
            'cogs.levels',
            'cogs.games',
            'cogs.customization',
            'cogs.onboarding'
        ]
        
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Cog {cog} chargé avec succès")
            except Exception as e:
                logger.error(f"Erreur lors du chargement du cog {cog}: {e}")
    
    async def on_ready(self):
        """Appelé quand le bot est prêt"""
        logger.info(f'{self.user} est connecté et prêt !')
        logger.info(f'Connecté à {len(self.guilds)} serveur(s)')
        
        # Définir le statut du bot
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(self.guilds)} serveur(s) | {self.config['prefix']}help"
        )
        await self.change_presence(activity=activity)
    
    async def on_command_error(self, ctx, error):
        """Gestion globale des erreurs"""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore les commandes inexistantes
        
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Permissions insuffisantes",
                description="Vous n'avez pas les permissions nécessaires pour utiliser cette commande.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
        
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="❌ Argument manquant",
                description=f"Il manque un argument requis : `{error.param.name}`",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
        
        elif isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                title="⏰ Cooldown",
                description=f"Cette commande est en cooldown. Réessayez dans {error.retry_after:.1f} secondes.",
                color=0xf39c12
            )
            await ctx.send(embed=embed)
        
        else:
            logger.error(f"Erreur non gérée dans {ctx.command}: {error}")
            embed = discord.Embed(
                title="❌ Erreur",
                description="Une erreur inattendue s'est produite. Veuillez contacter un administrateur.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)

async def main():
    """Fonction principale"""
    bot = CommunityBot()
    
    try:
        token = os.getenv('DISCORD_TOKEN')
        if not token:
            logger.error("Token Discord non trouvé ! Vérifiez votre fichier .env")
            return
        
        await bot.start(token)
    except KeyboardInterrupt:
        logger.info("Arrêt du bot...")
    except Exception as e:
        logger.error(f"Erreur lors du démarrage du bot: {e}")
    finally:
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
