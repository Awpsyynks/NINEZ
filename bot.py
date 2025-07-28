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

        # Variables pour l'anti-raid et l'automod
        self.raid_detection = {
            'joins': [],  # Liste des joins récents
            'messages': {},  # Messages par utilisateur
            'raid_mode': False,
            'quarantine_role': None
        }

        # Variables pour l'économie
        self.economy_data = {}

        # Variables pour les giveaways
        self.active_giveaways = {}

        # Variables pour les suggestions
        self.suggestions_data = {}

        # Système de persistance des données
        self.persistent_data = {
            'tickets': {},
            'welcome': {},
            'roles': {},
            'moderation': {},
            'levels': {},
            'onboarding': {},
            'antiraid': {},
            'automod': {},
            'economy': {},
            'music': {},
            'logs': {},
            'giveaways': {},
            'suggestions': {}
        }

        # Charger les données sauvegardées
        self.load_persistent_data()

    def load_persistent_data(self):
        """Charge toutes les données persistantes depuis les fichiers"""
        try:
            # Charger les données principales
            with open('persistent_data.json', 'r', encoding='utf-8') as f:
                self.persistent_data = json.load(f)
            logger.info("✅ Données persistantes chargées avec succès")
        except FileNotFoundError:
            logger.info("📁 Aucun fichier de données persistantes trouvé, création d'un nouveau")
            self.save_persistent_data()
        except Exception as e:
            logger.error(f"❌ Erreur lors du chargement des données: {e}")

        # Charger les données spécifiques
        self.load_warnings()
        self.load_muted_users()

    def save_persistent_data(self):
        """Sauvegarde toutes les données persistantes"""
        try:
            with open('persistent_data.json', 'w', encoding='utf-8') as f:
                json.dump(self.persistent_data, f, indent=2, ensure_ascii=False)
            logger.info("💾 Données persistantes sauvegardées")
        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde: {e}")

    def load_warnings(self):
        """Charge les avertissements"""
        try:
            with open('warnings.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Convertir les clés string en int
                self.warnings = {int(k): v for k, v in data.items()}
            logger.info("⚠️ Avertissements chargés")
        except FileNotFoundError:
            self.warnings = {}
        except Exception as e:
            logger.error(f"❌ Erreur chargement avertissements: {e}")
            self.warnings = {}

    def save_warnings(self):
        """Sauvegarde les avertissements"""
        try:
            with open('warnings.json', 'w', encoding='utf-8') as f:
                json.dump(self.warnings, f, indent=2)
            logger.info("💾 Avertissements sauvegardés")
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde avertissements: {e}")

    def load_muted_users(self):
        """Charge les utilisateurs mutés"""
        try:
            with open('muted_users.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.muted_users = set(data)
            logger.info("🔇 Utilisateurs mutés chargés")
        except FileNotFoundError:
            self.muted_users = set()
        except Exception as e:
            logger.error(f"❌ Erreur chargement muted: {e}")
            self.muted_users = set()

    def save_muted_users(self):
        """Sauvegarde les utilisateurs mutés"""
        try:
            with open('muted_users.json', 'w', encoding='utf-8') as f:
                json.dump(list(self.muted_users), f, indent=2)
            logger.info("💾 Utilisateurs mutés sauvegardés")
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde muted: {e}")

    def get_persistent_data(self, category, key=None, default=None):
        """Récupère des données persistantes"""
        if category not in self.persistent_data:
            self.persistent_data[category] = {}

        if key is None:
            return self.persistent_data[category]

        return self.persistent_data[category].get(key, default)

    def set_persistent_data(self, category, key, value):
        """Définit des données persistantes"""
        if category not in self.persistent_data:
            self.persistent_data[category] = {}

        self.persistent_data[category][key] = value
        self.save_persistent_data()

    def update_persistent_data(self, category, data_dict):
        """Met à jour plusieurs données persistantes"""
        if category not in self.persistent_data:
            self.persistent_data[category] = {}

        self.persistent_data[category].update(data_dict)
        self.save_persistent_data()

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
            'cogs.onboarding',
            'cogs.antiraid',
            'cogs.automod',
            'cogs.economy',
            'cogs.music',
            'cogs.logs',
            'cogs.giveaways',
            'cogs.suggestions'
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

        # Charger les configurations des cogs
        await self.load_cog_configurations()

    async def load_cog_configurations(self):
        """Charge les configurations de tous les cogs"""
        logger.info("🔄 Chargement des configurations des cogs...")

        # Attendre que tous les cogs soient chargés
        await asyncio.sleep(2)

        # Charger les configurations spécifiques
        for cog_name, cog in self.cogs.items():
            if hasattr(cog, 'load_from_persistent_data'):
                try:
                    await cog.load_from_persistent_data()
                    logger.info(f"✅ Configuration {cog_name} chargée")
                except Exception as e:
                    logger.error(f"❌ Erreur chargement {cog_name}: {e}")

    async def close(self):
        """Appelé quand le bot se ferme"""
        logger.info("🔄 Sauvegarde avant fermeture...")

        # Sauvegarder toutes les données
        self.save_persistent_data()
        self.save_warnings()
        self.save_muted_users()

        # Sauvegarder les configurations des cogs
        for cog_name, cog in self.cogs.items():
            if hasattr(cog, 'save_to_persistent_data'):
                try:
                    await cog.save_to_persistent_data()
                    logger.info(f"💾 Configuration {cog_name} sauvegardée")
                except Exception as e:
                    logger.error(f"❌ Erreur sauvegarde {cog_name}: {e}")

        logger.info("✅ Sauvegarde terminée")
        await super().close()

    @commands.command(name='save_all')
    @commands.is_owner()
    async def save_all_data(self, ctx):
        """Sauvegarde toutes les données manuellement"""
        embed = discord.Embed(
            title="💾 Sauvegarde en cours...",
            description="Sauvegarde de toutes les configurations...",
            color=0x3498db
        )
        message = await ctx.send(embed=embed)

        # Sauvegarder toutes les données
        self.save_persistent_data()
        self.save_warnings()
        self.save_muted_users()

        saved_cogs = []
        failed_cogs = []

        # Sauvegarder les configurations des cogs
        for cog_name, cog in self.cogs.items():
            if hasattr(cog, 'save_to_persistent_data'):
                try:
                    await cog.save_to_persistent_data()
                    saved_cogs.append(cog_name)
                except Exception as e:
                    failed_cogs.append(f"{cog_name}: {e}")

        # Message de confirmation
        embed = discord.Embed(
            title="✅ Sauvegarde terminée !",
            description="Toutes les données ont été sauvegardées",
            color=0x2ecc71
        )

        if saved_cogs:
            embed.add_field(
                name="💾 Cogs sauvegardés",
                value="\n".join(f"✅ {cog}" for cog in saved_cogs),
                inline=False
            )

        if failed_cogs:
            embed.add_field(
                name="❌ Erreurs",
                value="\n".join(failed_cogs),
                inline=False
            )

        await message.edit(embed=embed)

    @commands.command(name='load_all')
    @commands.is_owner()
    async def load_all_data(self, ctx):
        """Charge toutes les données manuellement"""
        embed = discord.Embed(
            title="🔄 Chargement en cours...",
            description="Chargement de toutes les configurations...",
            color=0x3498db
        )
        message = await ctx.send(embed=embed)

        # Charger toutes les données
        self.load_persistent_data()

        loaded_cogs = []
        failed_cogs = []

        # Charger les configurations des cogs
        for cog_name, cog in self.cogs.items():
            if hasattr(cog, 'load_from_persistent_data'):
                try:
                    await cog.load_from_persistent_data()
                    loaded_cogs.append(cog_name)
                except Exception as e:
                    failed_cogs.append(f"{cog_name}: {e}")

        # Message de confirmation
        embed = discord.Embed(
            title="✅ Chargement terminé !",
            description="Toutes les données ont été chargées",
            color=0x2ecc71
        )

        if loaded_cogs:
            embed.add_field(
                name="🔄 Cogs chargés",
                value="\n".join(f"✅ {cog}" for cog in loaded_cogs),
                inline=False
            )

        if failed_cogs:
            embed.add_field(
                name="❌ Erreurs",
                value="\n".join(failed_cogs),
                inline=False
            )

        await message.edit(embed=embed)

    @commands.command(name='persistent_status')
    @commands.has_permissions(administrator=True)
    async def persistent_status(self, ctx):
        """Affiche le statut des données persistantes"""
        embed = discord.Embed(
            title="📊 Statut des Données Persistantes",
            description="État de la sauvegarde automatique",
            color=0x3498db
        )

        # Vérifier les fichiers de données
        import os
        files_status = []

        data_files = [
            'persistent_data.json',
            'warnings.json',
            'muted_users.json',
            'config.json'
        ]

        for file in data_files:
            if os.path.exists(file):
                size = os.path.getsize(file)
                files_status.append(f"✅ {file} ({size} bytes)")
            else:
                files_status.append(f"❌ {file} (manquant)")

        embed.add_field(
            name="📁 Fichiers de données",
            value="\n".join(files_status),
            inline=False
        )

        # Statut des cogs
        cogs_with_persistence = []
        cogs_without_persistence = []

        for cog_name, cog in self.cogs.items():
            if hasattr(cog, 'save_to_persistent_data') and hasattr(cog, 'load_from_persistent_data'):
                cogs_with_persistence.append(cog_name)
            else:
                cogs_without_persistence.append(cog_name)

        if cogs_with_persistence:
            embed.add_field(
                name="✅ Cogs avec persistance",
                value="\n".join(cogs_with_persistence),
                inline=True
            )

        if cogs_without_persistence:
            embed.add_field(
                name="⚠️ Cogs sans persistance",
                value="\n".join(cogs_without_persistence),
                inline=True
            )

        # Données persistantes
        data_categories = list(self.persistent_data.keys())
        embed.add_field(
            name="📋 Catégories de données",
            value="\n".join(f"• {cat}" for cat in data_categories),
            inline=False
        )

        embed.add_field(
            name="🔧 Commandes utiles",
            value="`!save_all` - Sauvegarder manuellement\n`!load_all` - Charger manuellement\n`!persistent_status` - Voir ce statut",
            inline=False
        )

        embed.set_footer(text="Les données sont sauvegardées automatiquement à chaque modification")

        await ctx.send(embed=embed)
    
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
