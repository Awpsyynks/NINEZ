import discord
from discord.ext import commands
import json
import logging
from datetime import datetime
import asyncio

logger = logging.getLogger('discord_bot.suggestions')

class SuggestionView(discord.ui.View):
    """Vue pour les boutons de suggestion"""
    
    def __init__(self, suggestion_id):
        super().__init__(timeout=None)
        self.suggestion_id = suggestion_id
    
    @discord.ui.button(label='👍', style=discord.ButtonStyle.success, custom_id='suggestion_upvote')
    async def upvote(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Vote pour la suggestion"""
        cog = interaction.client.get_cog('Suggestions')
        if cog:
            await cog.handle_vote(interaction, self.suggestion_id, 'upvote')
    
    @discord.ui.button(label='👎', style=discord.ButtonStyle.danger, custom_id='suggestion_downvote')
    async def downvote(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Vote contre la suggestion"""
        cog = interaction.client.get_cog('Suggestions')
        if cog:
            await cog.handle_vote(interaction, self.suggestion_id, 'downvote')

class SuggestionManageView(discord.ui.View):
    """Vue pour la gestion des suggestions (modérateurs)"""
    
    def __init__(self, suggestion_id):
        super().__init__(timeout=None)
        self.suggestion_id = suggestion_id
    
    @discord.ui.button(label='✅ Approuver', style=discord.ButtonStyle.success, custom_id='suggestion_approve')
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Approuve la suggestion"""
        cog = interaction.client.get_cog('Suggestions')
        if cog:
            await cog.handle_manage(interaction, self.suggestion_id, 'approve')
    
    @discord.ui.button(label='❌ Rejeter', style=discord.ButtonStyle.danger, custom_id='suggestion_reject')
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Rejette la suggestion"""
        cog = interaction.client.get_cog('Suggestions')
        if cog:
            await cog.handle_manage(interaction, self.suggestion_id, 'reject')
    
    @discord.ui.button(label='🔄 En cours', style=discord.ButtonStyle.primary, custom_id='suggestion_progress')
    async def in_progress(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Marque la suggestion comme en cours"""
        cog = interaction.client.get_cog('Suggestions')
        if cog:
            await cog.handle_manage(interaction, self.suggestion_id, 'in_progress')

class Suggestions(commands.Cog):
    """Système de suggestions et feedback"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config = self.load_config()
        self.suggestions = self.load_suggestions()
        
    def load_config(self):
        """Charge la configuration des suggestions"""
        try:
            with open('suggestions_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            default_config = {
                "enabled": True,
                "channels": {
                    "suggestions": None,
                    "approved": None,
                    "rejected": None
                },
                "settings": {
                    "anonymous_suggestions": False,
                    "auto_thread": True,
                    "require_reason_for_rejection": True,
                    "min_suggestion_length": 10,
                    "max_suggestion_length": 1000,
                    "cooldown_minutes": 5
                },
                "roles": {
                    "suggestion_manager": None,
                    "can_suggest": []
                },
                "voting": {
                    "enabled": True,
                    "show_vote_count": True,
                    "allow_vote_change": True
                }
            }
            self.save_config(default_config)
            return default_config
    
    def load_suggestions(self):
        """Charge les suggestions"""
        try:
            with open('suggestions.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def save_config(self, config=None):
        """Sauvegarde la configuration"""
        if config is None:
            config = self.config
        try:
            with open('suggestions_config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erreur sauvegarde config suggestions: {e}")
    
    def save_suggestions(self):
        """Sauvegarde les suggestions"""
        try:
            with open('suggestions.json', 'w', encoding='utf-8') as f:
                json.dump(self.suggestions, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erreur sauvegarde suggestions: {e}")
    
    def can_manage_suggestions(self, member):
        """Vérifie si un membre peut gérer les suggestions"""
        if member.guild_permissions.administrator:
            return True
        
        manager_role_id = self.config['roles']['suggestion_manager']
        if manager_role_id:
            manager_role = member.guild.get_role(manager_role_id)
            if manager_role and manager_role in member.roles:
                return True
        
        return False
    
    def can_suggest(self, member):
        """Vérifie si un membre peut faire des suggestions"""
        if not self.config['enabled']:
            return False
        
        allowed_roles = self.config['roles']['can_suggest']
        if not allowed_roles:  # Si aucun rôle spécifié, tout le monde peut suggérer
            return True
        
        for role in member.roles:
            if role.id in allowed_roles:
                return True
        
        return False
    
    async def handle_vote(self, interaction, suggestion_id, vote_type):
        """Gère les votes sur les suggestions"""
        if suggestion_id not in self.suggestions:
            await interaction.response.send_message("❌ Cette suggestion n'existe plus.", ephemeral=True)
            return
        
        if not self.config['voting']['enabled']:
            await interaction.response.send_message("❌ Les votes sont désactivés.", ephemeral=True)
            return
        
        suggestion = self.suggestions[suggestion_id]
        user_id = str(interaction.user.id)
        
        # Vérifier si l'utilisateur a déjà voté
        current_vote = suggestion['votes'].get(user_id)
        
        if current_vote == vote_type:
            # Retirer le vote
            del suggestion['votes'][user_id]
            await interaction.response.send_message(f"✅ Vote retiré.", ephemeral=True)
        elif current_vote and not self.config['voting']['allow_vote_change']:
            await interaction.response.send_message("❌ Vous avez déjà voté pour cette suggestion.", ephemeral=True)
            return
        else:
            # Ajouter/changer le vote
            suggestion['votes'][user_id] = vote_type
            vote_text = "pour" if vote_type == "upvote" else "contre"
            await interaction.response.send_message(f"✅ Vous avez voté {vote_text} cette suggestion.", ephemeral=True)
        
        # Mettre à jour l'embed
        await self.update_suggestion_embed(interaction, suggestion_id)
        self.save_suggestions()
    
    async def handle_manage(self, interaction, suggestion_id, action):
        """Gère les actions de modération sur les suggestions"""
        if not self.can_manage_suggestions(interaction.user):
            await interaction.response.send_message("❌ Vous n'avez pas les permissions pour gérer les suggestions.", ephemeral=True)
            return
        
        if suggestion_id not in self.suggestions:
            await interaction.response.send_message("❌ Cette suggestion n'existe plus.", ephemeral=True)
            return
        
        suggestion = self.suggestions[suggestion_id]
        
        if action == 'approve':
            suggestion['status'] = 'approved'
            suggestion['moderator'] = interaction.user.id
            suggestion['moderated_at'] = datetime.now().isoformat()
            
            await interaction.response.send_message("✅ Suggestion approuvée !", ephemeral=True)
            
        elif action == 'reject':
            # Demander une raison si requis
            if self.config['settings']['require_reason_for_rejection']:
                modal = RejectReasonModal(suggestion_id)
                await interaction.response.send_modal(modal)
                return
            else:
                suggestion['status'] = 'rejected'
                suggestion['moderator'] = interaction.user.id
                suggestion['moderated_at'] = datetime.now().isoformat()
                
                await interaction.response.send_message("❌ Suggestion rejetée.", ephemeral=True)
        
        elif action == 'in_progress':
            suggestion['status'] = 'in_progress'
            suggestion['moderator'] = interaction.user.id
            suggestion['moderated_at'] = datetime.now().isoformat()
            
            await interaction.response.send_message("🔄 Suggestion marquée comme en cours !", ephemeral=True)
        
        # Mettre à jour l'embed
        await self.update_suggestion_embed(interaction, suggestion_id)
        self.save_suggestions()
    
    async def update_suggestion_embed(self, interaction, suggestion_id):
        """Met à jour l'embed d'une suggestion"""
        suggestion = self.suggestions[suggestion_id]
        
        # Calculer les votes
        upvotes = sum(1 for vote in suggestion['votes'].values() if vote == 'upvote')
        downvotes = sum(1 for vote in suggestion['votes'].values() if vote == 'downvote')
        
        # Couleur selon le statut
        status_colors = {
            'pending': 0x3498db,
            'approved': 0x2ecc71,
            'rejected': 0xe74c3c,
            'in_progress': 0xf39c12
        }
        
        status_emojis = {
            'pending': '⏳',
            'approved': '✅',
            'rejected': '❌',
            'in_progress': '🔄'
        }
        
        status = suggestion['status']
        
        embed = discord.Embed(
            title=f"{status_emojis[status]} Suggestion #{suggestion_id}",
            description=suggestion['content'],
            color=status_colors[status],
            timestamp=datetime.fromisoformat(suggestion['created_at'])
        )
        
        # Auteur
        if not suggestion.get('anonymous', False):
            author = interaction.guild.get_member(suggestion['author_id'])
            if author:
                embed.set_author(name=author.display_name, icon_url=author.display_avatar.url)
        else:
            embed.set_author(name="Suggestion anonyme")
        
        # Votes
        if self.config['voting']['enabled'] and self.config['voting']['show_vote_count']:
            embed.add_field(name="👍 Pour", value=str(upvotes), inline=True)
            embed.add_field(name="👎 Contre", value=str(downvotes), inline=True)
            
            # Ratio
            total_votes = upvotes + downvotes
            if total_votes > 0:
                ratio = (upvotes / total_votes) * 100
                embed.add_field(name="📊 Ratio", value=f"{ratio:.1f}%", inline=True)
        
        # Statut
        embed.add_field(name="📋 Statut", value=status.replace('_', ' ').title(), inline=True)
        
        # Modérateur
        if suggestion.get('moderator'):
            moderator = interaction.guild.get_member(suggestion['moderator'])
            if moderator:
                embed.add_field(name="👮 Modéré par", value=moderator.mention, inline=True)
        
        # Raison de rejet
        if status == 'rejected' and suggestion.get('rejection_reason'):
            embed.add_field(name="📝 Raison du rejet", value=suggestion['rejection_reason'], inline=False)
        
        embed.set_footer(text=f"ID: {suggestion_id}")
        
        # Vues selon le statut
        if status == 'pending':
            vote_view = SuggestionView(suggestion_id)
            manage_view = SuggestionManageView(suggestion_id)
            
            # Combiner les vues
            combined_view = discord.ui.View(timeout=None)
            for item in vote_view.children:
                combined_view.add_item(item)
            for item in manage_view.children:
                combined_view.add_item(item)
            
            await interaction.edit_original_response(embed=embed, view=combined_view)
        else:
            await interaction.edit_original_response(embed=embed, view=None)
    
    @commands.command(name='suggest')
    @commands.cooldown(1, 300, commands.BucketType.user)  # 5 minutes de cooldown
    async def suggest(self, ctx, *, suggestion):
        """Fait une suggestion"""
        if not self.can_suggest(ctx.author):
            embed = discord.Embed(
                title="❌ Permissions insuffisantes",
                description="Vous n'avez pas la permission de faire des suggestions.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        # Vérifier la longueur
        min_length = self.config['settings']['min_suggestion_length']
        max_length = self.config['settings']['max_suggestion_length']
        
        if len(suggestion) < min_length:
            embed = discord.Embed(
                title="❌ Suggestion trop courte",
                description=f"Minimum {min_length} caractères.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        if len(suggestion) > max_length:
            embed = discord.Embed(
                title="❌ Suggestion trop longue",
                description=f"Maximum {max_length} caractères.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        # Canal de suggestions
        suggestions_channel_id = self.config['channels']['suggestions']
        if not suggestions_channel_id:
            embed = discord.Embed(
                title="❌ Canal non configuré",
                description="Le canal de suggestions n'est pas configuré.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        suggestions_channel = ctx.guild.get_channel(suggestions_channel_id)
        if not suggestions_channel:
            embed = discord.Embed(
                title="❌ Canal introuvable",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        # Créer la suggestion
        suggestion_id = f"{ctx.guild.id}_{len(self.suggestions) + 1}"
        
        suggestion_data = {
            'id': suggestion_id,
            'author_id': ctx.author.id,
            'content': suggestion,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'votes': {},
            'anonymous': self.config['settings']['anonymous_suggestions']
        }
        
        # Créer l'embed
        embed = discord.Embed(
            title="⏳ Nouvelle Suggestion",
            description=suggestion,
            color=0x3498db,
            timestamp=datetime.now()
        )
        
        if not suggestion_data['anonymous']:
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        else:
            embed.set_author(name="Suggestion anonyme")
        
        embed.add_field(name="👍 Pour", value="0", inline=True)
        embed.add_field(name="👎 Contre", value="0", inline=True)
        embed.add_field(name="📋 Statut", value="En attente", inline=True)
        embed.set_footer(text=f"ID: {suggestion_id}")
        
        # Vues
        vote_view = SuggestionView(suggestion_id)
        manage_view = SuggestionManageView(suggestion_id)
        
        combined_view = discord.ui.View(timeout=None)
        for item in vote_view.children:
            combined_view.add_item(item)
        for item in manage_view.children:
            combined_view.add_item(item)
        
        # Envoyer dans le canal de suggestions
        suggestion_message = await suggestions_channel.send(embed=embed, view=combined_view)
        
        # Créer un thread si activé
        if self.config['settings']['auto_thread']:
            thread = await suggestion_message.create_thread(
                name=f"Discussion - Suggestion #{suggestion_id}",
                auto_archive_duration=1440  # 24 heures
            )
            await thread.send(f"💬 Discutez de cette suggestion ici !")
        
        # Sauvegarder
        suggestion_data['message_id'] = suggestion_message.id
        suggestion_data['channel_id'] = suggestions_channel.id
        self.suggestions[suggestion_id] = suggestion_data
        self.save_suggestions()
        
        # Confirmer à l'utilisateur
        embed = discord.Embed(
            title="✅ Suggestion envoyée",
            description=f"Votre suggestion a été envoyée dans {suggestions_channel.mention}",
            color=0x2ecc71
        )
        await ctx.send(embed=embed)
        
        # Supprimer le message de commande
        try:
            await ctx.message.delete()
        except:
            pass

class RejectReasonModal(discord.ui.Modal):
    """Modal pour demander la raison du rejet"""
    
    def __init__(self, suggestion_id):
        super().__init__(title="Raison du rejet")
        self.suggestion_id = suggestion_id
        
        self.reason = discord.ui.TextInput(
            label="Raison du rejet",
            placeholder="Expliquez pourquoi cette suggestion est rejetée...",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=True
        )
        self.add_item(self.reason)
    
    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog('Suggestions')
        if cog and self.suggestion_id in cog.suggestions:
            suggestion = cog.suggestions[self.suggestion_id]
            suggestion['status'] = 'rejected'
            suggestion['moderator'] = interaction.user.id
            suggestion['moderated_at'] = datetime.now().isoformat()
            suggestion['rejection_reason'] = self.reason.value
            
            await cog.update_suggestion_embed(interaction, self.suggestion_id)
            cog.save_suggestions()
            
            await interaction.response.send_message("❌ Suggestion rejetée avec raison.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Suggestions(bot))
