import discord
from discord.ext import commands
import json
import logging

logger = logging.getLogger('discord_bot.role_selection')

class RoleSelection(commands.Cog):
    """Cog pour gérer la sélection de rôles par réaction"""
    
    def __init__(self, bot):
        self.bot = bot
        self.role_message_id = None
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Récupère l'ID du message de sélection de rôles au démarrage"""
        try:
            # Charger l'ID du message depuis un fichier de données persistantes
            try:
                with open('data/role_message.json', 'r') as f:
                    data = json.load(f)
                    self.role_message_id = data.get('message_id')
            except FileNotFoundError:
                pass
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données de rôles: {e}")
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Gère l'ajout de réactions pour les rôles"""
        # Ignore les réactions du bot
        if payload.user_id == self.bot.user.id:
            return
        
        # Vérifie si c'est le bon message
        if payload.message_id != self.role_message_id:
            return
        
        try:
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                return
            
            member = guild.get_member(payload.user_id)
            if not member:
                return
            
            # Récupère l'emoji et le rôle correspondant
            emoji = str(payload.emoji)
            selectable_roles = self.bot.config['roles']['selectable_roles']
            
            if emoji in selectable_roles:
                role_id = selectable_roles[emoji]['role_id']
                if role_id:
                    role = guild.get_role(role_id)
                    if role and role not in member.roles:
                        await member.add_roles(role)
                        logger.info(f"Rôle {role.name} ajouté à {member.name}")
                        
                        # Envoie un message privé de confirmation
                        try:
                            embed = discord.Embed(
                                title="✅ Rôle ajouté",
                                description=f"Le rôle **{role.name}** vous a été attribué !",
                                color=0x2ecc71
                            )
                            await member.send(embed=embed)
                        except discord.Forbidden:
                            pass  # L'utilisateur a désactivé les MPs
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout de rôle: {e}")
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """Gère la suppression de réactions pour les rôles"""
        # Ignore les réactions du bot
        if payload.user_id == self.bot.user.id:
            return
        
        # Vérifie si c'est le bon message
        if payload.message_id != self.role_message_id:
            return
        
        try:
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                return
            
            member = guild.get_member(payload.user_id)
            if not member:
                return
            
            # Récupère l'emoji et le rôle correspondant
            emoji = str(payload.emoji)
            selectable_roles = self.bot.config['roles']['selectable_roles']
            
            if emoji in selectable_roles:
                role_id = selectable_roles[emoji]['role_id']
                if role_id:
                    role = guild.get_role(role_id)
                    if role and role in member.roles:
                        await member.remove_roles(role)
                        logger.info(f"Rôle {role.name} retiré de {member.name}")
                        
                        # Envoie un message privé de confirmation
                        try:
                            embed = discord.Embed(
                                title="➖ Rôle retiré",
                                description=f"Le rôle **{role.name}** vous a été retiré !",
                                color=0xf39c12
                            )
                            await member.send(embed=embed)
                        except discord.Forbidden:
                            pass  # L'utilisateur a désactivé les MPs
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de rôle: {e}")
    
    @commands.command(name='setup_roles')
    @commands.has_permissions(administrator=True)
    async def setup_roles(self, ctx, channel: discord.TextChannel = None):
        """Configure le système de sélection de rôles"""
        if not channel:
            channel = ctx.channel
        
        # Mise à jour de la configuration
        self.bot.config['channels']['role_selection'] = channel.id
        
        # Création de l'embed
        embed = discord.Embed(
            title=self.bot.config['messages']['role_selection_title'],
            description=self.bot.config['messages']['role_selection_description'],
            color=int(self.bot.config['embed_color'], 16)
        )
        
        embed.add_field(
            name="ℹ️ Comment ça marche ?",
            value="Cliquez sur une réaction pour obtenir le rôle correspondant.\nCliquez à nouveau pour le retirer !",
            inline=False
        )
        
        # Envoie le message
        message = await channel.send(embed=embed)
        
        # Ajoute toutes les réactions
        selectable_roles = self.bot.config['roles']['selectable_roles']
        for emoji in selectable_roles.keys():
            await message.add_reaction(emoji)
        
        # Sauvegarde l'ID du message
        self.role_message_id = message.id
        
        # Crée le dossier data s'il n'existe pas
        import os
        os.makedirs('data', exist_ok=True)
        
        # Sauvegarde dans un fichier
        with open('data/role_message.json', 'w') as f:
            json.dump({'message_id': message.id}, f)
        
        # Sauvegarde de la configuration
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(self.bot.config, f, indent=2, ensure_ascii=False)
        
        embed_confirm = discord.Embed(
            title="✅ Configuration terminée",
            description=f"Le système de sélection de rôles a été configuré dans {channel.mention}",
            color=0x2ecc71
        )
        await ctx.send(embed=embed_confirm)
        logger.info(f"Système de rôles configuré dans {channel.name}")
    
    @commands.command(name='add_role')
    @commands.has_permissions(administrator=True)
    async def add_selectable_role(self, ctx, emoji: str, role: discord.Role):
        """Ajoute un rôle sélectionnable"""
        # Mise à jour de la configuration
        self.bot.config['roles']['selectable_roles'][emoji] = {
            'name': role.name,
            'role_id': role.id
        }
        
        # Sauvegarde de la configuration
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(self.bot.config, f, indent=2, ensure_ascii=False)
        
        embed = discord.Embed(
            title="✅ Rôle ajouté",
            description=f"Le rôle {role.mention} a été associé à l'emoji {emoji}",
            color=0x2ecc71
        )
        await ctx.send(embed=embed)
        logger.info(f"Rôle sélectionnable ajouté: {emoji} -> {role.name}")

async def setup(bot):
    await bot.add_cog(RoleSelection(bot))
