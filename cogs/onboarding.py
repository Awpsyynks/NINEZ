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

    @commands.command(name='create_mega_server')
    @commands.has_permissions(administrator=True)
    async def create_mega_server(self, ctx):
        """🚀 CRÉE UN SERVEUR COMMUNAUTAIRE ULTRA-COMPLET AUTOMATIQUEMENT !"""
        guild = ctx.guild

        # Message de début
        embed = discord.Embed(
            title="🚀 CRÉATION DU MEGA-SERVEUR COMMUNAUTAIRE",
            description="**Création automatique d'un serveur communautaire complet !**\n\n⏳ Cela peut prendre quelques minutes...",
            color=0xf1c40f
        )
        embed.add_field(
            name="🎯 Ce qui va être créé",
            value="• **15+ catégories** thématiques\n• **50+ salons** texte et vocal\n• **20+ rôles** colorés\n• **Permissions** optimisées\n• **Système d'onboarding** complet",
            inline=False
        )
        message = await ctx.send(embed=embed)

        # Créer tous les rôles nécessaires d'abord
        await self.create_all_roles(guild, message)

        # Créer toutes les catégories et salons
        await self.create_all_categories_and_channels(guild, message)

        # Configuration finale
        await self.setup_final_configuration(ctx, guild, message)

    async def create_all_roles(self, guild, message):
        """Crée tous les rôles nécessaires"""
        embed = discord.Embed(
            title="🎭 CRÉATION DES RÔLES",
            description="Création de tous les rôles colorés et fonctionnels...",
            color=0x9b59b6
        )
        await message.edit(embed=embed)

        # Rôles de base
        base_roles = [
            {"name": "👑 Fondateur", "color": 0xffd700, "permissions": discord.Permissions.all()},
            {"name": "🛡️ Administrateur", "color": 0xe74c3c, "permissions": discord.Permissions(administrator=True)},
            {"name": "⚔️ Modérateur", "color": 0x3498db, "permissions": discord.Permissions(manage_messages=True, manage_roles=True, kick_members=True)},
            {"name": "🎯 Helper", "color": 0x2ecc71, "permissions": discord.Permissions(manage_messages=True)},
            {"name": "🤖 Bot", "color": 0x95a5a6, "permissions": discord.Permissions.none()},
        ]

        # Rôles de communauté (avec couleurs stylées)
        community_roles = [
            {"name": "💬 Discuteur", "color": 0x3498db},
            {"name": "😂 Rigoleur", "color": 0xf39c12},
            {"name": "🎮 Gamer", "color": 0x9b59b6},
            {"name": "🤝 Social", "color": 0xe91e63},
            {"name": "📚 Intellectuel", "color": 0x1abc9c},
            {"name": "🎵 Mélomane", "color": 0xff6b6b},
            {"name": "🎨 Créatif", "color": 0xfeca57},
            {"name": "💻 Développeur", "color": 0x48dbfb},
            {"name": "📱 Tech", "color": 0x0abde3},
            {"name": "🏃 Sportif", "color": 0x00d2d3},
        ]

        # Rôles de niveau
        level_roles = [
            {"name": "🌟 Niveau 10", "color": 0xf1c40f},
            {"name": "💎 Niveau 25", "color": 0x3498db},
            {"name": "🏆 Niveau 50", "color": 0x9b59b6},
            {"name": "👑 Niveau 100", "color": 0xe74c3c},
        ]

        # Rôles spéciaux
        special_roles = [
            {"name": "🎂 Anniversaire", "color": 0xff69b4},
            {"name": "🎉 Événement", "color": 0xffa500},
            {"name": "💰 VIP", "color": 0xffd700},
            {"name": "🔇 Muted", "color": 0x95a5a6},
            {"name": "⏳ Non Vérifié", "color": 0xe74c3c},
            {"name": "✅ Membre Vérifié", "color": 0x2ecc71},
        ]

        all_roles = base_roles + community_roles + level_roles + special_roles

        for role_data in all_roles:
            existing_role = discord.utils.get(guild.roles, name=role_data["name"])
            if not existing_role:
                try:
                    permissions = role_data.get("permissions", discord.Permissions.none())
                    await guild.create_role(
                        name=role_data["name"],
                        color=role_data["color"],
                        permissions=permissions,
                        reason="Création automatique du mega-serveur"
                    )
                except Exception as e:
                    logger.error(f"Erreur création rôle {role_data['name']}: {e}")

    async def create_all_categories_and_channels(self, guild, message):
        """Crée toutes les catégories et salons"""
        embed = discord.Embed(
            title="🏗️ CRÉATION DES SALONS",
            description="Création de toutes les catégories et salons...",
            color=0x3498db
        )
        await message.edit(embed=embed)

        # Récupérer les rôles créés
        verified_role = discord.utils.get(guild.roles, name="✅ Membre Vérifié")
        unverified_role = discord.utils.get(guild.roles, name="⏳ Non Vérifié")
        muted_role = discord.utils.get(guild.roles, name="🔇 Muted")

        # Permissions de base
        base_overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        if verified_role:
            base_overwrites[verified_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        if muted_role:
            base_overwrites[muted_role] = discord.PermissionOverwrite(send_messages=False, add_reactions=False)

        # 1. CATÉGORIE ONBOARDING
        await self.create_onboarding_category(guild, unverified_role, verified_role)

        # 2. CATÉGORIE INFORMATIONS
        await self.create_info_category(guild, base_overwrites)

        # 3. CATÉGORIE DISCUSSION GÉNÉRALE
        await self.create_general_category(guild, base_overwrites)

        # 4. CATÉGORIE GAMING
        await self.create_gaming_category(guild, base_overwrites)

        # 5. CATÉGORIE CRÉATIVITÉ
        await self.create_creative_category(guild, base_overwrites)

        # 6. CATÉGORIE DÉTENTE
        await self.create_chill_category(guild, base_overwrites)

        # 7. CATÉGORIE VOCAL GÉNÉRAL
        await self.create_voice_general_category(guild, base_overwrites)

        # 8. CATÉGORIE VOCAL GAMING
        await self.create_voice_gaming_category(guild, base_overwrites)

        # 9. CATÉGORIE ÉVÉNEMENTS
        await self.create_events_category(guild, base_overwrites)

        # 10. CATÉGORIE MODÉRATION
        await self.create_moderation_category(guild)

    async def create_onboarding_category(self, guild, unverified_role, verified_role):
        """Crée la catégorie d'onboarding"""
        category = await self.get_or_create_category(guild, "📋 ACCUEIL & RÈGLES")

        # Permissions spéciales pour l'onboarding
        public_overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        verified_overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        if verified_role:
            verified_overwrites[verified_role] = discord.PermissionOverwrite(read_messages=True, send_messages=False)

        channels = [
            {"name": "👋-bienvenue", "topic": "🎉 Messages de bienvenue automatiques !", "overwrites": public_overwrites},
            {"name": "📋-règles", "topic": "📜 Accepte les règles pour accéder au serveur !", "overwrites": public_overwrites},
            {"name": "🌟-choix-communauté", "topic": "🎯 Choisis ton type de membre et reçois ton rôle coloré !", "overwrites": verified_overwrites},
            {"name": "📢-annonces", "topic": "📣 Annonces importantes du serveur", "overwrites": public_overwrites},
            {"name": "🆕-nouveautés", "topic": "✨ Nouvelles fonctionnalités et mises à jour", "overwrites": public_overwrites},
        ]

        for channel_data in channels:
            await self.get_or_create_text_channel(guild, channel_data["name"], category, channel_data["topic"], channel_data["overwrites"])

    async def create_info_category(self, guild, base_overwrites):
        """Crée la catégorie d'informations"""
        category = await self.get_or_create_category(guild, "ℹ️ INFORMATIONS")

        info_overwrites = {**base_overwrites}
        info_overwrites[guild.default_role] = discord.PermissionOverwrite(read_messages=True, send_messages=False)

        channels = [
            {"name": "📊-statistiques", "topic": "📈 Stats du serveur en temps réel"},
            {"name": "🎯-objectifs", "topic": "🏆 Objectifs et défis du serveur"},
            {"name": "🔗-liens-utiles", "topic": "🌐 Liens importants et ressources"},
            {"name": "❓-faq", "topic": "🤔 Questions fréquemment posées"},
            {"name": "📝-changelog", "topic": "📋 Historique des modifications"},
        ]

        for channel_data in channels:
            await self.get_or_create_text_channel(guild, channel_data["name"], category, channel_data["topic"], info_overwrites)

    async def create_general_category(self, guild, base_overwrites):
        """Crée la catégorie de discussion générale"""
        category = await self.get_or_create_category(guild, "💬 DISCUSSION GÉNÉRALE")

        channels = [
            {"name": "💬-général", "topic": "💭 Discussion générale pour tous les sujets"},
            {"name": "🗣️-débats", "topic": "🎯 Débats constructifs et discussions profondes"},
            {"name": "❓-questions", "topic": "🤔 Posez vos questions à la communauté"},
            {"name": "💡-idées", "topic": "🧠 Partagez vos idées et projets"},
            {"name": "📰-actualités", "topic": "🌍 Actualités et news du monde"},
            {"name": "🎓-éducation", "topic": "📚 Discussions éducatives et apprentissage"},
        ]

        for channel_data in channels:
            await self.get_or_create_text_channel(guild, channel_data["name"], category, channel_data["topic"], base_overwrites)

    async def create_gaming_category(self, guild, base_overwrites):
        """Crée la catégorie gaming"""
        category = await self.get_or_create_category(guild, "🎮 GAMING")

        channels = [
            {"name": "🎮-général-gaming", "topic": "🕹️ Discussion générale sur les jeux vidéo"},
            {"name": "🔥-nouveautés-jeux", "topic": "✨ Nouveaux jeux et sorties"},
            {"name": "👥-recherche-équipe", "topic": "🤝 Trouvez des partenaires de jeu"},
            {"name": "🏆-compétitions", "topic": "⚔️ Tournois et compétitions"},
            {"name": "📱-mobile-gaming", "topic": "📲 Jeux mobiles et discussions"},
            {"name": "💻-pc-gaming", "topic": "🖥️ Gaming PC, configs et optimisation"},
            {"name": "🎯-fps-games", "topic": "🔫 FPS: CS:GO, Valorant, COD..."},
            {"name": "⚔️-moba-games", "topic": "🛡️ MOBA: LoL, Dota, Heroes..."},
            {"name": "🏰-mmorpg", "topic": "🗡️ MMORPG et jeux de rôle"},
        ]

        for channel_data in channels:
            await self.get_or_create_text_channel(guild, channel_data["name"], category, channel_data["topic"], base_overwrites)

    async def create_creative_category(self, guild, base_overwrites):
        """Crée la catégorie créativité"""
        category = await self.get_or_create_category(guild, "🎨 CRÉATIVITÉ")

        channels = [
            {"name": "🎨-galerie-art", "topic": "🖼️ Partagez vos créations artistiques"},
            {"name": "📸-photographie", "topic": "📷 Photos et techniques de photographie"},
            {"name": "🎵-musique", "topic": "🎶 Musique, compositions et découvertes"},
            {"name": "✍️-écriture", "topic": "📝 Écriture créative et littérature"},
            {"name": "🎬-vidéos", "topic": "🎥 Créations vidéo et montage"},
            {"name": "💻-programmation", "topic": "⌨️ Code, projets et développement"},
            {"name": "🏗️-projets", "topic": "🔨 Vos projets en cours et collaborations"},
        ]

        for channel_data in channels:
            await self.get_or_create_text_channel(guild, channel_data["name"], category, channel_data["topic"], base_overwrites)

    async def create_chill_category(self, guild, base_overwrites):
        """Crée la catégorie détente"""
        category = await self.get_or_create_category(guild, "😎 DÉTENTE & FUN")

        channels = [
            {"name": "😂-memes", "topic": "🤣 Memes et images drôles"},
            {"name": "🎭-blagues", "topic": "😄 Blagues et humour"},
            {"name": "🍕-nourriture", "topic": "🍔 Cuisine et gastronomie"},
            {"name": "🎬-films-séries", "topic": "📺 Cinéma et séries TV"},
            {"name": "📚-livres", "topic": "📖 Littérature et recommandations"},
            {"name": "🏃-sport", "topic": "⚽ Sports et activités physiques"},
            {"name": "🌍-voyages", "topic": "✈️ Voyages et découvertes"},
            {"name": "🐾-animaux", "topic": "🐱 Photos et histoires d'animaux"},
            {"name": "🎲-jeux-bot", "topic": "🤖 Commandes du bot et mini-jeux"},
        ]

        for channel_data in channels:
            await self.get_or_create_text_channel(guild, channel_data["name"], category, channel_data["topic"], base_overwrites)

    async def create_voice_general_category(self, guild, base_overwrites):
        """Crée la catégorie vocal générale"""
        category = await self.get_or_create_category(guild, "🔊 VOCAL GÉNÉRAL")

        voice_channels = [
            "🎤 Salon Principal",
            "💬 Discussion Libre",
            "🎵 Musique & Chill",
            "📚 Étude Silencieuse",
            "🤝 Rencontres",
            "🌙 Nocturne",
        ]

        for channel_name in voice_channels:
            await self.get_or_create_voice_channel(guild, channel_name, category, base_overwrites)

    async def create_voice_gaming_category(self, guild, base_overwrites):
        """Crée la catégorie vocal gaming"""
        category = await self.get_or_create_category(guild, "🎮 VOCAL GAMING")

        voice_channels = [
            "🎯 Gaming Général",
            "⚔️ Équipe 1",
            "🛡️ Équipe 2",
            "🏆 Compétition",
            "🎲 Party Games",
            "📱 Mobile Gaming",
            "💻 PC Gaming",
            "🎮 Console Gaming",
        ]

        for channel_name in voice_channels:
            await self.get_or_create_voice_channel(guild, channel_name, category, base_overwrites)

    async def create_events_category(self, guild, base_overwrites):
        """Crée la catégorie événements"""
        category = await self.get_or_create_category(guild, "🎉 ÉVÉNEMENTS")

        channels = [
            {"name": "🎁-giveaways", "topic": "🎉 Giveaways et concours en cours"},
            {"name": "🎪-événements", "topic": "🎊 Événements spéciaux du serveur"},
            {"name": "🏆-tournois", "topic": "⚔️ Tournois et compétitions"},
            {"name": "🎂-anniversaires", "topic": "🎈 Anniversaires des membres"},
            {"name": "📅-planning", "topic": "📋 Planning des événements à venir"},
            {"name": "💡-suggestions", "topic": "🤔 Vos suggestions pour le serveur"},
        ]

        for channel_data in channels:
            await self.get_or_create_text_channel(guild, channel_data["name"], category, channel_data["topic"], base_overwrites)

    async def create_moderation_category(self, guild):
        """Crée la catégorie modération (privée)"""
        category = await self.get_or_create_category(guild, "🛡️ MODÉRATION")

        # Permissions pour staff seulement
        admin_role = discord.utils.get(guild.roles, name="🛡️ Administrateur")
        mod_role = discord.utils.get(guild.roles, name="⚔️ Modérateur")
        helper_role = discord.utils.get(guild.roles, name="🎯 Helper")

        staff_overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        if admin_role:
            staff_overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        if mod_role:
            staff_overwrites[mod_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        if helper_role:
            staff_overwrites[helper_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channels = [
            {"name": "🛡️-staff-général", "topic": "💼 Discussion générale du staff"},
            {"name": "📊-logs", "topic": "📋 Logs automatiques du serveur"},
            {"name": "⚠️-rapports", "topic": "🚨 Rapports de modération"},
            {"name": "🔧-commandes-bot", "topic": "🤖 Commandes et tests du bot"},
            {"name": "📝-notes-membres", "topic": "📄 Notes sur les membres"},
        ]

        for channel_data in channels:
            await self.get_or_create_text_channel(guild, channel_data["name"], category, channel_data["topic"], staff_overwrites)

        # Salon vocal staff
        await self.get_or_create_voice_channel(guild, "🛡️ Réunion Staff", category, staff_overwrites)

    async def get_or_create_category(self, guild, name):
        """Récupère ou crée une catégorie"""
        category = discord.utils.get(guild.categories, name=name)
        if not category:
            try:
                category = await guild.create_category(name, reason="Création automatique du mega-serveur")
            except Exception as e:
                logger.error(f"Erreur création catégorie {name}: {e}")
        return category

    async def get_or_create_text_channel(self, guild, name, category, topic, overwrites):
        """Récupère ou crée un salon textuel"""
        channel = discord.utils.get(guild.channels, name=name)
        if not channel:
            try:
                channel = await guild.create_text_channel(
                    name,
                    category=category,
                    topic=topic,
                    overwrites=overwrites,
                    reason="Création automatique du mega-serveur"
                )
            except Exception as e:
                logger.error(f"Erreur création salon {name}: {e}")
        return channel

    async def get_or_create_voice_channel(self, guild, name, category, overwrites):
        """Récupère ou crée un salon vocal"""
        channel = discord.utils.get(guild.voice_channels, name=name)
        if not channel:
            try:
                channel = await guild.create_voice_channel(
                    name,
                    category=category,
                    overwrites=overwrites,
                    reason="Création automatique du mega-serveur"
                )
            except Exception as e:
                logger.error(f"Erreur création vocal {name}: {e}")
        return channel

    async def setup_final_configuration(self, ctx, guild, message):
        """Configuration finale du serveur"""
        embed = discord.Embed(
            title="⚙️ CONFIGURATION FINALE",
            description="Configuration des systèmes automatiques...",
            color=0x2ecc71
        )
        await message.edit(embed=embed)

        # Configuration des systèmes automatiques
        rules_channel = discord.utils.get(guild.channels, name="📋-règles")
        choice_channel = discord.utils.get(guild.channels, name="🌟-choix-communauté")
        welcome_channel = discord.utils.get(guild.channels, name="👋-bienvenue")
        logs_channel = discord.utils.get(guild.channels, name="📊-logs")
        suggestions_channel = discord.utils.get(guild.channels, name="💡-suggestions")
        giveaways_channel = discord.utils.get(guild.channels, name="🎁-giveaways")

        # Configuration du bot
        if rules_channel:
            await self.setup_rules(ctx, rules_channel)

        if choice_channel:
            await self.setup_community_choice(ctx, choice_channel)

        # Configuration des autres systèmes
        if welcome_channel:
            self.bot.config['channels']['welcome'] = welcome_channel.id

        # Sauvegarder la config
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(self.bot.config, f, indent=2, ensure_ascii=False)

        # Message de succès final
        final_embed = discord.Embed(
            title="🎉 MEGA-SERVEUR CRÉÉ AVEC SUCCÈS !",
            description="**Votre serveur communautaire ultra-complet est maintenant prêt !** 🚀",
            color=0x00ff00
        )

        final_embed.add_field(
            name="📊 Statistiques de création",
            value=f"• **{len(guild.categories)}** catégories créées\n• **{len(guild.text_channels)}** salons texte\n• **{len(guild.voice_channels)}** salons vocaux\n• **{len(guild.roles)}** rôles configurés",
            inline=False
        )

        final_embed.add_field(
            name="🎯 Catégories principales",
            value="📋 **Accueil & Règles** - Onboarding complet\nℹ️ **Informations** - Stats et infos\n💬 **Discussion** - Conversations générales\n🎮 **Gaming** - Tout pour les gamers\n🎨 **Créativité** - Art et projets\n😎 **Détente** - Fun et memes\n🔊 **Vocal** - Salons vocaux\n🎉 **Événements** - Giveaways et concours\n🛡️ **Modération** - Outils staff",
            inline=False
        )

        final_embed.add_field(
            name="🚀 Fonctionnalités activées",
            value="✅ **Système d'onboarding** automatique\n✅ **Rôles colorés** par communauté\n✅ **Permissions** optimisées\n✅ **Anti-raid** et sécurité\n✅ **Économie** et jeux\n✅ **Musique** et divertissement\n✅ **Logs** et modération\n✅ **Giveaways** et événements",
            inline=False
        )

        final_embed.add_field(
            name="🎮 Pour les gamers",
            value=f"• **9 salons gaming** spécialisés\n• **8 salons vocaux** pour jouer\n• Rôles par jeux favoris\n• Système de team building",
            inline=True
        )

        final_embed.add_field(
            name="💬 Pour discuter",
            value=f"• **6 salons discussion** thématiques\n• **6 salons vocaux** généraux\n• Débats et questions\n• Communauté active",
            inline=True
        )

        final_embed.add_field(
            name="🎨 Pour créer",
            value=f"• **7 salons créatifs** spécialisés\n• Galerie d'art et projets\n• Collaboration communautaire\n• Partage de créations",
            inline=True
        )

        final_embed.add_field(
            name="🔧 Commandes utiles",
            value="`!onboarding_stats` - Statistiques\n`!verify_member @user` - Vérifier\n`!reset_choice` - Changer de rôle\n`!antiraid setup` - Sécurité\n`!economy setup` - Économie\n`!music setup` - Musique",
            inline=False
        )

        final_embed.set_footer(text="🎉 Votre serveur est maintenant le plus complet de Discord ! Amusez-vous bien !")
        final_embed.set_thumbnail(url=guild.icon.url if guild.icon else None)

        await message.edit(embed=final_embed)
        logger.info(f"Mega-serveur créé avec succès par {ctx.author.name}")

    @commands.command(name='setup_onboarding_complete')
    @commands.has_permissions(administrator=True)
    async def setup_complete_onboarding(self, ctx):
        """Configuration complète automatique de l'onboarding (version simple)"""
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
            value="`!onboarding_stats` - Voir les statistiques\n`!verify_member @user` - Vérifier manuellement\n`!reset_choice` - Changer son choix\n`!create_mega_server` - Créer un serveur complet !",
            inline=False
        )

        final_embed.set_footer(text="Utilisez !create_mega_server pour un serveur ultra-complet !")

        await message.edit(embed=final_embed)
        logger.info(f"Onboarding complet configuré par {ctx.author.name}")

    @commands.command(name='create_specialized_channels')
    @commands.has_permissions(administrator=True)
    async def create_specialized_channels(self, ctx):
        """Crée des salons spécialisés selon les rôles de communauté"""
        guild = ctx.guild

        embed = discord.Embed(
            title="🎯 CRÉATION DE SALONS SPÉCIALISÉS",
            description="Création de salons privés pour chaque communauté...",
            color=0x9b59b6
        )
        message = await ctx.send(embed=embed)

        # Récupérer les rôles de communauté
        community_roles = [
            {"role": "💬 Discuteur", "channels": ["💬-salon-discuteurs", "🗣️-débats-privés"], "voice": "💬 Vocal Discuteurs"},
            {"role": "😂 Rigoleur", "channels": ["😂-salon-rigoleurs", "🎭-blagues-privées"], "voice": "😂 Vocal Rigoleurs"},
            {"role": "🎮 Gamer", "channels": ["🎮-salon-gamers", "🏆-tournois-privés"], "voice": "🎮 Vocal Gamers"},
            {"role": "🤝 Social", "channels": ["🤝-salon-sociaux", "💕-rencontres"], "voice": "🤝 Vocal Sociaux"},
            {"role": "📚 Intellectuel", "channels": ["📚-salon-intellectuels", "🧠-réflexions"], "voice": "📚 Vocal Intellectuels"},
        ]

        created_channels = []

        for role_data in community_roles:
            role = discord.utils.get(guild.roles, name=role_data["role"])
            if not role:
                continue

            # Créer la catégorie pour ce rôle
            category_name = f"🔒 {role_data['role'].upper()}"
            category = discord.utils.get(guild.categories, name=category_name)
            if not category:
                category = await guild.create_category(
                    category_name,
                    reason="Catégorie spécialisée pour communauté"
                )

            # Permissions pour cette communauté seulement
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }

            # Créer les salons texte
            for channel_name in role_data["channels"]:
                existing_channel = discord.utils.get(guild.channels, name=channel_name)
                if not existing_channel:
                    try:
                        channel = await guild.create_text_channel(
                            channel_name,
                            category=category,
                            overwrites=overwrites,
                            topic=f"Salon privé pour les {role_data['role']} !",
                            reason="Salon spécialisé automatique"
                        )
                        created_channels.append(channel.mention)
                    except Exception as e:
                        logger.error(f"Erreur création salon {channel_name}: {e}")

            # Créer le salon vocal
            voice_name = role_data["voice"]
            existing_voice = discord.utils.get(guild.voice_channels, name=voice_name)
            if not existing_voice:
                try:
                    voice_channel = await guild.create_voice_channel(
                        voice_name,
                        category=category,
                        overwrites=overwrites,
                        reason="Vocal spécialisé automatique"
                    )
                    created_channels.append(f"🔊 {voice_channel.name}")
                except Exception as e:
                    logger.error(f"Erreur création vocal {voice_name}: {e}")

        # Message de confirmation
        final_embed = discord.Embed(
            title="✅ SALONS SPÉCIALISÉS CRÉÉS !",
            description="Des salons privés ont été créés pour chaque communauté ! 🎉",
            color=0x2ecc71
        )

        if created_channels:
            # Diviser en chunks pour éviter les limites de Discord
            chunks = [created_channels[i:i+10] for i in range(0, len(created_channels), 10)]
            for i, chunk in enumerate(chunks):
                field_name = f"🎯 Salons créés {i+1}" if len(chunks) > 1 else "🎯 Salons créés"
                final_embed.add_field(
                    name=field_name,
                    value="\n".join(chunk),
                    inline=False
                )

        final_embed.add_field(
            name="🔒 Accès privé",
            value="Seuls les membres avec le bon rôle peuvent voir ces salons !",
            inline=False
        )

        final_embed.add_field(
            name="💡 Comment ça marche",
            value="1. Les membres choisissent leur communauté\n2. Ils reçoivent le rôle correspondant\n3. Ils accèdent automatiquement aux salons privés\n4. Ils peuvent discuter avec des personnes similaires !",
            inline=False
        )

        await message.edit(embed=final_embed)
        logger.info(f"Salons spécialisés créés par {ctx.author.name}")

    @commands.command(name='server_template_info')
    async def server_template_info(self, ctx):
        """Affiche les informations sur les templates de serveur disponibles"""
        embed = discord.Embed(
            title="🏗️ TEMPLATES DE SERVEUR DISPONIBLES",
            description="Choisissez le template parfait pour votre communauté !",
            color=0x3498db
        )

        embed.add_field(
            name="🚀 `!create_mega_server`",
            value="**SERVEUR ULTRA-COMPLET**\n• 10+ catégories thématiques\n• 50+ salons texte et vocal\n• 25+ rôles colorés\n• Système d'onboarding complet\n• Parfait pour grandes communautés",
            inline=False
        )

        embed.add_field(
            name="🎯 `!create_specialized_channels`",
            value="**SALONS SPÉCIALISÉS**\n• Salons privés par communauté\n• Accès basé sur les rôles\n• Parfait pour segmenter les discussions\n• Complément du mega-serveur",
            inline=False
        )

        embed.add_field(
            name="📋 `!setup_onboarding_complete`",
            value="**ONBOARDING SIMPLE**\n• Système de règles interactif\n• Choix de communauté\n• Messages de bienvenue\n• Parfait pour commencer",
            inline=False
        )

        embed.add_field(
            name="🎮 Templates spécialisés",
            value="**Gaming**: Optimisé pour les gamers\n**Créatif**: Pour les artistes et créateurs\n**Éducatif**: Pour l'apprentissage\n**Social**: Pour faire des rencontres",
            inline=False
        )

        embed.add_field(
            name="💡 Recommandations",
            value="• **Nouveau serveur**: `!create_mega_server`\n• **Serveur existant**: `!setup_onboarding_complete`\n• **Communautés actives**: `!create_specialized_channels`",
            inline=False
        )

        embed.set_footer(text="Utilisez les commandes pour créer votre serveur parfait !")

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Onboarding(bot))
