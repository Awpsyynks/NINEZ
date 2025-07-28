import discord
from discord.ext import commands, tasks
import json
import random
import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger('discord_bot.economy')

class Economy(commands.Cog):
    """Système d'économie complet avec monnaie virtuelle"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config = self.load_config()
        self.user_data = self.load_user_data()
        self.shop_items = self.load_shop_items()
        self.daily_reset.start()
        
    def load_config(self):
        """Charge la configuration de l'économie"""
        try:
            with open('economy_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            default_config = {
                "currency": {
                    "name": "coins",
                    "symbol": "🪙",
                    "starting_amount": 100
                },
                "daily": {
                    "enabled": True,
                    "min_amount": 50,
                    "max_amount": 200,
                    "streak_bonus": 10
                },
                "work": {
                    "enabled": True,
                    "cooldown": 3600,  # 1 heure
                    "min_amount": 20,
                    "max_amount": 100,
                    "jobs": [
                        {"name": "Développeur", "min": 80, "max": 150},
                        {"name": "Designer", "min": 60, "max": 120},
                        {"name": "Streamer", "min": 40, "max": 200},
                        {"name": "Gamer Pro", "min": 30, "max": 180},
                        {"name": "Modérateur", "min": 50, "max": 100}
                    ]
                },
                "gambling": {
                    "enabled": True,
                    "slots": {
                        "min_bet": 10,
                        "max_bet": 500,
                        "jackpot_chance": 0.01
                    },
                    "coinflip": {
                        "min_bet": 5,
                        "max_bet": 1000
                    }
                },
                "shop": {
                    "enabled": True,
                    "tax_rate": 0.05
                },
                "trading": {
                    "enabled": True,
                    "tax_rate": 0.02
                }
            }
            self.save_config(default_config)
            return default_config
    
    def load_user_data(self):
        """Charge les données des utilisateurs"""
        try:
            with open('economy_users.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def load_shop_items(self):
        """Charge les objets de la boutique"""
        try:
            with open('shop_items.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            default_items = {
                "roles": [
                    {"id": "vip", "name": "VIP", "price": 5000, "description": "Rôle VIP exclusif", "role_id": None},
                    {"id": "premium", "name": "Premium", "price": 10000, "description": "Rôle Premium avec avantages", "role_id": None}
                ],
                "items": [
                    {"id": "boost", "name": "Boost XP", "price": 500, "description": "Double l'XP pendant 1 heure", "duration": 3600},
                    {"id": "protection", "name": "Protection", "price": 1000, "description": "Protection contre les vols pendant 24h", "duration": 86400},
                    {"id": "multiplier", "name": "Multiplicateur", "price": 2000, "description": "Multiplie les gains par 2 pendant 30 min", "duration": 1800}
                ],
                "cosmetics": [
                    {"id": "badge1", "name": "Badge Doré", "price": 3000, "description": "Badge doré pour votre profil", "emoji": "🏆"},
                    {"id": "badge2", "name": "Badge Diamant", "price": 8000, "description": "Badge diamant ultra rare", "emoji": "💎"}
                ]
            }
            self.save_shop_items(default_items)
            return default_items
    
    def save_config(self, config=None):
        """Sauvegarde la configuration"""
        if config is None:
            config = self.config
        try:
            with open('economy_config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erreur sauvegarde config économie: {e}")
    
    def save_user_data(self):
        """Sauvegarde les données utilisateurs"""
        try:
            with open('economy_users.json', 'w', encoding='utf-8') as f:
                json.dump(self.user_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erreur sauvegarde données utilisateurs: {e}")
    
    def save_shop_items(self, items=None):
        """Sauvegarde les objets de la boutique"""
        if items is None:
            items = self.shop_items
        try:
            with open('shop_items.json', 'w', encoding='utf-8') as f:
                json.dump(items, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erreur sauvegarde boutique: {e}")
    
    def get_user_data(self, user_id):
        """Récupère les données d'un utilisateur"""
        user_id = str(user_id)
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                "balance": self.config['currency']['starting_amount'],
                "bank": 0,
                "daily_streak": 0,
                "last_daily": None,
                "last_work": None,
                "inventory": {},
                "active_effects": {},
                "stats": {
                    "total_earned": 0,
                    "total_spent": 0,
                    "work_count": 0,
                    "gamble_wins": 0,
                    "gamble_losses": 0
                }
            }
        return self.user_data[user_id]
    
    def add_money(self, user_id, amount, reason=""):
        """Ajoute de l'argent à un utilisateur"""
        user_data = self.get_user_data(user_id)
        user_data['balance'] += amount
        user_data['stats']['total_earned'] += amount
        self.save_user_data()
        logger.info(f"Ajouté {amount} coins à {user_id} - {reason}")
    
    def remove_money(self, user_id, amount, reason=""):
        """Retire de l'argent à un utilisateur"""
        user_data = self.get_user_data(user_id)
        if user_data['balance'] >= amount:
            user_data['balance'] -= amount
            user_data['stats']['total_spent'] += amount
            self.save_user_data()
            logger.info(f"Retiré {amount} coins à {user_id} - {reason}")
            return True
        return False
    
    @tasks.loop(hours=24)
    async def daily_reset(self):
        """Reset quotidien des cooldowns"""
        logger.info("Reset quotidien de l'économie")
    
    # Commandes d'économie
    @commands.command(name='balance', aliases=['bal', 'money'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def balance(self, ctx, member: discord.Member = None):
        """Affiche le solde d'un utilisateur"""
        if member is None:
            member = ctx.author
        
        user_data = self.get_user_data(member.id)
        currency = self.config['currency']
        
        embed = discord.Embed(
            title=f"💰 Portefeuille de {member.display_name}",
            color=0xf1c40f,
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name=f"{currency['symbol']} Argent liquide",
            value=f"{user_data['balance']:,} {currency['name']}",
            inline=True
        )
        embed.add_field(
            name="🏦 Banque",
            value=f"{user_data['bank']:,} {currency['name']}",
            inline=True
        )
        embed.add_field(
            name="💎 Total",
            value=f"{user_data['balance'] + user_data['bank']:,} {currency['name']}",
            inline=True
        )
        
        # Statistiques
        stats = user_data['stats']
        embed.add_field(
            name="📊 Statistiques",
            value=f"Gagné: {stats['total_earned']:,}\n"
                  f"Dépensé: {stats['total_spent']:,}\n"
                  f"Travaux: {stats['work_count']}",
            inline=False
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)
    
    @commands.command(name='daily')
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def daily(self, ctx):
        """Récupère la récompense quotidienne"""
        if not self.config['daily']['enabled']:
            embed = discord.Embed(
                title="❌ Récompense quotidienne désactivée",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        user_data = self.get_user_data(ctx.author.id)
        now = datetime.now()
        
        # Vérifier si l'utilisateur a déjà récupéré sa récompense aujourd'hui
        if user_data['last_daily']:
            last_daily = datetime.fromisoformat(user_data['last_daily'])
            if (now - last_daily).days < 1:
                next_daily = last_daily + timedelta(days=1)
                time_left = next_daily - now
                hours, remainder = divmod(time_left.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                
                embed = discord.Embed(
                    title="⏰ Récompense déjà récupérée",
                    description=f"Revenez dans {hours}h {minutes}m",
                    color=0xf39c12
                )
                await ctx.send(embed=embed)
                return
        
        # Calculer la récompense
        config = self.config['daily']
        base_amount = random.randint(config['min_amount'], config['max_amount'])
        
        # Bonus de série
        if user_data['last_daily']:
            last_daily = datetime.fromisoformat(user_data['last_daily'])
            if (now - last_daily).days == 1:
                user_data['daily_streak'] += 1
            else:
                user_data['daily_streak'] = 1
        else:
            user_data['daily_streak'] = 1
        
        streak_bonus = user_data['daily_streak'] * config['streak_bonus']
        total_amount = base_amount + streak_bonus
        
        # Donner la récompense
        self.add_money(ctx.author.id, total_amount, "Récompense quotidienne")
        user_data['last_daily'] = now.isoformat()
        
        embed = discord.Embed(
            title="🎁 Récompense quotidienne récupérée !",
            color=0x2ecc71,
            timestamp=now
        )
        
        currency = self.config['currency']
        embed.add_field(
            name="💰 Récompense",
            value=f"{total_amount:,} {currency['name']} {currency['symbol']}",
            inline=True
        )
        embed.add_field(
            name="🔥 Série",
            value=f"{user_data['daily_streak']} jour(s)",
            inline=True
        )
        
        if streak_bonus > 0:
            embed.add_field(
                name="🎯 Bonus série",
                value=f"+{streak_bonus:,} {currency['name']}",
                inline=True
            )
        
        embed.set_footer(text="Revenez demain pour continuer votre série !")
        await ctx.send(embed=embed)
    
    @commands.command(name='work')
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def work(self, ctx):
        """Travaille pour gagner de l'argent"""
        if not self.config['work']['enabled']:
            embed = discord.Embed(
                title="❌ Travail désactivé",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        user_data = self.get_user_data(ctx.author.id)
        now = datetime.now()
        
        # Vérifier le cooldown
        if user_data['last_work']:
            last_work = datetime.fromisoformat(user_data['last_work'])
            cooldown = self.config['work']['cooldown']
            if (now - last_work).seconds < cooldown:
                time_left = cooldown - (now - last_work).seconds
                hours, remainder = divmod(time_left, 3600)
                minutes, _ = divmod(remainder, 60)
                
                embed = discord.Embed(
                    title="⏰ Vous êtes fatigué",
                    description=f"Reposez-vous encore {hours}h {minutes}m",
                    color=0xf39c12
                )
                await ctx.send(embed=embed)
                return
        
        # Choisir un travail aléatoire
        jobs = self.config['work']['jobs']
        job = random.choice(jobs)
        amount = random.randint(job['min'], job['max'])
        
        # Appliquer les multiplicateurs actifs
        if 'multiplier' in user_data['active_effects']:
            effect = user_data['active_effects']['multiplier']
            if datetime.now() < datetime.fromisoformat(effect['expires']):
                amount *= 2
                multiplier_active = True
            else:
                del user_data['active_effects']['multiplier']
                multiplier_active = False
        else:
            multiplier_active = False
        
        # Donner la récompense
        self.add_money(ctx.author.id, amount, f"Travail: {job['name']}")
        user_data['last_work'] = now.isoformat()
        user_data['stats']['work_count'] += 1
        
        embed = discord.Embed(
            title="💼 Travail terminé !",
            color=0x2ecc71,
            timestamp=now
        )
        
        currency = self.config['currency']
        embed.add_field(
            name="👔 Métier",
            value=job['name'],
            inline=True
        )
        embed.add_field(
            name="💰 Salaire",
            value=f"{amount:,} {currency['name']} {currency['symbol']}",
            inline=True
        )
        
        if multiplier_active:
            embed.add_field(
                name="⚡ Multiplicateur",
                value="x2 actif !",
                inline=True
            )
        
        # Messages aléatoires
        work_messages = [
            f"Vous avez excellé en tant que {job['name']} !",
            f"Une journée productive en tant que {job['name']} !",
            f"Votre travail de {job['name']} a été remarqué !",
            f"Vous avez terminé vos tâches de {job['name']} avec brio !"
        ]
        embed.description = random.choice(work_messages)
        
        await ctx.send(embed=embed)

    @commands.command(name='slots')
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def slots(self, ctx, bet: int):
        """Machine à sous"""
        if not self.config['gambling']['enabled']:
            embed = discord.Embed(
                title="❌ Jeux d'argent désactivés",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        slots_config = self.config['gambling']['slots']
        currency = self.config['currency']

        # Vérifier les limites de mise
        if bet < slots_config['min_bet'] or bet > slots_config['max_bet']:
            embed = discord.Embed(
                title="❌ Mise invalide",
                description=f"Mise entre {slots_config['min_bet']} et {slots_config['max_bet']} {currency['name']}",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        # Vérifier le solde
        user_data = self.get_user_data(ctx.author.id)
        if user_data['balance'] < bet:
            embed = discord.Embed(
                title="❌ Solde insuffisant",
                description=f"Vous avez besoin de {bet:,} {currency['name']}",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        # Retirer la mise
        self.remove_money(ctx.author.id, bet, "Mise aux machines à sous")

        # Symboles des machines à sous
        symbols = ['🍒', '🍋', '🍊', '🍇', '⭐', '💎', '7️⃣']
        weights = [30, 25, 20, 15, 7, 2, 1]  # Probabilités

        # Tirer les symboles
        result = random.choices(symbols, weights=weights, k=3)

        # Calculer les gains
        winnings = 0
        multiplier = 0

        if result[0] == result[1] == result[2]:  # Trois identiques
            if result[0] == '💎':
                multiplier = 50
            elif result[0] == '7️⃣':
                multiplier = 25
            elif result[0] == '⭐':
                multiplier = 10
            elif result[0] == '🍇':
                multiplier = 5
            else:
                multiplier = 3
        elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:  # Deux identiques
            multiplier = 1.5

        # Jackpot chance
        if random.random() < slots_config['jackpot_chance']:
            multiplier = 100
            jackpot = True
        else:
            jackpot = False

        winnings = int(bet * multiplier)

        # Donner les gains
        if winnings > 0:
            self.add_money(ctx.author.id, winnings, "Gains machines à sous")
            user_data['stats']['gamble_wins'] += 1
        else:
            user_data['stats']['gamble_losses'] += 1

        # Créer l'embed
        embed = discord.Embed(
            title="🎰 Machine à Sous",
            color=0xf1c40f if winnings > 0 else 0xe74c3c,
            timestamp=datetime.now()
        )

        embed.add_field(
            name="🎲 Résultat",
            value=" | ".join(result),
            inline=False
        )

        embed.add_field(
            name="💰 Mise",
            value=f"{bet:,} {currency['name']}",
            inline=True
        )

        if winnings > 0:
            embed.add_field(
                name="🎉 Gains",
                value=f"{winnings:,} {currency['name']} (x{multiplier})",
                inline=True
            )
            if jackpot:
                embed.add_field(
                    name="💎 JACKPOT !",
                    value="Félicitations !",
                    inline=True
                )
        else:
            embed.add_field(
                name="😢 Perdu",
                value="Réessayez !",
                inline=True
            )

        embed.add_field(
            name="💳 Nouveau solde",
            value=f"{user_data['balance']:,} {currency['name']}",
            inline=False
        )

        await ctx.send(embed=embed)

    @commands.command(name='coinflip', aliases=['cf'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def coinflip(self, ctx, bet: int, choice: str):
        """Pile ou face"""
        if not self.config['gambling']['enabled']:
            embed = discord.Embed(
                title="❌ Jeux d'argent désactivés",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        cf_config = self.config['gambling']['coinflip']
        currency = self.config['currency']

        # Vérifier le choix
        choice = choice.lower()
        if choice not in ['pile', 'face', 'heads', 'tails']:
            embed = discord.Embed(
                title="❌ Choix invalide",
                description="Choisissez `pile` ou `face`",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        # Normaliser le choix
        if choice in ['heads', 'pile']:
            choice = 'pile'
        else:
            choice = 'face'

        # Vérifier les limites
        if bet < cf_config['min_bet'] or bet > cf_config['max_bet']:
            embed = discord.Embed(
                title="❌ Mise invalide",
                description=f"Mise entre {cf_config['min_bet']} et {cf_config['max_bet']} {currency['name']}",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        # Vérifier le solde
        user_data = self.get_user_data(ctx.author.id)
        if user_data['balance'] < bet:
            embed = discord.Embed(
                title="❌ Solde insuffisant",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        # Retirer la mise
        self.remove_money(ctx.author.id, bet, "Mise pile ou face")

        # Lancer la pièce
        result = random.choice(['pile', 'face'])
        won = choice == result

        # Calculer les gains
        if won:
            winnings = bet * 2
            self.add_money(ctx.author.id, winnings, "Gains pile ou face")
            user_data['stats']['gamble_wins'] += 1
        else:
            winnings = 0
            user_data['stats']['gamble_losses'] += 1

        # Créer l'embed
        embed = discord.Embed(
            title="🪙 Pile ou Face",
            color=0x2ecc71 if won else 0xe74c3c,
            timestamp=datetime.now()
        )

        result_emoji = "🟡" if result == 'pile' else "⚪"
        embed.add_field(
            name="🎲 Résultat",
            value=f"{result_emoji} {result.title()}",
            inline=True
        )

        embed.add_field(
            name="🎯 Votre choix",
            value=choice.title(),
            inline=True
        )

        if won:
            embed.add_field(
                name="🎉 Vous avez gagné !",
                value=f"+{winnings:,} {currency['name']}",
                inline=True
            )
        else:
            embed.add_field(
                name="😢 Vous avez perdu",
                value=f"-{bet:,} {currency['name']}",
                inline=True
            )

        embed.add_field(
            name="💳 Nouveau solde",
            value=f"{user_data['balance']:,} {currency['name']}",
            inline=False
        )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Economy(bot))
