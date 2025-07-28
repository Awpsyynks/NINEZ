import discord
from discord.ext import commands
import re
import json
import logging
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger('discord_bot.automod')

class AutoMod(commands.Cog):
    """Système d'automodération intelligent"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config = self.load_config()
        self.word_filters = self.load_word_filters()
        self.user_violations = {}  # Tracking des violations par utilisateur
        
    def load_config(self):
        """Charge la configuration d'automodération"""
        try:
            with open('automod_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            default_config = {
                "enabled": True,
                "filters": {
                    "profanity": {
                        "enabled": True,
                        "action": "delete",  # delete, warn, mute, kick, ban
                        "punishment_escalation": True
                    },
                    "spam": {
                        "enabled": True,
                        "max_mentions": 5,
                        "max_emojis": 10,
                        "max_caps_percentage": 70,
                        "action": "warn"
                    },
                    "links": {
                        "enabled": True,
                        "whitelist": [],
                        "block_invites": True,
                        "block_suspicious": True,
                        "action": "delete"
                    },
                    "zalgo": {
                        "enabled": True,
                        "action": "delete"
                    },
                    "repeated_text": {
                        "enabled": True,
                        "max_repeated_chars": 5,
                        "action": "warn"
                    }
                },
                "punishments": {
                    "escalation_enabled": True,
                    "escalation_steps": ["warn", "mute", "kick", "ban"],
                    "mute_duration": 600,  # 10 minutes
                    "reset_violations_after": 86400  # 24 heures
                },
                "channels": {
                    "logs": None,
                    "ignored": []
                },
                "roles": {
                    "ignored": [],
                    "muted": None
                },
                "whitelist": {
                    "users": [],
                    "roles": []
                }
            }
            self.save_config(default_config)
            return default_config
    
    def load_word_filters(self):
        """Charge les filtres de mots"""
        try:
            with open('word_filters.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            default_filters = {
                "profanity": [
                    # Mots grossiers en français (version censurée pour l'exemple)
                    "c*n", "s*lope", "enc*lé",
                    # Ajoutez vos propres mots selon vos besoins
                ],
                "slurs": [
                    # Insultes discriminatoires (version censurée)
                    # Ajoutez selon vos besoins de modération
                ],
                "spam_words": [
                    "discord.gg", "bit.ly", "tinyurl", "free nitro", "giveaway"
                ]
            }
            self.save_word_filters(default_filters)
            return default_filters
    
    def save_config(self, config=None):
        """Sauvegarde la configuration"""
        if config is None:
            config = self.config
        try:
            with open('automod_config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erreur sauvegarde config automod: {e}")
    
    def save_word_filters(self, filters=None):
        """Sauvegarde les filtres de mots"""
        if filters is None:
            filters = self.word_filters
        try:
            with open('word_filters.json', 'w', encoding='utf-8') as f:
                json.dump(filters, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erreur sauvegarde filtres: {e}")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Analyse automatique des messages"""
        if not message.guild or message.author.bot:
            return
        
        if not self.config['enabled']:
            return
        
        # Vérifier les exemptions
        if self.is_exempt(message.author, message.channel):
            return
        
        # Analyser le message
        violations = await self.analyze_message(message)
        
        if violations:
            await self.handle_violations(message, violations)
    
    def is_exempt(self, member, channel):
        """Vérifie si un membre/canal est exempté"""
        # Canaux ignorés
        if channel.id in self.config['channels']['ignored']:
            return True
        
        # Utilisateurs whitelist
        if member.id in self.config['whitelist']['users']:
            return True
        
        # Rôles ignorés/whitelist
        for role in member.roles:
            if role.id in self.config['roles']['ignored'] or role.id in self.config['whitelist']['roles']:
                return True
        
        # Permissions de modération
        if member.guild_permissions.manage_messages:
            return True
        
        return False
    
    async def analyze_message(self, message):
        """Analyse un message et retourne les violations"""
        violations = []
        content = message.content
        
        # Filtre de grossièretés
        if self.config['filters']['profanity']['enabled']:
            if self.contains_profanity(content):
                violations.append({
                    'type': 'profanity',
                    'reason': 'Langage inapproprié détecté',
                    'action': self.config['filters']['profanity']['action']
                })
        
        # Filtre de spam
        if self.config['filters']['spam']['enabled']:
            spam_violations = self.check_spam_content(content, message)
            violations.extend(spam_violations)
        
        # Filtre de liens
        if self.config['filters']['links']['enabled']:
            link_violations = self.check_links(content)
            violations.extend(link_violations)
        
        # Filtre Zalgo/caractères spéciaux
        if self.config['filters']['zalgo']['enabled']:
            if self.contains_zalgo(content):
                violations.append({
                    'type': 'zalgo',
                    'reason': 'Caractères spéciaux/Zalgo détectés',
                    'action': self.config['filters']['zalgo']['action']
                })
        
        # Filtre de texte répété
        if self.config['filters']['repeated_text']['enabled']:
            if self.contains_repeated_text(content):
                violations.append({
                    'type': 'repeated_text',
                    'reason': 'Texte répétitif détecté',
                    'action': self.config['filters']['repeated_text']['action']
                })
        
        return violations
    
    def contains_profanity(self, content):
        """Vérifie si le contenu contient des grossièretés"""
        content_lower = content.lower()
        
        for word in self.word_filters['profanity']:
            # Remplacer les * par des caractères quelconques
            pattern = word.replace('*', r'[a-zA-Z0-9@#$%^&*()_+\-=\[\]{}|;:,.<>?]')
            if re.search(pattern, content_lower):
                return True
        
        return False
    
    def check_spam_content(self, content, message):
        """Vérifie le contenu spam"""
        violations = []
        config = self.config['filters']['spam']
        
        # Vérifier les mentions excessives
        mentions = len(message.mentions) + len(message.role_mentions)
        if mentions > config['max_mentions']:
            violations.append({
                'type': 'spam_mentions',
                'reason': f'Trop de mentions ({mentions})',
                'action': config['action']
            })
        
        # Vérifier les emojis excessifs
        emoji_count = len(re.findall(r'<:[^:]+:\d+>|[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', content))
        if emoji_count > config['max_emojis']:
            violations.append({
                'type': 'spam_emojis',
                'reason': f'Trop d\'emojis ({emoji_count})',
                'action': config['action']
            })
        
        # Vérifier les majuscules excessives
        if len(content) > 10:
            caps_count = sum(1 for c in content if c.isupper())
            caps_percentage = (caps_count / len(content)) * 100
            if caps_percentage > config['max_caps_percentage']:
                violations.append({
                    'type': 'spam_caps',
                    'reason': f'Trop de majuscules ({caps_percentage:.1f}%)',
                    'action': config['action']
                })
        
        return violations
    
    def check_links(self, content):
        """Vérifie les liens suspects"""
        violations = []
        config = self.config['filters']['links']
        
        # Détecter les URLs
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, content)
        
        for url in urls:
            # Vérifier la whitelist
            if any(domain in url for domain in config['whitelist']):
                continue
            
            # Vérifier les invitations Discord
            if config['block_invites'] and ('discord.gg' in url or 'discordapp.com/invite' in url):
                violations.append({
                    'type': 'discord_invite',
                    'reason': 'Invitation Discord non autorisée',
                    'action': config['action']
                })
            
            # Vérifier les liens suspects
            if config['block_suspicious']:
                suspicious_domains = ['bit.ly', 'tinyurl.com', 'goo.gl', 't.co']
                if any(domain in url for domain in suspicious_domains):
                    violations.append({
                        'type': 'suspicious_link',
                        'reason': 'Lien raccourci suspect',
                        'action': config['action']
                    })
        
        return violations
    
    def contains_zalgo(self, content):
        """Détecte les caractères Zalgo"""
        zalgo_chars = [
            '\u0300', '\u0301', '\u0302', '\u0303', '\u0304', '\u0305', '\u0306', '\u0307',
            '\u0308', '\u0309', '\u030A', '\u030B', '\u030C', '\u030D', '\u030E', '\u030F'
        ]
        
        zalgo_count = sum(content.count(char) for char in zalgo_chars)
        return zalgo_count > 5  # Seuil de détection
    
    def contains_repeated_text(self, content):
        """Détecte le texte répétitif"""
        max_repeated = self.config['filters']['repeated_text']['max_repeated_chars']
        
        # Vérifier les caractères répétés
        for i in range(len(content) - max_repeated):
            char = content[i]
            if content[i:i+max_repeated+1] == char * (max_repeated + 1):
                return True
        
        return False
    
    async def handle_violations(self, message, violations):
        """Gère les violations détectées"""
        user_id = message.author.id
        
        # Initialiser le tracking des violations
        if user_id not in self.user_violations:
            self.user_violations[user_id] = {
                'count': 0,
                'last_violation': datetime.now(),
                'violations': []
            }
        
        # Ajouter les violations
        for violation in violations:
            self.user_violations[user_id]['violations'].append({
                'type': violation['type'],
                'reason': violation['reason'],
                'timestamp': datetime.now(),
                'message_id': message.id
            })
        
        self.user_violations[user_id]['count'] += len(violations)
        self.user_violations[user_id]['last_violation'] = datetime.now()
        
        # Supprimer le message si nécessaire
        if any(v['action'] == 'delete' for v in violations):
            try:
                await message.delete()
            except discord.NotFound:
                pass
        
        # Appliquer les punitions
        await self.apply_punishment(message.author, violations)
        
        # Logger les violations
        await self.log_violations(message, violations)
    
    async def apply_punishment(self, member, violations):
        """Applique les punitions selon l'escalade"""
        if not self.config['punishments']['escalation_enabled']:
            # Appliquer la punition directe
            for violation in violations:
                await self.execute_action(member, violation['action'], violation['reason'])
            return
        
        # Système d'escalade
        user_data = self.user_violations[member.id]
        violation_count = user_data['count']
        
        escalation_steps = self.config['punishments']['escalation_steps']
        
        # Déterminer l'étape d'escalade
        step_index = min(violation_count - 1, len(escalation_steps) - 1)
        action = escalation_steps[step_index]
        
        reason = f"Automodération - {violation_count} violation(s)"
        await self.execute_action(member, action, reason)
    
    async def execute_action(self, member, action, reason):
        """Exécute une action de punition"""
        try:
            if action == "warn":
                # Ajouter un avertissement (intégration avec le système existant)
                if hasattr(self.bot, 'warnings'):
                    if member.id not in self.bot.warnings:
                        self.bot.warnings[member.id] = 0
                    self.bot.warnings[member.id] += 1
                
            elif action == "mute":
                mute_role_id = self.config['roles']['muted']
                if mute_role_id:
                    mute_role = member.guild.get_role(mute_role_id)
                    if mute_role:
                        await member.add_roles(mute_role, reason=reason)
                        
                        # Démute automatique
                        duration = self.config['punishments']['mute_duration']
                        await asyncio.sleep(duration)
                        await member.remove_roles(mute_role, reason="Démute automatique")
                
            elif action == "kick":
                await member.kick(reason=reason)
                
            elif action == "ban":
                await member.ban(reason=reason)
                
        except discord.Forbidden:
            logger.error(f"Permissions insuffisantes pour {action} {member.name}")
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de {action}: {e}")
    
    async def log_violations(self, message, violations):
        """Log les violations dans le canal de logs"""
        log_channel_id = self.config['channels']['logs']
        if not log_channel_id:
            return
        
        log_channel = message.guild.get_channel(log_channel_id)
        if not log_channel:
            return
        
        embed = discord.Embed(
            title="🤖 Automodération - Violation détectée",
            color=0xe74c3c,
            timestamp=datetime.now()
        )
        
        embed.add_field(name="👤 Utilisateur", value=f"{message.author.mention} ({message.author.id})", inline=False)
        embed.add_field(name="📍 Canal", value=message.channel.mention, inline=True)
        embed.add_field(name="📝 Message", value=message.content[:500] if message.content else "Aucun contenu", inline=False)
        
        violations_text = "\n".join(f"• {v['reason']}" for v in violations)
        embed.add_field(name="⚠️ Violations", value=violations_text, inline=False)
        
        user_data = self.user_violations.get(message.author.id, {})
        embed.add_field(name="📊 Total violations", value=str(user_data.get('count', 0)), inline=True)
        
        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            logger.error("Permissions insuffisantes pour envoyer dans le canal de logs")

    # Commandes de configuration
    @commands.group(name='automod', invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def automod(self, ctx):
        """Commandes d'automodération"""
        embed = discord.Embed(
            title="🤖 Automodération",
            description="Système d'automodération intelligent",
            color=0x3498db
        )
        embed.add_field(
            name="📋 Commandes disponibles",
            value="`!automod status` - Statut du système\n"
                  "`!automod toggle` - Activer/désactiver\n"
                  "`!automod setup` - Configuration initiale\n"
                  "`!automod filters` - Gérer les filtres\n"
                  "`!automod whitelist` - Gérer la whitelist\n"
                  "`!automod violations @user` - Voir les violations",
            inline=False
        )
        await ctx.send(embed=embed)

    @automod.command(name='status')
    @commands.has_permissions(manage_guild=True)
    async def automod_status(self, ctx):
        """Affiche le statut de l'automodération"""
        config = self.config

        embed = discord.Embed(
            title="📊 Statut Automodération",
            color=0x2ecc71 if config['enabled'] else 0xe74c3c,
            timestamp=datetime.now()
        )

        status = "🟢 Activé" if config['enabled'] else "🔴 Désactivé"
        embed.add_field(name="🤖 Système", value=status, inline=True)
        embed.add_field(name="👥 Violations trackées", value=str(len(self.user_violations)), inline=True)

        # Filtres actifs
        active_filters = []
        for filter_name, filter_config in config['filters'].items():
            if filter_config['enabled']:
                active_filters.append(filter_name.title())

        embed.add_field(
            name="🔍 Filtres actifs",
            value=", ".join(active_filters) if active_filters else "Aucun",
            inline=False
        )

        # Statistiques récentes
        recent_violations = 0
        for user_data in self.user_violations.values():
            if (datetime.now() - user_data['last_violation']).days < 1:
                recent_violations += 1

        embed.add_field(name="📈 Violations (24h)", value=str(recent_violations), inline=True)

        await ctx.send(embed=embed)

    @automod.command(name='toggle')
    @commands.has_permissions(administrator=True)
    async def toggle_automod(self, ctx):
        """Active/désactive l'automodération"""
        self.config['enabled'] = not self.config['enabled']
        self.save_config()

        status = "activée" if self.config['enabled'] else "désactivée"
        color = 0x2ecc71 if self.config['enabled'] else 0xe74c3c

        embed = discord.Embed(
            title=f"🤖 Automodération {status.title()}",
            description=f"L'automodération a été **{status}**.",
            color=color
        )
        await ctx.send(embed=embed)

    @automod.command(name='setup')
    @commands.has_permissions(administrator=True)
    async def setup_automod(self, ctx):
        """Configuration initiale de l'automodération"""
        embed = discord.Embed(
            title="⚙️ Configuration Automodération",
            description="Configuration du système d'automodération...",
            color=0x3498db
        )

        # Créer le rôle Muted s'il n'existe pas
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not muted_role:
            muted_role = await ctx.guild.create_role(
                name="Muted",
                color=discord.Color.dark_grey(),
                reason="Rôle de mute pour l'automodération"
            )

            # Configurer les permissions
            for channel in ctx.guild.channels:
                await channel.set_permissions(muted_role, send_messages=False, add_reactions=False)

        # Mettre à jour la config
        self.config['roles']['muted'] = muted_role.id
        self.save_config()

        embed.add_field(
            name="✅ Rôle Muted",
            value=f"{muted_role.mention} créé/configuré",
            inline=False
        )
        embed.add_field(
            name="📝 Prochaines étapes",
            value="1. Configurez le canal de logs avec `!automod logs #canal`\n"
                  "2. Ajustez les filtres selon vos besoins\n"
                  "3. Le système est maintenant actif !",
            inline=False
        )

        await ctx.send(embed=embed)

    @automod.command(name='logs')
    @commands.has_permissions(administrator=True)
    async def set_automod_logs(self, ctx, channel: discord.TextChannel):
        """Configure le canal de logs d'automodération"""
        self.config['channels']['logs'] = channel.id
        self.save_config()

        embed = discord.Embed(
            title="📝 Canal de logs configuré",
            description=f"Les logs d'automodération seront envoyés dans {channel.mention}",
            color=0x2ecc71
        )
        await ctx.send(embed=embed)

    @automod.command(name='filters')
    @commands.has_permissions(manage_guild=True)
    async def manage_filters(self, ctx, filter_name: str = None, action: str = None):
        """Gère les filtres d'automodération"""
        if not filter_name:
            # Afficher tous les filtres
            embed = discord.Embed(
                title="🔍 Filtres d'Automodération",
                color=0x3498db
            )

            for name, config in self.config['filters'].items():
                status = "🟢 Activé" if config['enabled'] else "🔴 Désactivé"
                action_text = config.get('action', 'N/A')
                embed.add_field(
                    name=f"{name.title()}",
                    value=f"Statut: {status}\nAction: {action_text}",
                    inline=True
                )

            embed.add_field(
                name="💡 Utilisation",
                value="`!automod filters <nom> toggle` - Activer/désactiver\n"
                      "`!automod filters <nom> action <action>` - Changer l'action",
                inline=False
            )

            await ctx.send(embed=embed)
            return

        if filter_name not in self.config['filters']:
            embed = discord.Embed(
                title="❌ Filtre invalide",
                description=f"Filtres disponibles: {', '.join(self.config['filters'].keys())}",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        if action == 'toggle':
            # Basculer l'état du filtre
            self.config['filters'][filter_name]['enabled'] = not self.config['filters'][filter_name]['enabled']
            self.save_config()

            status = "activé" if self.config['filters'][filter_name]['enabled'] else "désactivé"
            embed = discord.Embed(
                title="✅ Filtre mis à jour",
                description=f"Le filtre **{filter_name}** a été **{status}**.",
                color=0x2ecc71
            )
            await ctx.send(embed=embed)

        elif action == 'action':
            embed = discord.Embed(
                title="⚙️ Actions disponibles",
                description="Actions possibles: `delete`, `warn`, `mute`, `kick`, `ban`\n"
                           "Utilisez: `!automod filters " + filter_name + " action <action>`",
                color=0x3498db
            )
            await ctx.send(embed=embed)

        else:
            # Changer l'action du filtre
            valid_actions = ['delete', 'warn', 'mute', 'kick', 'ban']
            if action in valid_actions:
                self.config['filters'][filter_name]['action'] = action
                self.save_config()

                embed = discord.Embed(
                    title="✅ Action mise à jour",
                    description=f"L'action du filtre **{filter_name}** est maintenant **{action}**.",
                    color=0x2ecc71
                )
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="❌ Action invalide",
                    description=f"Actions valides: {', '.join(valid_actions)}",
                    color=0xe74c3c
                )
                await ctx.send(embed=embed)

    @automod.command(name='violations')
    @commands.has_permissions(manage_guild=True)
    async def view_violations(self, ctx, member: discord.Member):
        """Affiche les violations d'un utilisateur"""
        user_id = member.id

        if user_id not in self.user_violations:
            embed = discord.Embed(
                title="✅ Aucune violation",
                description=f"{member.mention} n'a aucune violation enregistrée.",
                color=0x2ecc71
            )
            await ctx.send(embed=embed)
            return

        user_data = self.user_violations[user_id]

        embed = discord.Embed(
            title=f"📊 Violations de {member.display_name}",
            color=0xf39c12,
            timestamp=datetime.now()
        )

        embed.add_field(name="📈 Total violations", value=str(user_data['count']), inline=True)
        embed.add_field(name="⏰ Dernière violation", value=user_data['last_violation'].strftime("%d/%m/%Y %H:%M"), inline=True)

        # Afficher les dernières violations
        recent_violations = user_data['violations'][-5:]  # 5 dernières
        if recent_violations:
            violations_text = ""
            for v in recent_violations:
                violations_text += f"• **{v['type']}**: {v['reason']}\n"
                violations_text += f"  _{v['timestamp'].strftime('%d/%m %H:%M')}_\n"

            embed.add_field(name="🔍 Violations récentes", value=violations_text[:1000], inline=False)

        embed.set_thumbnail(url=member.display_avatar.url)

        await ctx.send(embed=embed)

    @automod.command(name='whitelist')
    @commands.has_permissions(administrator=True)
    async def manage_automod_whitelist(self, ctx, action: str, target: discord.Member = None, role: discord.Role = None):
        """Gère la whitelist d'automodération"""
        if action not in ['add', 'remove', 'list']:
            embed = discord.Embed(
                title="❌ Action invalide",
                description="Utilisez `add`, `remove`, ou `list`",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        if action == 'list':
            embed = discord.Embed(
                title="📋 Whitelist Automodération",
                color=0x3498db
            )

            # Utilisateurs
            users = []
            for user_id in self.config['whitelist']['users']:
                user = ctx.guild.get_member(user_id)
                if user:
                    users.append(user.mention)

            embed.add_field(
                name="👥 Utilisateurs",
                value="\n".join(users) if users else "Aucun",
                inline=False
            )

            # Rôles
            roles = []
            for role_id in self.config['whitelist']['roles']:
                role = ctx.guild.get_role(role_id)
                if role:
                    roles.append(role.mention)

            embed.add_field(
                name="🎭 Rôles",
                value="\n".join(roles) if roles else "Aucun",
                inline=False
            )

            await ctx.send(embed=embed)
            return

        # Ajouter/retirer de la whitelist
        if target:
            whitelist_key = 'users'
            target_id = target.id
            target_mention = target.mention
        elif role:
            whitelist_key = 'roles'
            target_id = role.id
            target_mention = role.mention
        else:
            embed = discord.Embed(
                title="❌ Cible manquante",
                description="Spécifiez un utilisateur ou un rôle",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        if action == 'add':
            if target_id not in self.config['whitelist'][whitelist_key]:
                self.config['whitelist'][whitelist_key].append(target_id)
                message = f"✅ {target_mention} ajouté à la whitelist"
            else:
                message = f"ℹ️ {target_mention} est déjà dans la whitelist"
        else:  # remove
            if target_id in self.config['whitelist'][whitelist_key]:
                self.config['whitelist'][whitelist_key].remove(target_id)
                message = f"✅ {target_mention} retiré de la whitelist"
            else:
                message = f"ℹ️ {target_mention} n'est pas dans la whitelist"

        self.save_config()

        embed = discord.Embed(
            title="🛡️ Whitelist mise à jour",
            description=message,
            color=0x2ecc71
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AutoMod(bot))
