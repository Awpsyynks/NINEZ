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

async def setup(bot):
    await bot.add_cog(Moderation(bot))
