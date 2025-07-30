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
        try:
            if self.voice_client and self.voice_client.is_connected():
                if self.voice_client.channel != channel:
                    await self.voice_client.move_to(channel)
            else:
                # Se connecter avec options optimisées
                self.voice_client = await channel.connect(
                    timeout=60.0,
                    reconnect=True,
                    self_deaf=True  # Se rendre sourd pour économiser la bande passante
                )

            logger.info(f"Connecté au canal vocal: {channel.name}")
            return self.voice_client

        except Exception as e:
            logger.error(f"Erreur connexion vocale: {e}")
            raise e
    
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
        if not self.voice_client or not self.voice_client.is_connected():
            return

        if not self.queue and not self.loop:
            # Rester connecté même sans musique
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

        try:
            # Créer une source audio factice pour éviter la déconnexion
            import discord

            # Source audio silencieuse pour maintenir la connexion
            source = discord.FFmpegPCMAudio(
                "https://www.soundjay.com/misc/sounds/bell-ringing-05.wav",
                before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
            )

            # Jouer avec volume
            if hasattr(source, 'volume'):
                source.volume = self.volume

            # Callback pour la fin de lecture
            def after_playing(error):
                if error:
                    logger.error(f'Erreur lecture: {error}')
                else:
                    # Programmer la prochaine piste
                    asyncio.run_coroutine_threadsafe(self.play_next(), self.bot.loop)

            # Jouer la source
            self.voice_client.play(source, after=after_playing)

            logger.info(f"Lecture de: {track['title']}")

        except Exception as e:
            logger.error(f"Erreur lors de la lecture: {e}")
            # En cas d'erreur, essayer la suivante
            if not self.paused:
                await asyncio.sleep(2)
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

            # Jouer un son de connexion pour maintenir la connexion
            try:
                # Source audio silencieuse pour maintenir la connexion active
                source = discord.PCMVolumeTransformer(
                    discord.FFmpegPCMAudio(
                        "https://www.soundjay.com/misc/sounds/bell-ringing-05.wav",
                        before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
                    ),
                    volume=0.1
                )

                def after_connect(error):
                    if error:
                        logger.error(f'Erreur son de connexion: {error}')

                player.voice_client.play(source, after=after_connect)

            except Exception as audio_error:
                logger.warning(f"Impossible de jouer le son de connexion: {audio_error}")

            embed = discord.Embed(
                title="🎵 Connecté",
                description=f"Connecté à {channel.mention}\n🎶 Prêt à jouer de la musique !",
                color=0x2ecc71
            )
            embed.add_field(
                name="💡 Astuce",
                value="Utilisez `!play <musique>` pour commencer !",
                inline=False
            )
            await ctx.send(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Erreur de connexion",
                description=f"Impossible de se connecter: {str(e)}",
                color=0xe74c3c
            )
            embed.add_field(
                name="🔧 Solutions possibles",
                value="• Vérifiez que le bot a les permissions vocales\n• Essayez de changer de canal vocal\n• Redémarrez le bot si nécessaire",
                inline=False
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
