import asyncio
import os
import discord
from discord.ext import commands
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
import uvicorn

# Initialize the FastAPI web server
app = FastAPI(title="CA Inter Study Tracker")

# MongoDB connection string (You will get this from MongoDB Atlas)
# In production, use os.getenv("MONGO_URI")
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority")
DB_NAME = "ca_inter_tracker"

# Global database client variable
db_client = None
db = None

# Initialize the Discord Bot with slash command support
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Provide your Discord Bot Token via environment variables in Render
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "YOUR_DISCORD_BOT_TOKEN_HERE")

@app.on_event("startup")
async def startup_event():
    global db_client, db
    
    # 1. Connect to MongoDB Atlas
    try:
        db_client = AsyncIOMotorClient(MONGO_URI)
        db = db_client[DB_NAME]
        print("✅ Connected to MongoDB successfully!")
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")

    # 2. Launch the Discord Bot in the background
    print("🚀 Launching Discord Bot...")
    asyncio.create_task(bot.start(DISCORD_TOKEN))

@app.on_event("shutdown")
async def shutdown_event():
    # Cleanly close database and bot on shutdown
    global db_client
    if db_client:
        db_client.close()
    await bot.close()

@app.get("/ping")
async def keep_alive_ping():
    """
    UptimeRobot will hit this endpoint every 5-10 minutes.
    This prevents the Render free tier from spinning down the service!
    """
    return {"status": "alive", "message": "Render instance is awake!"}

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """
    This route serves the HTML file we built earlier.
    In a real scenario, you'd read the index.html file from disk and return it.
    """
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content, status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Dashboard HTML not found. Please add index.html to the directory.</h1>", status_code=404)

@app.get("/api/progress")
async def get_progress():
    """
    The Javascript in your HTML will call this route to fetch real-time 
    lecture completion data from MongoDB.
    """
    if db is None:
        return JSONResponse(content={"error": "Database not connected"}, status_code=500)
    
    # Example query to fetch watched lectures
    # data = await db.lectures.find({"completed": True}).to_list(length=1000)
    return {"status": "success", "data": "Database query goes here"}

@bot.event
async def on_ready():
    print(f'✅ Discord Bot logged in as {bot.user}')
    # Sync slash commands with Discord
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

@bot.tree.command(name="log", description="Log a completed CA Inter lecture")
async def log_lecture(interaction: discord.Interaction, subject: str, lecture_number: int):
    """
    Slash command to log a lecture right from Discord.
    """
    # Example logic: Update MongoDB here
    # await db.lectures.update_one(...)
    
    await interaction.response.send_message(
        f"✅ Awesome job! I've marked **{subject.capitalize()} Lecture {lecture_number}** as completed.\nKeep up the great pace!",
        ephemeral=False
    )

from datetime import datetime, date

@bot.tree.command(name="today", description="Get your daily CA Inter itinerary")
async def today_plan(interaction: discord.Interaction):
    """
    Fetches today's targets by querying the database.
    """
    # 1. Logic: Determine "Day Number" (Assuming Day 1 is June 26)
    start_date = date(2026, 6, 26)
    today = date.today()
    day_num = (today - start_date).days + 1
    
    # 2. Logic: Query the database for the lectures assigned to this day
    # This logic assumes we add a 'day_assigned' field to your DB lectures.
    # For now, let's pull all incomplete lectures for the 'current' batch.
    
    # Simple fetch: Get first 6 incomplete lectures (matches your Day 1)
    cursor = db.lectures.find({"completed": False}).limit(6)
    lectures = await cursor.to_list(length=6)
    
    if not lectures:
        await interaction.response.send_message("🎉 You are all caught up!")
        return

    # 3. Format the embed
    embed = discord.Embed(
        title=f"📅 Study Plan - Day {day_num}",
        description="Here is what you need to cover today to stay on track.",
        color=discord.Color.blue()
    )
    
    for lec in lectures:
        embed.add_field(
            name=f"{lec['subject']}", 
            value=f"{lec['chapter']} (Lec {lec['lecture_number']})", 
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    # To run this locally, you would run: python main.py
    # Render will use a command like: uvicorn main:app --host 0.0.0.0 --port $PORT
    print("Starting Uvicorn server...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
