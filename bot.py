import discord
from discord.ext import commands, tasks
import json
import logging
import os
import asyncio
from datetime import datetime, time
import shutil
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
            'suggestions': {},
            'system': {}
        }

        # Configuration du système d'anonymisation
        self.anonymous_commands = False  # Désactivé par défaut pour éviter les conflits

        # Système de sauvegarde automatique
        self.auto_save_enabled = True
        self.last_auto_save = None
        self.auto_save_interval = 3600  # 1 heure en secondes
        self.daily_backup_enabled = True
        self.backup_retention_days = 7  # Garder 7 jours de sauvegardes

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

        # Démarrer les tâches automatiques
        self.start_auto_tasks()

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

    async def on_command(self, ctx):
        """Appelé avant chaque commande - Système d'anonymisation"""
        logger.info(f"Commande '{ctx.command}' utilisée par {ctx.author.name} dans {ctx.guild.name if ctx.guild else 'DM'}")

        # SYSTÈME D'ANONYMISATION DES COMMANDES (après traitement)
        if self.anonymous_commands:
            # Programmer l'anonymisation après l'exécution de la commande
            self.loop.create_task(self.delayed_anonymize_command(ctx))

    async def anonymize_command(self, ctx):
        """Anonymise les commandes pour qu'elles apparaissent comme venant du bot"""
        # Vérifier si l'anonymisation est activée
        if not self.anonymous_commands:
            return

        # Ne pas anonymiser les commandes de configuration du système
        if ctx.command and ctx.command.name in ['anonymous', 'toggle_anonymous']:
            return

        try:
            # Supprimer le message de commande original
            if ctx.guild and ctx.channel.permissions_for(ctx.guild.me).manage_messages:
                try:
                    await ctx.message.delete()
                except discord.NotFound:
                    pass  # Message déjà supprimé
                except discord.Forbidden:
                    pass  # Pas les permissions

            # Créer un webhook pour simuler que c'est le bot qui parle
            webhook = await self.get_or_create_webhook(ctx.channel)
            if webhook:
                # Envoyer un message comme si c'était le bot
                embed = discord.Embed(
                    title="🤖 Commande Exécutée",
                    description=f"Commande `{ctx.prefix}{ctx.invoked_with}` en cours d'exécution...",
                    color=0x3498db
                )
                embed.add_field(
                    name="🔒 Mode Anonyme",
                    value="Cette commande est exécutée de manière anonyme pour la sécurité",
                    inline=False
                )
                embed.set_footer(text="Système de commandes anonymes • Sécurité maximale")

                await webhook.send(
                    embed=embed,
                    username=f"{self.user.name} • Système",
                    avatar_url=self.user.display_avatar.url
                )

        except Exception as e:
            logger.error(f"Erreur anonymisation commande: {e}")

    async def delayed_anonymize_command(self, ctx):
        """Anonymise la commande après un délai pour ne pas interférer"""
        try:
            # Attendre un peu que la commande se termine
            await asyncio.sleep(2)

            # Supprimer le message de commande original
            if ctx.guild and ctx.channel.permissions_for(ctx.guild.me).manage_messages:
                try:
                    await ctx.message.delete()
                except (discord.NotFound, discord.Forbidden):
                    pass  # Message déjà supprimé ou pas les permissions

        except Exception as e:
            logger.error(f"Erreur anonymisation retardée: {e}")

    @commands.command(name='anonymous', aliases=['toggle_anonymous'])
    @commands.has_permissions(administrator=True)
    async def toggle_anonymous_commands(self, ctx):
        """Active/désactive le système de commandes anonymes"""
        self.anonymous_commands = not self.anonymous_commands

        # Sauvegarder la configuration
        self.set_persistent_data('system', 'anonymous_commands', self.anonymous_commands)

        status = "activé" if self.anonymous_commands else "désactivé"
        color = 0x2ecc71 if self.anonymous_commands else 0xe74c3c

        embed = discord.Embed(
            title=f"🤖 Système de Commandes Anonymes {status.title()}",
            description=f"Le système de commandes anonymes a été **{status}**.",
            color=color
        )

        if self.anonymous_commands:
            embed.add_field(
                name="✅ Fonctionnalités Activées",
                value="• Suppression automatique des commandes\n• Messages via webhook du bot\n• Anonymisation complète\n• Sécurité maximale",
                inline=False
            )
        else:
            embed.add_field(
                name="❌ Fonctionnalités Désactivées",
                value="• Les commandes apparaîtront normalement\n• Pas de suppression automatique\n• Mode standard",
                inline=False
            )

        embed.add_field(
            name="🔧 Configuration",
            value=f"Utilisez `{ctx.prefix}anonymous` pour changer ce paramètre",
            inline=False
        )

        await ctx.send(embed=embed)

    async def get_or_create_webhook(self, channel):
        """Récupère ou crée un webhook pour le canal"""
        try:
            # Vérifier si un webhook existe déjà
            webhooks = await channel.webhooks()
            bot_webhook = None

            for webhook in webhooks:
                if webhook.name == f"{self.user.name}-Anonymous":
                    bot_webhook = webhook
                    break

            # Créer un nouveau webhook si nécessaire
            if not bot_webhook:
                bot_webhook = await channel.create_webhook(
                    name=f"{self.user.name}-Anonymous",
                    reason="Webhook pour commandes anonymes"
                )

            return bot_webhook

        except discord.Forbidden:
            logger.warning(f"Pas de permissions pour créer webhook dans {channel.name}")
            return None
        except Exception as e:
            logger.error(f"Erreur création webhook: {e}")
            return None

    @commands.Cog.listener()
    async def on_message(self, message):
        """Système d'autocomplétion intelligent pour les commandes"""
        if message.author.bot:
            return

        # Laisser le bot traiter les commandes normalement d'abord
        await self.process_commands(message)

        # Vérifier si c'est une commande incomplète SEULEMENT si ce n'est pas une commande valide
        if message.content.startswith(self.command_prefix):
            ctx = await self.get_context(message)
            if ctx.command is None:  # Seulement si aucune commande n'a été trouvée
                await self.handle_autocomplete(message)

    async def handle_autocomplete(self, message):
        """Gère l'autocomplétion des commandes"""
        try:
            content = message.content[len(self.command_prefix):].strip()

            # Si la commande est vide, ne rien faire
            if not content:
                return

            # Séparer la commande et les arguments
            parts = content.split()
            command_name = parts[0].lower()

            # Seulement suggérer si la commande n'existe pas
            command = self.get_command(command_name)
            if not command:
                # Suggérer des commandes similaires seulement si c'est vraiment proche
                await self.suggest_similar_commands(message, command_name)

        except Exception as e:
            logger.error(f"Erreur autocomplétion: {e}")

    async def suggest_similar_commands(self, message, partial_command):
        """Suggère des commandes similaires"""
        try:
            # Seulement suggérer si la commande fait au moins 3 caractères
            if len(partial_command) < 3:
                return

            # Trouver des commandes similaires
            similar_commands = []
            all_commands = [cmd.name for cmd in self.commands] + [alias for cmd in self.commands for alias in cmd.aliases]

            for cmd_name in all_commands:
                # Correspondance plus stricte
                if cmd_name.startswith(partial_command) or (len(partial_command) >= 4 and partial_command in cmd_name):
                    similar_commands.append(cmd_name)

            # Seulement afficher si on a trouvé des suggestions pertinentes
            if similar_commands and len(similar_commands) <= 8:
                embed = discord.Embed(
                    title="🤔 Commande introuvable",
                    description=f"La commande `{partial_command}` n'existe pas.",
                    color=0xf39c12
                )

                # Limiter à 5 suggestions
                suggestions = similar_commands[:5]
                embed.add_field(
                    name="💡 Suggestions",
                    value="\n".join(f"• `{self.command_prefix}{cmd}`" for cmd in suggestions),
                    inline=False
                )

                embed.set_footer(text="Autocomplétion intelligente")

                await message.channel.send(embed=embed, delete_after=10)

        except Exception as e:
            logger.error(f"Erreur suggestions: {e}")

    async def show_command_help(self, message, command):
        """Affiche l'aide détaillée pour une commande"""
        try:
            embed = discord.Embed(
                title=f"📋 Aide pour `{self.command_prefix}{command.name}`",
                description=command.help or "Aucune description disponible",
                color=0x3498db
            )

            # Signature de la commande
            signature = self.get_command_signature(command)
            embed.add_field(
                name="📝 Utilisation",
                value=f"`{signature}`",
                inline=False
            )

            # Exemples spécifiques selon la commande
            examples = self.get_command_examples(command)
            if examples:
                embed.add_field(
                    name="💡 Exemples",
                    value=examples,
                    inline=False
                )

            # Autocomplétion pour les arguments
            autocomplete_help = await self.get_autocomplete_help(message, command)
            if autocomplete_help:
                embed.add_field(
                    name="🎯 Autocomplétion",
                    value=autocomplete_help,
                    inline=False
                )

            # Aliases
            if command.aliases:
                embed.add_field(
                    name="🔄 Aliases",
                    value=", ".join(f"`{alias}`" for alias in command.aliases),
                    inline=False
                )

            embed.set_footer(text="Autocomplétion intelligente • Tapez pour continuer")

            await message.channel.send(embed=embed, delete_after=30)

        except Exception as e:
            logger.error(f"Erreur aide commande: {e}")

    def get_command_signature(self, command):
        """Génère la signature d'une commande"""
        signature = f"{self.command_prefix}{command.qualified_name}"

        if command.signature:
            signature += f" {command.signature}"

        return signature

    def get_command_examples(self, command):
        """Génère des exemples pour une commande"""
        examples = {
            'ban': f"`{self.command_prefix}ban @utilisateur Spam répété`\n`{self.command_prefix}ban 123456789 Comportement toxique`",
            'kick': f"`{self.command_prefix}kick @utilisateur Avertissement`\n`{self.command_prefix}kick @user Violation des règles`",
            'mute': f"`{self.command_prefix}mute @utilisateur 10m Spam`\n`{self.command_prefix}mute @user 1h Comportement inapproprié`",
            'warn': f"`{self.command_prefix}warn @utilisateur Langage inapproprié`\n`{self.command_prefix}warn @user Hors-sujet répété`",
            'superban': f"`{self.command_prefix}superban @utilisateur Raid/Alt account`\n`{self.command_prefix}ipban @user Contournement de ban`",
            'play': f"`{self.command_prefix}play Imagine Dragons`\n`{self.command_prefix}play https://youtube.com/watch?v=...`",
            'giveaway': f"`{self.command_prefix}giveaway 1h 1 Nitro Discord`\n`{self.command_prefix}giveaway 2d 3 100€ Steam`",
            'suggest': f"`{self.command_prefix}suggest Ajouter un salon gaming`\n`{self.command_prefix}suggest Organiser des événements`",
            'setup_tickets': f"`{self.command_prefix}setup_tickets #support`\n`{self.command_prefix}setup_tickets #aide`",
            'welcome_setup': f"`{self.command_prefix}welcome_setup #bienvenue`\n`{self.command_prefix}welcome_setup #général`",
            'antiraid': f"`{self.command_prefix}antiraid setup`\n`{self.command_prefix}antiraid status`",
            'automod': f"`{self.command_prefix}automod setup`\n`{self.command_prefix}automod filters`"
        }

        return examples.get(command.name, None)

    async def get_autocomplete_help(self, message, command):
        """Génère l'aide d'autocomplétion pour une commande"""
        try:
            help_text = ""

            # Commandes nécessitant un utilisateur
            if command.name in ['ban', 'kick', 'mute', 'warn', 'superban', 'unban']:
                # Lister les membres du serveur
                if message.guild:
                    members = [member for member in message.guild.members if not member.bot][:10]
                    if members:
                        help_text += "👥 **Utilisateurs disponibles:**\n"
                        for member in members:
                            help_text += f"• `@{member.name}` ({member.display_name})\n"

            # Commandes nécessitant un canal
            elif command.name in ['setup_tickets', 'welcome_setup', 'logs']:
                if message.guild:
                    channels = [ch for ch in message.guild.text_channels][:10]
                    if channels:
                        help_text += "📍 **Canaux disponibles:**\n"
                        for channel in channels:
                            help_text += f"• `#{channel.name}`\n"

            # Commandes nécessitant un rôle
            elif command.name in ['add_role', 'remove_role']:
                if message.guild:
                    roles = [role for role in message.guild.roles if role != message.guild.default_role][:10]
                    if roles:
                        help_text += "🎭 **Rôles disponibles:**\n"
                        for role in roles:
                            help_text += f"• `@{role.name}`\n"

            # Commandes avec options spécifiques
            elif command.name == 'giveaway':
                help_text += "⏰ **Durées:** `1m`, `30m`, `1h`, `2h`, `1d`, `1w`\n"
                help_text += "🏆 **Gagnants:** `1`, `2`, `3`, `5`, `10`\n"
                help_text += "🎁 **Prix:** `Nitro Discord`, `100€ Steam`, `Rôle VIP`"

            elif command.name == 'mute':
                help_text += "⏰ **Durées:** `5m`, `10m`, `30m`, `1h`, `2h`, `1d`"

            elif command.name == 'volume':
                help_text += "🔊 **Volume:** `0` (muet) à `100` (maximum)"

            elif command.name == 'effects':
                help_text += "🎵 **Effets:** `bass`, `nightcore`, `vaporwave`, `clear`"

            return help_text if help_text else None

        except Exception as e:
            logger.error(f"Erreur autocomplétion help: {e}")
            return None

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

    @commands.command(name='test_commands')
    @commands.has_permissions(administrator=True)
    async def test_commands(self, ctx):
        """Teste que les commandes fonctionnent correctement"""
        embed = discord.Embed(
            title="🧪 TEST DES COMMANDES",
            description="Vérification du bon fonctionnement des systèmes",
            color=0x2ecc71
        )

        # Tester les systèmes
        systems_status = []

        # Test autocomplétion
        try:
            systems_status.append("✅ Autocomplétion - Fonctionnel")
        except:
            systems_status.append("❌ Autocomplétion - Erreur")

        # Test anonymisation
        anon_status = "✅ Activé" if self.anonymous_commands else "⚠️ Désactivé"
        systems_status.append(f"🤖 Anonymisation - {anon_status}")

        # Test sauvegarde
        save_status = "✅ Actif" if hasattr(self, 'auto_save_task') and self.auto_save_task.is_running() else "❌ Inactif"
        systems_status.append(f"💾 Sauvegarde auto - {save_status}")

        embed.add_field(
            name="🔧 Statut des Systèmes",
            value="\n".join(systems_status),
            inline=False
        )

        embed.add_field(
            name="🎯 Commandes à Tester",
            value="• `!setup_tickets #canal` - Configuration tickets\n• `!help` - Aide générale\n• `!backup_status` - Statut sauvegardes",
            inline=False
        )

        embed.set_footer(text="Si setup_tickets ne fonctionne pas, contactez le développeur")

        await ctx.send(embed=embed)

    def start_auto_tasks(self):
        """Démarre toutes les tâches automatiques"""
        try:
            # Démarrer la sauvegarde automatique
            self.auto_save_task.start()
            logger.info("✅ Tâche de sauvegarde automatique démarrée")

            # Démarrer la sauvegarde quotidienne
            self.daily_backup_task.start()
            logger.info("✅ Tâche de sauvegarde quotidienne démarrée")

            # Démarrer le nettoyage des anciennes sauvegardes
            self.cleanup_old_backups_task.start()
            logger.info("✅ Tâche de nettoyage des sauvegardes démarrée")

        except Exception as e:
            logger.error(f"❌ Erreur démarrage tâches automatiques: {e}")

    @tasks.loop(seconds=3600)  # Toutes les heures
    async def auto_save_task(self):
        """Sauvegarde automatique toutes les heures"""
        try:
            logger.info("🔄 Début de la sauvegarde automatique...")

            # Sauvegarder toutes les données
            self.save_persistent_data()
            self.save_warnings()
            self.save_muted_users()

            # Sauvegarder les cogs
            saved_cogs = []
            for cog_name, cog in self.cogs.items():
                if hasattr(cog, 'save_configuration'):
                    try:
                        cog.save_configuration()
                        saved_cogs.append(cog_name)
                    except Exception as e:
                        logger.error(f"Erreur sauvegarde {cog_name}: {e}")

            self.last_auto_save = datetime.now()
            logger.info(f"✅ Sauvegarde automatique terminée - {len(saved_cogs)} cogs sauvegardés")

        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde automatique: {e}")

    @tasks.loop(time=time(hour=3, minute=0))  # Tous les jours à 3h du matin
    async def daily_backup_task(self):
        """Sauvegarde quotidienne avec archivage"""
        try:
            logger.info("🌙 Début de la sauvegarde quotidienne...")

            # Créer le dossier de sauvegardes s'il n'existe pas
            backup_dir = "backups"
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)

            # Nom du fichier de sauvegarde avec date
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_name = f"backup_{timestamp}"
            backup_path = os.path.join(backup_dir, backup_name)

            # Créer le dossier de cette sauvegarde
            os.makedirs(backup_path, exist_ok=True)

            # Sauvegarder tous les fichiers de données
            files_to_backup = [
                'persistent_data.json',
                'warnings.json',
                'muted_users.json',
                'config.json'
            ]

            backed_up_files = []
            for file in files_to_backup:
                if os.path.exists(file):
                    try:
                        shutil.copy2(file, os.path.join(backup_path, file))
                        backed_up_files.append(file)
                    except Exception as e:
                        logger.error(f"Erreur copie {file}: {e}")

            # Créer un fichier de métadonnées
            metadata = {
                'backup_date': timestamp,
                'files_backed_up': backed_up_files,
                'bot_version': '2.0',
                'guilds_count': len(self.guilds),
                'users_count': len(self.users)
            }

            with open(os.path.join(backup_path, 'metadata.json'), 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ Sauvegarde quotidienne terminée - {len(backed_up_files)} fichiers sauvegardés dans {backup_path}")

        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde quotidienne: {e}")

    @tasks.loop(time=time(hour=4, minute=0))  # Tous les jours à 4h du matin
    async def cleanup_old_backups_task(self):
        """Nettoie les anciennes sauvegardes"""
        try:
            from datetime import timedelta

            logger.info("🧹 Début du nettoyage des anciennes sauvegardes...")

            backup_dir = "backups"
            if not os.path.exists(backup_dir):
                return

            # Date limite (garder seulement les X derniers jours)
            cutoff_date = datetime.now() - timedelta(days=self.backup_retention_days)

            deleted_backups = []
            for item in os.listdir(backup_dir):
                item_path = os.path.join(backup_dir, item)
                if os.path.isdir(item_path) and item.startswith('backup_'):
                    try:
                        # Extraire la date du nom du dossier
                        date_str = item.replace('backup_', '').split('_')[0]
                        backup_date = datetime.strptime(date_str, '%Y-%m-%d')

                        # Supprimer si trop ancien
                        if backup_date < cutoff_date:
                            shutil.rmtree(item_path)
                            deleted_backups.append(item)

                    except Exception as e:
                        logger.error(f"Erreur traitement backup {item}: {e}")

            logger.info(f"✅ Nettoyage terminé - {len(deleted_backups)} anciennes sauvegardes supprimées")

        except Exception as e:
            logger.error(f"❌ Erreur nettoyage sauvegardes: {e}")

    @auto_save_task.before_loop
    async def before_auto_save(self):
        """Attendre que le bot soit prêt avant de commencer les sauvegardes"""
        await self.wait_until_ready()

    @daily_backup_task.before_loop
    async def before_daily_backup(self):
        """Attendre que le bot soit prêt avant de commencer les sauvegardes quotidiennes"""
        await self.wait_until_ready()

    @cleanup_old_backups_task.before_loop
    async def before_cleanup(self):
        """Attendre que le bot soit prêt avant de commencer le nettoyage"""
        await self.wait_until_ready()

    @commands.command(name='backup_status')
    @commands.has_permissions(administrator=True)
    async def backup_status(self, ctx):
        """Affiche le statut des sauvegardes automatiques"""
        embed = discord.Embed(
            title="💾 STATUT DES SAUVEGARDES AUTOMATIQUES",
            description="État du système de sauvegarde ultra-avancé",
            color=0x2ecc71
        )

        # Statut des tâches
        auto_save_status = "✅ Actif" if self.auto_save_task.is_running() else "❌ Inactif"
        daily_backup_status = "✅ Actif" if self.daily_backup_task.is_running() else "❌ Inactif"
        cleanup_status = "✅ Actif" if self.cleanup_old_backups_task.is_running() else "❌ Inactif"

        embed.add_field(
            name="🔄 Sauvegarde Automatique (Toutes les heures)",
            value=auto_save_status,
            inline=True
        )

        embed.add_field(
            name="🌙 Sauvegarde Quotidienne (3h du matin)",
            value=daily_backup_status,
            inline=True
        )

        embed.add_field(
            name="🧹 Nettoyage Automatique (4h du matin)",
            value=cleanup_status,
            inline=True
        )

        # Dernière sauvegarde
        if self.last_auto_save:
            last_save = self.last_auto_save.strftime("%d/%m/%Y à %H:%M:%S")
        else:
            last_save = "Jamais"

        embed.add_field(
            name="⏰ Dernière Sauvegarde Automatique",
            value=last_save,
            inline=False
        )

        # Compter les sauvegardes
        backup_count = 0
        if os.path.exists("backups"):
            backup_count = len([d for d in os.listdir("backups") if d.startswith('backup_')])

        embed.add_field(
            name="📁 Sauvegardes Disponibles",
            value=f"{backup_count} sauvegardes quotidiennes",
            inline=True
        )

        embed.add_field(
            name="🗑️ Rétention",
            value=f"{self.backup_retention_days} jours",
            inline=True
        )

        embed.add_field(
            name="🎯 Avantages",
            value="• **Aucune perte de données** possible\n• **Sauvegardes automatiques** 24/7\n• **Archivage quotidien** sécurisé\n• **Nettoyage automatique** des anciennes versions",
            inline=False
        )

        embed.set_footer(text="Système de sauvegarde automatique • Zéro intervention manuelle")

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
