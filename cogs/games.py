import discord
from discord.ext import commands
import random
import asyncio
import logging

logger = logging.getLogger('discord_bot.games')

class Games(commands.Cog):
    """Cog pour les mini-jeux interactifs"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}  # Pour éviter les jeux multiples
        
    @commands.command(name='rps')
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def rock_paper_scissors(self, ctx, choice: str = None):
        """Pierre-papier-ciseaux contre le bot"""
        if not choice:
            embed = discord.Embed(
                title="🎮 Pierre-Papier-Ciseaux",
                description="Utilisez `!rps [pierre/papier/ciseaux]`",
                color=0x3498db
            )
            await ctx.send(embed=embed)
            return
        
        choice = choice.lower()
        valid_choices = ['pierre', 'papier', 'ciseaux', 'rock', 'paper', 'scissors']
        
        if choice not in valid_choices:
            embed = discord.Embed(
                title="❌ Choix invalide",
                description="Choisissez entre : `pierre`, `papier`, ou `ciseaux`",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        # Normalisation des choix
        choice_map = {
            'pierre': 'pierre', 'rock': 'pierre',
            'papier': 'papier', 'paper': 'papier',
            'ciseaux': 'ciseaux', 'scissors': 'ciseaux'
        }
        user_choice = choice_map[choice]
        bot_choice = random.choice(['pierre', 'papier', 'ciseaux'])
        
        # Emojis
        emoji_map = {'pierre': '🗿', 'papier': '📄', 'ciseaux': '✂️'}
        
        # Logique du jeu
        if user_choice == bot_choice:
            result = "🤝 Égalité !"
            color = 0xf39c12
        elif (user_choice == 'pierre' and bot_choice == 'ciseaux') or \
             (user_choice == 'papier' and bot_choice == 'pierre') or \
             (user_choice == 'ciseaux' and bot_choice == 'papier'):
            result = "🎉 Vous gagnez !"
            color = 0x2ecc71
        else:
            result = "😔 Vous perdez !"
            color = 0xe74c3c
        
        embed = discord.Embed(
            title="🎮 Pierre-Papier-Ciseaux",
            description=f"**{result}**",
            color=color
        )
        embed.add_field(name="Votre choix", value=f"{emoji_map[user_choice]} {user_choice.title()}", inline=True)
        embed.add_field(name="Mon choix", value=f"{emoji_map[bot_choice]} {bot_choice.title()}", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='guess')
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def guess_number(self, ctx, max_number: int = 100):
        """Jeu de devinette de nombre"""
        if max_number < 10 or max_number > 1000:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Le nombre maximum doit être entre 10 et 1000.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        if ctx.author.id in self.active_games:
            embed = discord.Embed(
                title="❌ Jeu en cours",
                description="Vous avez déjà un jeu en cours !",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        secret_number = random.randint(1, max_number)
        attempts = 0
        max_attempts = min(10, max(5, max_number // 20))
        
        self.active_games[ctx.author.id] = True
        
        embed = discord.Embed(
            title="🎯 Jeu de Devinette",
            description=f"J'ai choisi un nombre entre **1** et **{max_number}**.\nVous avez **{max_attempts}** tentatives pour le deviner !",
            color=0x3498db
        )
        embed.set_footer(text="Tapez votre nombre dans le chat !")
        await ctx.send(embed=embed)
        
        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel
        
        while attempts < max_attempts:
            try:
                message = await self.bot.wait_for('message', timeout=60.0, check=check)
                
                try:
                    guess = int(message.content)
                except ValueError:
                    continue
                
                attempts += 1
                
                if guess == secret_number:
                    embed = discord.Embed(
                        title="🎉 Félicitations !",
                        description=f"Vous avez trouvé le nombre **{secret_number}** en **{attempts}** tentative(s) !",
                        color=0x2ecc71
                    )
                    await ctx.send(embed=embed)
                    break
                elif guess < secret_number:
                    hint = "📈 Plus grand !"
                else:
                    hint = "📉 Plus petit !"
                
                remaining = max_attempts - attempts
                if remaining > 0:
                    embed = discord.Embed(
                        title=f"🎯 Tentative {attempts}/{max_attempts}",
                        description=f"{hint}\nIl vous reste **{remaining}** tentative(s).",
                        color=0xf39c12
                    )
                    await ctx.send(embed=embed)
                else:
                    embed = discord.Embed(
                        title="😔 Perdu !",
                        description=f"Le nombre était **{secret_number}**.\nMeilleure chance la prochaine fois !",
                        color=0xe74c3c
                    )
                    await ctx.send(embed=embed)
                    break
                    
            except asyncio.TimeoutError:
                embed = discord.Embed(
                    title="⏰ Temps écoulé !",
                    description=f"Le nombre était **{secret_number}**.",
                    color=0xe74c3c
                )
                await ctx.send(embed=embed)
                break
        
        if ctx.author.id in self.active_games:
            del self.active_games[ctx.author.id]
    
    @commands.command(name='coinflip')
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def coin_flip(self, ctx, bet: str = None):
        """Lance une pièce (pile ou face)"""
        if bet and bet.lower() not in ['pile', 'face', 'heads', 'tails']:
            embed = discord.Embed(
                title="❌ Pari invalide",
                description="Choisissez `pile` ou `face` (optionnel)",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        result = random.choice(['pile', 'face'])
        emoji = '🪙' if result == 'pile' else '🔘'
        
        embed = discord.Embed(
            title="🪙 Lancer de Pièce",
            description=f"La pièce tombe sur... **{result.upper()}** {emoji}",
            color=0xf1c40f
        )
        
        if bet:
            bet_normalized = 'pile' if bet.lower() in ['pile', 'heads'] else 'face'
            if bet_normalized == result:
                embed.add_field(name="🎉 Résultat", value="Vous avez gagné votre pari !", inline=False)
                embed.color = 0x2ecc71
            else:
                embed.add_field(name="😔 Résultat", value="Vous avez perdu votre pari !", inline=False)
                embed.color = 0xe74c3c
        
        await ctx.send(embed=embed)
    
    @commands.command(name='dice')
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def roll_dice(self, ctx, sides: int = 6, count: int = 1):
        """Lance un ou plusieurs dés"""
        if sides < 2 or sides > 100:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Le dé doit avoir entre 2 et 100 faces.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        if count < 1 or count > 10:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Vous pouvez lancer entre 1 et 10 dés.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        results = [random.randint(1, sides) for _ in range(count)]
        total = sum(results)
        
        embed = discord.Embed(
            title="🎲 Lancer de Dé(s)",
            color=0x9b59b6
        )
        
        if count == 1:
            embed.description = f"Résultat : **{results[0]}**"
        else:
            embed.description = f"Résultats : {' + '.join(map(str, results))} = **{total}**"
            embed.add_field(name="📊 Détails", value=f"{count} dé(s) à {sides} faces", inline=True)
            embed.add_field(name="🎯 Total", value=f"{total}", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='trivia')
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def trivia_question(self, ctx):
        """Question de culture générale"""
        questions = [
            {
                "question": "Quelle est la capitale de l'Australie ?",
                "options": ["Sydney", "Melbourne", "Canberra", "Perth"],
                "answer": 2,
                "explanation": "Canberra est la capitale de l'Australie, pas Sydney !"
            },
            {
                "question": "Combien de continents y a-t-il sur Terre ?",
                "options": ["5", "6", "7", "8"],
                "answer": 2,
                "explanation": "Il y a 7 continents : Afrique, Antarctique, Asie, Europe, Amérique du Nord, Océanie et Amérique du Sud."
            },
            {
                "question": "Quel est l'élément chimique avec le symbole 'Au' ?",
                "options": ["Argent", "Or", "Aluminium", "Arsenic"],
                "answer": 1,
                "explanation": "Au vient du latin 'aurum' qui signifie or."
            },
            {
                "question": "En quelle année a eu lieu la chute du mur de Berlin ?",
                "options": ["1987", "1989", "1991", "1993"],
                "answer": 1,
                "explanation": "Le mur de Berlin est tombé le 9 novembre 1989."
            },
            {
                "question": "Quel est le plus grand océan du monde ?",
                "options": ["Atlantique", "Indien", "Arctique", "Pacifique"],
                "answer": 3,
                "explanation": "L'océan Pacifique couvre environ un tiers de la surface de la Terre."
            }
        ]
        
        question_data = random.choice(questions)
        
        embed = discord.Embed(
            title="🧠 Question de Culture Générale",
            description=question_data["question"],
            color=0x3498db
        )
        
        options_text = ""
        for i, option in enumerate(question_data["options"]):
            options_text += f"{i+1}️⃣ {option}\n"
        
        embed.add_field(name="Options", value=options_text, inline=False)
        embed.set_footer(text="Répondez avec le numéro de votre choix (1-4) • Temps limite : 30 secondes")
        
        message = await ctx.send(embed=embed)
        
        # Ajouter les réactions
        reactions = ['1️⃣', '2️⃣', '3️⃣', '4️⃣']
        for reaction in reactions:
            await message.add_reaction(reaction)
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in reactions and reaction.message.id == message.id
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            user_answer = reactions.index(str(reaction.emoji))
            correct_answer = question_data["answer"]
            
            if user_answer == correct_answer:
                result_embed = discord.Embed(
                    title="🎉 Correct !",
                    description=question_data["explanation"],
                    color=0x2ecc71
                )
            else:
                result_embed = discord.Embed(
                    title="❌ Incorrect !",
                    description=f"La bonne réponse était : **{question_data['options'][correct_answer]}**\n\n{question_data['explanation']}",
                    color=0xe74c3c
                )
            
            await ctx.send(embed=result_embed)
            
        except asyncio.TimeoutError:
            timeout_embed = discord.Embed(
                title="⏰ Temps écoulé !",
                description=f"La bonne réponse était : **{question_data['options'][question_data['answer']]}**\n\n{question_data['explanation']}",
                color=0xf39c12
            )
            await ctx.send(embed=timeout_embed)

    @commands.command(name='slots')
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def slot_machine(self, ctx):
        """Machine à sous virtuelle"""
        symbols = ['🍒', '🍋', '🍊', '🍇', '⭐', '💎', '7️⃣']
        weights = [30, 25, 20, 15, 7, 2, 1]  # Probabilités

        # Génération des résultats
        results = random.choices(symbols, weights=weights, k=3)

        # Animation
        embed = discord.Embed(
            title="🎰 Machine à Sous",
            description="🎲 🎲 🎲\nLancement en cours...",
            color=0xf1c40f
        )
        message = await ctx.send(embed=embed)

        await asyncio.sleep(1)

        # Résultat final
        result_text = " ".join(results)

        # Calcul des gains
        if results[0] == results[1] == results[2]:
            if results[0] == '💎':
                multiplier = 100
                win_text = "🎉 JACKPOT DIAMANT ! 💎"
            elif results[0] == '7️⃣':
                multiplier = 50
                win_text = "🎉 TRIPLE SEPT ! 7️⃣"
            elif results[0] == '⭐':
                multiplier = 25
                win_text = "🌟 TRIPLE ÉTOILE !"
            else:
                multiplier = 10
                win_text = "🎉 TRIPLE !"
            color = 0x2ecc71
        elif results[0] == results[1] or results[1] == results[2] or results[0] == results[2]:
            multiplier = 2
            win_text = "🎊 PAIRE !"
            color = 0xf39c12
        else:
            multiplier = 0
            win_text = "😔 Perdu..."
            color = 0xe74c3c

        embed = discord.Embed(
            title="🎰 Machine à Sous",
            description=f"**{result_text}**\n\n{win_text}",
            color=color
        )

        if multiplier > 0:
            embed.add_field(name="💰 Gains", value=f"Multiplicateur x{multiplier}", inline=True)

        await message.edit(embed=embed)

    @commands.command(name='hangman')
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def hangman_game(self, ctx):
        """Jeu du pendu"""
        if ctx.author.id in self.active_games:
            embed = discord.Embed(
                title="❌ Jeu en cours",
                description="Vous avez déjà un jeu en cours !",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        words = [
            "PYTHON", "DISCORD", "ORDINATEUR", "PROGRAMMATION", "INTELLIGENCE",
            "TECHNOLOGIE", "INTERNET", "SERVEUR", "DEVELOPPEUR", "ALGORITHME",
            "VARIABLE", "FONCTION", "BOUCLE", "CONDITION", "TABLEAU"
        ]

        word = random.choice(words)
        guessed_letters = set()
        wrong_guesses = 0
        max_wrong = 6

        self.active_games[ctx.author.id] = True

        def get_display_word():
            return " ".join([letter if letter in guessed_letters else "_" for letter in word])

        def get_hangman_art():
            stages = [
                "```\n  +---+\n  |   |\n      |\n      |\n      |\n      |\n=========\n```",
                "```\n  +---+\n  |   |\n  O   |\n      |\n      |\n      |\n=========\n```",
                "```\n  +---+\n  |   |\n  O   |\n  |   |\n      |\n      |\n=========\n```",
                "```\n  +---+\n  |   |\n  O   |\n /|   |\n      |\n      |\n=========\n```",
                "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n      |\n      |\n=========\n```",
                "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n /    |\n      |\n=========\n```",
                "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n / \\  |\n      |\n=========\n```"
            ]
            return stages[wrong_guesses]

        embed = discord.Embed(
            title="🎪 Jeu du Pendu",
            description=f"**Mot à deviner :** `{get_display_word()}`\n\n{get_hangman_art()}",
            color=0x3498db
        )
        embed.add_field(name="❌ Erreurs", value=f"{wrong_guesses}/{max_wrong}", inline=True)
        embed.add_field(name="📝 Lettres essayées", value="Aucune", inline=True)
        embed.set_footer(text="Tapez une lettre dans le chat ! (A-Z)")

        await ctx.send(embed=embed)

        def check(message):
            return (message.author == ctx.author and
                   message.channel == ctx.channel and
                   len(message.content) == 1 and
                   message.content.isalpha())

        while wrong_guesses < max_wrong and "_" in get_display_word():
            try:
                message = await self.bot.wait_for('message', timeout=120.0, check=check)
                letter = message.content.upper()

                if letter in guessed_letters:
                    await ctx.send("❌ Vous avez déjà essayé cette lettre !")
                    continue

                guessed_letters.add(letter)

                if letter in word:
                    result = "✅ Bonne lettre !"
                    color = 0x2ecc71
                else:
                    wrong_guesses += 1
                    result = "❌ Lettre incorrecte !"
                    color = 0xe74c3c

                embed = discord.Embed(
                    title="🎪 Jeu du Pendu",
                    description=f"**Mot à deviner :** `{get_display_word()}`\n\n{get_hangman_art()}\n\n{result}",
                    color=color
                )
                embed.add_field(name="❌ Erreurs", value=f"{wrong_guesses}/{max_wrong}", inline=True)
                embed.add_field(name="📝 Lettres essayées", value=" ".join(sorted(guessed_letters)), inline=True)

                if "_" not in get_display_word():
                    embed.title = "🎉 Félicitations !"
                    embed.description = f"**Mot trouvé :** `{word}`\n\nVous avez gagné !"
                    embed.color = 0x2ecc71
                elif wrong_guesses >= max_wrong:
                    embed.title = "😔 Perdu !"
                    embed.description = f"**Le mot était :** `{word}`\n\n{get_hangman_art()}"
                    embed.color = 0xe74c3c
                else:
                    embed.set_footer(text="Tapez une lettre dans le chat ! (A-Z)")

                await ctx.send(embed=embed)

            except asyncio.TimeoutError:
                embed = discord.Embed(
                    title="⏰ Temps écoulé !",
                    description=f"**Le mot était :** `{word}`",
                    color=0xf39c12
                )
                await ctx.send(embed=embed)
                break

        if ctx.author.id in self.active_games:
            del self.active_games[ctx.author.id]

async def setup(bot):
    await bot.add_cog(Games(bot))
