import discord
from discord.ext import commands
import json
import logging
import math
import random
from datetime import datetime, timedelta

logger = logging.getLogger('discord_bot.levels')

class Levels(commands.Cog):
    """Cog pour gérer le système de niveaux et d'XP"""
    
    def __init__(self, bot):
        self.bot = bot
        self.xp_data = {}
        self.last_message = {}  # Pour éviter le spam XP
        self.load_xp_data()
    
    def load_xp_data(self):
        """Charge les données XP depuis le fichier"""
        try:
            with open('xp_data.json', 'r', encoding='utf-8') as f:
                self.xp_data = json.load(f)
        except FileNotFoundError:
            self.xp_data = {}
            logger.info("Fichier XP créé")
    
    def save_xp_data(self):
        """Sauvegarde les données XP"""
        try:
            with open('xp_data.json', 'w', encoding='utf-8') as f:
                json.dump(self.xp_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde XP: {e}")
    
    def get_level_from_xp(self, xp):
        """Calcule le niveau basé sur l'XP"""
        return int(math.sqrt(xp / 100))
    
    def get_xp_for_level(self, level):
        """Calcule l'XP nécessaire pour un niveau"""
        return level * level * 100
    
    def get_user_data(self, user_id):
        """Récupère les données d'un utilisateur"""
        user_id = str(user_id)
        if user_id not in self.xp_data:
            self.xp_data[user_id] = {
                'xp': 0,
                'level': 0,
                'messages': 0
            }
        return self.xp_data[user_id]
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Donne de l'XP pour chaque message"""
        if message.author.bot:
            return
        
        if message.guild is None:
            return
        
        user_id = str(message.author.id)
        now = datetime.now()
        
        # Vérification anti-spam (1 minute entre les gains XP)
        if user_id in self.last_message:
            if now - self.last_message[user_id] < timedelta(minutes=1):
                return
        
        self.last_message[user_id] = now
        
        # Récupération des données utilisateur
        user_data = self.get_user_data(message.author.id)
        old_level = user_data['level']
        
        # Gain d'XP aléatoire (15-25 XP par message)
        xp_gain = random.randint(15, 25)
        user_data['xp'] += xp_gain
        user_data['messages'] += 1
        
        # Calcul du nouveau niveau
        new_level = self.get_level_from_xp(user_data['xp'])
        user_data['level'] = new_level
        
        # Vérification de level up
        if new_level > old_level:
            embed = discord.Embed(
                title="🎉 Level Up !",
                description=f"Félicitations {message.author.mention} !\nTu es maintenant **niveau {new_level}** !",
                color=0xf1c40f
            )
            embed.set_thumbnail(url=message.author.display_avatar.url)
            embed.add_field(name="💎 XP Total", value=f"{user_data['xp']:,}", inline=True)
            embed.add_field(name="📨 Messages", value=f"{user_data['messages']:,}", inline=True)
            
            # Vérification des récompenses
            reward = self.get_level_reward(new_level)
            if reward:
                embed.add_field(name="🎁 Récompense", value=reward, inline=False)
            
            await message.channel.send(embed=embed)
            logger.info(f"{message.author.name} a atteint le niveau {new_level}")
        
        # Sauvegarde périodique
        if random.randint(1, 10) == 1:  # 10% de chance
            self.save_xp_data()
    
    def get_level_reward(self, level):
        """Retourne la récompense pour un niveau donné"""
        rewards = {
            5: "🏆 Rôle **Membre Actif**",
            10: "⭐ Rôle **Membre Dévoué**",
            15: "💎 Rôle **Membre VIP**",
            20: "👑 Rôle **Membre Légendaire**",
            25: "🌟 Rôle **Membre Mythique**",
            30: "🔥 Rôle **Membre Divin**"
        }
        return rewards.get(level)
    
    @commands.command(name='rank')
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def show_rank(self, ctx, member: discord.Member = None):
        """Affiche le rang d'un utilisateur"""
        if not member:
            member = ctx.author
        
        user_data = self.get_user_data(member.id)
        current_level = user_data['level']
        current_xp = user_data['xp']
        
        # XP pour le niveau suivant
        next_level_xp = self.get_xp_for_level(current_level + 1)
        current_level_xp = self.get_xp_for_level(current_level)
        progress_xp = current_xp - current_level_xp
        needed_xp = next_level_xp - current_level_xp
        
        # Calcul du rang
        sorted_users = sorted(self.xp_data.items(), key=lambda x: x[1]['xp'], reverse=True)
        rank = next((i + 1 for i, (uid, _) in enumerate(sorted_users) if uid == str(member.id)), "N/A")
        
        embed = discord.Embed(
            title=f"📊 Rang de {member.display_name}",
            color=int(self.bot.config['embed_color'], 16)
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        
        embed.add_field(name="🏆 Rang", value=f"#{rank}", inline=True)
        embed.add_field(name="⭐ Niveau", value=f"{current_level}", inline=True)
        embed.add_field(name="💎 XP Total", value=f"{current_xp:,}", inline=True)
        
        embed.add_field(name="📈 Progression", value=f"{progress_xp:,}/{needed_xp:,} XP", inline=True)
        embed.add_field(name="📨 Messages", value=f"{user_data['messages']:,}", inline=True)
        embed.add_field(name="🎯 Prochain niveau", value=f"Niveau {current_level + 1}", inline=True)
        
        # Barre de progression
        progress_percent = (progress_xp / needed_xp) * 100 if needed_xp > 0 else 100
        progress_bar = "█" * int(progress_percent / 10) + "░" * (10 - int(progress_percent / 10))
        embed.add_field(name="📊 Barre de progression", value=f"`{progress_bar}` {progress_percent:.1f}%", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='leaderboard', aliases=['lb', 'top'])
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def show_leaderboard(self, ctx, page: int = 1):
        """Affiche le classement des niveaux"""
        if page < 1:
            page = 1
        
        # Tri des utilisateurs par XP
        sorted_users = sorted(self.xp_data.items(), key=lambda x: x[1]['xp'], reverse=True)
        
        # Pagination
        per_page = 10
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_users = sorted_users[start_idx:end_idx]
        
        if not page_users:
            embed = discord.Embed(
                title="❌ Page vide",
                description="Cette page du classement est vide.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="🏆 Classement des Niveaux",
            description=f"Page {page} • Top {start_idx + 1}-{start_idx + len(page_users)}",
            color=0xf1c40f
        )
        
        leaderboard_text = ""
        for i, (user_id, data) in enumerate(page_users, start=start_idx + 1):
            try:
                user = self.bot.get_user(int(user_id))
                if user:
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
                    leaderboard_text += f"{medal} **#{i}** {user.display_name}\n"
                    leaderboard_text += f"   ⭐ Niveau {data['level']} • 💎 {data['xp']:,} XP\n\n"
            except:
                continue
        
        if leaderboard_text:
            embed.description += f"\n\n{leaderboard_text}"
        
        total_pages = math.ceil(len(sorted_users) / per_page)
        embed.set_footer(text=f"Page {page}/{total_pages} • {len(sorted_users)} membres classés")
        
        await ctx.send(embed=embed)

    @commands.command(name='setxp')
    @commands.has_permissions(administrator=True)
    async def set_xp(self, ctx, member: discord.Member, amount: int):
        """Définit l'XP d'un utilisateur (admin seulement)"""
        if amount < 0:
            embed = discord.Embed(
                title="❌ Erreur",
                description="L'XP ne peut pas être négative.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        user_data = self.get_user_data(member.id)
        old_xp = user_data['xp']
        old_level = user_data['level']

        user_data['xp'] = amount
        user_data['level'] = self.get_level_from_xp(amount)

        self.save_xp_data()

        embed = discord.Embed(
            title="✅ XP modifiée",
            description=f"XP de {member.mention} mise à jour",
            color=0x2ecc71
        )
        embed.add_field(name="Ancien", value=f"Niveau {old_level} • {old_xp:,} XP", inline=True)
        embed.add_field(name="Nouveau", value=f"Niveau {user_data['level']} • {amount:,} XP", inline=True)

        await ctx.send(embed=embed)
        logger.info(f"XP de {member.name} modifiée par {ctx.author.name}: {old_xp} -> {amount}")

    @commands.command(name='addxp')
    @commands.has_permissions(administrator=True)
    async def add_xp(self, ctx, member: discord.Member, amount: int):
        """Ajoute de l'XP à un utilisateur (admin seulement)"""
        user_data = self.get_user_data(member.id)
        old_xp = user_data['xp']
        old_level = user_data['level']

        user_data['xp'] += amount
        if user_data['xp'] < 0:
            user_data['xp'] = 0

        user_data['level'] = self.get_level_from_xp(user_data['xp'])

        self.save_xp_data()

        embed = discord.Embed(
            title="✅ XP ajoutée",
            description=f"{amount:+,} XP pour {member.mention}",
            color=0x2ecc71 if amount > 0 else 0xe74c3c
        )
        embed.add_field(name="Ancien", value=f"Niveau {old_level} • {old_xp:,} XP", inline=True)
        embed.add_field(name="Nouveau", value=f"Niveau {user_data['level']} • {user_data['xp']:,} XP", inline=True)

        await ctx.send(embed=embed)
        logger.info(f"XP de {member.name} modifiée par {ctx.author.name}: {old_xp} -> {user_data['xp']}")

    @commands.command(name='rewards')
    async def show_rewards(self, ctx):
        """Affiche les récompenses par niveau"""
        embed = discord.Embed(
            title="🎁 Récompenses par Niveau",
            description="Voici les récompenses que vous pouvez obtenir en montant de niveau :",
            color=0xf1c40f
        )

        rewards_text = ""
        rewards = {
            5: "🏆 Rôle **Membre Actif**",
            10: "⭐ Rôle **Membre Dévoué**",
            15: "💎 Rôle **Membre VIP**",
            20: "👑 Rôle **Membre Légendaire**",
            25: "🌟 Rôle **Membre Mythique**",
            30: "🔥 Rôle **Membre Divin**"
        }

        for level, reward in rewards.items():
            rewards_text += f"**Niveau {level}** : {reward}\n"

        embed.description += f"\n\n{rewards_text}"
        embed.add_field(
            name="💡 Comment gagner de l'XP ?",
            value="• Envoyez des messages (15-25 XP par message)\n• Participez aux discussions\n• Restez actif sur le serveur",
            inline=False
        )
        embed.set_footer(text="Utilisez !rank pour voir votre progression")

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Levels(bot))
