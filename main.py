import discord
from discord import app_commands
from discord.ext import commands
import os
import json
from keep_alive import keep_alive

# Lista de mascotas válidas
PETS = ["A ofertar", "Bunny", "Dog", "Golden Lab", "Gamerant", "Grow a Garden", "Radio Times", "Black Bunny", "Cat", "Chicken", "Deer",
    "Orange Tabby", "Spotted Deer", "Pig", "Rooster", "Monkey", "Cow", "Polar Bear", "Sea Otter", "Turtle", "Silver Monkey",
    "Brown Mouse", "Grey Mouse", "Caterpillar", "Giant Ant", "Praying Mantis", "Red Fox", "Red Giant Ant", "Snail", "Squirrel", "YouTube",
    "Dragonfly", "Indiatimes", "Pocket Tactics", "Starfish", "Crab", "Seagull", "Flamingo", "Toucan", "Sea Turtle", "Orangutan",
    "Seal", "Ostrich", "Peacock", "Capybara", "Scarlet Macaw", "Mimic Octopus", "Meerkat", "Sand Snake", "Axolotl", "Hyacinth Macaw",
    "Fennec Fox", "Bee", "Honey Bee", "Bear Bee", "Petal Bee", "Queen Bee", "Wasp", "Tarantula Hawk", "Moth", "Butterfly", "Disco Bee",
    "Hedgehog", "Kiwi", "Frog", "Mole", "Moon Cat", "Blood Kiwi", "Echo Frog", "Night Owl", "Raccoon", "Panda", "Blood Hedgehog",
    "Chicken Zombie", "Firefly", "Owl", "Golden Bee", "Cooked Owl", "Blood Owl", "T Rex", "Raptor", "Triceratops", "Stegosaurus",
    "Pterodactyl", "Brontosaurus"]

CANAL_TRADE_ID = 1392657923712352307
TRADES_FILE = "trades.json"
TRADEANDO_ROLE_NAME = "Tradeando"

# Diccionario con URLs de imagenes reales
PET_IMAGES = {
    "Butterfly": "https://media.discordapp.net/attachments/1392970425461637151/1392971785389084954/Butterfly.png",
    "T Rex": "https://media.discordapp.net/attachments/1392970425461637151/1392980131177304124/T-Rex.png",
    # Puedes agregar más aquí...
}

def get_pet_image_url(pet_name):
    return PET_IMAGES.get(pet_name, "https://via.placeholder.com/150?text=Sin+imagen")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree
trade_requests = {}

def load_trades():
    if os.path.exists(TRADES_FILE):
        with open(TRADES_FILE, "r") as f:
            return json.load(f)
    return {}

def save_trades(data):
    with open(TRADES_FILE, "w") as f:
        json.dump(data, f, indent=4)

trades_data = load_trades()

async def autocomplete_pet(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=pet, value=pet)
        for pet in PETS if current.lower() in pet.lower()
    ][:25]

@bot.event
async def on_ready():
    try:
        synced = await tree.sync()
        print(f"✅ Bot conectado como {bot.user} — {len(synced)} comandos slash sincronizados.")
    except Exception as e:
        print(f"❌ Error al sincronizar comandos: {e}")

@tree.command(name="trade", description="Haz un trade con otra persona")
@app_commands.describe(quiero="La pet que quieres", doy="La pet que das")
@app_commands.autocomplete(quiero=autocomplete_pet, doy=autocomplete_pet)
async def trade(interaction: discord.Interaction, quiero: str, doy: str):
    autor = interaction.user

    if interaction.channel.id != CANAL_TRADE_ID:
        await interaction.response.send_message(f"❌ Este comando solo puede usarse en <#{CANAL_TRADE_ID}>.", ephemeral=True)
        return

    trade_requests[autor.id] = (quiero.lower(), doy.lower())

    for user_id, (q, d) in trade_requests.items():
        if user_id != autor.id and q == doy.lower() and d == quiero.lower():
            otro_usuario = await bot.fetch_user(user_id)
            guild = interaction.guild
            admin_roles = [r for r in guild.roles if r.permissions.administrator or r.name in ["Admins", "Mods"]]

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                autor: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                guild.get_member(otro_usuario.id): discord.PermissionOverwrite(view_channel=True, send_messages=True)
            }
            for role in admin_roles:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

            canal = await guild.create_text_channel(
                f"trade-{autor.name}-{otro_usuario.name}",
                overwrites=overwrites
            )

            role_tradeando = discord.utils.get(guild.roles, name=TRADEANDO_ROLE_NAME)
            if role_tradeando:
                await guild.get_member(autor.id).add_roles(role_tradeando)
                await guild.get_member(otro_usuario.id).add_roles(role_tradeando)

            view = ConfirmTradeView(autor.id, user_id, canal, role_tradeando)

            embed = discord.Embed(
                title="🎉 ¡Match Detectado!",
                description=(
                    f"👤 {autor.mention} quiere 🧸 **{quiero}**\n"
                    f"🎁 Ofrece: **{doy}**\n\n"
                    f"👤 {otro_usuario.mention} quiere 🧸 **{doy}**\n"
                    f"🎁 Ofrece: **{quiero}**\n\n"
                    f"🔒 *Un admin debe confirmar usando los botones de abajo.*"
                ),
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=get_pet_image_url(quiero))
            embed.set_footer(text="Sistema de Trade | Team 24k")
            embed.timestamp = interaction.created_at

            await canal.send(embed=embed, view=view)

            del trade_requests[autor.id]
            del trade_requests[user_id]

            await interaction.response.send_message("✅ ¡Match encontrado! Canal creado.")
            return

    # Si no hay coincidencia aún
    embed = discord.Embed(
        title="📥 Petición guardada",
        description=f"🔁 Quieres 🧸 **{quiero}**, das 🎁 **{doy}**\n⌛ Esperando coincidencia...",
        color=discord.Color.blurple()
    )
    embed.set_thumbnail(url=get_pet_image_url(quiero))
    embed.set_footer(text="Sistema de Trade | Team 24k")
    embed.timestamp = interaction.created_at

    await interaction.response.send_message(embed=embed)

class ConfirmTradeView(discord.ui.View):
    def __init__(self, user1_id, user2_id, channel, tradeando_role):
        super().__init__(timeout=None)
        self.user1_id = user1_id
        self.user2_id = user2_id
        self.channel = channel
        self.tradeando_role = tradeando_role

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.guild_permissions.administrator:
            return True
        await interaction.response.send_message("❌ Solo administradores pueden confirmar trades.", ephemeral=True)
        return False

    async def _remove_roles(self):
        guild = self.channel.guild
        for uid in [self.user1_id, self.user2_id]:
            member = guild.get_member(uid)
            if member and self.tradeando_role in member.roles:
                await member.remove_roles(self.tradeando_role)

    @discord.ui.button(label="✅ Trade completado", style=discord.ButtonStyle.success)
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        for user_id in [self.user1_id, self.user2_id]:
            trades_data[str(user_id)] = trades_data.get(str(user_id), 0) + 1
        save_trades(trades_data)
        await self._remove_roles()
        await interaction.response.send_message("✅ Trade registrado y canal cerrado.")
        await self.channel.delete()

    @discord.ui.button(label="❌ Trade cancelado", style=discord.ButtonStyle.danger)
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._remove_roles()
        await interaction.response.send_message("❌ Trade cancelado. Canal cerrado.")
        await self.channel.delete()

keep_alive()

token = os.getenv("TOKEN")
if not token:
    raise ValueError("❌ TOKEN no encontrado.")
bot.run(token)
