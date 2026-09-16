import os
import sqlite3
import discord
from discord.ext import commands
from dotenv import load_dotenv

# ==========================================
# 1. LOAD ENVIRONMENT VARIABLES
# ==========================================
load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# ==========================================
# 2. DATABASE SETUP (SQLite)
# ==========================================
# This creates a local file named 'scores.db' in the same folder
conn = sqlite3.connect("scores.db")
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS jackbox (
                player TEXT PRIMARY KEY, 
                score INTEGER)''')
conn.commit()

# ==========================================
# 3. DISCORD BOT CONFIGURATION
# ==========================================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in successfully as {bot.user} (ID: {bot.user.id})")
    print("------")

# ==========================================
# 4. GLOBAL ERROR HANDLER
# ==========================================
@bot.event
async def on_command_error(ctx, error):
    """Handles errors when someone without the role tries to use a command."""
    if isinstance(error, commands.MissingRole):
        await ctx.send("❌ You do not have permission to use this command. You need the **ORGANIZACIJA** role.")
    elif isinstance(error, commands.CommandNotFound):
        pass # Ignores typos
    else:
        print(f"Error in command {ctx.command}: {error}")

# ==========================================
# 5. HELPER FUNCTION TO UPDATE SCORE
# ==========================================
def update_player_score(player_name: str, score_to_add: int) -> int:
    """Queries local SQLite for existing score, adds new points, and updates."""
    c.execute("SELECT score FROM jackbox WHERE player = ?", (player_name,))
    row = c.fetchone()
    
    if row:
        # Player exists, add to their current score
        new_total = row[0] + score_to_add
        c.execute("UPDATE jackbox SET score = ? WHERE player = ?", (new_total, player_name))
    else:
        # New player, insert them
        new_total = score_to_add
        c.execute("INSERT INTO jackbox (player, score) VALUES (?, ?)", (player_name, new_total))
        
    conn.commit()
    return new_total

# ==========================================
# 6. BOT COMMANDS
# ==========================================

# Command: !addscore @Player 1500 (RESTRICTED)
@bot.command()
@commands.has_role("ORGANIZACIJA")
async def addscore(ctx, player: discord.Member, score: int):
    new_total = update_player_score(player.display_name, score)
    await ctx.send(f"✅ Added **{score}** points to **{player.display_name}**! (Total: **{new_total}** pts)")

# Command: !addscores @Player1 4000 @Player2 3200 (RESTRICTED)
@bot.command()
@commands.has_role("ORGANIZACIJA")
async def addscores(ctx, *args):
    if len(args) == 0 or len(args) % 2 != 0:
        return await ctx.send("❌ Usage: `!addscores @Player1 4000 @Player2 3000`")

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

# Command: !resetboard (RESTRICTED)
@bot.command(name="resetboard")
@commands.has_role("ORGANIZACIJA")
async def resetboard(ctx):
    c.execute("DELETE FROM jackbox")
    conn.commit()
    await ctx.send("🗑️ The leaderboard has been completely reset!")

# Command: !leaderboard (PUBLIC - NO ROLE REQUIRED)
@bot.command()
async def leaderboard(ctx):
    c.execute("SELECT player, score FROM jackbox ORDER BY score DESC LIMIT 10")
    rows = c.fetchall()
    
    if not rows:
        return await ctx.send("The leaderboard is currently empty! Go play some Jackbox.")

    board = "**🏆 Official Jackbox Leaderboard 🏆**\n\n"
    for index, row in enumerate(rows, 1):
        board += f"**#{index}** {row[0]} — **{row[1]}** pts\n"
    
    await ctx.send(board)

# ==========================================
# 7. RUN BOT
# ==========================================
if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ Error: DISCORD_BOT_TOKEN is missing from your .env file!")
    else:
        bot.run(BOT_TOKEN)