import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import timedelta, datetime
from collections import defaultdict, deque
import random

# ==========================================
# KONFIGURACJA BOTA
# ==========================================
TOKEN = 'MTU2Mjg0NjYwNzA4MTIwOTg2OA.G58J96.V53gN9JWrTi7KLJUQ2IqF9Yw2LH3MeiM52k8QE'  # Wklej swój Token z Discord Developer Portal
IMAGE_URL = 'https://cdn.discordapp.com/attachments/1550977404665860100/1562853528047980544/Zrzut_ekranu_2026-10-22_170144.png?ex=6adb8045&is=6ada2ec5&hm=d922a1c66e31f6a60cb4e9065263db897503294ced7b14b956d5e33f1db64e10&'  # Link do Twojego obrazka z kaczką[cite: 3]

# LISTA ID RÓL (wpisz po przecinku ID wszystkich ról, które mają widzieć tickety):
STAFF_ROLE_IDS = [1550979082345250876, 1550978209103880354, 1550978922831810701, 1552362361032015982]  
# ==========================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# System Anty-link (max 3 linki w 10 min)
user_links = defaultdict(lambda: deque())


# --- 1. TICKET SYSTEM ---

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Dołączenie do klanu", description="Chcesz dołączyć do naszego klanu?", emoji="⚔️"),
            discord.SelectOption(label="Składki", description="Pytania lub sprawy związane ze składkami", emoji="💰"),
            discord.SelectOption(label="Pytanie", description="Masz ogólne pytanie?", emoji="❓"),
            discord.SelectOption(label="Inne", description="Inne sprawy", emoji="📁"),
        ]
        super().__init__(placeholder="Wybierz kategorię zgłoszenia...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        category_name = self.values[0]
        guild = interaction.guild
        user = interaction.user

        # Domyślne uprawnienia do kanału
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # Nadawanie uprawnień wszystkim wskazanym rolom
        for role_id in STAFF_ROLE_IDS:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel_name = f"ticket-{user.name}".lower().replace(" ", "-")
        ticket_channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites)

        embed = discord.Embed(
            title=f"🎫 Zgłoszenie: {category_name}",
            description=f"Witaj {user.mention}!\nOpisz swój problem lub sprawę. Administracja odpowie najszybciej jak to możliwe.",
            color=discord.Color.blue()
        )
        embed.set_image(url=IMAGE_URL) # Obrazek z kaczką[cite: 3]
        
        await ticket_channel.send(embed=embed, view=TicketControlView())
        await interaction.response.send_message(f"Twój ticket został utworzony: {ticket_channel.mention}", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Przejmij Ticket ✋", style=discord.ButtonStyle.primary, custom_id="claim_ticket")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Sprawdzanie czy użytkownik posiada którąkolwiek z dozwolonych ról lub jest administratorem
        user_role_ids = [role.id for role in interaction.user.roles]
        has_permission = any(role_id in user_role_ids for role_id in STAFF_ROLE_IDS) or interaction.user.guild_permissions.administrator

        if not has_permission:
            await interaction.response.send_message("Nie masz uprawnień do przejęcia tego ticketu!", ephemeral=True)
            return

        embed = discord.Embed(
            description=f"✋ Ticket został przejęty przez: {interaction.user.mention}",
            color=discord.Color.green()
        )
        button.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label="Zamknij Ticket 🔒", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Kanał zostanie usunięty za 5 sekund...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

@bot.tree.command(name="setup_ticket", description="Wysyła panel ticketów na kanał")
@app_commands.checks.has_permissions(administrator=True)
async def setup_ticket(interaction: discord.Interaction):
    embed = discord.Embed(
        title="CENTRUM POMOCY / TICKET",
        description="Wybierz opcję z poniższego menu, aby otworzyć prywatny kanał z administracją.",
        color=discord.Color.green()
    )
    embed.set_image(url=IMAGE_URL) # Obrazek z kaczką[cite: 3]
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("Panel ticket został wysłany!", ephemeral=True)


# --- 2. POWITANIA (Z POLSKIMI ZNAKAMI I OBRAZKIEM) ---

@bot.event
async def on_member_join(member: discord.Member):
    welcome_channel = discord.utils.get(member.guild.text_channels, name="powitania")
    if not welcome_channel:
        welcome_channel = member.guild.system_channel

    if welcome_channel:
        embed = discord.Embed(
            title="Nowy członek serwera!",
            description=f"Siema {member.mention}, dobrze że jesteś.",
            color=discord.Color.gold()
        )
        embed.set_image(url=IMAGE_URL) # Obrazek z kaczką[cite: 3]
        await welcome_channel.send(content=f"Siema {member.mention}, dobrze że jesteś.", embed=embed)


# --- 3. KOMENDA /CLEAR ---

@bot.tree.command(name="clear", description="Usuwa określoną ilość wiadomości")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, ilosc: int):
    if ilosc <= 0:
        await interaction.response.send_message("Podaj liczbę większą niż 0!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=ilosc)
    await interaction.followup.send(f"Usunięto `{len(deleted)}` wiadomości.", ephemeral=True)


# --- 4. PANEL KONKURSÓW (GIVEAWAY) ---

@bot.tree.command(name="konkurs", description="Stwórz nowy konkurs")
@app_commands.checks.has_permissions(administrator=True)
async def konkurs(interaction: discord.Interaction, nagroda: str, czas_minut: int, ilosc_wygranych: int):
    embed = discord.Embed(
        title=f"🎉 KONKURS: {nagroda}",
        description=f"Kliknij przycisk poniżej, aby dołączyć!\n\n**Wygranych:** {ilosc_wygranych}\n**Czas:** {czas_minut} min.",
        color=discord.Color.purple()
    )
    embed.set_image(url=IMAGE_URL) # Obrazek z kaczką[cite: 3]

    participants = []

    class GiveawayView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=czas_minut * 60)

        @discord.ui.button(label="Dołącz do konkursu 🎉", style=discord.ButtonStyle.success)
        async def join(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user in participants:
                await button_interaction.response.send_message("Już bierzesz udział w tym konkursie!", ephemeral=True)
            else:
                participants.append(button_interaction.user)
                await button_interaction.response.send_message("Pomyślnie dołączono do konkursu!", ephemeral=True)

    await interaction.response.send_message("Konkurs wystartował!", ephemeral=True)
    await interaction.channel.send(embed=embed, view=GiveawayView())

    await asyncio.sleep(czas_minut * 60)

    if not participants:
        await interaction.channel.send(f"Konkurs na **{nagroda}** zakończony! Nikt nie wziął udziału.")
    else:
        winners = random.sample(participants, min(len(participants), ilosc_wygranych))
        winners_mentions = ", ".join([w.mention for w in winners])
        await interaction.channel.send(f"🎉 Gratulacje {winners_mentions}! Wygraliście **{nagroda}**!")


# --- 5. ANTY-LINK (Max 3 linki / 10 minut, 4. link = timeout 10 min) ---

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if "http://" in message.content or "https://" in message.content: