import discord
from discord.ext import commands
import json
import logging
from datetime import datetime

logger = logging.getLogger('discord_bot.tickets')

class TicketView(discord.ui.View):
    """Vue pour les boutons de ticket"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label='Fermer le ticket', style=discord.ButtonStyle.danger, emoji='🔒', custom_id='close_ticket_btn')
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Ferme le ticket"""
        if not interaction.user.guild_permissions.manage_channels:
            embed = discord.Embed(
                title="❌ Permissions insuffisantes",
                description="Vous n'avez pas les permissions pour fermer ce ticket.",
                color=0xe74c3c
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🔒 Fermeture du ticket",
            description="Ce ticket va être fermé dans 5 secondes...",
            color=0xf39c12
        )
        await interaction.response.send_message(embed=embed)
        
        # Attendre 5 secondes puis supprimer le canal
        import asyncio
        await asyncio.sleep(5)
        
        try:
            await interaction.channel.delete(reason=f"Ticket fermé par {interaction.user}")
            logger.info(f"Ticket {interaction.channel.name} fermé par {interaction.user.name}")
        except discord.NotFound:
            pass  # Le canal a déjà été supprimé

class CreateTicketView(discord.ui.View):
    """Vue pour créer un ticket"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label='Créer un ticket', style=discord.ButtonStyle.primary, emoji='🎫', custom_id='create_ticket_btn')
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Crée un nouveau ticket"""
        guild = interaction.guild
        user = interaction.user
        
        # Vérifie si l'utilisateur a déjà un ticket ouvert
        existing_ticket = discord.utils.get(guild.channels, name=f"ticket-{user.name.lower()}")
        if existing_ticket:
            embed = discord.Embed(
                title="❌ Ticket déjà existant",
                description=f"Vous avez déjà un ticket ouvert : {existing_ticket.mention}",
                color=0xe74c3c
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Récupère la catégorie des tickets
        bot = interaction.client
        tickets_category_id = bot.config['channels']['tickets_category']
        tickets_category = None
        
        if tickets_category_id:
            tickets_category = guild.get_channel(tickets_category_id)
        
        if not tickets_category:
            # Crée la catégorie si elle n'existe pas
            tickets_category = await guild.create_category(
                name="🎫 Tickets",
                reason="Catégorie pour les tickets de support"
            )
            bot.config['channels']['tickets_category'] = tickets_category.id
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(bot.config, f, indent=2, ensure_ascii=False)
        
        # Crée le canal de ticket
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # Ajoute les permissions pour les modérateurs
        for role in guild.roles:
            if role.permissions.manage_channels:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{user.name.lower()}",
            category=tickets_category,
            overwrites=overwrites,
            reason=f"Ticket créé par {user}"
        )
        
        # Envoie le message d'accueil dans le ticket
        embed = discord.Embed(
            title="🎫 Nouveau ticket",
            description=f"Bonjour {user.mention} !\n\nVotre ticket a été créé avec succès. Un membre du staff vous répondra bientôt.\n\n**Décrivez votre problème ou votre demande ci-dessous.**",
            color=int(bot.config['embed_color'], 16)
        )
        embed.set_footer(text="Utilisez le bouton ci-dessous pour fermer ce ticket.")
        
        view = TicketView()
        await ticket_channel.send(embed=embed, view=view)
        
        # Confirme la création du ticket
        embed_confirm = discord.Embed(
            title="✅ Ticket créé",
            description=f"Votre ticket a été créé : {ticket_channel.mention}",
            color=0x2ecc71
        )
        await interaction.response.send_message(embed=embed_confirm, ephemeral=True)

        # Enregistrer le ticket actif
        tickets_cog = bot.get_cog('Tickets')
        if tickets_cog:
            tickets_cog.active_tickets[user.id] = ticket_channel.id
            tickets_cog.save_configuration()

        # Log la création du ticket
        logs_channel_id = bot.config['channels']['logs']
        if logs_channel_id:
            logs_channel = guild.get_channel(logs_channel_id)
            if logs_channel:
                log_embed = discord.Embed(
                    title="🎫 Nouveau ticket",
                    description=f"**{user.name}#{user.discriminator}** a créé un ticket",
                    color=int(bot.config['embed_color'], 16),
                    timestamp=datetime.utcnow()
                )
                log_embed.add_field(name="Canal", value=ticket_channel.mention, inline=True)
                log_embed.set_thumbnail(url=user.display_avatar.url)
                await logs_channel.send(embed=log_embed)
        
        logger.info(f"Ticket créé par {user.name}: {ticket_channel.name}")

class Tickets(commands.Cog):
    """Cog pour gérer le système de tickets"""

    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        """Charge les vues persistantes au démarrage"""
        self.bot.add_view(TicketView())
        self.bot.add_view(CreateTicketView())
        logger.info("✅ Vues persistantes des tickets chargées")
        self.active_tickets = {}  # {user_id: channel_id}

        # Charger la configuration depuis les données persistantes
        self.load_configuration()

    def load_configuration(self):
        """Charge la configuration depuis les données persistantes"""
        if hasattr(self.bot, 'get_persistent_data'):
            config = self.bot.get_persistent_data('tickets', 'config', {})
            self.active_tickets = config.get('active_tickets', {})
            # Convertir les clés string en int pour active_tickets
            self.active_tickets = {int(k): v for k, v in self.active_tickets.items()}

    def save_configuration(self):
        """Sauvegarde la configuration dans les données persistantes"""
        if hasattr(self.bot, 'set_persistent_data'):
            config = {
                'active_tickets': self.active_tickets
            }
            self.bot.set_persistent_data('tickets', 'config', config)

    async def load_from_persistent_data(self):
        """Méthode appelée par le bot pour charger les données"""
        self.load_configuration()

        # Restaurer les vues des boutons si nécessaire
        ticket_channel_id = self.bot.config['channels'].get('tickets')
        if ticket_channel_id:
            for guild in self.bot.guilds:
                channel = guild.get_channel(ticket_channel_id)
                if channel:
                    # Ajouter la vue persistante pour les boutons
                    view = CreateTicketView()
                    self.bot.add_view(view)
                    break

    async def save_to_persistent_data(self):
        """Méthode appelée par le bot pour sauvegarder les données"""
        self.save_configuration()
    
    @commands.command(name='ticket')
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def create_ticket_command(self, ctx):
        """Crée un nouveau ticket (commande alternative)"""
        guild = ctx.guild
        user = ctx.author
        
        # Vérifie si l'utilisateur a déjà un ticket ouvert
        existing_ticket = discord.utils.get(guild.channels, name=f"ticket-{user.name.lower()}")
        if existing_ticket:
            embed = discord.Embed(
                title="❌ Ticket déjà existant",
                description=f"Vous avez déjà un ticket ouvert : {existing_ticket.mention}",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        # Utilise la même logique que le bouton
        view = CreateTicketView()
        await view.create_ticket.callback(view, type('MockInteraction', (), {
            'guild': guild,
            'user': user,
            'client': self.bot,
            'response': type('MockResponse', (), {
                'send_message': lambda embed, ephemeral=False: ctx.send(embed=embed)
            })()
        })())
    
    @commands.command(name='setup_tickets')
    @commands.has_permissions(administrator=True)
    async def setup_tickets(self, ctx, channel: discord.TextChannel = None):
        """Configure le système de tickets"""
        if not channel:
            channel = ctx.channel
        
        embed = discord.Embed(
            title="🎫 Système de tickets",
            description="Cliquez sur le bouton ci-dessous pour créer un ticket de support.\n\n**Quand utiliser les tickets ?**\n• Signaler un problème\n• Demander de l'aide\n• Contacter le staff\n• Faire une suggestion",
            color=int(self.bot.config['embed_color'], 16)
        )
        embed.set_footer(text="Un canal privé sera créé pour vous.")
        
        view = CreateTicketView()
        message = await channel.send(embed=embed, view=view)

        # Sauvegarder la configuration
        self.bot.config['channels']['tickets'] = channel.id
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(self.bot.config, f, indent=2, ensure_ascii=False)

        # Sauvegarder dans les données persistantes
        self.save_configuration()

        embed_confirm = discord.Embed(
            title="✅ Configuration terminée",
            description=f"Le système de tickets a été configuré dans {channel.mention}",
            color=0x2ecc71
        )
        embed_confirm.add_field(
            name="💾 Persistance",
            value="✅ Configuration sauvegardée automatiquement",
            inline=False
        )
        await ctx.send(embed=embed_confirm)
        logger.info(f"Système de tickets configuré dans {channel.name}")
    
    @commands.command(name='add')
    @commands.has_permissions(manage_channels=True)
    async def add_user_to_ticket(self, ctx, member: discord.Member):
        """Ajoute un utilisateur au ticket actuel"""
        if not ctx.channel.name.startswith('ticket-'):
            embed = discord.Embed(
                title="❌ Erreur",
                description="Cette commande ne peut être utilisée que dans un canal de ticket.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        # Ajoute les permissions de lecture et d'écriture pour l'utilisateur
        overwrites = ctx.channel.overwrites
        overwrites[member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        try:
            await ctx.channel.edit(overwrites=overwrites, reason=f"Utilisateur ajouté par {ctx.author}")

            embed = discord.Embed(
                title="✅ Utilisateur ajouté",
                description=f"{member.mention} a été ajouté à ce ticket.",
                color=0x2ecc71
            )
            await ctx.send(embed=embed)
            logger.info(f"Utilisateur {member.name} ajouté au ticket {ctx.channel.name} par {ctx.author.name}")

        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Je n'ai pas les permissions pour modifier ce canal.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)

    @commands.command(name='remove')
    @commands.has_permissions(manage_channels=True)
    async def remove_user_from_ticket(self, ctx, member: discord.Member):
        """Retire un utilisateur du ticket actuel"""
        if not ctx.channel.name.startswith('ticket-'):
            embed = discord.Embed(
                title="❌ Erreur",
                description="Cette commande ne peut être utilisée que dans un canal de ticket.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        # Retire les permissions pour l'utilisateur
        overwrites = ctx.channel.overwrites
        if member in overwrites:
            del overwrites[member]
        else:
            overwrites[member] = discord.PermissionOverwrite(read_messages=False, send_messages=False)

        try:
            await ctx.channel.edit(overwrites=overwrites, reason=f"Utilisateur retiré par {ctx.author}")

            embed = discord.Embed(
                title="✅ Utilisateur retiré",
                description=f"{member.mention} a été retiré de ce ticket.",
                color=0x2ecc71
            )
            await ctx.send(embed=embed)
            logger.info(f"Utilisateur {member.name} retiré du ticket {ctx.channel.name} par {ctx.author.name}")

        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Je n'ai pas les permissions pour modifier ce canal.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)

    @commands.command(name='close')
    @commands.has_permissions(manage_channels=True)
    async def close_ticket_command(self, ctx):
        """Ferme le ticket actuel (commande alternative)"""
        if not ctx.channel.name.startswith('ticket-'):
            embed = discord.Embed(
                title="❌ Erreur",
                description="Cette commande ne peut être utilisée que dans un canal de ticket.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="🔒 Fermeture du ticket",
            description="Ce ticket va être fermé dans 5 secondes...",
            color=0xf39c12
        )
        await ctx.send(embed=embed)

        import asyncio
        await asyncio.sleep(5)

        try:
            await ctx.channel.delete(reason=f"Ticket fermé par {ctx.author}")
            logger.info(f"Ticket {ctx.channel.name} fermé par {ctx.author.name}")
        except discord.NotFound:
            pass

async def setup(bot):
    await bot.add_cog(Tickets(bot))
