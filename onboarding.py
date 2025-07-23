import discord
from discord.ext import commands
import json
import logging
from datetime import datetime

logger = logging.getLogger('discord_bot.onboarding')

class RulesView(discord.ui.View):
    """Vue pour accepter les règles"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label='✅ J\'accepte les règles', style=discord.ButtonStyle.success, emoji='📋')
    async def accept_rules(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Accepte les règles et donne accès au serveur"""
        guild = interaction.guild
        user = interaction.user
        
        # Rôle "Membre Vérifié" 
        verified_role = discord.utils.get(guild.roles, name="Membre Vérifié")
        if not verified_role:
            # Crée le rôle s'il n'existe pas
            verified_role = await guild.create_role(
                name="Membre Vérifié",
                color=0x2ecc71,
                reason="Rôle pour les membres qui ont accepté les règles"
            )
        
        # Retire le rôle "Non Vérifié" s'il existe
        unverified_role = discord.utils.get(guild.roles, name="Non Vérifié")
        if unverified_role and unverified_role in user.roles:
            await user.remove_roles(unverified_role, reason="Règles acceptées")
        
        # Ajoute le rôle vérifié
        await user.add_roles(verified_role, reason="Règles acceptées")
        
        embed = discord.Embed(
            title="🎉 Bienvenue dans la communauté !",
            description=f"Merci {user.mention} d'avoir accepté les règles !\n\nTu peux maintenant accéder à tous les salons du serveur. 🚀",
            color=0x2ecc71
        )
        embed.add_field(
            name="🎯 Prochaine étape",
            value="Va dans le salon **choix-communauté** pour nous dire pourquoi tu es là !",
            inline=False
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.timestamp = datetime.now()
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"{user.name} a accepté les règles")

class CommunityChoiceView(discord.ui.View):
    """Vue pour choisir pourquoi on est sur le serveur"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label='💬 Discuter', style=discord.ButtonStyle.primary, emoji='💭')
    async def choice_discuss(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "Discuter", "💬", 0x3498db, "Tu aimes échanger et parler avec la communauté !")
    
    @discord.ui.button(label='😂 Rigoler', style=discord.ButtonStyle.secondary, emoji='🤣')
    async def choice_laugh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "Rigoler", "😂", 0xf39c12, "Tu es là pour t'amuser et faire rire les autres !")
    
    @discord.ui.button(label='🎮 Jouer', style=discord.ButtonStyle.success, emoji='🕹️')
    async def choice_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "Jouer", "🎮", 0x9b59b6, "Tu es un gamer dans l'âme !")
    
    @discord.ui.button(label='🤝 Faire des amis', style=discord.ButtonStyle.danger, emoji='❤️')
    async def choice_friends(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "Faire des amis", "🤝", 0xe91e63, "Tu cherches à créer des liens avec la communauté !")
    
    @discord.ui.button(label='📚 Apprendre', style=discord.ButtonStyle.primary, emoji='🧠')
    async def choice_learn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "Apprendre", "📚", 0x1abc9c, "Tu es là pour découvrir et apprendre de nouvelles choses !")
    
    async def handle_choice(self, interaction, choice_name, emoji, color, description):
        """Gère le choix de l'utilisateur"""
        user = interaction.user
        guild = interaction.guild
        
        # Rôle basé sur le choix
        role_name = f"{emoji} {choice_name}"
        choice_role = discord.utils.get(guild.roles, name=role_name)
        
        if not choice_role:
            # Crée le rôle s'il n'existe pas
            choice_role = await guild.create_role(
                name=role_name,
                color=color,
                reason=f"Rôle pour les membres qui sont là pour {choice_name.lower()}"
            )
        
        # Ajoute le rôle
        await user.add_roles(choice_role, reason=f"Choix: {choice_name}")
        
        embed = discord.Embed(
            title=f"{emoji} Excellent choix !",
            description=f"**{user.display_name}**, {description}",
            color=color
        )
        embed.add_field(
            name="🎭 Ton rôle",
            value=f"Tu as maintenant le rôle **{role_name}** !",
            inline=True
        )
        embed.add_field(
            name="🌟 Avantages",
            value="• Accès aux salons spécialisés\n• Communauté de personnes similaires\n• Événements dédiés",
            inline=True
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="Tu peux changer de rôle à tout moment !")
        embed.timestamp = datetime.now()
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Message public stylé
        public_embed = discord.Embed(
            description=f"🎉 **{user.display_name}** nous a rejoint pour **{choice_name.lower()}** ! {emoji}",
            color=color
        )
        await interaction.followup.send(embed=public_embed)
        
        logger.info(f"{user.name} a choisi: {choice_name}")

class Onboarding(commands.Cog):
    """Cog pour l'onboarding et l'accueil des nouveaux membres"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='setup_rules')
    @commands.has_permissions(administrator=True)
    async def setup_rules(self, ctx, channel: discord.TextChannel = None):
        """Configure le système de règles avec acceptation"""
        if not channel:
            channel = ctx.channel
        
        # Création des rôles nécessaires
        guild = ctx.guild
        
        # Rôle "Non Vérifié"
        unverified_role = discord.utils.get(guild.roles, name="Non Vérifié")
        if not unverified_role:
            unverified_role = await guild.create_role(
                name="Non Vérifié",
                color=0xe74c3c,
                reason="Rôle pour les nouveaux membres non vérifiés"
            )
        
        # Rôle "Membre Vérifié"
        verified_role = discord.utils.get(guild.roles, name="Membre Vérifié")
        if not verified_role:
            verified_role = await guild.create_role(
                name="Membre Vérifié",
                color=0x2ecc71,
                reason="Rôle pour les membres vérifiés"
            )
        
        # Embed des règles stylé
        rules_embed = discord.Embed(
            title="📋 RÈGLES DU SERVEUR",
            description="**Bienvenue sur notre serveur !** 🎉\n\nPour accéder à tous les salons, tu dois d'abord accepter nos règles :",
            color=0x3498db
        )
        
        rules_embed.add_field(
            name="1️⃣ Respect",
            value="• Respecte tous les membres\n• Pas d'insultes ou de harcèlement\n• Sois poli et bienveillant",
            inline=False
        )
        
        rules_embed.add_field(
            name="2️⃣ Contenu",
            value="• Pas de contenu NSFW\n• Pas de spam ou flood\n• Utilise les bons salons",
            inline=False
        )
        
        rules_embed.add_field(
            name="3️⃣ Comportement",
            value="• Pas de pub sans autorisation\n• Pas de trolling excessif\n• Écoute les modérateurs",
            inline=False
        )
        
        rules_embed.add_field(
            name="4️⃣ Sanctions",
            value="• 1er avertissement : Warning\n• 2ème avertissement : Mute temporaire\n• 3ème avertissement : Ban définitif",
            inline=False
        )
        
        rules_embed.add_field(
            name="🎯 Important",
            value="En cliquant sur le bouton ci-dessous, tu acceptes toutes ces règles et tu pourras accéder au serveur !",
            inline=False
        )
        
        rules_embed.set_footer(text="Clique sur le bouton pour accepter les règles !")
        rules_embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        
        view = RulesView()
        await channel.send(embed=rules_embed, view=view)
        
        # Confirmation
        confirm_embed = discord.Embed(
            title="✅ Système de règles configuré",
            description=f"Le système de règles a été configuré dans {channel.mention}",
            color=0x2ecc71
        )
        confirm_embed.add_field(
            name="🎭 Rôles créés",
            value=f"• {unverified_role.mention} - Nouveaux membres\n• {verified_role.mention} - Membres vérifiés",
            inline=False
        )
        await ctx.send(embed=confirm_embed)
        logger.info(f"Système de règles configuré dans {channel.name}")
    
    @commands.command(name='setup_community_choice')
    @commands.has_permissions(administrator=True)
    async def setup_community_choice(self, ctx, channel: discord.TextChannel = None):
        """Configure le système de choix de communauté"""
        if not channel:
            channel = ctx.channel
        
        # Embed stylé pour les choix
        choice_embed = discord.Embed(
            title="🌟 CHOIX DE COMMUNAUTÉ",
            description="**Dis-nous pourquoi tu es là !** 🎯\n\nChaque choix te donnera un rôle spécial et l'accès à des salons dédiés :",
            color=0xf1c40f
        )
        
        choice_embed.add_field(
            name="💬 Discuter",
            value="Tu aimes échanger, débattre et parler de tout et de rien avec la communauté !",
            inline=True
        )
        
        choice_embed.add_field(
            name="😂 Rigoler",
            value="Tu es là pour t'amuser, faire des blagues et partager de bons moments !",
            inline=True
        )
        
        choice_embed.add_field(
            name="🎮 Jouer",
            value="Tu es un gamer et tu cherches des partenaires de jeu ou des discussions gaming !",
            inline=True
        )
        
        choice_embed.add_field(
            name="🤝 Faire des amis",
            value="Tu veux créer des liens, rencontrer de nouvelles personnes et agrandir ton cercle !",
            inline=True
        )
        
        choice_embed.add_field(
            name="📚 Apprendre",
            value="Tu es curieux et tu veux découvrir, apprendre et partager tes connaissances !",
            inline=True
        )
        
        choice_embed.add_field(
            name="🎁 Bonus",
            value="• Rôle coloré unique\n• Accès aux salons spécialisés\n• Événements dédiés\n• Communauté similaire",
            inline=False
        )
        
        choice_embed.set_footer(text="Clique sur le bouton qui te correspond le mieux !")
        choice_embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
        
        view = CommunityChoiceView()
        await channel.send(embed=choice_embed, view=view)
        
        # Confirmation
        confirm_embed = discord.Embed(
            title="✅ Système de choix configuré",
            description=f"Le système de choix de communauté a été configuré dans {channel.mention}",
            color=0x2ecc71
        )
        await ctx.send(embed=confirm_embed)
        logger.info(f"Système de choix configuré dans {channel.name}")

    @commands.command(name='verify_member')
    @commands.has_permissions(manage_roles=True)
    async def verify_member(self, ctx, member: discord.Member):
        """Vérifie manuellement un membre (modérateurs)"""
        guild = ctx.guild

        # Rôles
        unverified_role = discord.utils.get(guild.roles, name="Non Vérifié")
        verified_role = discord.utils.get(guild.roles, name="Membre Vérifié")

        if not verified_role:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Le système de règles n'est pas configuré. Utilisez `!setup_rules` d'abord.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        # Retire le rôle non vérifié et ajoute le vérifié
        if unverified_role and unverified_role in member.roles:
            await member.remove_roles(unverified_role, reason=f"Vérifié manuellement par {ctx.author}")

        await member.add_roles(verified_role, reason=f"Vérifié manuellement par {ctx.author}")

        embed = discord.Embed(
            title="✅ Membre vérifié",
            description=f"{member.mention} a été vérifié manuellement par {ctx.author.mention}",
            color=0x2ecc71
        )
        await ctx.send(embed=embed)
        logger.info(f"{member.name} vérifié manuellement par {ctx.author.name}")

    @commands.command(name='unverify_member')
    @commands.has_permissions(manage_roles=True)
    async def unverify_member(self, ctx, member: discord.Member):
        """Retire la vérification d'un membre (modérateurs)"""
        guild = ctx.guild

        # Rôles
        unverified_role = discord.utils.get(guild.roles, name="Non Vérifié")
        verified_role = discord.utils.get(guild.roles, name="Membre Vérifié")

        if not unverified_role:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Le système de règles n'est pas configuré. Utilisez `!setup_rules` d'abord.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        # Retire le rôle vérifié et ajoute le non vérifié
        if verified_role and verified_role in member.roles:
            await member.remove_roles(verified_role, reason=f"Dévérifié par {ctx.author}")

        await member.add_roles(unverified_role, reason=f"Dévérifié par {ctx.author}")

        embed = discord.Embed(
            title="⚠️ Membre dévérifié",
            description=f"{member.mention} a été dévérifié par {ctx.author.mention}",
            color=0xf39c12
        )
        await ctx.send(embed=embed)
        logger.info(f"{member.name} dévérifié par {ctx.author.name}")

    @commands.command(name='onboarding_stats')
    @commands.has_permissions(manage_guild=True)
    async def onboarding_stats(self, ctx):
        """Affiche les statistiques d'onboarding"""
        guild = ctx.guild

        # Comptage des rôles
        unverified_role = discord.utils.get(guild.roles, name="Non Vérifié")
        verified_role = discord.utils.get(guild.roles, name="Membre Vérifié")

        unverified_count = len(unverified_role.members) if unverified_role else 0
        verified_count = len(verified_role.members) if verified_role else 0

        # Comptage des choix de communauté
        choice_roles = {
            "💬 Discuter": 0,
            "😂 Rigoler": 0,
            "🎮 Jouer": 0,
            "🤝 Faire des amis": 0,
            "📚 Apprendre": 0
        }

        for role_name in choice_roles.keys():
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                choice_roles[role_name] = len(role.members)

        embed = discord.Embed(
            title="📊 Statistiques d'Onboarding",
            description=f"Statistiques pour **{guild.name}**",
            color=0x3498db
        )

        embed.add_field(
            name="🔐 Vérification",
            value=f"• **Non vérifiés** : {unverified_count}\n• **Vérifiés** : {verified_count}",
            inline=True
        )

        total_choices = sum(choice_roles.values())
        embed.add_field(
            name="🌟 Choix de communauté",
            value=f"• **Total avec choix** : {total_choices}",
            inline=True
        )

        embed.add_field(
            name="📈 Taux de conversion",
            value=f"• **Vérification** : {(verified_count/(verified_count+unverified_count)*100):.1f}%" if (verified_count+unverified_count) > 0 else "N/A",
            inline=True
        )

        # Détail des choix
        choices_text = ""
        for choice, count in choice_roles.items():
            percentage = (count/total_choices*100) if total_choices > 0 else 0
            choices_text += f"• **{choice}** : {count} ({percentage:.1f}%)\n"

        if choices_text:
            embed.add_field(
                name="🎯 Répartition des choix",
                value=choices_text,
                inline=False
            )

        embed.set_footer(text=f"Total membres : {guild.member_count}")
        embed.timestamp = datetime.now()

        await ctx.send(embed=embed)

    @commands.command(name='reset_choice')
    async def reset_choice(self, ctx):
        """Permet à un utilisateur de changer son choix de communauté"""
        user = ctx.author
        guild = ctx.guild

        # Retire tous les rôles de choix existants
        choice_role_names = ["💬 Discuter", "😂 Rigoler", "🎮 Jouer", "🤝 Faire des amis", "📚 Apprendre"]
        removed_roles = []

        for role_name in choice_role_names:
            role = discord.utils.get(guild.roles, name=role_name)
            if role and role in user.roles:
                await user.remove_roles(role, reason="Reset du choix de communauté")
                removed_roles.append(role_name)

        if removed_roles:
            embed = discord.Embed(
                title="🔄 Choix réinitialisé",
                description=f"Tes anciens rôles ont été supprimés : {', '.join(removed_roles)}",
                color=0xf39c12
            )
            embed.add_field(
                name="🎯 Prochaine étape",
                value="Va dans le salon **choix-communauté** pour faire un nouveau choix !",
                inline=False
            )
        else:
            embed = discord.Embed(
                title="ℹ️ Aucun choix à réinitialiser",
                description="Tu n'as pas encore fait de choix de communauté.",
                color=0x3498db
            )
            embed.add_field(
                name="🎯 Suggestion",
                value="Va dans le salon **choix-communauté** pour faire ton choix !",
                inline=False
            )

        await ctx.send(embed=embed)
        logger.info(f"{user.name} a réinitialisé son choix de communauté")

    @commands.command(name='setup_onboarding_complete')
    @commands.has_permissions(administrator=True)
    async def setup_complete_onboarding(self, ctx):
        """Configuration complète automatique de l'onboarding"""
        guild = ctx.guild

        # Étape 1: Créer les salons nécessaires
        embed = discord.Embed(
            title="🚀 Configuration Onboarding Complète",
            description="Création automatique des salons et configuration...",
            color=0x3498db
        )
        message = await ctx.send(embed=embed)

        # Créer la catégorie Onboarding
        onboarding_category = discord.utils.get(guild.categories, name="📋 ONBOARDING")
        if not onboarding_category:
            onboarding_category = await guild.create_category(
                "📋 ONBOARDING",
                reason="Catégorie pour l'onboarding automatique"
            )

        # Créer le salon des règles
        rules_channel = discord.utils.get(guild.channels, name="règles")
        if not rules_channel:
            # Permissions pour le salon des règles
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }

            rules_channel = await guild.create_text_channel(
                "règles",
                category=onboarding_category,
                overwrites=overwrites,
                topic="📋 Accepte les règles pour accéder au serveur !",
                reason="Salon des règles automatique"
            )

        # Créer le salon de choix de communauté
        choice_channel = discord.utils.get(guild.channels, name="choix-communauté")
        if not choice_channel:
            # Permissions pour le salon de choix (seulement membres vérifiés)
            verified_role = discord.utils.get(guild.roles, name="Membre Vérifié")
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }

            if verified_role:
                overwrites[verified_role] = discord.PermissionOverwrite(read_messages=True, send_messages=False)

            choice_channel = await guild.create_text_channel(
                "choix-communauté",
                category=onboarding_category,
                overwrites=overwrites,
                topic="🌟 Dis-nous pourquoi tu es là et reçois ton rôle coloré !",
                reason="Salon de choix de communauté automatique"
            )

        # Créer le salon de bienvenue si nécessaire
        welcome_channel = discord.utils.get(guild.channels, name="bienvenue")
        if not welcome_channel:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }

            welcome_channel = await guild.create_text_channel(
                "bienvenue",
                category=onboarding_category,
                overwrites=overwrites,
                topic="🎉 Messages de bienvenue pour les nouveaux membres !",
                reason="Salon de bienvenue automatique"
            )

        # Configuration automatique
        await self.setup_rules(ctx, rules_channel)
        await self.setup_community_choice(ctx, choice_channel)

        # Configuration du bienvenue
        self.bot.config['channels']['welcome'] = welcome_channel.id
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(self.bot.config, f, indent=2, ensure_ascii=False)

        # Message de confirmation final
        final_embed = discord.Embed(
            title="✅ Onboarding Configuré avec Succès !",
            description="Votre système d'onboarding complet est maintenant actif ! 🎉",
            color=0x2ecc71
        )

        final_embed.add_field(
            name="📋 Salons créés",
            value=f"• {rules_channel.mention} - Règles interactives\n• {choice_channel.mention} - Choix de communauté\n• {welcome_channel.mention} - Messages de bienvenue",
            inline=False
        )

        final_embed.add_field(
            name="🎯 Fonctionnement",
            value="1. Nouveau membre arrive → Rôle 'Non Vérifié'\n2. Va dans règles → Accepte → Rôle 'Membre Vérifié'\n3. Va dans choix-communauté → Choisit → Rôle coloré",
            inline=False
        )

        final_embed.add_field(
            name="🔧 Commandes utiles",
            value="`!onboarding_stats` - Voir les statistiques\n`!verify_member @user` - Vérifier manuellement\n`!reset_choice` - Changer son choix",
            inline=False
        )

        final_embed.set_footer(text="Système d'onboarding NINEZ - Prêt à l'emploi !")

        await message.edit(embed=final_embed)
        logger.info(f"Onboarding complet configuré par {ctx.author.name}")

async def setup(bot):
    await bot.add_cog(Onboarding(bot))
