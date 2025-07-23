import discord
from discord.ext import commands
import logging

logger = logging.getLogger('discord_bot.welcome')

class Welcome(commands.Cog):
    """Cog pour gérer les messages de bienvenue"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Envoie un message de bienvenue quand un membre rejoint"""
        try:
            # Récupération du canal de bienvenue depuis la config
            welcome_channel_id = self.bot.config['channels']['welcome']
            
            if not welcome_channel_id:
                logger.warning("Canal de bienvenue non configuré")
                return
            
            welcome_channel = self.bot.get_channel(welcome_channel_id)
            if not welcome_channel:
                logger.error(f"Canal de bienvenue {welcome_channel_id} introuvable")
                return
            
            # Création de l'embed de bienvenue
            embed = discord.Embed(
                title=self.bot.config['messages']['welcome_title'],
                description=self.bot.config['messages']['welcome_description'].format(user=member.mention),
                color=int(self.bot.config['embed_color'], 16)
            )
            
            # Ajout de l'avatar du membre
            embed.set_thumbnail(url=member.display_avatar.url)
            
            # Ajout d'informations sur le serveur
            embed.add_field(
                name="📊 Informations du serveur",
                value=f"Tu es le **{member.guild.member_count}ème** membre !",
                inline=False
            )
            
            # Ajout du footer
            embed.set_footer(
                text=f"Membre depuis",
                icon_url=member.guild.icon.url if member.guild.icon else None
            )
            embed.timestamp = member.joined_at
            
            await welcome_channel.send(embed=embed)
            logger.info(f"Message de bienvenue envoyé pour {member.name}")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du message de bienvenue: {e}")
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Envoie un message d'au revoir et log quand un membre quitte"""
        try:
            # Reset des warnings quand quelqu'un quitte le serveur
            if hasattr(self.bot, 'warnings') and member.id in self.bot.warnings:
                del self.bot.warnings[member.id]
                logger.info(f"Warnings supprimés pour {member.name} (a quitté le serveur)")

            # Message d'au revoir
            goodbye_channel_id = self.bot.config['channels'].get('goodbye')
            if goodbye_channel_id:
                goodbye_channel = self.bot.get_channel(goodbye_channel_id)
                if goodbye_channel:
                    goodbye_message = self.bot.config['messages'].get('goodbye_description', "Au revoir {user} ! 👋")

                    embed = discord.Embed(
                        title="👋 Au revoir !",
                        description=goodbye_message.format(user=f"**{member.name}#{member.discriminator}**"),
                        color=0xe74c3c
                    )
                    embed.set_thumbnail(url=member.display_avatar.url)
                    embed.add_field(
                        name="📊 Membres restants",
                        value=f"{member.guild.member_count}",
                        inline=True
                    )
                    embed.timestamp = discord.utils.utcnow()

                    await goodbye_channel.send(embed=embed)
                    logger.info(f"Message d'au revoir envoyé pour {member.name}")

            # Log dans le canal de logs
            logs_channel_id = self.bot.config['channels'].get('logs')
            if logs_channel_id:
                logs_channel = self.bot.get_channel(logs_channel_id)
                if logs_channel:
                    embed = discord.Embed(
                        title="👋 Membre parti",
                        description=f"**{member.name}#{member.discriminator}** a quitté le serveur",
                        color=0xe74c3c
                    )
                    embed.set_thumbnail(url=member.display_avatar.url)
                    embed.add_field(
                        name="📊 Membres restants",
                        value=f"{member.guild.member_count}",
                        inline=True
                    )
                    embed.timestamp = discord.utils.utcnow()

                    await logs_channel.send(embed=embed)
                    logger.info(f"Log de départ envoyé pour {member.name}")

        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du message de départ: {e}")
    
    @commands.command(name='welcome_setup')
    @commands.has_permissions(administrator=True)
    async def setup_welcome(self, ctx, channel: discord.TextChannel = None):
        """Configure le canal de bienvenue"""
        if not channel:
            channel = ctx.channel
        
        # Mise à jour de la configuration
        self.bot.config['channels']['welcome'] = channel.id
        
        # Sauvegarde de la configuration
        import json
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(self.bot.config, f, indent=2, ensure_ascii=False)
        
        embed = discord.Embed(
            title="✅ Configuration mise à jour",
            description=f"Le canal de bienvenue a été défini sur {channel.mention}",
            color=0x2ecc71
        )
        await ctx.send(embed=embed)
        logger.info(f"Canal de bienvenue configuré: {channel.name}")
    
    @commands.command(name='welcome_message')
    @commands.has_permissions(administrator=True)
    async def set_welcome_message(self, ctx, *, message: str):
        """Personnalise le message de bienvenue"""
        # Mise à jour de la configuration
        self.bot.config['messages']['welcome_description'] = message

        # Sauvegarde de la configuration
        import json
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(self.bot.config, f, indent=2, ensure_ascii=False)

        embed = discord.Embed(
            title="✅ Message de bienvenue mis à jour",
            description=f"Nouveau message : {message}",
            color=0x2ecc71
        )
        await ctx.send(embed=embed)
        logger.info(f"Message de bienvenue mis à jour par {ctx.author.name}")

    @commands.command(name='goodbye_setup')
    @commands.has_permissions(administrator=True)
    async def setup_goodbye(self, ctx, channel: discord.TextChannel = None):
        """Configure le canal d'au revoir"""
        if not channel:
            channel = ctx.channel

        # Mise à jour de la configuration
        if 'goodbye' not in self.bot.config['channels']:
            self.bot.config['channels']['goodbye'] = None
        self.bot.config['channels']['goodbye'] = channel.id

        # Sauvegarde de la configuration
        import json
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(self.bot.config, f, indent=2, ensure_ascii=False)

        embed = discord.Embed(
            title="✅ Configuration mise à jour",
            description=f"Le canal d'au revoir a été défini sur {channel.mention}",
            color=0x2ecc71
        )
        await ctx.send(embed=embed)
        logger.info(f"Canal d'au revoir configuré: {channel.name}")

    @commands.command(name='goodbye_message')
    @commands.has_permissions(administrator=True)
    async def set_goodbye_message(self, ctx, *, message: str):
        """Personnalise le message d'au revoir"""
        # Mise à jour de la configuration
        if 'goodbye_description' not in self.bot.config['messages']:
            self.bot.config['messages']['goodbye_description'] = "Au revoir {user} ! 👋"
        self.bot.config['messages']['goodbye_description'] = message

        # Sauvegarde de la configuration
        import json
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(self.bot.config, f, indent=2, ensure_ascii=False)

        embed = discord.Embed(
            title="✅ Message d'au revoir mis à jour",
            description=f"Nouveau message : {message}",
            color=0x2ecc71
        )
        await ctx.send(embed=embed)
        logger.info(f"Message d'au revoir mis à jour par {ctx.author.name}")

    @commands.command(name='test_welcome')
    @commands.has_permissions(administrator=True)
    async def test_welcome(self, ctx):
        """Teste le message de bienvenue avec l'utilisateur actuel"""
        # Simule l'événement on_member_join
        await self.on_member_join(ctx.author)

        embed = discord.Embed(
            title="✅ Test effectué",
            description="Le message de bienvenue de test a été envoyé !",
            color=0x2ecc71
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Welcome(bot))
