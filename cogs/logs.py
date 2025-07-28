import discord
from discord.ext import commands
import json
import logging
from datetime import datetime, timedelta
import asyncio
import aiohttp

logger = logging.getLogger('discord_bot.logs')

class Logs(commands.Cog):
    """Système de logs et audit complet"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config = self.load_config()
        self.log_cache = []  # Cache pour les logs récents
        
    def load_config(self):
        """Charge la configuration des logs"""
        try:
            with open('logs_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            default_config = {
                "enabled": True,
                "channels": {
                    "general": None,
                    "moderation": None,
                    "member": None,
                    "message": None,
                    "voice": None,
                    "server": None
                },
                "webhooks": {
                    "general": None,
                    "moderation": None,
                    "member": None,
                    "message": None,
                    "voice": None,
                    "server": None
                },
                "events": {
                    "member_join": True,
                    "member_leave": True,
                    "member_update": True,
                    "member_ban": True,
                    "member_unban": True,
                    "message_delete": True,
                    "message_edit": True,
                    "message_bulk_delete": True,
                    "voice_join": True,
                    "voice_leave": True,
                    "voice_move": True,
                    "role_create": True,
                    "role_delete": True,
                    "role_update": True,
                    "channel_create": True,
                    "channel_delete": True,
                    "channel_update": True,
                    "guild_update": True,
                    "emoji_update": True,
                    "invite_create": True,
                    "invite_delete": True
                },
                "filters": {
                    "ignore_bots": True,
                    "ignore_webhooks": True,
                    "min_message_length": 0,
                    "ignored_channels": [],
                    "ignored_users": [],
                    "ignored_roles": []
                },
                "archive": {
                    "enabled": True,
                    "days_to_keep": 30,
                    "auto_cleanup": True
                }
            }
            self.save_config(default_config)
            return default_config
    
    def save_config(self, config=None):
        """Sauvegarde la configuration"""
        if config is None:
            config = self.config
        try:
            with open('logs_config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erreur sauvegarde config logs: {e}")
    
    def should_log_event(self, event_type, **kwargs):
        """Vérifie si un événement doit être loggé"""
        if not self.config['enabled']:
            return False
        
        if not self.config['events'].get(event_type, False):
            return False
        
        # Filtres
        filters = self.config['filters']
        
        # Ignorer les bots
        if filters['ignore_bots'] and 'user' in kwargs:
            if kwargs['user'].bot:
                return False
        
        # Ignorer les webhooks
        if filters['ignore_webhooks'] and 'webhook' in kwargs:
            if kwargs['webhook']:
                return False
        
        # Canaux ignorés
        if 'channel' in kwargs:
            if kwargs['channel'].id in filters['ignored_channels']:
                return False
        
        # Utilisateurs ignorés
        if 'user' in kwargs:
            if kwargs['user'].id in filters['ignored_users']:
                return False
        
        # Rôles ignorés
        if 'member' in kwargs:
            for role in kwargs['member'].roles:
                if role.id in filters['ignored_roles']:
                    return False
        
        return True
    
    async def send_log(self, log_type, embed, guild):
        """Envoie un log dans le canal approprié"""
        channel_id = self.config['channels'].get(log_type)
        webhook_url = self.config['webhooks'].get(log_type)
        
        # Envoyer via webhook si configuré
        if webhook_url:
            try:
                async with aiohttp.ClientSession() as session:
                    webhook = discord.Webhook.from_url(webhook_url, session=session)
                    await webhook.send(embed=embed)
                return
            except Exception as e:
                logger.error(f"Erreur webhook {log_type}: {e}")
        
        # Envoyer via canal si configuré
        if channel_id:
            channel = guild.get_channel(channel_id)
            if channel:
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    logger.error(f"Permissions insuffisantes pour le canal de logs {log_type}")
    
    # Événements de membres
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Log l'arrivée d'un membre"""
        if not self.should_log_event('member_join', user=member):
            return
        
        embed = discord.Embed(
            title="📥 Membre rejoint",
            color=0x2ecc71,
            timestamp=datetime.now()
        )
        
        embed.add_field(name="👤 Utilisateur", value=f"{member.mention} ({member.id})", inline=False)
        embed.add_field(name="📅 Compte créé", value=member.created_at.strftime("%d/%m/%Y %H:%M"), inline=True)
        embed.add_field(name="⏰ Rejoint le", value=member.joined_at.strftime("%d/%m/%Y %H:%M"), inline=True)
        embed.add_field(name="📊 Âge du compte", value=f"{(datetime.now() - member.created_at).days} jours", inline=True)
        embed.add_field(name="👥 Nombre de membres", value=str(member.guild.member_count), inline=True)
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"ID: {member.id}")
        
        await self.send_log('member', embed, member.guild)
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Log le départ d'un membre"""
        if not self.should_log_event('member_leave', user=member):
            return
        
        embed = discord.Embed(
            title="📤 Membre parti",
            color=0xe74c3c,
            timestamp=datetime.now()
        )
        
        embed.add_field(name="👤 Utilisateur", value=f"{member.mention} ({member.id})", inline=False)
        embed.add_field(name="⏰ Rejoint le", value=member.joined_at.strftime("%d/%m/%Y %H:%M") if member.joined_at else "Inconnu", inline=True)
        embed.add_field(name="📊 Temps sur le serveur", value=str(datetime.now() - member.joined_at).days + " jours" if member.joined_at else "Inconnu", inline=True)
        embed.add_field(name="👥 Nombre de membres", value=str(member.guild.member_count), inline=True)
        
        # Afficher les rôles qu'il avait
        if member.roles[1:]:  # Exclure @everyone
            roles = ", ".join([role.mention for role in member.roles[1:]])
            embed.add_field(name="🎭 Rôles", value=roles[:1000], inline=False)
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"ID: {member.id}")
        
        await self.send_log('member', embed, member.guild)
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Log les modifications de membre"""
        if not self.should_log_event('member_update', member=after):
            return
        
        changes = []
        
        # Changement de pseudo
        if before.display_name != after.display_name:
            changes.append(f"**Pseudo:** {before.display_name} → {after.display_name}")
        
        # Changement de rôles
        if before.roles != after.roles:
            added_roles = set(after.roles) - set(before.roles)
            removed_roles = set(before.roles) - set(after.roles)
            
            if added_roles:
                roles_text = ", ".join([role.mention for role in added_roles])
                changes.append(f"**Rôles ajoutés:** {roles_text}")
            
            if removed_roles:
                roles_text = ", ".join([role.mention for role in removed_roles])
                changes.append(f"**Rôles retirés:** {roles_text}")
        
        if not changes:
            return
        
        embed = discord.Embed(
            title="✏️ Membre modifié",
            color=0xf39c12,
            timestamp=datetime.now()
        )
        
        embed.add_field(name="👤 Utilisateur", value=f"{after.mention} ({after.id})", inline=False)
        embed.add_field(name="📝 Modifications", value="\n".join(changes), inline=False)
        
        embed.set_thumbnail(url=after.display_avatar.url)
        embed.set_footer(text=f"ID: {after.id}")
        
        await self.send_log('member', embed, after.guild)
    
    # Événements de messages
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Log la suppression de messages"""
        if not self.should_log_event('message_delete', user=message.author, channel=message.channel):
            return
        
        if len(message.content) < self.config['filters']['min_message_length']:
            return
        
        embed = discord.Embed(
            title="🗑️ Message supprimé",
            color=0xe74c3c,
            timestamp=datetime.now()
        )
        
        embed.add_field(name="👤 Auteur", value=f"{message.author.mention} ({message.author.id})", inline=False)
        embed.add_field(name="📍 Canal", value=message.channel.mention, inline=True)
        embed.add_field(name="⏰ Envoyé le", value=message.created_at.strftime("%d/%m/%Y %H:%M"), inline=True)
        
        # Contenu du message (limité)
        content = message.content[:1000] if message.content else "*Aucun contenu texte*"
        embed.add_field(name="📝 Contenu", value=content, inline=False)
        
        # Pièces jointes
        if message.attachments:
            attachments = "\n".join([f"• {att.filename}" for att in message.attachments])
            embed.add_field(name="📎 Pièces jointes", value=attachments[:500], inline=False)
        
        embed.set_thumbnail(url=message.author.display_avatar.url)
        embed.set_footer(text=f"Message ID: {message.id}")
        
        await self.send_log('message', embed, message.guild)
    
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Log l'édition de messages"""
        if not self.should_log_event('message_edit', user=after.author, channel=after.channel):
            return
        
        if before.content == after.content:
            return
        
        if len(before.content) < self.config['filters']['min_message_length']:
            return
        
        embed = discord.Embed(
            title="✏️ Message modifié",
            color=0xf39c12,
            timestamp=datetime.now()
        )
        
        embed.add_field(name="👤 Auteur", value=f"{after.author.mention} ({after.author.id})", inline=False)
        embed.add_field(name="📍 Canal", value=after.channel.mention, inline=True)
        embed.add_field(name="🔗 Lien", value=f"[Aller au message]({after.jump_url})", inline=True)
        
        # Contenu avant/après
        before_content = before.content[:500] if before.content else "*Aucun contenu*"
        after_content = after.content[:500] if after.content else "*Aucun contenu*"
        
        embed.add_field(name="📝 Avant", value=before_content, inline=False)
        embed.add_field(name="📝 Après", value=after_content, inline=False)
        
        embed.set_thumbnail(url=after.author.display_avatar.url)
        embed.set_footer(text=f"Message ID: {after.id}")
        
        await self.send_log('message', embed, after.guild)
    
    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        """Log la suppression en masse de messages"""
        if not messages:
            return
        
        guild = messages[0].guild
        channel = messages[0].channel
        
        if not self.should_log_event('message_bulk_delete', channel=channel):
            return
        
        embed = discord.Embed(
            title="🗑️ Suppression en masse",
            color=0xe74c3c,
            timestamp=datetime.now()
        )
        
        embed.add_field(name="📍 Canal", value=channel.mention, inline=True)
        embed.add_field(name="📊 Nombre", value=str(len(messages)), inline=True)
        
        # Auteurs des messages supprimés
        authors = {}
        for msg in messages:
            if msg.author.id in authors:
                authors[msg.author.id] += 1
            else:
                authors[msg.author.id] = 1
        
        authors_text = ""
        for author_id, count in sorted(authors.items(), key=lambda x: x[1], reverse=True)[:5]:
            user = guild.get_member(author_id)
            if user:
                authors_text += f"• {user.mention}: {count} message(s)\n"
        
        if authors_text:
            embed.add_field(name="👥 Auteurs principaux", value=authors_text, inline=False)
        
        embed.set_footer(text=f"Canal ID: {channel.id}")
        
        await self.send_log('message', embed, guild)

    # Événements vocaux
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Log les changements d'état vocal"""
        if not self.should_log_event('voice_join', member=member):
            return

        # Rejoindre un canal
        if before.channel is None and after.channel is not None:
            embed = discord.Embed(
                title="🔊 Rejoint un canal vocal",
                color=0x2ecc71,
                timestamp=datetime.now()
            )
            embed.add_field(name="👤 Utilisateur", value=f"{member.mention} ({member.id})", inline=False)
            embed.add_field(name="📍 Canal", value=after.channel.mention, inline=True)
            embed.set_thumbnail(url=member.display_avatar.url)
            await self.send_log('voice', embed, member.guild)

        # Quitter un canal
        elif before.channel is not None and after.channel is None:
            embed = discord.Embed(
                title="🔇 Quitté un canal vocal",
                color=0xe74c3c,
                timestamp=datetime.now()
            )
            embed.add_field(name="👤 Utilisateur", value=f"{member.mention} ({member.id})", inline=False)
            embed.add_field(name="📍 Canal", value=before.channel.mention, inline=True)
            embed.set_thumbnail(url=member.display_avatar.url)
            await self.send_log('voice', embed, member.guild)

        # Changer de canal
        elif before.channel != after.channel and before.channel is not None and after.channel is not None:
            embed = discord.Embed(
                title="🔄 Changé de canal vocal",
                color=0xf39c12,
                timestamp=datetime.now()
            )
            embed.add_field(name="👤 Utilisateur", value=f"{member.mention} ({member.id})", inline=False)
            embed.add_field(name="📍 De", value=before.channel.mention, inline=True)
            embed.add_field(name="📍 Vers", value=after.channel.mention, inline=True)
            embed.set_thumbnail(url=member.display_avatar.url)
            await self.send_log('voice', embed, member.guild)

    # Événements de serveur
    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        """Log les modifications du serveur"""
        if not self.should_log_event('guild_update'):
            return

        changes = []

        if before.name != after.name:
            changes.append(f"**Nom:** {before.name} → {after.name}")

        if before.icon != after.icon:
            changes.append("**Icône:** Modifiée")

        if before.banner != after.banner:
            changes.append("**Bannière:** Modifiée")

        if before.verification_level != after.verification_level:
            changes.append(f"**Niveau de vérification:** {before.verification_level} → {after.verification_level}")

        if not changes:
            return

        embed = discord.Embed(
            title="⚙️ Serveur modifié",
            color=0x3498db,
            timestamp=datetime.now()
        )

        embed.add_field(name="📝 Modifications", value="\n".join(changes), inline=False)
        embed.set_thumbnail(url=after.icon.url if after.icon else None)

        await self.send_log('server', embed, after)

    # Commandes de configuration
    @commands.group(name='logs', invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def logs_config(self, ctx):
        """Configuration du système de logs"""
        embed = discord.Embed(
            title="📋 Configuration des Logs",
            description="Système de logs et audit complet",
            color=0x3498db
        )
        embed.add_field(
            name="📋 Commandes disponibles",
            value="`!logs status` - Statut du système\n"
                  "`!logs toggle` - Activer/désactiver\n"
                  "`!logs channels` - Configurer les canaux\n"
                  "`!logs events` - Gérer les événements\n"
                  "`!logs filters` - Configurer les filtres\n"
                  "`!logs export` - Exporter les logs",
            inline=False
        )
        await ctx.send(embed=embed)

    @logs_config.command(name='status')
    @commands.has_permissions(manage_guild=True)
    async def logs_status(self, ctx):
        """Affiche le statut du système de logs"""
        config = self.config

        embed = discord.Embed(
            title="📊 Statut des Logs",
            color=0x2ecc71 if config['enabled'] else 0xe74c3c,
            timestamp=datetime.now()
        )

        status = "🟢 Activé" if config['enabled'] else "🔴 Désactivé"
        embed.add_field(name="📋 Système", value=status, inline=True)

        # Canaux configurés
        configured_channels = sum(1 for ch in config['channels'].values() if ch is not None)
        embed.add_field(name="📍 Canaux configurés", value=f"{configured_channels}/6", inline=True)

        # Événements actifs
        active_events = sum(1 for event in config['events'].values() if event)
        total_events = len(config['events'])
        embed.add_field(name="📅 Événements actifs", value=f"{active_events}/{total_events}", inline=True)

        # Filtres
        filters = config['filters']
        embed.add_field(
            name="🔍 Filtres",
            value=f"Ignorer bots: {'✅' if filters['ignore_bots'] else '❌'}\n"
                  f"Ignorer webhooks: {'✅' if filters['ignore_webhooks'] else '❌'}\n"
                  f"Canaux ignorés: {len(filters['ignored_channels'])}\n"
                  f"Utilisateurs ignorés: {len(filters['ignored_users'])}",
            inline=False
        )

        await ctx.send(embed=embed)

    @logs_config.command(name='toggle')
    @commands.has_permissions(administrator=True)
    async def toggle_logs(self, ctx):
        """Active/désactive le système de logs"""
        self.config['enabled'] = not self.config['enabled']
        self.save_config()

        status = "activé" if self.config['enabled'] else "désactivé"
        color = 0x2ecc71 if self.config['enabled'] else 0xe74c3c

        embed = discord.Embed(
            title=f"📋 Logs {status.title()}",
            description=f"Le système de logs a été **{status}**.",
            color=color
        )
        await ctx.send(embed=embed)

    @logs_config.command(name='channels')
    @commands.has_permissions(administrator=True)
    async def configure_channels(self, ctx, log_type: str = None, channel: discord.TextChannel = None):
        """Configure les canaux de logs"""
        valid_types = list(self.config['channels'].keys())

        if log_type is None:
            # Afficher la configuration actuelle
            embed = discord.Embed(
                title="📍 Configuration des Canaux",
                color=0x3498db
            )

            for log_type, channel_id in self.config['channels'].items():
                if channel_id:
                    channel_obj = ctx.guild.get_channel(channel_id)
                    value = channel_obj.mention if channel_obj else "Canal supprimé"
                else:
                    value = "Non configuré"

                embed.add_field(
                    name=f"📋 {log_type.title()}",
                    value=value,
                    inline=True
                )

            embed.add_field(
                name="💡 Utilisation",
                value=f"`!logs channels <type> #canal`\nTypes: {', '.join(valid_types)}",
                inline=False
            )

            await ctx.send(embed=embed)
            return

        if log_type not in valid_types:
            embed = discord.Embed(
                title="❌ Type invalide",
                description=f"Types disponibles: {', '.join(valid_types)}",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        if channel is None:
            # Supprimer la configuration
            self.config['channels'][log_type] = None
            message = f"Canal de logs **{log_type}** supprimé"
        else:
            # Configurer le canal
            self.config['channels'][log_type] = channel.id
            message = f"Canal de logs **{log_type}** configuré sur {channel.mention}"

        self.save_config()

        embed = discord.Embed(
            title="✅ Configuration mise à jour",
            description=message,
            color=0x2ecc71
        )
        await ctx.send(embed=embed)

    @logs_config.command(name='events')
    @commands.has_permissions(administrator=True)
    async def configure_events(self, ctx, event: str = None, state: str = None):
        """Configure les événements à logger"""
        if event is None:
            # Afficher tous les événements
            embed = discord.Embed(
                title="📅 Configuration des Événements",
                color=0x3498db
            )

            # Grouper les événements par catégorie
            categories = {
                "Membres": ["member_join", "member_leave", "member_update", "member_ban", "member_unban"],
                "Messages": ["message_delete", "message_edit", "message_bulk_delete"],
                "Vocal": ["voice_join", "voice_leave", "voice_move"],
                "Serveur": ["role_create", "role_delete", "role_update", "channel_create", "channel_delete", "channel_update", "guild_update", "emoji_update", "invite_create", "invite_delete"]
            }

            for category, events in categories.items():
                event_status = []
                for event_name in events:
                    if event_name in self.config['events']:
                        status = "✅" if self.config['events'][event_name] else "❌"
                        event_status.append(f"{status} {event_name}")

                if event_status:
                    embed.add_field(
                        name=f"📂 {category}",
                        value="\n".join(event_status[:5]),  # Limite à 5 par catégorie
                        inline=True
                    )

            embed.add_field(
                name="💡 Utilisation",
                value="`!logs events <événement> <on/off>`",
                inline=False
            )

            await ctx.send(embed=embed)
            return

        if event not in self.config['events']:
            embed = discord.Embed(
                title="❌ Événement invalide",
                description=f"Événements disponibles: {', '.join(self.config['events'].keys())}",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        if state is None:
            # Afficher l'état actuel
            current_state = self.config['events'][event]
            status = "activé" if current_state else "désactivé"

            embed = discord.Embed(
                title=f"📅 Événement: {event}",
                description=f"État actuel: **{status}**",
                color=0x2ecc71 if current_state else 0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        # Modifier l'état
        if state.lower() in ['on', 'true', '1', 'enable', 'activé']:
            self.config['events'][event] = True
            status = "activé"
            color = 0x2ecc71
        elif state.lower() in ['off', 'false', '0', 'disable', 'désactivé']:
            self.config['events'][event] = False
            status = "désactivé"
            color = 0xe74c3c
        else:
            embed = discord.Embed(
                title="❌ État invalide",
                description="Utilisez `on` ou `off`",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        self.save_config()

        embed = discord.Embed(
            title="✅ Événement mis à jour",
            description=f"Événement **{event}** {status}",
            color=color
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Logs(bot))
