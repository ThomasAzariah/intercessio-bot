import discord
import os
from discord.ext import commands, tasks
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# === CONFIGURATION GÉNÉRALE ===
TOKEN = os.getenv("DISCORD_TOKEN")                     # Remplace par ton token Discord
INTENTIONS_CHANNEL_NAME = "intercessio"     # Nom exact du salon pour publier les intentions
RESUME_CHANNEL_NAME = "général"     # Nom exact du salon pour publier les intentions
SOURCE_CHANNEL_NAME = "postez-vos-intentions-anonymes"  # Seul salon d'où l'on peut envoyer une intention
ADMIN_ROLE_NAME = "Ancien"                  # Rôle ayant accès à la commande !purge
MAX_INTENTION_LENGTH = 100                  # Taille maximale d'une intention

# Stockage temporaire en mémoire
intentions_du_jour = []
last_sent_day = None  # Pour éviter le spam du résumé à 20h

# === INTENTS DISCORD ===
intents = discord.Intents.default()
intents.message_content = True  # Permet de lire le contenu des messages

# === INITIALISATION DU BOT ===
bot = commands.Bot(command_prefix="!", intents=intents)

# === COMMANDE : !prier ===
@bot.command()
async def prier(ctx, *, message: str):
    """Ajoute une intention de prière de manière anonyme"""

    # Supprime d'abord le message utilisateur (toujours)
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass  # Si le bot n'a pas les permissions, il ne crashe pas

    # Vérifie que la commande vient du bon salon
    if ctx.channel.name != SOURCE_CHANNEL_NAME:
        await ctx.send(f"⛔ Merci d’utiliser cette commande uniquement dans le salon #{SOURCE_CHANNEL_NAME}.", delete_after=10)
        return

    # Vérifie la longueur de l’intention
    if len(message) > MAX_INTENTION_LENGTH:
        await ctx.send(f"⛔ Ton intention est trop longue (max {MAX_INTENTION_LENGTH} caractères).", delete_after=10)
        return

    # Récupère le salon d’affichage
    channel = discord.utils.get(ctx.guild.text_channels, name=INTENTIONS_CHANNEL_NAME)
    if not channel:
        await ctx.send("⛔ Le salon d'intentions n'existe pas.", delete_after=10)
        return

    # Enregistre l’intention et l’affiche anonymement
    intentions_du_jour.append(message)
    embed = discord.Embed(
        description=f"🙏 Nouvelle intention de prière :\n> {message}\n\nN'hésitez pas à porter cette intention dans votre prière.",
        color=discord.Color.blue()
    )
    sent = await channel.send(embed=embed)
    await sent.add_reaction("🙏")

# === COMMANDE : !intention ===
@bot.command()
async def intention(ctx):
    """Envoie en DM la liste des intentions du jour"""
    if not intentions_du_jour:
        await ctx.author.send("📭 Aucune intention n'a été partagée aujourd'hui.")
    else:
        texte = "\n".join([f"- {msg}" for msg in intentions_du_jour])
        await ctx.author.send(f"📋 Intentions partagées aujourd'hui :\n{texte}")

# === COMMANDE : !purge ===
@bot.command()
async def purge(ctx):
    """Vide la liste des intentions ET efface les messages du bot dans le salon intercessio (admin uniquement)"""
    if not any(role.name.lower() == ADMIN_ROLE_NAME.lower() for role in ctx.author.roles):
        await ctx.send("⛔ Tu n'as pas les permissions pour cette commande.")
        return

    # Vide la mémoire
    intentions_du_jour.clear()

    # Trouve le salon intercessio
    channel = discord.utils.get(ctx.guild.text_channels, name=INTENTIONS_CHANNEL_NAME)
    if not channel:
        await ctx.send("⛔ Salon #intercessio introuvable.")
        return

    # Supprime les messages du bot uniquement
    async for message in channel.history(limit=100):
        if message.author == bot.user:
            try:
                await message.delete()
            except discord.Forbidden:
                await ctx.send("⚠️ Je n'ai pas la permission de supprimer certains messages.")
            except discord.HTTPException:
                pass  # Ignore les erreurs d'effacement

    await ctx.send("✅ Intentions du jour effacées.")

# === TÂCHE AUTOMATIQUE : Résumé à 20h ===
@tasks.loop(minutes=1)
async def resume_quotidien():
    global last_sent_day
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    if now.hour == 20 and now.minute == 0 and last_sent_day != today_str and intentions_du_jour:
        for guild in bot.guilds:
            channel = discord.utils.get(guild.text_channels, name=RESUME_CHANNEL_NAME)
            if channel:
                texte = "\n".join([f"- {msg}" for msg in intentions_du_jour])
                await channel.send(f"📋 Intentions partagées aujourd'hui :\n{texte}")
        last_sent_day = today_str  # Marque comme envoyé pour aujourd'hui

# === ÉVÉNEMENT : Bot prêt ===
@bot.event
async def on_ready():
    print(f"✅ Intercessio connecté en tant que {bot.user}")
    resume_quotidien.start()

# === LANCEMENT DU BOT ===
bot.run(TOKEN)