import discord
from discord.ext import commands
import asyncio
import json
import logging
from datetime import datetime
import re
import aiohttp

logger = logging.getLogger('discord_bot.music')

class MusicPlayer:
    """Lecteur de musique pour un serveur"""
    
    def __init__(self, bot, guild):
        self.bot = bot
        self.guild = guild
        self.voice_client = None
        self.queue = []
        self.current = None
        self.volume = 0.5
        self.loop = False
        self.loop_queue = False
        self.shuffle = False
        self.paused = False
        self.effects = {
            'bass_boost': False,
            'nightcore': False,
            'vaporwave': False
        }
        
    async def connect(self, channel):
        """Se connecte à un canal vocal"""
        if self.voice_client:
            await self.voice_client.move_to(channel)
        else:
            self.voice_client = await channel.connect()
        return self.voice_client
    
    async def disconnect(self):
        """Se déconnecte du canal vocal"""
        if self.voice_client:
            await self.voice_client.disconnect()
            self.voice_client = None
    
    def add_to_queue(self, track):
        """Ajoute une piste à la queue"""
        self.queue.append(track)
    
    def remove_from_queue(self, index):
        """Retire une piste de la queue"""
        if 0 <= index < len(self.queue):
            return self.queue.pop(index)
        return None
    
    def clear_queue(self):
        """Vide la queue"""
        self.queue.clear()
    
    async def play_next(self):
        """Joue la prochaine piste"""
        if not self.queue and not self.loop:
            return
        
        if self.loop and self.current:
            # Rejouer la piste actuelle
            track = self.current
        elif self.queue:
            # Prendre la prochaine piste
            track = self.queue.pop(0)
            if self.loop_queue:
                self.queue.append(track)
        else:
            return
        
        self.current = track
        
        # Ici, vous devriez implémenter la lecture audio
        # Pour cet exemple, nous simulons la lecture
        logger.info(f"Lecture de: {track['title']}")
        
        # Simuler la durée de la piste (pour l'exemple)
        await asyncio.sleep(1)  # En réalité, cela serait la durée de la piste
        
        # Jouer la suivante
        if not self.paused:
            await self.play_next()

class Track:
    """Représente une piste audio"""
    
    def __init__(self, title, url, duration, thumbnail, requester):
        self.title = title
        self.url = url
        self.duration = duration
        self.thumbnail = thumbnail
        self.requester = requester
        self.source = None  # Source audio (sera définie lors de la lecture)

class Music(commands.Cog):
    """Système de musique avancé"""
    
    def __init__(self, bot):
        self.bot = bot
        self.players = {}  # {guild_id: MusicPlayer}
        self.playlists = self.load_playlists()
        
    def load_playlists(self):
        """Charge les playlists sauvegardées"""
        try:
            with open('playlists.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def save_playlists(self):
        """Sauvegarde les playlists"""
        try:
            with open('playlists.json', 'w', encoding='utf-8') as f:
                json.dump(self.playlists, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erreur sauvegarde playlists: {e}")
    
    def get_player(self, guild):
        """Récupère ou crée un lecteur pour un serveur"""
        if guild.id not in self.players:
            self.players[guild.id] = MusicPlayer(self.bot, guild)
        return self.players[guild.id]
    
    async def search_youtube(self, query):
        """Recherche sur YouTube (simulation)"""
        # Dans un vrai bot, vous utiliseriez l'API YouTube ou youtube-dl
        # Ici, nous simulons une recherche
        return {
            'title': f"Résultat pour: {query}",
            'url': f"https://youtube.com/watch?v=example",
            'duration': "3:45",
            'thumbnail': "https://img.youtube.com/vi/example/maxresdefault.jpg"
        }
    
    @commands.command(name='join', aliases=['connect'])
    async def join_voice(self, ctx):
        """Rejoint le canal vocal de l'utilisateur"""
        if not ctx.author.voice:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Vous devez être dans un canal vocal !",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        channel = ctx.author.voice.channel
        player = self.get_player(ctx.guild)
        
        try:
            await player.connect(channel)
            embed = discord.Embed(
                title="🎵 Connecté",
                description=f"Connecté à {channel.mention}",
                color=0x2ecc71
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Erreur de connexion",
                description=str(e),
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
    
    @commands.command(name='leave', aliases=['disconnect'])
    async def leave_voice(self, ctx):
        """Quitte le canal vocal"""
        player = self.get_player(ctx.guild)
        
        if not player.voice_client:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Je ne suis pas connecté à un canal vocal !",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        await player.disconnect()
        player.clear_queue()
        
        embed = discord.Embed(
            title="👋 Déconnecté",
            description="Déconnecté du canal vocal",
            color=0x2ecc71
        )
        await ctx.send(embed=embed)
    
    @commands.command(name='play', aliases=['p'])
    async def play_music(self, ctx, *, query):
        """Joue de la musique"""
        if not ctx.author.voice:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Vous devez être dans un canal vocal !",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        player = self.get_player(ctx.guild)
        
        # Se connecter si pas déjà connecté
        if not player.voice_client:
            await player.connect(ctx.author.voice.channel)
        
        # Rechercher la musique
        embed = discord.Embed(
            title="🔍 Recherche en cours...",
            description=f"Recherche de: `{query}`",
            color=0x3498db
        )
        search_msg = await ctx.send(embed=embed)
        
        try:
            # Simuler la recherche (remplacez par une vraie recherche)
            result = await self.search_youtube(query)
            
            # Créer la piste
            track = {
                'title': result['title'],
                'url': result['url'],
                'duration': result['duration'],
                'thumbnail': result['thumbnail'],
                'requester': ctx.author
            }
            
            # Ajouter à la queue
            player.add_to_queue(track)
            
            # Mettre à jour le message
            embed = discord.Embed(
                title="✅ Ajouté à la queue",
                description=f"**{track['title']}**",
                color=0x2ecc71
            )
            embed.add_field(name="⏱️ Durée", value=track['duration'], inline=True)
            embed.add_field(name="👤 Demandé par", value=ctx.author.mention, inline=True)
            embed.add_field(name="📍 Position", value=f"{len(player.queue)}", inline=True)
            embed.set_thumbnail(url=track['thumbnail'])
            
            await search_msg.edit(embed=embed)
            
            # Commencer la lecture si rien ne joue
            if not player.current:
                await player.play_next()
                
        except Exception as e:
            embed = discord.Embed(
                title="❌ Erreur de recherche",
                description=f"Impossible de trouver: `{query}`",
                color=0xe74c3c
            )
            await search_msg.edit(embed=embed)
    
    @commands.command(name='queue', aliases=['q'])
    async def show_queue(self, ctx):
        """Affiche la queue de musique"""
        player = self.get_player(ctx.guild)
        
        if not player.queue and not player.current:
            embed = discord.Embed(
                title="📭 Queue vide",
                description="Aucune musique en cours ou en attente",
                color=0x95a5a6
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="🎵 Queue de musique",
            color=0x3498db,
            timestamp=datetime.now()
        )
        
        # Musique actuelle
        if player.current:
            embed.add_field(
                name="🎶 En cours",
                value=f"**{player.current['title']}**\nDemandé par {player.current['requester'].mention}",
                inline=False
            )
        
        # Queue
        if player.queue:
            queue_text = ""
            for i, track in enumerate(player.queue[:10]):  # Limite à 10
                queue_text += f"`{i+1}.` **{track['title']}** - {track['requester'].mention}\n"
            
            if len(player.queue) > 10:
                queue_text += f"\n... et {len(player.queue) - 10} autres"
            
            embed.add_field(
                name="📋 En attente",
                value=queue_text,
                inline=False
            )
        
        # Informations
        embed.add_field(name="🔊 Volume", value=f"{int(player.volume * 100)}%", inline=True)
        embed.add_field(name="🔁 Loop", value="✅" if player.loop else "❌", inline=True)
        embed.add_field(name="🔀 Shuffle", value="✅" if player.shuffle else "❌", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='skip', aliases=['s'])
    async def skip_track(self, ctx):
        """Passe à la musique suivante"""
        player = self.get_player(ctx.guild)
        
        if not player.current:
            embed = discord.Embed(
                title="❌ Rien ne joue",
                description="Aucune musique en cours",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        # Arrêter la musique actuelle
        if player.voice_client and player.voice_client.is_playing():
            player.voice_client.stop()
        
        embed = discord.Embed(
            title="⏭️ Musique passée",
            description=f"**{player.current['title']}** a été passée",
            color=0x2ecc71
        )
        await ctx.send(embed=embed)
        
        # Jouer la suivante
        await player.play_next()
    
    @commands.command(name='pause')
    async def pause_music(self, ctx):
        """Met en pause la musique"""
        player = self.get_player(ctx.guild)
        
        if not player.voice_client or not player.voice_client.is_playing():
            embed = discord.Embed(
                title="❌ Rien ne joue",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        player.voice_client.pause()
        player.paused = True
        
        embed = discord.Embed(
            title="⏸️ Musique en pause",
            description=f"**{player.current['title']}** mis en pause",
            color=0xf39c12
        )
        await ctx.send(embed=embed)
    
    @commands.command(name='resume')
    async def resume_music(self, ctx):
        """Reprend la musique"""
        player = self.get_player(ctx.guild)
        
        if not player.voice_client or not player.voice_client.is_paused():
            embed = discord.Embed(
                title="❌ Musique non en pause",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        player.voice_client.resume()
        player.paused = False
        
        embed = discord.Embed(
            title="▶️ Musique reprise",
            description=f"**{player.current['title']}** reprend",
            color=0x2ecc71
        )
        await ctx.send(embed=embed)
    
    @commands.command(name='volume', aliases=['vol'])
    async def set_volume(self, ctx, volume: int = None):
        """Ajuste le volume (0-100)"""
        player = self.get_player(ctx.guild)
        
        if volume is None:
            embed = discord.Embed(
                title="🔊 Volume actuel",
                description=f"Volume: {int(player.volume * 100)}%",
                color=0x3498db
            )
            await ctx.send(embed=embed)
            return
        
        if not 0 <= volume <= 100:
            embed = discord.Embed(
                title="❌ Volume invalide",
                description="Le volume doit être entre 0 et 100",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return
        
        player.volume = volume / 100
        
        if player.voice_client and hasattr(player.voice_client.source, 'volume'):
            player.voice_client.source.volume = player.volume
        
        embed = discord.Embed(
            title="🔊 Volume ajusté",
            description=f"Volume réglé à {volume}%",
            color=0x2ecc71
        )
        await ctx.send(embed=embed)

    @commands.command(name='effects')
    async def audio_effects(self, ctx, effect: str = None):
        """Applique des effets audio (bass, nightcore, vaporwave)"""
        player = self.get_player(ctx.guild)

        if effect is None:
            # Afficher les effets disponibles
            embed = discord.Embed(
                title="🎛️ Effets Audio",
                description="Effets disponibles:",
                color=0x3498db
            )

            effects_status = []
            for effect_name, active in player.effects.items():
                status = "✅" if active else "❌"
                effects_status.append(f"{status} {effect_name}")

            embed.add_field(
                name="📊 État actuel",
                value="\n".join(effects_status),
                inline=False
            )
            embed.add_field(
                name="💡 Utilisation",
                value="`!effects bass` - Bass boost\n"
                      "`!effects nightcore` - Nightcore\n"
                      "`!effects vaporwave` - Vaporwave\n"
                      "`!effects clear` - Supprimer tous les effets",
                inline=False
            )
            await ctx.send(embed=embed)
            return

        effect = effect.lower()

        if effect == 'clear':
            # Supprimer tous les effets
            for key in player.effects:
                player.effects[key] = False

            embed = discord.Embed(
                title="🎛️ Effets supprimés",
                description="Tous les effets audio ont été supprimés",
                color=0x2ecc71
            )
            await ctx.send(embed=embed)
            return

        if effect not in player.effects:
            embed = discord.Embed(
                title="❌ Effet invalide",
                description="Effets disponibles: bass, nightcore, vaporwave, clear",
                color=0xe74c3c
            )
            await ctx.send(embed=embed)
            return

        # Basculer l'effet
        player.effects[effect] = not player.effects[effect]
        status = "activé" if player.effects[effect] else "désactivé"

        embed = discord.Embed(
            title="🎛️ Effet audio",
            description=f"Effet **{effect}** {status}",
            color=0x2ecc71 if player.effects[effect] else 0x95a5a6
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Music(bot))
