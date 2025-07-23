import discord
from discord.ext import commands
import time
import logging
from datetime import datetime

logger = logging.getLogger('discord_bot.utilities')

class Utilities(commands.Cog):
    """Cog pour les commandes utilitaires et d'information"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='help')
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def help_command(self, ctx, *, command_name=None):
        """Affiche l'aide pour les commandes"""
        prefix = self.bot.config['prefix']
        
        if command_name:
            # Aide pour une commande spécifique
            command = self.bot.get_command(command_name)
            if not command:
                embed = discord.Embed(
                    title="❌ Commande introuvable",
                    description=f"La commande `{command_name}` n'existe pas.",
                    color=0xe74c3c
                )
                await ctx.send(embed=embed)
                return
            
            embed = discord.Embed(
                title=f"📖 Aide - {prefix}{command.name}",
                description=command.help or "Aucune description disponible.",
                color=int(self.bot.config['embed_color'], 16)
            )
            
            if command.usage:
                embed.add_field(name="📝 Usage", value=f"`{prefix}{command.name} {command.usage}`", inline=False)
            
            if command.aliases:
                embed.add_field(name="🔄 Alias", value=", ".join([f"`{alias}`" for alias in command.aliases]), inline=False)
            
            await ctx.send(embed=embed)
            return
        
        # Aide générale
        embed = discord.Embed(
            title="📚 Aide - Commandes disponibles",
            description=f"Préfixe du bot : `{prefix}`\nUtilisez `{prefix}help <commande>` pour plus d'informations sur une commande spécifique.",
            color=int(self.bot.config['embed_color'], 16)
        )
        
        # Modération
        moderation_commands = [
            f"`{prefix}ban <membre> [raison]` - Bannit un membre",
            f"`{prefix}kick <membre> [raison]` - Expulse un membre",
            f"`{prefix}mute <membre> [durée] [raison]` - Rend muet un membre",
            f"`{prefix}unmute <membre> [raison]` - Démute un membre",
            f"`{prefix}clear [nombre]` - Supprime des messages",
            f"`{prefix}warn <membre> [raison]` - Avertit un membre"
        ]
        embed.add_field(name="🔨 Modération", value="\n".join(moderation_commands), inline=False)
        
        # Utilitaires
        utility_commands = [
            f"`{prefix}ping` - Affiche la latence du bot",
            f"`{prefix}userinfo [membre]` - Informations sur un utilisateur",
            f"`{prefix}serverinfo` - Informations sur le serveur",
            f"`{prefix}avatar [membre]` - Avatar d'un utilisateur"
        ]
        embed.add_field(name="🔧 Utilitaires", value="\n".join(utility_commands), inline=False)
        
        # Fun
        fun_commands = [
            f"`{prefix}joke` - Raconte une blague",
            f"`{prefix}quote` - Affiche une citation",
            f"`{prefix}trivia` - Question de culture générale",
            f"`{prefix}8ball <question>` - Boule magique",
            f"`{prefix}poll <question>` - Crée un sondage"
        ]
        embed.add_field(name="🎲 Fun", value="\n".join(fun_commands), inline=False)
        
        # Tickets
        ticket_commands = [
            f"`{prefix}ticket` - Crée un ticket de support",
            f"`{prefix}close` - Ferme un ticket (staff uniquement)"
        ]
        embed.add_field(name="🎫 Tickets", value="\n".join(ticket_commands), inline=False)
        
        # Configuration (admin uniquement)
        if ctx.author.guild_permissions.administrator:
            config_commands = [
                f"`{prefix}setup_roles [canal]` - Configure la sélection de rôles",
                f"`{prefix}setup_tickets [canal]` - Configure le système de tickets",
                f"`{prefix}welcome_setup [canal]` - Configure les messages de bienvenue",
                f"`{prefix}add_role <emoji> <rôle>` - Ajoute un rôle sélectionnable"
            ]
            embed.add_field(name="⚙️ Configuration", value="\n".join(config_commands), inline=False)
        
        embed.set_footer(text=f"Bot développé pour {ctx.guild.name}")
        await ctx.send(embed=embed)
    
    @commands.command(name='ping')
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ping(self, ctx):
        """Affiche la latence du bot"""
        start_time = time.time()
        message = await ctx.send("🏓 Pong !")
        end_time = time.time()
        
        latency = round(self.bot.latency * 1000)
        response_time = round((end_time - start_time) * 1000)
        
        embed = discord.Embed(
            title="🏓 Pong !",
            color=int(self.bot.config['embed_color'], 16)
        )
        embed.add_field(name="📡 Latence WebSocket", value=f"{latency}ms", inline=True)
        embed.add_field(name="⚡ Temps de réponse", value=f"{response_time}ms", inline=True)
        
        await message.edit(content=None, embed=embed)
    
    @commands.command(name='userinfo')
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def userinfo(self, ctx, member: discord.Member = None):
        """Affiche les informations d'un utilisateur"""
        if not member:
            member = ctx.author
        
        embed = discord.Embed(
            title=f"👤 Informations - {member.name}",
            color=member.color if member.color != discord.Color.default() else int(self.bot.config['embed_color'], 16)
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Informations de base
        embed.add_field(name="🏷️ Nom complet", value=f"{member.name}#{member.discriminator}", inline=True)
        embed.add_field(name="🆔 ID", value=member.id, inline=True)
        embed.add_field(name="🤖 Bot", value="Oui" if member.bot else "Non", inline=True)
        
        # Dates
        embed.add_field(name="📅 Compte créé", value=f"<t:{int(member.created_at.timestamp())}:F>", inline=False)
        embed.add_field(name="📥 A rejoint le serveur", value=f"<t:{int(member.joined_at.timestamp())}:F>", inline=False)
        
        # Rôles
        if len(member.roles) > 1:
            roles = [role.mention for role in member.roles[1:]]  # Exclut @everyone
            roles_text = ", ".join(roles) if len(", ".join(roles)) <= 1024 else f"{len(roles)} rôles"
            embed.add_field(name="🎭 Rôles", value=roles_text, inline=False)
        
        # Statut
        status_emoji = {
            discord.Status.online: "🟢",
            discord.Status.idle: "🟡",
            discord.Status.dnd: "🔴",
            discord.Status.offline: "⚫"
        }
        embed.add_field(name="📊 Statut", value=f"{status_emoji.get(member.status, '❓')} {member.status.name.title()}", inline=True)
        
        # Activité
        if member.activity:
            activity_type = {
                discord.ActivityType.playing: "🎮 Joue à",
                discord.ActivityType.streaming: "📺 Stream",
                discord.ActivityType.listening: "🎵 Écoute",
                discord.ActivityType.watching: "👀 Regarde",
                discord.ActivityType.custom: "💭",
                discord.ActivityType.competing: "🏆 Participe à"
            }
            activity_text = f"{activity_type.get(member.activity.type, '❓')} {member.activity.name}"
            embed.add_field(name="🎯 Activité", value=activity_text, inline=True)
        
        embed.set_footer(text=f"Demandé par {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
    
    @commands.command(name='serverinfo')
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def serverinfo(self, ctx):
        """Affiche les informations du serveur"""
        guild = ctx.guild
        
        embed = discord.Embed(
            title=f"🏰 Informations - {guild.name}",
            color=int(self.bot.config['embed_color'], 16)
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # Informations de base
        embed.add_field(name="🆔 ID", value=guild.id, inline=True)
        embed.add_field(name="👑 Propriétaire", value=guild.owner.mention if guild.owner else "Inconnu", inline=True)
        embed.add_field(name="📅 Créé le", value=f"<t:{int(guild.created_at.timestamp())}:F>", inline=False)
        
        # Statistiques
        total_members = guild.member_count
        bots = sum(1 for member in guild.members if member.bot)
        humans = total_members - bots
        
        embed.add_field(name="👥 Membres", value=f"**Total :** {total_members}\n**Humains :** {humans}\n**Bots :** {bots}", inline=True)
        embed.add_field(name="📺 Canaux", value=f"**Texte :** {len(guild.text_channels)}\n**Vocal :** {len(guild.voice_channels)}\n**Catégories :** {len(guild.categories)}", inline=True)
        embed.add_field(name="🎭 Rôles", value=len(guild.roles), inline=True)
        
        # Niveau de vérification
        verification_levels = {
            discord.VerificationLevel.none: "Aucune",
            discord.VerificationLevel.low: "Faible",
            discord.VerificationLevel.medium: "Moyenne",
            discord.VerificationLevel.high: "Élevée",
            discord.VerificationLevel.highest: "Très élevée"
        }
        embed.add_field(name="🔒 Niveau de vérification", value=verification_levels.get(guild.verification_level, "Inconnu"), inline=True)
        
        # Fonctionnalités
        features = []
        if guild.premium_tier > 0:
            features.append(f"Nitro Boost Niveau {guild.premium_tier}")
        if guild.features:
            features.extend([feature.replace('_', ' ').title() for feature in guild.features[:3]])
        
        if features:
            embed.add_field(name="✨ Fonctionnalités", value="\n".join(features), inline=True)
        
        embed.set_footer(text=f"Demandé par {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
    
    @commands.command(name='avatar')
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def avatar(self, ctx, member: discord.Member = None):
        """Affiche l'avatar d'un utilisateur"""
        if not member:
            member = ctx.author
        
        embed = discord.Embed(
            title=f"🖼️ Avatar de {member.name}",
            color=member.color if member.color != discord.Color.default() else int(self.bot.config['embed_color'], 16)
        )
        
        embed.set_image(url=member.display_avatar.url)
        embed.add_field(name="🔗 Liens", value=f"[PNG]({member.display_avatar.with_format('png').url}) | [JPG]({member.display_avatar.with_format('jpg').url}) | [WEBP]({member.display_avatar.with_format('webp').url})", inline=False)
        
        embed.set_footer(text=f"Demandé par {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Utilities(bot))
