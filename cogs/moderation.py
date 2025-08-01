import discord
from discord.ext import commands
import json
import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger('discord_bot.moderation')

class Moderation(commands.Cog):
    """Cog pour les commandes de modération"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def log_action(self, action, moderator, target, reason=None, duration=None):
        """Envoie un log de l'action de modération"""
        try:
            logs_channel_id = self.bot.config['channels']['logs']
            if not logs_channel_id:
                return
            
            logs_channel = self.bot.get_channel(logs_channel_id)
            if not logs_channel:
                return
            
            embed = discord.Embed(
                title=f"🔨 {action}",
                color=0xe74c3c,
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(name="👤 Cible", value=f"{target.mention} ({target.name}#{target.discriminator})", inline=True)
            embed.add_field(name="👮 Modérateur", value=f"{moderator.mention}", inline=True)
            
            if reason:
                embed.add_field(name="📝 Raison", value=reason, inline=False)
            
            if duration:
                embed.add_field(name="⏰ Durée", value=duration, inline=True)
            
            embed.set_thumbnail(url=target.display_avatar.url)
            
            await logs_channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du log: {e}")
    
    @commands.command(name='ban')
    @commands.has_permissions(ban_members=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ban_member(self, ctx, member: discord.Member, *, reason="Aucune raison spécifiée"):
        """Bannit un membre du serveur"""
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Vous ne pouvez pas bannir ce membre (rôle supérieur ou égal).",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        if member == ctx.author:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Vous ne pouvez pas vous bannir vous-même !",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        try:
            # Envoie un message privé au membre avant le ban
            try:
                dm_embed = discord.Embed(
                    title="🔨 Vous avez été banni",
                    description=f"Vous avez été banni du serveur **{ctx.guild.name}**",
                    color=0xe74c3c
                )
                dm_embed.add_field(name="📝 Raison", value=reason, inline=False)
                dm_embed.add_field(name="👮 Modérateur", value=f"{ctx.author.name}#{ctx.author.discriminator}", inline=False)
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                pass
            
            await member.ban(reason=f"Par {ctx.author}: {reason}")
            
            embed = discord.Embed(
                title="✅ Membre banni",
                description=f"**{member.name}#{member.discriminator}** a été banni.",
                color=0x2ecc71
            )
            embed.add_field(name="📝 Raison", value=reason, inline=False)
            await ctx.send(embed=embed)
            
            await self.log_action("Bannissement", ctx.author, member, reason)
            logger.info(f"{member.name} banni par {ctx.author.name}")
            
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Je n'ai pas les permissions pour bannir ce membre.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)

    @commands.command(name='superban', aliases=['ipban'])
    @commands.has_permissions(administrator=True)
    async def super_ban(self, ctx, member: discord.Member, *, reason="Aucune raison spécifiée"):
        """Ban ultra-sévère avec protection maximale anti-contournement"""
        if member == ctx.author:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Vous ne pouvez pas vous super-bannir vous-même !",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        if member.top_role >= ctx.author.top_role and not ctx.author.guild_permissions.administrator:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Vous ne pouvez pas super-bannir ce membre !",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        try:
            # Enregistrer TOUTES les informations possibles
            await self.register_super_ban_info(ctx.guild, member, reason, ctx.author)

            # Message privé d'avertissement sévère
            try:
                dm_embed = discord.Embed(
                    title="⚡ SUPER-BAN APPLIQUÉ",
                    description=f"Vous avez été **DÉFINITIVEMENT BANNI** du serveur **{ctx.guild.name}**",
                    color=0x8b0000
                )
                dm_embed.add_field(name="📝 Raison", value=reason, inline=False)
                dm_embed.add_field(name="👮 Modérateur", value=f"{ctx.author.name}#{ctx.author.discriminator}", inline=False)
                dm_embed.add_field(
                    name="🚨 AVERTISSEMENT SÉVÈRE",
                    value="• Votre empreinte digitale a été enregistrée\n• Tous vos comptes alternatifs seront automatiquement détectés\n• Toute tentative de contournement entraînera un ban immédiat\n• Cette sanction est DÉFINITIVE et IRRÉVOCABLE",
                    inline=False
                )
                await member.send(embed=dm_embed)
            except:
                pass

            # Ban avec suppression maximale des messages
            await member.ban(reason=f"SUPER-BAN par {ctx.author}: {reason}", delete_message_days=7)

            embed = discord.Embed(
                title="⚡ SUPER-BAN APPLIQUÉ",
                description=f"**{member.name}#{member.discriminator}** a été définitivement banni avec protection maximale",
                color=0x8b0000
            )
            embed.add_field(name="📝 Raison", value=reason, inline=False)
            embed.add_field(name="👮 Modérateur", value=f"{ctx.author.name}#{ctx.author.discriminator}", inline=False)
            embed.add_field(
                name="🛡️ Protection Ultra-Sévère Activée",
                value="✅ Empreinte digitale complète enregistrée\n✅ Détection d'avatar et de comportement\n✅ Surveillance des comptes similaires\n✅ Ban automatique des alts détectés\n✅ Historique permanent sauvegardé",
                inline=False
            )
            embed.add_field(
                name="⚠️ Niveau de Protection",
                value="🔴 **MAXIMUM** - Contournement quasi-impossible",
                inline=False
            )
            await ctx.send(embed=embed)

            # Log l'action avec niveau critique
            await self.log_action("SUPER-BANNISSEMENT", ctx.author, member, reason)
            logger.critical(f"SUPER-BAN: {ctx.author.name} a super-banni {member.name} pour: {reason}")

        except Exception as e:
            embed = discord.Embed(
                title="❌ Erreur Super-Ban",
                description=f"Erreur lors du super-ban: {str(e)}",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)

    async def register_super_ban_info(self, guild, member, reason, moderator):
        """Enregistre TOUTES les informations possibles pour le super-ban"""
        from datetime import datetime

        # Récupérer les informations d'autorisation si disponibles
        auth_data = {}
        if hasattr(self.bot, 'get_persistent_data'):
            authorized_users = self.bot.get_persistent_data('moderation', 'authorized_users', {})
            if str(member.id) in authorized_users:
                auth_data = authorized_users[str(member.id)]

        super_ban_data = {
            'user_id': member.id,
            'username': str(member),
            'display_name': member.display_name,
            'discriminator': member.discriminator,
            'avatar_hash': str(member.avatar.key) if member.avatar else None,
            'account_created': member.created_at.isoformat(),
            'joined_at': member.joined_at.isoformat() if member.joined_at else None,
            'ban_time': datetime.now().isoformat(),
            'reason': reason,
            'moderator': str(moderator),
            'guild_id': guild.id,
            'ban_type': 'SUPER_BAN',
            'roles': [role.id for role in member.roles if role != guild.default_role],
            'nickname_history': [member.display_name],
            'status': str(member.status) if hasattr(member, 'status') else None,
            'activity': str(member.activity) if hasattr(member, 'activity') and member.activity else None,
            'mutual_guilds_count': len(member.mutual_guilds) if hasattr(member, 'mutual_guilds') else 0,
            'premium_since': member.premium_since.isoformat() if member.premium_since else None,
            'flags': str(member.public_flags) if hasattr(member, 'public_flags') else None,
            # NOUVELLES DONNÉES D'AUTORISATION
            'authorization_data': auth_data,
            'ip_hash': auth_data.get('ip_hash', 'unknown'),
            'user_agent': auth_data.get('user_agent', 'unknown'),
            'authorization_time': auth_data.get('authorization_time', 'unknown'),
            'email_hash': auth_data.get('email_hash', 'unknown'),
            'device_fingerprint': auth_data.get('device_fingerprint', 'unknown')
        }

        # Sauvegarder dans les super-bans
        if hasattr(self.bot, 'set_persistent_data'):
            super_banned = self.bot.get_persistent_data('moderation', 'super_banned_users', {})
            super_banned[str(member.id)] = super_ban_data
            self.bot.set_persistent_data('moderation', 'super_banned_users', super_banned)

            # Aussi dans la liste normale pour compatibilité
            banned_users = self.bot.get_persistent_data('moderation', 'banned_users', {})
            banned_users[str(member.id)] = super_ban_data
            self.bot.set_persistent_data('moderation', 'banned_users', banned_users)

    @commands.command(name='banlist')
    @commands.has_permissions(ban_members=True)
    async def ban_list(self, ctx):
        """Affiche la liste des utilisateurs bannis avec détection d'alts"""
        if not hasattr(self.bot, 'get_persistent_data'):
            embed = discord.Embed(
                title="❌ Système non disponible",
                description="Le système de persistance n'est pas activé",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        super_banned = self.bot.get_persistent_data('moderation', 'super_banned_users', {})
        banned_users = self.bot.get_persistent_data('moderation', 'banned_users', {})

        if not super_banned and not banned_users:
            embed = discord.Embed(
                title="📋 Liste des Bannis",
                description="Aucun utilisateur banni enregistré",
                color=0x95a5a6
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="📋 LISTE DES UTILISATEURS BANNIS",
            description="Utilisateurs bannis avec système anti-contournement",
            color=0xe74c3c
        )

        # Super-bans
        if super_banned:
            super_ban_text = ""
            for user_id, data in list(super_banned.items())[:5]:  # Limite à 5
                username = data.get('username', 'Inconnu')
                reason = data.get('reason', 'Aucune raison')[:50]
                ban_time = data.get('ban_time', '')
                if ban_time:
                    try:
                        from datetime import datetime
                        ban_date = datetime.fromisoformat(ban_time).strftime("%d/%m/%Y")
                    except:
                        ban_date = "Date inconnue"
                else:
                    ban_date = "Date inconnue"

                super_ban_text += f"⚡ **{username}** (ID: {user_id})\n📝 {reason}\n📅 {ban_date}\n\n"

            embed.add_field(
                name="🚨 SUPER-BANS (Protection Maximale)",
                value=super_ban_text[:1000] if super_ban_text else "Aucun",
                inline=False
            )

        # Bans normaux
        normal_bans = {k: v for k, v in banned_users.items() if v.get('ban_type') != 'SUPER_BAN'}
        if normal_bans:
            ban_text = ""
            for user_id, data in list(normal_bans.items())[:5]:  # Limite à 5
                username = data.get('username', 'Inconnu')
                reason = data.get('reason', 'Aucune raison')[:50]
                ban_text += f"🔨 **{username}** (ID: {user_id})\n📝 {reason}\n\n"

            embed.add_field(
                name="🔨 Bans Normaux",
                value=ban_text[:1000] if ban_text else "Aucun",
                inline=False
            )

        # Statistiques
        total_super = len(super_banned)
        total_normal = len(normal_bans)
        embed.add_field(
            name="📊 Statistiques",
            value=f"⚡ Super-bans: {total_super}\n🔨 Bans normaux: {total_normal}\n📋 Total: {total_super + total_normal}",
            inline=True
        )

        embed.add_field(
            name="🛡️ Protection Active",
            value="✅ Détection automatique d'alts\n✅ Surveillance des nouveaux comptes\n✅ Ban automatique si détection",
            inline=True
        )

        embed.set_footer(text="Utilisez !superban pour une protection maximale")

        await ctx.send(embed=embed)

    @commands.command(name='unban')
    @commands.has_permissions(ban_members=True)
    async def unban_user(self, ctx, user_id: int, *, reason="Aucune raison spécifiée"):
        """Débannit un utilisateur et le retire du système anti-contournement"""
        try:
            # Débannir de Discord
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user, reason=f"Par {ctx.author}: {reason}")

            # Retirer du système anti-contournement
            if hasattr(self.bot, 'get_persistent_data'):
                super_banned = self.bot.get_persistent_data('moderation', 'super_banned_users', {})
                banned_users = self.bot.get_persistent_data('moderation', 'banned_users', {})

                was_super_banned = str(user_id) in super_banned

                # Retirer des listes
                if str(user_id) in super_banned:
                    del super_banned[str(user_id)]
                    self.bot.set_persistent_data('moderation', 'super_banned_users', super_banned)

                if str(user_id) in banned_users:
                    del banned_users[str(user_id)]
                    self.bot.set_persistent_data('moderation', 'banned_users', banned_users)

            embed = discord.Embed(
                title="✅ Utilisateur débanni",
                description=f"**{user.name}#{user.discriminator}** a été débanni",
                color=0x2ecc71
            )
            embed.add_field(name="📝 Raison", value=reason, inline=False)
            embed.add_field(name="👮 Modérateur", value=ctx.author.mention, inline=False)

            if was_super_banned:
                embed.add_field(name="🛡️ Système Anti-Contournement", value="✅ Retiré du système de détection", inline=False)

            await ctx.send(embed=embed)

            # Log l'action
            await self.log_action("DÉBAN", ctx.author, user, reason)
            logger.info(f"{ctx.author.name} a débanni {user.name} pour: {reason}")

        except discord.NotFound:
            embed = discord.Embed(
                title="❌ Utilisateur introuvable",
                description="Cet utilisateur n'est pas banni ou n'existe pas",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Erreur",
                description=f"Erreur lors du déban: {str(e)}",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)

    @commands.command(name='kick')
    @commands.has_permissions(kick_members=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def kick_member(self, ctx, member: discord.Member, *, reason="Aucune raison spécifiée"):
        """Expulse un membre du serveur"""
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Vous ne pouvez pas expulser ce membre (rôle supérieur ou égal).",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        if member == ctx.author:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Vous ne pouvez pas vous expulser vous-même !",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        try:
            # Envoie un message privé au membre avant le kick
            try:
                dm_embed = discord.Embed(
                    title="👢 Vous avez été expulsé",
                    description=f"Vous avez été expulsé du serveur **{ctx.guild.name}**",
                    color=0xf39c12
                )
                dm_embed.add_field(name="📝 Raison", value=reason, inline=False)
                dm_embed.add_field(name="👮 Modérateur", value=f"{ctx.author.name}#{ctx.author.discriminator}", inline=False)
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                pass
            
            await member.kick(reason=f"Par {ctx.author}: {reason}")
            
            embed = discord.Embed(
                title="✅ Membre expulsé",
                description=f"**{member.name}#{member.discriminator}** a été expulsé.",
                color=0x2ecc71
            )
            embed.add_field(name="📝 Raison", value=reason, inline=False)
            await ctx.send(embed=embed)
            
            await self.log_action("Expulsion", ctx.author, member, reason)
            logger.info(f"{member.name} expulsé par {ctx.author.name}")
            
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Je n'ai pas les permissions pour expulser ce membre.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)

    @commands.command(name='mute')
    @commands.has_permissions(manage_roles=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def mute_member(self, ctx, member: discord.Member, duration: int = None, *, reason="Aucune raison spécifiée"):
        """Rend muet un membre (durée en minutes)"""
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Vous ne pouvez pas rendre muet ce membre (rôle supérieur ou égal).",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        if member == ctx.author:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Vous ne pouvez pas vous rendre muet vous-même !",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        # Récupère ou crée le rôle "Muet"
        muted_role_id = self.bot.config['roles']['muted']
        muted_role = None

        if muted_role_id:
            muted_role = ctx.guild.get_role(muted_role_id)

        if not muted_role:
            # Crée le rôle "Muet"
            muted_role = await ctx.guild.create_role(
                name="Muet",
                color=discord.Color.dark_grey(),
                reason="Rôle de mute automatique"
            )

            # Configure les permissions pour tous les canaux
            for channel in ctx.guild.channels:
                await channel.set_permissions(muted_role, send_messages=False, speak=False)

            # Sauvegarde l'ID du rôle
            self.bot.config['roles']['muted'] = muted_role.id
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(self.bot.config, f, indent=2, ensure_ascii=False)

        try:
            await member.add_roles(muted_role, reason=f"Par {ctx.author}: {reason}")
            self.bot.muted_users.add(member.id)

            duration_text = f"{duration} minutes" if duration else "Indéterminée"

            embed = discord.Embed(
                title="🔇 Membre rendu muet",
                description=f"**{member.name}#{member.discriminator}** a été rendu muet.",
                color=0xf39c12
            )
            embed.add_field(name="📝 Raison", value=reason, inline=False)
            embed.add_field(name="⏰ Durée", value=duration_text, inline=True)
            await ctx.send(embed=embed)

            await self.log_action("Mute", ctx.author, member, reason, duration_text)

            # Démute automatiquement après la durée spécifiée
            if duration:
                await asyncio.sleep(duration * 60)
                if member.id in self.bot.muted_users:
                    await member.remove_roles(muted_role, reason="Fin du mute automatique")
                    self.bot.muted_users.discard(member.id)

                    embed = discord.Embed(
                        title="🔊 Mute expiré",
                        description=f"**{member.name}#{member.discriminator}** n'est plus muet.",
                        color=0x2ecc71
                    )
                    await ctx.send(embed=embed)

            logger.info(f"{member.name} rendu muet par {ctx.author.name}")

        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Je n'ai pas les permissions pour rendre muet ce membre.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)

    @commands.command(name='unmute')
    @commands.has_permissions(manage_roles=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def unmute_member(self, ctx, member: discord.Member, *, reason="Aucune raison spécifiée"):
        """Retire le mute d'un membre"""
        muted_role_id = self.bot.config['roles']['muted']
        if not muted_role_id:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Aucun rôle de mute configuré.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        muted_role = ctx.guild.get_role(muted_role_id)
        if not muted_role or muted_role not in member.roles:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Ce membre n'est pas muet.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        try:
            await member.remove_roles(muted_role, reason=f"Par {ctx.author}: {reason}")
            self.bot.muted_users.discard(member.id)

            embed = discord.Embed(
                title="🔊 Membre démute",
                description=f"**{member.name}#{member.discriminator}** n'est plus muet.",
                color=0x2ecc71
            )
            embed.add_field(name="📝 Raison", value=reason, inline=False)
            await ctx.send(embed=embed)

            await self.log_action("Unmute", ctx.author, member, reason)
            logger.info(f"{member.name} démute par {ctx.author.name}")

        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Je n'ai pas les permissions pour démuter ce membre.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)

    @commands.command(name='clear')
    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def clear_messages(self, ctx, amount: int = 10):
        """Supprime un nombre de messages (max 100)"""
        if amount > 100:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Vous ne pouvez pas supprimer plus de 100 messages à la fois.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        if amount < 1:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Vous devez spécifier un nombre positif de messages à supprimer.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        try:
            deleted = await ctx.channel.purge(limit=amount + 1)  # +1 pour inclure la commande

            embed = discord.Embed(
                title="🗑️ Messages supprimés",
                description=f"**{len(deleted) - 1}** messages ont été supprimés.",
                color=0x2ecc71
            )

            # Envoie le message de confirmation et le supprime après 5 secondes
            msg = await ctx.send(embed=embed)
            await asyncio.sleep(5)
            await msg.delete()

            await self.log_action("Clear", ctx.author, ctx.channel, f"{len(deleted) - 1} messages supprimés")
            logger.info(f"{len(deleted) - 1} messages supprimés par {ctx.author.name} dans {ctx.channel.name}")

        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Je n'ai pas les permissions pour supprimer des messages.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)

    @commands.command(name='warn')
    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def warn_member(self, ctx, member: discord.Member, *, reason="Aucune raison spécifiée"):
        """Avertit un membre"""
        if member == ctx.author:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Vous ne pouvez pas vous avertir vous-même !",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        # Ajoute l'avertissement
        if member.id not in self.bot.warnings:
            self.bot.warnings[member.id] = 0

        self.bot.warnings[member.id] += 1
        warning_count = self.bot.warnings[member.id]

        embed = discord.Embed(
            title="⚠️ Membre averti",
            description=f"**{member.name}#{member.discriminator}** a reçu un avertissement.",
            color=0xf39c12
        )
        embed.add_field(name="📝 Raison", value=reason, inline=False)
        embed.add_field(name="📊 Avertissements", value=f"{warning_count}/{self.bot.config['moderation']['max_warnings']}", inline=True)

        # Vérifie si le membre doit être sanctionné
        max_warnings = self.bot.config['moderation']['max_warnings']
        if warning_count >= max_warnings:
            embed.add_field(name="🔨 Action automatique", value="Membre banni pour trop d'avertissements", inline=False)

            try:
                await member.ban(reason=f"Trop d'avertissements ({warning_count}/{max_warnings})")
                await self.log_action("Ban automatique", self.bot.user, member, f"Trop d'avertissements ({warning_count}/{max_warnings})")
            except discord.Forbidden:
                embed.add_field(name="❌ Erreur", value="Impossible de bannir automatiquement ce membre", inline=False)

        await ctx.send(embed=embed)

        # Envoie un message privé au membre
        try:
            dm_embed = discord.Embed(
                title="⚠️ Avertissement reçu",
                description=f"Vous avez reçu un avertissement sur le serveur **{ctx.guild.name}**",
                color=0xf39c12
            )
            dm_embed.add_field(name="📝 Raison", value=reason, inline=False)
            dm_embed.add_field(name="📊 Avertissements", value=f"{warning_count}/{max_warnings}", inline=True)
            dm_embed.add_field(name="👮 Modérateur", value=f"{ctx.author.name}#{ctx.author.discriminator}", inline=True)
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        await self.log_action("Avertissement", ctx.author, member, reason)
        logger.info(f"{member.name} averti par {ctx.author.name} ({warning_count}/{max_warnings})")

    @commands.command(name='warnings')
    @commands.has_permissions(manage_messages=True)
    async def show_warnings(self, ctx, member: discord.Member = None):
        """Affiche les avertissements d'un membre"""
        if not member:
            member = ctx.author

        warning_count = self.bot.warnings.get(member.id, 0)
        max_warnings = 3

        embed = discord.Embed(
            title="⚠️ Avertissements",
            description=f"Avertissements de **{member.name}#{member.discriminator}**",
            color=0xf39c12
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(
            name="📊 Compteur",
            value=f"{warning_count}/{max_warnings}",
            inline=True
        )

        if warning_count == 0:
            embed.add_field(
                name="✅ Statut",
                value="Aucun avertissement",
                inline=True
            )
        elif warning_count < max_warnings:
            embed.add_field(
                name="⚠️ Statut",
                value=f"Encore {max_warnings - warning_count} avant le ban",
                inline=True
            )
        else:
            embed.add_field(
                name="🔨 Statut",
                value="Devrait être banni",
                inline=True
            )

        embed.set_footer(text=f"Demandé par {ctx.author.name}")
        embed.timestamp = discord.utils.utcnow()

        await ctx.send(embed=embed)
        logger.info(f"Avertissements de {member.name} consultés par {ctx.author.name}")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Détection automatique des comptes alternatifs et contournements de ban"""
        # SYSTÈME D'AUTORISATION OBLIGATOIRE
        await self.require_bot_authorization(member)

        # DÉTECTION AUTOMATIQUE DES COMPTES ALTERNATIFS
        await self.check_for_ban_evasion(member)

    async def require_bot_authorization(self, member):
        """Force l'autorisation du bot pour identifier parfaitement l'utilisateur"""
        try:
            # Créer un embed d'autorisation obligatoire
            auth_embed = discord.Embed(
                title="🔐 AUTORISATION OBLIGATOIRE REQUISE",
                description=f"**Bienvenue {member.mention} !**\n\nPour accéder au serveur, vous devez **OBLIGATOIREMENT** autoriser notre bot à accéder à vos informations Discord.",
                color=0xff6b6b
            )

            auth_embed.add_field(
                name="🚨 POURQUOI C'EST OBLIGATOIRE ?",
                value="• **Sécurité maximale** du serveur\n• **Identification unique** de votre compte\n• **Protection anti-contournement** de ban\n• **Prévention des comptes alternatifs**",
                inline=False
            )

            # Utiliser votre site x10hosting
            auth_url = "https://bot9z.x10.mx/"

            auth_embed.add_field(
                name="🔗 LIEN D'AUTORISATION OBLIGATOIRE",
                value=f"[**CLIQUEZ ICI POUR AUTORISER LE BOT**]({auth_url})",
                inline=False
            )

            auth_embed.add_field(
                name="📋 INFORMATIONS COLLECTÉES",
                value="• **ID Discord unique** (impossible à falsifier)\n• **Email associé** au compte\n• **Serveurs en commun**\n• **Date de création** du compte\n• **Statut de vérification** Discord",
                inline=False
            )

            auth_embed.add_field(
                name="⚠️ IMPORTANT",
                value="**Sans cette autorisation, vous ne pourrez PAS accéder au serveur.**\nCette mesure garantit la sécurité de tous les membres.",
                inline=False
            )

            auth_embed.set_footer(text="Sécurité maximale • Protection anti-contournement")

            # Envoyer en DM
            try:
                await member.send(embed=auth_embed)

                # Mettre en quarantaine jusqu'à autorisation
                quarantine_role = discord.utils.get(member.guild.roles, name="🔐 En Attente d'Autorisation")
                if not quarantine_role:
                    quarantine_role = await member.guild.create_role(
                        name="🔐 En Attente d'Autorisation",
                        color=0xff6b6b,
                        reason="Rôle d'attente d'autorisation"
                    )

                    # Aucun accès tant que pas autorisé
                    for channel in member.guild.channels:
                        try:
                            await channel.set_permissions(quarantine_role, read_messages=False, send_messages=False)
                        except:
                            pass

                await member.add_roles(quarantine_role, reason="En attente d'autorisation bot")

                # Log dans le serveur
                logs_channel = discord.utils.get(member.guild.channels, name="logs")
                if logs_channel:
                    log_embed = discord.Embed(
                        title="🔐 AUTORISATION REQUISE",
                        description=f"**{member.name}#{member.discriminator}** doit autoriser le bot",
                        color=0xff6b6b
                    )
                    log_embed.add_field(name="👤 Utilisateur", value=f"{member.mention} (ID: {member.id})", inline=False)
                    log_embed.add_field(name="📧 DM envoyé", value="✅ Instructions d'autorisation envoyées", inline=False)
                    log_embed.add_field(name="🔒 Statut", value="En quarantaine jusqu'à autorisation", inline=False)
                    await logs_channel.send(embed=log_embed)

            except discord.Forbidden:
                # Si DM impossible, message dans le serveur
                welcome_channel = discord.utils.get(member.guild.channels, name="bienvenue") or member.guild.system_channel
                if welcome_channel:
                    await welcome_channel.send(f"{member.mention}", embed=auth_embed)

        except Exception as e:
            logger.error(f"Erreur autorisation obligatoire: {e}")

    @commands.command(name='authorize_user')
    @commands.has_permissions(administrator=True)
    async def authorize_user_manually(self, ctx, member: discord.Member):
        """Autorise manuellement un utilisateur (admin seulement)"""
        try:
            # Retirer le rôle d'attente
            auth_role = discord.utils.get(member.guild.roles, name="🔐 En Attente d'Autorisation")
            if auth_role and auth_role in member.roles:
                await member.remove_roles(auth_role, reason=f"Autorisé manuellement par {ctx.author}")

            # Enregistrer l'autorisation
            if hasattr(self.bot, 'set_persistent_data'):
                authorized_users = self.bot.get_persistent_data('moderation', 'authorized_users', {})
                authorized_users[str(member.id)] = {
                    'user_id': member.id,
                    'username': str(member),
                    'authorized_by': str(ctx.author),
                    'authorization_time': datetime.now().isoformat(),
                    'method': 'manual',
                    'ip_hash': 'manual_auth',  # Pas d'IP pour auth manuelle
                    'user_agent': 'manual_auth'
                }
                self.bot.set_persistent_data('moderation', 'authorized_users', authorized_users)

            embed = discord.Embed(
                title="✅ Utilisateur Autorisé",
                description=f"**{member.name}#{member.discriminator}** a été autorisé manuellement",
                color=0x2ecc71
            )
            embed.add_field(name="👮 Autorisé par", value=ctx.author.mention, inline=False)
            embed.add_field(name="🔓 Accès", value="Accès complet au serveur accordé", inline=False)

            await ctx.send(embed=embed)

            # Notifier l'utilisateur
            try:
                user_embed = discord.Embed(
                    title="✅ AUTORISATION ACCORDÉE",
                    description=f"Vous avez été autorisé à accéder au serveur **{ctx.guild.name}** !",
                    color=0x2ecc71
                )
                user_embed.add_field(name="👮 Autorisé par", value=f"{ctx.author.name}#{ctx.author.discriminator}", inline=False)
                user_embed.add_field(name="🎉 Bienvenue", value="Vous pouvez maintenant profiter pleinement du serveur !", inline=False)
                await member.send(embed=user_embed)
            except:
                pass

        except Exception as e:
            embed = discord.Embed(
                title="❌ Erreur",
                description=f"Erreur lors de l'autorisation: {str(e)}",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)

    async def check_for_ban_evasion(self, member):
        """Détecte automatiquement les tentatives de contournement de ban"""
        if not hasattr(self.bot, 'get_persistent_data'):
            return

        # Récupérer les utilisateurs super-bannis
        super_banned = self.bot.get_persistent_data('moderation', 'super_banned_users', {})
        banned_users = self.bot.get_persistent_data('moderation', 'banned_users', {})

        # Vérifications multiples pour détecter les alts
        suspicion_score = 0
        detected_reasons = []

        # 1. Vérification directe de l'ID (au cas où)
        if str(member.id) in super_banned or str(member.id) in banned_users:
            suspicion_score = 100
            detected_reasons.append("ID utilisateur identique")

        # 2. Vérification de l'avatar
        if member.avatar:
            current_avatar = str(member.avatar.key)
            for banned_data in {**super_banned, **banned_users}.values():
                if banned_data.get('avatar_hash') == current_avatar and current_avatar:
                    suspicion_score += 40
                    detected_reasons.append("Avatar identique")
                    break

        # 3. Vérification du nom d'utilisateur similaire
        current_username = member.name.lower()
        for banned_data in {**super_banned, **banned_users}.values():
            banned_username = banned_data.get('username', '').lower()
            if banned_username and self.calculate_similarity(current_username, banned_username) > 0.8:
                suspicion_score += 30
                detected_reasons.append("Nom d'utilisateur très similaire")
                break

        # 4. Vérification de l'âge du compte (comptes très récents suspects)
        from datetime import datetime
        account_age_days = (datetime.now() - member.created_at).days
        if account_age_days < 7:  # Compte de moins d'une semaine
            suspicion_score += 20
            detected_reasons.append("Compte très récent")

        # 5. Vérification du timing (rejoint peu après un ban)
        for banned_data in {**super_banned, **banned_users}.values():
            if banned_data.get('ban_time'):
                try:
                    ban_time = datetime.fromisoformat(banned_data['ban_time'])
                    time_since_ban = (datetime.now() - ban_time).total_seconds() / 3600  # en heures
                    if time_since_ban < 24:  # Rejoint dans les 24h après un ban
                        suspicion_score += 25
                        detected_reasons.append("Rejoint peu après un bannissement")
                        break
                except:
                    pass

        # 6. VÉRIFICATION DES DONNÉES D'AUTORISATION (NOUVEAU)
        current_auth = self.bot.get_persistent_data('moderation', 'authorized_users', {}).get(str(member.id), {})

        for banned_data in {**super_banned, **banned_users}.values():
            banned_auth = banned_data.get('authorization_data', {})

            # Vérification IP (hash)
            if current_auth.get('ip_hash') and banned_auth.get('ip_hash'):
                if current_auth['ip_hash'] == banned_auth['ip_hash']:
                    suspicion_score += 60
                    detected_reasons.append("Même adresse IP détectée")
                    break

            # Vérification User-Agent (navigateur/appareil)
            if current_auth.get('user_agent') and banned_auth.get('user_agent'):
                if current_auth['user_agent'] == banned_auth['user_agent']:
                    suspicion_score += 30
                    detected_reasons.append("Même appareil/navigateur détecté")

            # Vérification empreinte d'appareil
            if current_auth.get('device_fingerprint') and banned_auth.get('device_fingerprint'):
                if current_auth['device_fingerprint'] == banned_auth['device_fingerprint']:
                    suspicion_score += 50
                    detected_reasons.append("Même empreinte d'appareil détectée")

            # Vérification email (hash)
            if current_auth.get('email_hash') and banned_auth.get('email_hash'):
                if current_auth['email_hash'] == banned_auth['email_hash']:
                    suspicion_score += 70
                    detected_reasons.append("Même email détecté")
                    break

        # Action selon le score de suspicion
        if suspicion_score >= 70:
            # BAN AUTOMATIQUE - Suspicion très élevée
            await self.auto_ban_suspected_alt(member, suspicion_score, detected_reasons)
        elif suspicion_score >= 40:
            # QUARANTAINE - Suspicion modérée
            await self.quarantine_suspected_alt(member, suspicion_score, detected_reasons)
        elif suspicion_score >= 20:
            # SURVEILLANCE - Suspicion légère
            await self.monitor_suspected_alt(member, suspicion_score, detected_reasons)

    def calculate_similarity(self, str1, str2):
        """Calcule la similarité entre deux chaînes"""
        if not str1 or not str2:
            return 0

        # Algorithme de distance de Levenshtein simplifié
        len1, len2 = len(str1), len(str2)
        if len1 == 0:
            return 0 if len2 == 0 else 0
        if len2 == 0:
            return 0

        # Calcul simple de similarité
        matches = sum(1 for a, b in zip(str1, str2) if a == b)
        return matches / max(len1, len2)

    async def auto_ban_suspected_alt(self, member, score, reasons):
        """Ban automatique d'un compte alternatif détecté"""
        try:
            reason = f"DÉTECTION AUTOMATIQUE ALT - Score: {score}% - Raisons: {', '.join(reasons)}"

            # Ban immédiat
            await member.ban(reason=reason, delete_message_days=1)

            # Log critique
            embed = discord.Embed(
                title="🚨 BAN AUTOMATIQUE - COMPTE ALTERNATIF DÉTECTÉ",
                description=f"**{member.name}#{member.discriminator}** ({member.id})",
                color=0x8b0000
            )
            embed.add_field(name="🎯 Score de suspicion", value=f"{score}%", inline=True)
            embed.add_field(name="🔍 Raisons détectées", value="\n".join(f"• {reason}" for reason in reasons), inline=False)
            embed.add_field(name="⚡ Action", value="**BAN AUTOMATIQUE IMMÉDIAT**", inline=False)

            # Envoyer dans les logs
            logs_channel = discord.utils.get(member.guild.channels, name="logs")
            if logs_channel:
                await logs_channel.send(embed=embed)

            logger.critical(f"BAN AUTOMATIQUE ALT: {member.name} - Score: {score}% - Raisons: {reasons}")

        except Exception as e:
            logger.error(f"Erreur ban automatique alt: {e}")

    async def quarantine_suspected_alt(self, member, score, reasons):
        """Met en quarantaine un compte suspect"""
        try:
            # Créer ou récupérer le rôle de quarantaine
            quarantine_role = discord.utils.get(member.guild.roles, name="🔒 Quarantaine")
            if not quarantine_role:
                quarantine_role = await member.guild.create_role(
                    name="🔒 Quarantaine",
                    color=0xff6b6b,
                    reason="Rôle de quarantaine automatique"
                )

                # Configurer les permissions (aucun accès)
                for channel in member.guild.channels:
                    try:
                        await channel.set_permissions(quarantine_role, read_messages=False, send_messages=False)
                    except:
                        pass

            # Appliquer la quarantaine
            await member.add_roles(quarantine_role, reason=f"Quarantaine automatique - Score suspicion: {score}%")

            # Log d'alerte
            embed = discord.Embed(
                title="⚠️ QUARANTAINE AUTOMATIQUE - COMPTE SUSPECT",
                description=f"**{member.name}#{member.discriminator}** ({member.id})",
                color=0xff6b6b
            )
            embed.add_field(name="🎯 Score de suspicion", value=f"{score}%", inline=True)
            embed.add_field(name="🔍 Raisons détectées", value="\n".join(f"• {reason}" for reason in reasons), inline=False)
            embed.add_field(name="🔒 Action", value="**QUARANTAINE APPLIQUÉE**", inline=False)

            logs_channel = discord.utils.get(member.guild.channels, name="logs")
            if logs_channel:
                await logs_channel.send(embed=embed)

            logger.warning(f"QUARANTAINE ALT: {member.name} - Score: {score}% - Raisons: {reasons}")

        except Exception as e:
            logger.error(f"Erreur quarantaine alt: {e}")

    async def monitor_suspected_alt(self, member, score, reasons):
        """Surveille un compte légèrement suspect"""
        try:
            embed = discord.Embed(
                title="👁️ SURVEILLANCE - COMPTE LÉGÈREMENT SUSPECT",
                description=f"**{member.name}#{member.discriminator}** ({member.id})",
                color=0xffa500
            )
            embed.add_field(name="🎯 Score de suspicion", value=f"{score}%", inline=True)
            embed.add_field(name="🔍 Raisons détectées", value="\n".join(f"• {reason}" for reason in reasons), inline=False)
            embed.add_field(name="👁️ Action", value="**SURVEILLANCE ACTIVÉE**", inline=False)

            logs_channel = discord.utils.get(member.guild.channels, name="logs")
            if logs_channel:
                await logs_channel.send(embed=embed)

            logger.info(f"SURVEILLANCE ALT: {member.name} - Score: {score}% - Raisons: {reasons}")

        except Exception as e:
            logger.error(f"Erreur surveillance alt: {e}")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
