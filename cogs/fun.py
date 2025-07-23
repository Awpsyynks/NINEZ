import discord
from discord.ext import commands
import random
import asyncio
import logging

logger = logging.getLogger('discord_bot.fun')

class Fun(commands.Cog):
    """Cog pour les commandes de divertissement et d'engagement"""
    
    def __init__(self, bot):
        self.bot = bot
        self.trivia_sessions = {}  # {channel_id: session_data}
    
    @commands.command(name='joke')
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def joke(self, ctx):
        """Raconte une blague aléatoire"""
        jokes = self.bot.config['fun']['jokes']
        joke = random.choice(jokes)
        
        embed = discord.Embed(
            title="😂 Blague du jour",
            description=joke,
            color=int(self.bot.config['embed_color'], 16)
        )
        embed.set_footer(text=f"Demandé par {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)
        logger.info(f"Blague envoyée par {ctx.author.name}")
    
    @commands.command(name='quote')
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def quote(self, ctx):
        """Affiche une citation inspirante"""
        quotes = self.bot.config['fun']['quotes']
        quote = random.choice(quotes)
        
        embed = discord.Embed(
            title="💭 Citation inspirante",
            description=f"*{quote}*",
            color=int(self.bot.config['embed_color'], 16)
        )
        embed.set_footer(text=f"Demandé par {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)
        logger.info(f"Citation envoyée par {ctx.author.name}")
    
    @commands.command(name='trivia')
    @commands.cooldown(1, 10, commands.BucketType.channel)
    async def trivia(self, ctx):
        """Lance une question de culture générale"""
        if ctx.channel.id in self.trivia_sessions:
            embed = discord.Embed(
                title="❌ Session en cours",
                description="Une session de trivia est déjà en cours dans ce canal !",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        trivia_questions = self.bot.config['fun']['trivia']
        question_data = random.choice(trivia_questions)
        
        embed = discord.Embed(
            title="🧠 Question de culture générale",
            description=f"**{question_data['question']}**\n\nVous avez 30 secondes pour répondre !",
            color=int(self.bot.config['embed_color'], 16)
        )
        embed.set_footer(text="Tapez votre réponse dans le chat !")
        
        await ctx.send(embed=embed)
        
        # Enregistre la session
        self.trivia_sessions[ctx.channel.id] = {
            'answer': question_data['answer'].lower(),
            'author': ctx.author,
            'start_time': asyncio.get_event_loop().time()
        }
        
        # Attend 30 secondes puis révèle la réponse si personne n'a trouvé
        await asyncio.sleep(30)
        
        if ctx.channel.id in self.trivia_sessions:
            embed = discord.Embed(
                title="⏰ Temps écoulé !",
                description=f"La bonne réponse était : **{question_data['answer']}**",
                color=0xf39c12
            )
            await ctx.send(embed=embed)
            del self.trivia_sessions[ctx.channel.id]
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Écoute les réponses aux questions de trivia"""
        if message.author.bot:
            return
        
        if message.channel.id not in self.trivia_sessions:
            return
        
        session = self.trivia_sessions[message.channel.id]
        user_answer = message.content.lower().strip()
        correct_answer = session['answer']
        
        # Vérifie si la réponse est correcte (avec une certaine tolérance)
        if user_answer == correct_answer or correct_answer in user_answer:
            elapsed_time = round(asyncio.get_event_loop().time() - session['start_time'], 1)
            
            embed = discord.Embed(
                title="🎉 Bonne réponse !",
                description=f"Félicitations {message.author.mention} !\nVous avez trouvé la bonne réponse en **{elapsed_time}s** !",
                color=0x2ecc71
            )
            embed.add_field(name="✅ Réponse", value=correct_answer.title(), inline=True)
            
            await message.channel.send(embed=embed)
            del self.trivia_sessions[message.channel.id]
            logger.info(f"Trivia résolue par {message.author.name} en {elapsed_time}s")
    
    @commands.command(name='8ball')
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def eight_ball(self, ctx, *, question=None):
        """Boule magique 8 - pose une question !"""
        if not question:
            embed = discord.Embed(
                title="❌ Question manquante",
                description="Vous devez poser une question !\nExemple : `!8ball Est-ce que je vais réussir mon examen ?`",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        responses = [
            "🟢 Oui, absolument !",
            "🟢 C'est certain !",
            "🟢 Sans aucun doute !",
            "🟢 Oui, définitivement !",
            "🟢 Tu peux compter dessus !",
            "🟡 Probablement oui",
            "🟡 Les signes pointent vers oui",
            "🟡 Réessaie plus tard",
            "🟡 Mieux vaut ne pas te le dire maintenant",
            "🟡 Concentre-toi et redemande",
            "🔴 N'y compte pas",
            "🔴 Ma réponse est non",
            "🔴 Mes sources disent non",
            "🔴 Les perspectives ne sont pas bonnes",
            "🔴 Très douteux"
        ]
        
        response = random.choice(responses)
        
        embed = discord.Embed(
            title="🎱 Boule magique 8",
            color=int(self.bot.config['embed_color'], 16)
        )
        embed.add_field(name="❓ Question", value=question, inline=False)
        embed.add_field(name="🔮 Réponse", value=response, inline=False)
        embed.set_footer(text=f"Demandé par {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)
        logger.info(f"8ball utilisé par {ctx.author.name}")
    
    @commands.command(name='poll')
    @commands.cooldown(1, 30, commands.BucketType.channel)
    async def poll(self, ctx, *, question):
        """Crée un sondage avec réactions"""
        if len(question) > 256:
            embed = discord.Embed(
                title="❌ Question trop longue",
                description="La question du sondage ne peut pas dépasser 256 caractères.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="📊 Sondage",
            description=f"**{question}**",
            color=int(self.bot.config['embed_color'], 16)
        )
        embed.add_field(name="Comment voter ?", value="✅ Pour voter OUI\n❌ Pour voter NON", inline=False)
        embed.set_footer(text=f"Sondage créé par {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        
        poll_message = await ctx.send(embed=embed)
        
        # Ajoute les réactions
        await poll_message.add_reaction("✅")
        await poll_message.add_reaction("❌")
        
        logger.info(f"Sondage créé par {ctx.author.name}: {question}")
    
    @commands.command(name='dice', aliases=['dé', 'roll'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def dice(self, ctx, sides: int = 6):
        """Lance un dé (par défaut 6 faces)"""
        if sides < 2:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Un dé doit avoir au moins 2 faces !",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        if sides > 100:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Un dé ne peut pas avoir plus de 100 faces !",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        result = random.randint(1, sides)
        
        embed = discord.Embed(
            title="🎲 Lancer de dé",
            description=f"Dé à {sides} faces",
            color=int(self.bot.config['embed_color'], 16)
        )
        embed.add_field(name="🎯 Résultat", value=f"**{result}**", inline=True)
        embed.set_footer(text=f"Lancé par {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)
        logger.info(f"Dé lancé par {ctx.author.name}: {result}/{sides}")
    
    @commands.command(name='coinflip', aliases=['pile-face', 'pf'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def coinflip(self, ctx):
        """Lance une pièce (pile ou face)"""
        result = random.choice(["Pile", "Face"])
        emoji = "🪙" if result == "Pile" else "🎭"
        
        embed = discord.Embed(
            title="🪙 Pile ou Face",
            description=f"La pièce tombe sur... **{result}** ! {emoji}",
            color=int(self.bot.config['embed_color'], 16)
        )
        embed.set_footer(text=f"Lancé par {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)
        logger.info(f"Pile ou face par {ctx.author.name}: {result}")

async def setup(bot):
    await bot.add_cog(Fun(bot))
