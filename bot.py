import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

# ==========================================
# 1. LOAD ENVIRONMENT VARIABLES & FIREBASE
# ==========================================
load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Initialize Firebase (Requires serviceAccountKey.json in the same directory)
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    print(f"❌ Firebase Error: {e}\nMake sure 'serviceAccountKey.json' is in your bot folder!")
    db = None

# ==========================================
# 2. DISCORD BOT CONFIGURATION
# ==========================================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=">", intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f"Logged in successfully as {bot.user} (ID: {bot.user.id})")
    print("------")

# ==========================================
# 3. GLOBAL ERROR HANDLER
# ==========================================
@bot.event
async def on_command_error(ctx, error):
    """Handles permission errors and ignores missing command errors."""
    if isinstance(error, commands.MissingRole):
        await ctx.send("❌ You do not have permission to use this command. You need the **ORGANIZACIJA** role.")
    elif isinstance(error, commands.CommandNotFound):
        pass  
    else:
        print(f"Error in command {ctx.command}: {error}")

# ==========================================
# 4. HELPER FUNCTION TO UPDATE SCORE (FIRESTORE)
# ==========================================
def update_player_score(player_name: str, score_to_add: int) -> int:
    """Queries the 'marathon' collection for an existing score, adds points, and updates."""
    doc_ref = db.collection("marathon").document(player_name)
    doc = doc_ref.get()
    
    if doc.exists:
        current_score = doc.to_dict().get("score", 0)
        new_total = current_score + score_to_add
    else:
        new_total = score_to_add
        
    # Only store the score field; the document ID represents the player's username
    doc_ref.set({"score": new_total})
    return new_total

# ==========================================
# 5. BOT COMMANDS
# ==========================================

# Command: >help (PUBLIC)
@bot.command(name="help")
async def help_command(ctx):
    """Displays the bot command manual."""
    embed = discord.Embed(
        title="🎮 Jackbox Leaderboard Manual",
        description="Command reference for score tracking and leaderboards.",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="🔒 Restricted Commands (ORGANIZACIJA Role Only)",
        value=(
            "• `>addscore @Player <score>`\n"
            "  Adds points to a single player.\n"
            "  *Example:* `>addscore @Alex 1500`\n\n"
            "• `>addscores @P1 <s1> @P2 <s2> ...`\n"
            "  Batch-adds points to multiple players.\n"
            "  *Example:* `>addscores @Alex 4000 @Sam 3200`\n\n"
            "• `>resetboard`\n"
            "  Permanently wipes all scores from the marathon database."
        ),
        inline=False
    )

    embed.add_field(
        name="🌐 Public Commands (Everyone)",
        value=(
            "• `>leaderboard`\n"
            "  Displays the top 10 players ranked by score.\n\n"
            "• `>help`\n"
            "  Displays this manual."
        ),
        inline=False
    )

    embed.set_footer(text="Note: You must directly tag players (@User) for score commands to register.")
    await ctx.send(embed=embed)

# Command: >addscore @Player 1500 (RESTRICTED)
@bot.command()
@commands.has_role("ORGANIZACIJA")
async def addscore(ctx, player: discord.Member, score: int):
    new_total = update_player_score(player.display_name, score)
    await ctx.send(f"✅ Added **{score}** points to **{player.display_name}**! (Total: **{new_total}** pts)")

# Command: >addscores @Player1 4000 @Player2 3200 (RESTRICTED)
@bot.command()
@commands.has_role("ORGANIZACIJA")
async def addscores(ctx, *args):
    if len(args) == 0 or len(args) % 2 != 0:
        return await ctx.send("❌ Usage: `>addscores @Player1 4000 @Player2 3000`")

    summary = []
    
    for i in range(0, len(args), 2):
        mention = args[i]
        score_str = args[i+1]
        
        try:
            member = await commands.MemberConverter().convert(ctx, mention)
            score = int(score_str)
            new_total = update_player_score(member.display_name, score)
            summary.append(f"• **{member.display_name}**: +{score} (Total: **{new_total}** pts)")
        except Exception:
            summary.append(f"⚠️ Failed to parse `{mention}` with score `{score_str}`")

    response_text = "**🎮 Scores Updated!**\n" + "\n".join(summary)
    await ctx.send(response_text)

# Command: >resetboard (RESTRICTED)
@bot.command(name="resetboard")
@commands.has_role("ORGANIZACIJA")
async def resetboard(ctx):
    docs = db.collection("marathon").stream()
    count = 0
    for doc in docs:
        doc.reference.delete()
        count += 1
    
    await ctx.send(f"🗑️ The leaderboard has been completely reset! ({count} records deleted)")

# Command: >leaderboard (PUBLIC)
@bot.command()
async def leaderboard(ctx):
    docs = db.collection("marathon").order_by("score", direction=firestore.Query.DESCENDING).limit(10).stream()
    
    board = "**🏆 Official Jackbox Leaderboard 🏆**\n\n"
    has_data = False
    
    for index, doc in enumerate(docs, 1):
        has_data = True
        data = doc.to_dict()
        player_name = doc.id  # Extract username directly from the document ID
        score = data.get("score", 0)
        board += f"**#{index}** {player_name} — **{score}** pts\n"
    
    if not has_data:
        return await ctx.send("The leaderboard is currently empty! Go play some Jackbox.")
        
    await ctx.send(board)

# ==========================================
# 6. RUN BOT
# ==========================================
if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ Error: DISCORD_BOT_TOKEN is missing from your .env file!")
    elif db is None:
        print("❌ Error: Bot will not start without Firebase access.")
    else:
        bot.run(BOT_TOKEN)