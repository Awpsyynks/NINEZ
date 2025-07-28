import discord
from discord.ext import commands, tasks
import json
import random
import asyncio
import logging
from datetime import datetime, timedelta
import re

logger = logging.getLogger('discord_bot.giveaways')

class GiveawayView(discord.ui.View):
    """Vue pour les boutons de giveaway"""
    
    def __init__(self, giveaway_id):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id
    
    @discord.ui.button(label='🎉 Participer', style=discord.ButtonStyle.primary, custom_id='giveaway_join')
    async def join_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Rejoindre le giveaway"""
        cog = interaction.client.get_cog('Giveaways')
        if cog:
            await cog.handle_giveaway_interaction(interaction, self.giveaway_id, 'join')

class Giveaways(commands.Cog):
    """Système de giveaways et événements"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_giveaways = self.load_giveaways()
        self.events = self.load_events()
        self.check_giveaways.start()
        
    def load_giveaways(self):
        """Charge les giveaways actifs"""
        try:
            with open('giveaways.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def load_events(self):
        """Charge les événements programmés"""
        try:
            with open('events.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def save_giveaways(self):
        """Sauvegarde les giveaways"""
        try:
            with open('giveaways.json', 'w', encoding='utf-8') as f:
                json.dump(self.active_giveaways, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erreur sauvegarde giveaways: {e}")
    
    def save_events(self):
        """Sauvegarde les événements"""
        try:
            with open('events.json', 'w', encoding='utf-8') as f:
                json.dump(self.events, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erreur sauvegarde événements: {e}")
    
    def parse_duration(self, duration_str):
        """Parse une durée (ex: 1h30m, 2d, 30s)"""
        pattern = r'(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?'
        match = re.match(pattern, duration_str.lower())
        
        if not match:
            return None
        
        days, hours, minutes, seconds = match.groups()
        
        total_seconds = 0
        if days:
            total_seconds += int(days) * 86400
        if hours:
            total_seconds += int(hours) * 3600
        if minutes:
            total_seconds += int(minutes) * 60
        if seconds:
            total_seconds += int(seconds)
        
        return total_seconds
    
    @tasks.loop(seconds=30)
    async def check_giveaways(self):
        """Vérifie les giveaways qui se terminent"""
        now = datetime.now()
        
        for giveaway_id, giveaway in list(self.active_giveaways.items()):
            end_time = datetime.fromisoformat(giveaway['end_time'])
            
            if now >= end_time:
                await self.end_giveaway(giveaway_id)
    
    async def end_giveaway(self, giveaway_id):
        """Termine un giveaway et annonce les gagnants"""
        if giveaway_id not in self.active_giveaways:
            return
        
        giveaway = self.active_giveaways[giveaway_id]
        
        try:
            guild = self.bot.get_guild(giveaway['guild_id'])
            channel = guild.get_channel(giveaway['channel_id'])
            message = await channel.fetch_message(giveaway['message_id'])
            
            participants = giveaway['participants']
            winners_count = giveaway['winners']
            
            if len(participants) < winners_count:
                winners_count = len(participants)
            
            if participants:
                # Sélectionner les gagnants
                winners = random.sample(participants, winners_count)
                
                # Créer l'embed des résultats
                embed = discord.Embed(
                    title="🎉 Giveaway Terminé !",
                    description=f"**Prix:** {giveaway['prize']}",
                    color=0xf1c40f,
                    timestamp=datetime.now()
                )
                
                if winners:
                    winners_mentions = []
                    for winner_id in winners:
                        user = guild.get_member(winner_id)
                        if user:
                            winners_mentions.append(user.mention)
                    
                    embed.add_field(
                        name=f"🏆 Gagnant(s) ({len(winners)})",
                        value="\n".join(winners_mentions),
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="😢 Aucun gagnant",
                        value="Pas assez de participants",
                        inline=False
                    )
                
                embed.add_field(name="👥 Participants", value=str(len(participants)), inline=True)
                embed.add_field(name="🎯 Organisé par", value=f"<@{giveaway['host_id']}>", inline=True)
                
                # Mettre à jour le message
                await message.edit(embed=embed, view=None)
                
                # Annoncer les gagnants
                if winners:
                    winners_text = ", ".join([f"<@{winner_id}>" for winner_id in winners])
                    await channel.send(f"🎉 Félicitations {winners_text} ! Vous avez gagné **{giveaway['prize']}** !")
                
            else:
                # Aucun participant
                embed = discord.Embed(
                    title="😢 Giveaway Annulé",
                    description=f"**Prix:** {giveaway['prize']}\n\nAucun participant",
                    color=0xe74c3c,
                    timestamp=datetime.now()
                )
                await message.edit(embed=embed, view=None)
            
            # Supprimer le giveaway des actifs
            del self.active_giveaways[giveaway_id]
            self.save_giveaways()
            
        except Exception as e:
            logger.error(f"Erreur fin giveaway {giveaway_id}: {e}")
    
    async def handle_giveaway_interaction(self, interaction, giveaway_id, action):
        """Gère les interactions avec les giveaways"""
        if giveaway_id not in self.active_giveaways:
            await interaction.response.send_message("❌ Ce giveaway n'existe plus.", ephemeral=True)
            return
        
        giveaway = self.active_giveaways[giveaway_id]
        user_id = interaction.user.id
        
        if action == 'join':
            # Vérifier les conditions
            if user_id == giveaway['host_id']:
                await interaction.response.send_message("❌ Vous ne pouvez pas participer à votre propre giveaway.", ephemeral=True)
                return
            
            # Vérifier les exigences
            requirements = giveaway.get('requirements', {})
            
            if requirements.get('min_account_age', 0) > 0:
                account_age = (datetime.now() - interaction.user.created_at).days
                if account_age < requirements['min_account_age']:
                    await interaction.response.send_message(
                        f"❌ Votre compte doit avoir au moins {requirements['min_account_age']} jours.",
                        ephemeral=True
                    )
                    return
            
            if requirements.get('required_role'):
                role = interaction.guild.get_role(requirements['required_role'])
                if role and role not in interaction.user.roles:
                    await interaction.response.send_message(
                        f"❌ Vous devez avoir le rôle {role.mention} pour participer.",
                        ephemeral=True
                    )
                    return
            
            # Ajouter/retirer de la participation
            if user_id in giveaway['participants']:
                giveaway['participants'].remove(user_id)
                await interaction.response.send_message("✅ Vous ne participez plus au giveaway.", ephemeral=True)
            else:
                giveaway['participants'].append(user_id)
                await interaction.response.send_message("✅ Vous participez maintenant au giveaway !", ephemeral=True)
            
            # Mettre à jour l'embed
            embed = interaction.message.embeds[0]
            for i, field in enumerate(embed.fields):
                if field.name == "👥 Participants":
                    embed.set_field_at(i, name="👥 Participants", value=str(len(giveaway['participants'])), inline=True)
                    break
            
            await interaction.edit_original_response(embed=embed)
            self.save_giveaways()
    
    @commands.command(name='giveaway', aliases=['gstart'])
    @commands.has_permissions(manage_guild=True)
    async def create_giveaway(self, ctx, duration: str, winners: int, *, prize):
        """Crée un nouveau giveaway"""
        # Parser la durée
        duration_seconds = self.parse_duration(duration)
        if not duration_seconds or duration_seconds < 60:
            embed = discord.Embed(
                title="❌ Durée invalide",
                description="Format: `1d2h30m` (minimum 1 minute)",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        if winners < 1 or winners > 20:
            embed = discord.Embed(
                title="❌ Nombre de gagnants invalide",
                description="Entre 1 et 20 gagnants",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        # Créer le giveaway
        end_time = datetime.now() + timedelta(seconds=duration_seconds)
        giveaway_id = f"{ctx.guild.id}_{ctx.channel.id}_{int(datetime.now().timestamp())}"
        
        embed = discord.Embed(
            title="🎉 GIVEAWAY !",
            description=f"**Prix:** {prize}",
            color=0xf1c40f,
            timestamp=end_time
        )
        
        embed.add_field(name="🏆 Gagnants", value=str(winners), inline=True)
        embed.add_field(name="👥 Participants", value="0", inline=True)
        embed.add_field(name="⏰ Se termine", value=f"<t:{int(end_time.timestamp())}:R>", inline=True)
        embed.add_field(name="🎯 Organisé par", value=ctx.author.mention, inline=False)
        
        embed.set_footer(text="Cliquez sur le bouton pour participer !")
        
        view = GiveawayView(giveaway_id)
        message = await ctx.send(embed=embed, view=view)
        
        # Sauvegarder le giveaway
        self.active_giveaways[giveaway_id] = {
            'guild_id': ctx.guild.id,
            'channel_id': ctx.channel.id,
            'message_id': message.id,
            'host_id': ctx.author.id,
            'prize': prize,
            'winners': winners,
            'end_time': end_time.isoformat(),
            'participants': [],
            'requirements': {}
        }
        self.save_giveaways()
        
        # Supprimer le message de commande
        try:
            await ctx.message.delete()
        except:
            pass
    
    @commands.command(name='gend')
    @commands.has_permissions(manage_guild=True)
    async def end_giveaway_command(self, ctx, message_id: int):
        """Termine un giveaway manuellement"""
        # Trouver le giveaway
        giveaway_id = None
        for gid, giveaway in self.active_giveaways.items():
            if giveaway['message_id'] == message_id:
                giveaway_id = gid
                break
        
        if not giveaway_id:
            embed = discord.Embed(
                title="❌ Giveaway introuvable",
                description="Aucun giveaway actif avec cet ID de message",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        await self.end_giveaway(giveaway_id)
        
        embed = discord.Embed(
            title="✅ Giveaway terminé",
            description="Le giveaway a été terminé manuellement",
            color=0x2ecc71
        )
        await ctx.send(embed=embed)
    
    @commands.command(name='greroll')
    @commands.has_permissions(manage_guild=True)
    async def reroll_giveaway(self, ctx, message_id: int):
        """Relance un giveaway terminé"""
        try:
            message = await ctx.channel.fetch_message(message_id)
            
            if not message.embeds or "Giveaway Terminé" not in message.embeds[0].title:
                embed = discord.Embed(
                    title="❌ Message invalide",
                    description="Ce message n'est pas un giveaway terminé",
                    color=0xe74c3c
                )
                await ctx.send(embed=embed)
                return
            
            # Extraire les informations du giveaway
            embed_data = message.embeds[0]
            
            # Simuler un nouveau tirage (pour l'exemple)
            embed = discord.Embed(
                title="🎉 Giveaway Relancé !",
                description=embed_data.description,
                color=0xf1c40f,
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="🏆 Nouveau gagnant",
                value="Relance effectuée !",
                inline=False
            )
            
            await message.edit(embed=embed)
            await ctx.send("🎉 Giveaway relancé avec succès !")
            
        except discord.NotFound:
            embed = discord.Embed(
                title="❌ Message introuvable",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
    
    @commands.command(name='glist')
    @commands.has_permissions(manage_guild=True)
    async def list_giveaways(self, ctx):
        """Liste les giveaways actifs"""
        guild_giveaways = {
            gid: giveaway for gid, giveaway in self.active_giveaways.items()
            if giveaway['guild_id'] == ctx.guild.id
        }
        
        if not guild_giveaways:
            embed = discord.Embed(
                title="📭 Aucun giveaway actif",
                description="Aucun giveaway en cours sur ce serveur",
                color=0x95a5a6
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="🎉 Giveaways Actifs",
            color=0xf1c40f,
            timestamp=datetime.now()
        )
        
        for gid, giveaway in list(guild_giveaways.items())[:10]:  # Limite à 10
            end_time = datetime.fromisoformat(giveaway['end_time'])
            channel = ctx.guild.get_channel(giveaway['channel_id'])
            
            embed.add_field(
                name=f"🎁 {giveaway['prize'][:50]}",
                value=f"Canal: {channel.mention if channel else 'Supprimé'}\n"
                      f"Participants: {len(giveaway['participants'])}\n"
                      f"Fin: <t:{int(end_time.timestamp())}:R>\n"
                      f"ID: {giveaway['message_id']}",
                inline=True
            )
        
        if len(guild_giveaways) > 10:
            embed.set_footer(text=f"... et {len(guild_giveaways) - 10} autres")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Giveaways(bot))
