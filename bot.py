import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from supabase import create_client, Client

# ==========================================
# 1. LOAD ENVIRONMENT VARIABLES
# ==========================================
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Initialize Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 2. DISCORD BOT CONFIGURATION
# ==========================================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in successfully as {bot.user} (ID: {bot.user.id})")
    print("------")

# ==========================================
# 3. HELPER FUNCTION TO UPDATE SCORE
# ==========================================
def update_player_score(player_name: str, score_to_add: int) -> int:
    """Queries Supabase for existing score, adds new points, and upserts."""
    response = supabase.table("jackbox").select("score").eq("player", player_name).execute()
    
    current_score = 0
    if response.data:
        current_score = response.data[0]["score"]
        
    new_total = current_score + score_to_add
    
    supabase.table("jackbox").upsert({
        "player": player_name,
        "score": new_total
    }).execute()
    
    return new_total

# ==========================================
# 4. BOT COMMANDS
# ==========================================

# Command: !addscore @Player 1500
@bot.command()
async def addscore(ctx, player: discord.Member, score: int):
    """Add points to a single player."""
    new_total = update_player_score(player.display_name, score)
    await ctx.send(f"✅ Added **{score}** points to **{player.display_name}**! (Total: **{new_total}** pts)")

# Command: !addscores @Player1 4000 @Player2 3200 @Player3 1500
@bot.command()
async def addscores(ctx, *args):
    """Batch add points to multiple players at once. Format: !addscores @User1 1000 @User2 500"""
    if len(args) == 0 or len(args) % 2 != 0:
        return await ctx.send("❌ Usage: `!addscores @Player1 4000 @Player2 3000` (must provide player-score pairs)")

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

# Command: !leaderboard
@bot.command()
async def leaderboard(ctx):
    """Display the top 10 players from Supabase."""
    response = supabase.table("jackbox").select("player, score").order("score", desc=True).limit(10).execute()
    
    if not response.data:
        return await ctx.send("The leaderboard is currently empty! Go play some Jackbox.")

    board = "**🏆 Official Jackbox Leaderboard 🏆**\n\n"
    for index, row in enumerate(response.data, 1):
        board += f"**#{index}** {row['player']} — **{row['score']}** pts\n"
    
    await ctx.send(board)

# Command: !resetboard
@bot.command(name="resetboard")
@commands.has_permissions(administrator=True)
async def resetboard(ctx):
    """Clear all records from the leaderboard (Admins only)."""
    supabase.table("jackbox").delete().neq("player", "").execute()
    await ctx.send("🗑️ The leaderboard has been completely reset!")

# ==========================================
# 5. RUN BOT
# ==========================================
if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ Error: DISCORD_BOT_TOKEN is missing from your .env file!")
    else:
        bot.run(BOT_TOKEN)