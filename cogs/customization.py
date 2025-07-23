import discord
from discord.ext import commands
import json
import logging
import re
from datetime import datetime
import pytz

logger = logging.getLogger('discord_bot.customization')

class Customization(commands.Cog):
    """Cog pour la personnalisation du bot"""
    
    def __init__(self, bot):
        self.bot = bot
        self.guild_settings = {}
        self.load_guild_settings()
    
    def load_guild_settings(self):
        """Charge les paramètres des serveurs"""
        try:
            with open('guild_settings.json', 'r', encoding='utf-8') as f:
                self.guild_settings = json.load(f)
        except FileNotFoundError:
            self.guild_settings = {}
            logger.info("Fichier de paramètres des serveurs créé")
    
    def save_guild_settings(self):
        """Sauvegarde les paramètres des serveurs"""
        try:
            with open('guild_settings.json', 'w', encoding='utf-8') as f:
                json.dump(self.guild_settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des paramètres: {e}")
    
    def get_guild_settings(self, guild_id):
        """Récupère les paramètres d'un serveur"""
        guild_id = str(guild_id)
        if guild_id not in self.guild_settings:
            self.guild_settings[guild_id] = {
                'prefix': '!',
                'embed_color': '0x3498db',
                'language': 'fr',
                'timezone': 'Europe/Paris'
            }
        return self.guild_settings[guild_id]
    
    @commands.command(name='color')
    @commands.has_permissions(administrator=True)
    async def set_embed_color(self, ctx, color: str):
        """Change la couleur des embeds du bot"""
        # Validation de la couleur hexadécimale
        if not re.match(r'^#?[0-9A-Fa-f]{6}$', color):
            embed = discord.Embed(
                title="❌ Couleur invalide",
                description="Utilisez un code couleur hexadécimal valide (ex: #3498db ou 3498db)",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        # Normalisation de la couleur
        if not color.startswith('#'):
            color = '#' + color
        
        # Conversion en format 0x
        hex_color = '0x' + color[1:]
        
        # Mise à jour des paramètres
        guild_settings = self.get_guild_settings(ctx.guild.id)
        old_color = guild_settings['embed_color']
        guild_settings['embed_color'] = hex_color
        
        # Mise à jour de la config globale du bot
        self.bot.config['embed_color'] = hex_color
        
        # Sauvegarde
        self.save_guild_settings()
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(self.bot.config, f, indent=2, ensure_ascii=False)
        
        # Démonstration avec la nouvelle couleur
        embed = discord.Embed(
            title="✅ Couleur mise à jour",
            description=f"La couleur des embeds a été changée de `{old_color}` vers `{hex_color}`",
            color=int(hex_color, 16)
        )
        embed.add_field(name="Aperçu", value="Voici un aperçu de la nouvelle couleur !", inline=False)
        await ctx.send(embed=embed)
        logger.info(f"Couleur des embeds changée pour {ctx.guild.name}: {old_color} -> {hex_color}")
    
    @commands.command(name='prefix')
    @commands.has_permissions(administrator=True)
    async def set_prefix(self, ctx, new_prefix: str):
        """Change le préfixe des commandes du bot"""
        if len(new_prefix) > 5:
            embed = discord.Embed(
                title="❌ Préfixe trop long",
                description="Le préfixe ne peut pas dépasser 5 caractères.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        if ' ' in new_prefix:
            embed = discord.Embed(
                title="❌ Préfixe invalide",
                description="Le préfixe ne peut pas contenir d'espaces.",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        # Mise à jour des paramètres
        guild_settings = self.get_guild_settings(ctx.guild.id)
        old_prefix = guild_settings['prefix']
        guild_settings['prefix'] = new_prefix
        
        # Sauvegarde
        self.save_guild_settings()
        
        embed = discord.Embed(
            title="✅ Préfixe mis à jour",
            description=f"Le préfixe a été changé de `{old_prefix}` vers `{new_prefix}`",
            color=int(self.bot.config['embed_color'], 16)
        )
        embed.add_field(
            name="💡 Exemple d'utilisation",
            value=f"`{new_prefix}help` - Affiche l'aide\n`{new_prefix}ping` - Teste la latence",
            inline=False
        )
        embed.set_footer(text=f"Nouveau préfixe: {new_prefix}")
        await ctx.send(embed=embed)
        logger.info(f"Préfixe changé pour {ctx.guild.name}: {old_prefix} -> {new_prefix}")
    
    @commands.command(name='language')
    @commands.has_permissions(administrator=True)
    async def set_language(self, ctx, lang: str):
        """Change la langue du bot (fr/en)"""
        lang = lang.lower()
        if lang not in ['fr', 'en', 'français', 'english', 'francais']:
            embed = discord.Embed(
                title="❌ Langue non supportée",
                description="Langues disponibles : `fr` (français), `en` (anglais)",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        # Normalisation
        if lang in ['français', 'francais']:
            lang = 'fr'
        elif lang == 'english':
            lang = 'en'
        
        # Mise à jour des paramètres
        guild_settings = self.get_guild_settings(ctx.guild.id)
        old_lang = guild_settings['language']
        guild_settings['language'] = lang
        
        # Sauvegarde
        self.save_guild_settings()
        
        # Messages selon la langue
        if lang == 'fr':
            title = "✅ Langue mise à jour"
            description = f"La langue a été changée de `{old_lang}` vers `{lang}` (Français)"
            note = "Note : Cette fonctionnalité sera pleinement implémentée dans une future mise à jour."
        else:
            title = "✅ Language Updated"
            description = f"Language changed from `{old_lang}` to `{lang}` (English)"
            note = "Note: This feature will be fully implemented in a future update."
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=int(self.bot.config['embed_color'], 16)
        )
        embed.add_field(name="📝 Note", value=note, inline=False)
        await ctx.send(embed=embed)
        logger.info(f"Langue changée pour {ctx.guild.name}: {old_lang} -> {lang}")
    
    @commands.command(name='timezone')
    @commands.has_permissions(administrator=True)
    async def set_timezone(self, ctx, *, timezone: str):
        """Change le fuseau horaire du serveur"""
        try:
            # Vérification que le fuseau horaire existe
            tz = pytz.timezone(timezone)
            
            # Mise à jour des paramètres
            guild_settings = self.get_guild_settings(ctx.guild.id)
            old_timezone = guild_settings['timezone']
            guild_settings['timezone'] = timezone
            
            # Sauvegarde
            self.save_guild_settings()
            
            # Affichage de l'heure actuelle dans le nouveau fuseau
            now = datetime.now(tz)
            time_str = now.strftime("%H:%M:%S")
            date_str = now.strftime("%d/%m/%Y")
            
            embed = discord.Embed(
                title="✅ Fuseau horaire mis à jour",
                description=f"Le fuseau horaire a été changé de `{old_timezone}` vers `{timezone}`",
                color=int(self.bot.config['embed_color'], 16)
            )
            embed.add_field(name="🕐 Heure actuelle", value=f"{time_str}", inline=True)
            embed.add_field(name="📅 Date actuelle", value=f"{date_str}", inline=True)
            embed.add_field(
                name="💡 Exemples de fuseaux",
                value="• `Europe/Paris`\n• `America/New_York`\n• `Asia/Tokyo`\n• `UTC`",
                inline=False
            )
            await ctx.send(embed=embed)
            logger.info(f"Fuseau horaire changé pour {ctx.guild.name}: {old_timezone} -> {timezone}")
            
        except pytz.exceptions.UnknownTimeZoneError:
            embed = discord.Embed(
                title="❌ Fuseau horaire invalide",
                description=f"Le fuseau horaire `{timezone}` n'existe pas.",
                color=0xe74c3c
            )
            embed.add_field(
                name="💡 Exemples valides",
                value="• `Europe/Paris`\n• `America/New_York`\n• `Asia/Tokyo`\n• `UTC`\n• `Europe/London`",
                inline=False
            )
            embed.add_field(
                name="🔗 Liste complète",
                value="[Voir tous les fuseaux horaires](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)",
                inline=False
            )
            await ctx.send(embed=embed)
    
    @commands.command(name='settings')
    @commands.has_permissions(administrator=True)
    async def show_settings(self, ctx):
        """Affiche les paramètres actuels du serveur"""
        guild_settings = self.get_guild_settings(ctx.guild.id)
        
        # Récupération de l'heure actuelle dans le fuseau du serveur
        try:
            tz = pytz.timezone(guild_settings['timezone'])
            now = datetime.now(tz)
            time_str = now.strftime("%H:%M:%S %d/%m/%Y")
        except:
            time_str = "Erreur de fuseau horaire"
        
        embed = discord.Embed(
            title="⚙️ Paramètres du Serveur",
            description=f"Configuration actuelle pour **{ctx.guild.name}**",
            color=int(guild_settings['embed_color'], 16)
        )
        
        embed.add_field(name="🎨 Couleur des embeds", value=guild_settings['embed_color'], inline=True)
        embed.add_field(name="📝 Préfixe", value=f"`{guild_settings['prefix']}`", inline=True)
        embed.add_field(name="🌍 Langue", value=guild_settings['language'].upper(), inline=True)
        embed.add_field(name="🕐 Fuseau horaire", value=guild_settings['timezone'], inline=True)
        embed.add_field(name="⏰ Heure locale", value=time_str, inline=True)
        embed.add_field(name="🆔 ID du serveur", value=ctx.guild.id, inline=True)
        
        embed.set_footer(text="Utilisez les commandes !color, !prefix, !language, !timezone pour modifier")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Customization(bot))
