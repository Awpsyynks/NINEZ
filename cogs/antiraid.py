import discord
from discord.ext import commands, tasks
import asyncio
import logging
from datetime import datetime, timedelta
import json
import re

logger = logging.getLogger('discord_bot.antiraid')

class AntiRaid(commands.Cog):
    """Système de protection anti-raid avancé"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config = self.load_config()
        
        # Données de détection
        self.join_tracker = []  # Joins récents
        self.message_tracker = {}  # Messages par utilisateur
        self.raid_mode = False
        self.quarantine_users = set()
        
        # Démarrer les tâches de nettoyage
        self.cleanup_tracker.start()
        
    def load_config(self):
        """Charge la configuration anti-raid"""
        try:
            with open('antiraid_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # Configuration par défaut
            default_config = {
                "enabled": True,
                "raid_detection": {
                    "joins_threshold": 5,  # Nombre de joins
                    "joins_timeframe": 10,  # En secondes
                    "auto_quarantine": True
                },
                "anti_spam": {
                    "enabled": True,
                    "max_messages": 5,
                    "timeframe": 10,
                    "max_duplicates": 3,
                    "punishment": "mute"  # mute, kick, ban
                },
                "verification": {
                    "enabled": True,
                    "min_account_age": 7,  # Jours
                    "require_avatar": False,
                    "auto_quarantine_new": True
                },
                "channels": {
                    "logs": None,
                    "quarantine": None
                },
                "roles": {
                    "quarantine": None,
                    "verified": None
                },
                "whitelist": {
                    "users": [],
                    "roles": []
                }
            }
            self.save_config(default_config)
            return default_config
    
    def save_config(self, config=None):
        """Sauvegarde la configuration"""
        if config is None:
            config = self.config
        try:
            with open('antiraid_config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erreur sauvegarde config anti-raid: {e}")
    
    @tasks.loop(minutes=1)
    async def cleanup_tracker(self):
        """Nettoie les données de tracking anciennes"""
        now = datetime.now()
        
        # Nettoie les joins anciens
        self.join_tracker = [
            join for join in self.join_tracker 
            if (now - join['time']).seconds < 300  # Garde 5 minutes
        ]
        
        # Nettoie les messages anciens
        for user_id in list(self.message_tracker.keys()):
            self.message_tracker[user_id] = [
                msg for msg in self.message_tracker[user_id]
                if (now - msg['time']).seconds < 60  # Garde 1 minute
            ]
            if not self.message_tracker[user_id]:
                del self.message_tracker[user_id]
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Détection de raid et vérification des nouveaux membres"""
        if not self.config['enabled']:
            return
            
        now = datetime.now()
        
        # Ajouter le join au tracker
        self.join_tracker.append({
            'user': member,
            'time': now
        })
        
        # Vérifier si c'est un raid
        await self.check_raid_detection(member.guild)
        
        # Vérifier l'âge du compte
        await self.check_account_verification(member)
        
        # Log du join
        await self.log_member_join(member)
    
    async def check_raid_detection(self, guild):
        """Vérifie s'il y a un raid en cours"""
        config = self.config['raid_detection']
        now = datetime.now()
        
        # Compter les joins récents
        recent_joins = [
            join for join in self.join_tracker
            if (now - join['time']).seconds <= config['joins_timeframe']
        ]
        
        if len(recent_joins) >= config['joins_threshold']:
            if not self.raid_mode:
                await self.activate_raid_mode(guild)
                
                # Quarantaine automatique des nouveaux arrivants
                if config['auto_quarantine']:
                    for join_data in recent_joins:
                        await self.quarantine_user(join_data['user'])
    
    async def activate_raid_mode(self, guild):
        """Active le mode anti-raid"""
        self.raid_mode = True
        
        embed = discord.Embed(
            title="🚨 MODE ANTI-RAID ACTIVÉ",
            description="Détection d'un raid potentiel. Mesures de protection activées.",
            color=0xe74c3c,
            timestamp=datetime.now()
        )
        embed.add_field(
            name="⚡ Actions automatiques",
            value="• Quarantaine des nouveaux membres\n• Surveillance renforcée\n• Logs détaillés",
            inline=False
        )
        
        # Envoyer dans le canal de logs
        log_channel = self.get_log_channel(guild)
        if log_channel:
            await log_channel.send(embed=embed)
        
        # Notifier les administrateurs
        await self.notify_admins(guild, embed)
        
        logger.warning(f"Mode anti-raid activé sur {guild.name}")
        
        # Désactiver automatiquement après 10 minutes
        await asyncio.sleep(600)
        await self.deactivate_raid_mode(guild)
    
    async def deactivate_raid_mode(self, guild):
        """Désactive le mode anti-raid"""
        self.raid_mode = False
        
        embed = discord.Embed(
            title="✅ MODE ANTI-RAID DÉSACTIVÉ",
            description="Le mode anti-raid a été désactivé automatiquement.",
            color=0x2ecc71,
            timestamp=datetime.now()
        )
        
        log_channel = self.get_log_channel(guild)
        if log_channel:
            await log_channel.send(embed=embed)
        
        logger.info(f"Mode anti-raid désactivé sur {guild.name}")
    
    async def check_account_verification(self, member):
        """Vérifie l'âge et la validité du compte"""
        config = self.config['verification']
        if not config['enabled']:
            return
        
        now = datetime.now()
        account_age = (now - member.created_at).days
        
        suspicious = False
        reasons = []
        
        # Vérifier l'âge du compte
        if account_age < config['min_account_age']:
            suspicious = True
            reasons.append(f"Compte trop récent ({account_age} jours)")
        
        # Vérifier l'avatar
        if config['require_avatar'] and member.display_avatar == member.default_avatar:
            suspicious = True
            reasons.append("Pas d'avatar personnalisé")
        
        # Vérifier le nom d'utilisateur
        if self.is_suspicious_username(member.name):
            suspicious = True
            reasons.append("Nom d'utilisateur suspect")
        
        if suspicious:
            if config['auto_quarantine_new'] or self.raid_mode:
                await self.quarantine_user(member, reasons)
            else:
                await self.log_suspicious_user(member, reasons)
    
    def is_suspicious_username(self, username):
        """Vérifie si un nom d'utilisateur est suspect"""
        suspicious_patterns = [
            r'^[a-zA-Z]+\d{4,}$',  # Nom + beaucoup de chiffres
            r'^.{1,3}$',  # Nom très court
            r'[^\w\s]',  # Caractères spéciaux
            r'discord|admin|mod|bot',  # Mots suspects
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, username, re.IGNORECASE):
                return True
        return False
    
    async def quarantine_user(self, member, reasons=None):
        """Met un utilisateur en quarantaine"""
        quarantine_role_id = self.config['roles']['quarantine']
        if not quarantine_role_id:
            return
        
        quarantine_role = member.guild.get_role(quarantine_role_id)
        if not quarantine_role:
            return
        
        try:
            # Retirer tous les autres rôles et ajouter la quarantaine
            await member.edit(roles=[quarantine_role], reason="Quarantaine automatique")
            self.quarantine_users.add(member.id)
            
            # Log de la quarantaine
            embed = discord.Embed(
                title="🔒 Utilisateur mis en quarantaine",
                color=0xf39c12,
                timestamp=datetime.now()
            )
            embed.add_field(name="👤 Utilisateur", value=f"{member.mention} ({member.id})", inline=False)
            embed.add_field(name="📅 Compte créé", value=member.created_at.strftime("%d/%m/%Y %H:%M"), inline=True)
            embed.add_field(name="⏰ Rejoint le", value=member.joined_at.strftime("%d/%m/%Y %H:%M"), inline=True)
            
            if reasons:
                embed.add_field(name="⚠️ Raisons", value="\n".join(f"• {reason}" for reason in reasons), inline=False)
            
            log_channel = self.get_log_channel(member.guild)
            if log_channel:
                await log_channel.send(embed=embed)
            
            logger.info(f"Utilisateur {member.name} mis en quarantaine")
            
        except discord.Forbidden:
            logger.error(f"Impossible de mettre {member.name} en quarantaine (permissions)")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Détection anti-spam et analyse des messages"""
        if not message.guild or message.author.bot:
            return
        
        if not self.config['anti_spam']['enabled']:
            return
        
        # Vérifier la whitelist
        if self.is_whitelisted(message.author):
            return
        
        await self.check_spam(message)
        await self.check_suspicious_content(message)
    
    async def check_spam(self, message):
        """Vérifie le spam de messages"""
        config = self.config['anti_spam']
        user_id = message.author.id
        now = datetime.now()
        
        # Initialiser le tracker pour l'utilisateur
        if user_id not in self.message_tracker:
            self.message_tracker[user_id] = []
        
        # Ajouter le message
        self.message_tracker[user_id].append({
            'content': message.content,
            'time': now,
            'channel': message.channel.id
        })
        
        # Nettoyer les anciens messages
        timeframe = config['timeframe']
        self.message_tracker[user_id] = [
            msg for msg in self.message_tracker[user_id]
            if (now - msg['time']).seconds <= timeframe
        ]
        
        recent_messages = self.message_tracker[user_id]
        
        # Vérifier le nombre de messages
        if len(recent_messages) > config['max_messages']:
            await self.punish_spammer(message.author, "Trop de messages", message.channel)
            return
        
        # Vérifier les doublons
        content_counts = {}
        for msg in recent_messages:
            content = msg['content'].lower().strip()
            content_counts[content] = content_counts.get(content, 0) + 1
        
        for content, count in content_counts.items():
            if count > config['max_duplicates']:
                await self.punish_spammer(message.author, "Messages dupliqués", message.channel)
                return

    async def check_suspicious_content(self, message):
        """Vérifie le contenu suspect"""
        content = message.content.lower()

        # Patterns suspects
        suspicious_patterns = [
            r'discord\.gg/\w+',  # Invitations Discord
            r'@everyone|@here',  # Mentions de masse
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',  # URLs
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, content):
                await self.log_suspicious_message(message, f"Pattern suspect: {pattern}")

    async def punish_spammer(self, member, reason, channel):
        """Punit un spammeur"""
        config = self.config['anti_spam']
        punishment = config['punishment']

        try:
            if punishment == "mute":
                mute_role = discord.utils.get(member.guild.roles, name="Muted")
                if mute_role:
                    await member.add_roles(mute_role, reason=f"Anti-spam: {reason}")
            elif punishment == "kick":
                await member.kick(reason=f"Anti-spam: {reason}")
            elif punishment == "ban":
                await member.ban(reason=f"Anti-spam: {reason}")

            # Log de la punition
            embed = discord.Embed(
                title="⚡ Action anti-spam",
                color=0xe74c3c,
                timestamp=datetime.now()
            )
            embed.add_field(name="👤 Utilisateur", value=f"{member.mention} ({member.id})", inline=False)
            embed.add_field(name="📝 Raison", value=reason, inline=False)
            embed.add_field(name="⚖️ Punition", value=punishment.title(), inline=False)
            embed.add_field(name="📍 Canal", value=channel.mention, inline=False)

            log_channel = self.get_log_channel(member.guild)
            if log_channel:
                await log_channel.send(embed=embed)

            # Nettoyer les messages du spammeur
            await self.cleanup_spam_messages(member, channel)

        except discord.Forbidden:
            logger.error(f"Impossible de punir {member.name} (permissions)")

    async def cleanup_spam_messages(self, member, channel):
        """Nettoie les messages de spam"""
        try:
            async for message in channel.history(limit=50):
                if message.author == member:
                    await message.delete()
        except discord.Forbidden:
            pass

    def is_whitelisted(self, member):
        """Vérifie si un membre est dans la whitelist"""
        whitelist = self.config['whitelist']

        # Vérifier l'utilisateur
        if member.id in whitelist['users']:
            return True

        # Vérifier les rôles
        for role in member.roles:
            if role.id in whitelist['roles']:
                return True

        return False

    def get_log_channel(self, guild):
        """Récupère le canal de logs"""
        log_channel_id = self.config['channels']['logs']
        if log_channel_id:
            return guild.get_channel(log_channel_id)
        return None

    async def notify_admins(self, guild, embed):
        """Notifie les administrateurs"""
        for member in guild.members:
            if member.guild_permissions.administrator and not member.bot:
                try:
                    await member.send(embed=embed)
                except discord.Forbidden:
                    pass

    async def log_member_join(self, member):
        """Log l'arrivée d'un membre"""
        embed = discord.Embed(
            title="📥 Nouveau membre",
            color=0x2ecc71,
            timestamp=datetime.now()
        )
        embed.add_field(name="👤 Utilisateur", value=f"{member.mention} ({member.id})", inline=False)
        embed.add_field(name="📅 Compte créé", value=member.created_at.strftime("%d/%m/%Y %H:%M"), inline=True)
        embed.add_field(name="⏰ Rejoint le", value=member.joined_at.strftime("%d/%m/%Y %H:%M"), inline=True)
        embed.add_field(name="📊 Âge du compte", value=f"{(datetime.now() - member.created_at).days} jours", inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)

        log_channel = self.get_log_channel(member.guild)
        if log_channel:
            await log_channel.send(embed=embed)

    async def log_suspicious_user(self, member, reasons):
        """Log un utilisateur suspect"""
        embed = discord.Embed(
            title="⚠️ Utilisateur suspect détecté",
            color=0xf39c12,
            timestamp=datetime.now()
        )
        embed.add_field(name="👤 Utilisateur", value=f"{member.mention} ({member.id})", inline=False)
        embed.add_field(name="📅 Compte créé", value=member.created_at.strftime("%d/%m/%Y %H:%M"), inline=True)
        embed.add_field(name="⏰ Rejoint le", value=member.joined_at.strftime("%d/%m/%Y %H:%M"), inline=True)
        embed.add_field(name="⚠️ Raisons", value="\n".join(f"• {reason}" for reason in reasons), inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)

        log_channel = self.get_log_channel(member.guild)
        if log_channel:
            await log_channel.send(embed=embed)

    async def log_suspicious_message(self, message, reason):
        """Log un message suspect"""
        embed = discord.Embed(
            title="🚨 Message suspect",
            color=0xe74c3c,
            timestamp=datetime.now()
        )
        embed.add_field(name="👤 Auteur", value=f"{message.author.mention} ({message.author.id})", inline=False)
        embed.add_field(name="📍 Canal", value=message.channel.mention, inline=True)
        embed.add_field(name="📝 Contenu", value=message.content[:1000], inline=False)
        embed.add_field(name="⚠️ Raison", value=reason, inline=False)

        log_channel = self.get_log_channel(message.guild)
        if log_channel:
            await log_channel.send(embed=embed)

    # Commandes de configuration
    @commands.group(name='antiraid', invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def antiraid(self, ctx):
        """Commandes de configuration anti-raid"""
        embed = discord.Embed(
            title="🛡️ Configuration Anti-Raid",
            description="Utilisez les sous-commandes pour configurer le système anti-raid.",
            color=0x3498db
        )
        embed.add_field(
            name="📋 Commandes disponibles",
            value="`!antiraid setup` - Configuration initiale\n"
                  "`!antiraid status` - Statut du système\n"
                  "`!antiraid toggle` - Activer/désactiver\n"
                  "`!antiraid whitelist` - Gérer la whitelist\n"
                  "`!antiraid quarantine` - Gérer la quarantaine",
            inline=False
        )
        await ctx.send(embed=embed)

    @antiraid.command(name='setup')
    @commands.has_permissions(administrator=True)
    async def setup_antiraid(self, ctx):
        """Configuration initiale du système anti-raid"""
        embed = discord.Embed(
            title="⚙️ Configuration Anti-Raid",
            description="Configuration du système de protection anti-raid...",
            color=0x3498db
        )

        # Créer le rôle de quarantaine s'il n'existe pas
        quarantine_role = discord.utils.get(ctx.guild.roles, name="Quarantaine")
        if not quarantine_role:
            quarantine_role = await ctx.guild.create_role(
                name="Quarantaine",
                color=discord.Color.orange(),
                reason="Rôle de quarantaine anti-raid"
            )

            # Configurer les permissions du rôle
            for channel in ctx.guild.channels:
                await channel.set_permissions(quarantine_role, send_messages=False, add_reactions=False)

        # Mettre à jour la config
        self.config['roles']['quarantine'] = quarantine_role.id
        self.save_config()

        embed.add_field(
            name="✅ Rôle de quarantaine",
            value=f"{quarantine_role.mention} créé/configuré",
            inline=False
        )
        embed.add_field(
            name="📝 Prochaines étapes",
            value="1. Configurez le canal de logs avec `!antiraid logs #canal`\n"
                  "2. Ajustez les paramètres si nécessaire\n"
                  "3. Le système est maintenant actif !",
            inline=False
        )

        await ctx.send(embed=embed)

    @antiraid.command(name='status')
    @commands.has_permissions(manage_guild=True)
    async def status_antiraid(self, ctx):
        """Affiche le statut du système anti-raid"""
        config = self.config

        embed = discord.Embed(
            title="📊 Statut Anti-Raid",
            color=0x2ecc71 if config['enabled'] else 0xe74c3c,
            timestamp=datetime.now()
        )

        # Statut général
        status = "🟢 Activé" if config['enabled'] else "🔴 Désactivé"
        raid_status = "🚨 ACTIF" if self.raid_mode else "✅ Normal"

        embed.add_field(name="🛡️ Système", value=status, inline=True)
        embed.add_field(name="⚡ Mode Raid", value=raid_status, inline=True)
        embed.add_field(name="🔒 En quarantaine", value=str(len(self.quarantine_users)), inline=True)

        # Configuration
        embed.add_field(
            name="⚙️ Détection de raid",
            value=f"Seuil: {config['raid_detection']['joins_threshold']} joins en {config['raid_detection']['joins_timeframe']}s",
            inline=False
        )
        embed.add_field(
            name="🚫 Anti-spam",
            value=f"Max messages: {config['anti_spam']['max_messages']} en {config['anti_spam']['timeframe']}s\n"
                  f"Punition: {config['anti_spam']['punishment'].title()}",
            inline=False
        )

        # Statistiques
        recent_joins = len([j for j in self.join_tracker if (datetime.now() - j['time']).seconds < 300])
        embed.add_field(name="📈 Joins récents (5min)", value=str(recent_joins), inline=True)
        embed.add_field(name="💬 Messages trackés", value=str(len(self.message_tracker)), inline=True)

        await ctx.send(embed=embed)

    @antiraid.command(name='toggle')
    @commands.has_permissions(administrator=True)
    async def toggle_antiraid(self, ctx):
        """Active/désactive le système anti-raid"""
        self.config['enabled'] = not self.config['enabled']
        self.save_config()

        status = "activé" if self.config['enabled'] else "désactivé"
        color = 0x2ecc71 if self.config['enabled'] else 0xe74c3c

        embed = discord.Embed(
            title=f"🛡️ Anti-Raid {status.title()}",
            description=f"Le système anti-raid a été **{status}**.",
            color=color
        )
        await ctx.send(embed=embed)

    @antiraid.command(name='logs')
    @commands.has_permissions(administrator=True)
    async def set_logs_channel(self, ctx, channel: discord.TextChannel):
        """Configure le canal de logs"""
        self.config['channels']['logs'] = channel.id
        self.save_config()

        embed = discord.Embed(
            title="📝 Canal de logs configuré",
            description=f"Les logs anti-raid seront envoyés dans {channel.mention}",
            color=0x2ecc71
        )
        await ctx.send(embed=embed)

    @antiraid.command(name='whitelist')
    @commands.has_permissions(administrator=True)
    async def manage_whitelist(self, ctx, action: str, target: discord.Member = None, role: discord.Role = None):
        """Gère la whitelist (add/remove user/role)"""
        if action not in ['add', 'remove']:
            embed = discord.Embed(
                title="❌ Action invalide",
                description="Utilisez `add` ou `remove`",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        if target:
            # Gestion utilisateur
            if action == 'add':
                if target.id not in self.config['whitelist']['users']:
                    self.config['whitelist']['users'].append(target.id)
                    message = f"✅ {target.mention} ajouté à la whitelist"
                else:
                    message = f"ℹ️ {target.mention} est déjà dans la whitelist"
            else:
                if target.id in self.config['whitelist']['users']:
                    self.config['whitelist']['users'].remove(target.id)
                    message = f"✅ {target.mention} retiré de la whitelist"
                else:
                    message = f"ℹ️ {target.mention} n'est pas dans la whitelist"

        elif role:
            # Gestion rôle
            if action == 'add':
                if role.id not in self.config['whitelist']['roles']:
                    self.config['whitelist']['roles'].append(role.id)
                    message = f"✅ {role.mention} ajouté à la whitelist"
                else:
                    message = f"ℹ️ {role.mention} est déjà dans la whitelist"
            else:
                if role.id in self.config['whitelist']['roles']:
                    self.config['whitelist']['roles'].remove(role.id)
                    message = f"✅ {role.mention} retiré de la whitelist"
                else:
                    message = f"ℹ️ {role.mention} n'est pas dans la whitelist"
        else:
            embed = discord.Embed(
                title="❌ Cible manquante",
                description="Spécifiez un utilisateur ou un rôle",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        self.save_config()

        embed = discord.Embed(
            title="🛡️ Whitelist mise à jour",
            description=message,
            color=0x2ecc71
        )
        await ctx.send(embed=embed)

    @antiraid.command(name='quarantine')
    @commands.has_permissions(administrator=True)
    async def manage_quarantine(self, ctx, action: str, member: discord.Member = None):
        """Gère la quarantaine (list/release)"""
        if action == 'list':
            # Lister les utilisateurs en quarantaine
            quarantine_role_id = self.config['roles']['quarantine']
            if not quarantine_role_id:
                embed = discord.Embed(
                    title="❌ Rôle de quarantaine non configuré",
                    description="Utilisez `!antiraid setup` d'abord",
                    color=0xe74c3c
                )
                await ctx.send(embed=embed)
                return

            quarantine_role = ctx.guild.get_role(quarantine_role_id)
            if not quarantine_role:
                embed = discord.Embed(
                    title="❌ Rôle de quarantaine introuvable",
                    color=0xe74c3c
                )
                await ctx.send(embed=embed)
                return

            quarantined_members = [member for member in ctx.guild.members if quarantine_role in member.roles]

            if not quarantined_members:
                embed = discord.Embed(
                    title="✅ Aucun utilisateur en quarantaine",
                    color=0x2ecc71
                )
                await ctx.send(embed=embed)
                return

            embed = discord.Embed(
                title="🔒 Utilisateurs en quarantaine",
                color=0xf39c12
            )

            for i, member in enumerate(quarantined_members[:10]):  # Limite à 10
                embed.add_field(
                    name=f"{i+1}. {member.name}",
                    value=f"ID: {member.id}\nRejoint: {member.joined_at.strftime('%d/%m/%Y')}",
                    inline=True
                )

            if len(quarantined_members) > 10:
                embed.set_footer(text=f"... et {len(quarantined_members) - 10} autres")

            await ctx.send(embed=embed)

        elif action == 'release' and member:
            # Libérer un utilisateur de la quarantaine
            quarantine_role_id = self.config['roles']['quarantine']
            if not quarantine_role_id:
                embed = discord.Embed(
                    title="❌ Rôle de quarantaine non configuré",
                    color=0xe74c3c
                )
                await ctx.send(embed=embed)
                return

            quarantine_role = ctx.guild.get_role(quarantine_role_id)
            if quarantine_role in member.roles:
                await member.remove_roles(quarantine_role, reason=f"Libéré par {ctx.author}")
                self.quarantine_users.discard(member.id)

                embed = discord.Embed(
                    title="✅ Utilisateur libéré",
                    description=f"{member.mention} a été libéré de la quarantaine",
                    color=0x2ecc71
                )
                await ctx.send(embed=embed)

                # Log de la libération
                log_embed = discord.Embed(
                    title="🔓 Libération de quarantaine",
                    color=0x2ecc71,
                    timestamp=datetime.now()
                )
                log_embed.add_field(name="👤 Utilisateur", value=f"{member.mention} ({member.id})", inline=False)
                log_embed.add_field(name="👮 Libéré par", value=f"{ctx.author.mention}", inline=False)

                log_channel = self.get_log_channel(ctx.guild)
                if log_channel:
                    await log_channel.send(embed=log_embed)
            else:
                embed = discord.Embed(
                    title="❌ Utilisateur non en quarantaine",
                    description=f"{member.mention} n'est pas en quarantaine",
                    color=0xe74c3c
                )
                await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Action invalide",
                description="Utilisez `list` ou `release @membre`",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)

    @antiraid.command(name='config')
    @commands.has_permissions(administrator=True)
    async def configure_antiraid(self, ctx, setting: str = None, value: str = None):
        """Configure les paramètres avancés"""
        if not setting:
            # Afficher la configuration actuelle
            embed = discord.Embed(
                title="⚙️ Configuration Anti-Raid",
                color=0x3498db
            )

            config = self.config
            embed.add_field(
                name="🚨 Détection de raid",
                value=f"Seuil: {config['raid_detection']['joins_threshold']} joins\n"
                      f"Délai: {config['raid_detection']['joins_timeframe']}s\n"
                      f"Auto-quarantaine: {config['raid_detection']['auto_quarantine']}",
                inline=False
            )
            embed.add_field(
                name="🚫 Anti-spam",
                value=f"Max messages: {config['anti_spam']['max_messages']}\n"
                      f"Délai: {config['anti_spam']['timeframe']}s\n"
                      f"Max doublons: {config['anti_spam']['max_duplicates']}\n"
                      f"Punition: {config['anti_spam']['punishment']}",
                inline=False
            )
            embed.add_field(
                name="✅ Vérification",
                value=f"Âge min compte: {config['verification']['min_account_age']} jours\n"
                      f"Avatar requis: {config['verification']['require_avatar']}\n"
                      f"Auto-quarantaine nouveaux: {config['verification']['auto_quarantine_new']}",
                inline=False
            )

            await ctx.send(embed=embed)
            return

        # Modifier un paramètre
        valid_settings = {
            'joins_threshold': ('raid_detection', 'joins_threshold', int),
            'joins_timeframe': ('raid_detection', 'joins_timeframe', int),
            'max_messages': ('anti_spam', 'max_messages', int),
            'spam_timeframe': ('anti_spam', 'timeframe', int),
            'max_duplicates': ('anti_spam', 'max_duplicates', int),
            'punishment': ('anti_spam', 'punishment', str),
            'min_account_age': ('verification', 'min_account_age', int),
        }

        if setting not in valid_settings:
            embed = discord.Embed(
                title="❌ Paramètre invalide",
                description=f"Paramètres disponibles: {', '.join(valid_settings.keys())}",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        if not value:
            embed = discord.Embed(
                title="❌ Valeur manquante",
                description="Spécifiez une valeur pour le paramètre",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        section, key, value_type = valid_settings[setting]

        try:
            if value_type == int:
                new_value = int(value)
            elif value_type == str:
                new_value = value
                if setting == 'punishment' and new_value not in ['mute', 'kick', 'ban']:
                    raise ValueError("Punition doit être: mute, kick, ou ban")

            self.config[section][key] = new_value
            self.save_config()

            embed = discord.Embed(
                title="✅ Configuration mise à jour",
                description=f"**{setting}** = `{new_value}`",
                color=0x2ecc71
            )
            await ctx.send(embed=embed)

        except ValueError as e:
            embed = discord.Embed(
                title="❌ Valeur invalide",
                description=str(e),
                color=0xe74c3c
            )
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AntiRaid(bot))
