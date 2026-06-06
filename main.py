# main.py
# Discord Radio Bot (Pycord)
# Fill BOT_TOKEN before running.

import discord
from discord.ext import commands

import os
BOT_TOKEN = os.getenv("BOT_TOKEN")

RADIO_CATEGORY_ID = 1512889116230946938
TEXT_CHANNEL_ID = 1512897164693733386
ZERO_HZ_CHANNEL_ID = 1512889116230946941

POLICE_ROLE_ID = 1512897922465796166
EMS_ROLE_ID = 1512897943861067836
JUSTICE_ROLE_ID = 1512897985707507732

GOV_CHANNELS = {
    "1": 1512897146175885523,
    "2": 1512897199414186134,
    "3": 1512897223149617182,
    "4": 1512897242745405520,
    "5": 1512897257421148300,
    "6": 1512897280431230992,
    "7": 1512897300081545317,
    "8": 1512897314962936129,
    "9": 1512897333551956140,
    "10": 1512897353353265342,
}

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

def has_role(member, role_id):
    return any(r.id == role_id for r in member.roles)

class FrequencyModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Radio Frequency")
        self.add_item(
            discord.ui.InputText(
                label="Frequency",
                placeholder="99.1",
                required=True
            )
        )

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user

        if not member.voice or member.voice.channel.id != ZERO_HZ_CHANNEL_ID:
            await interaction.response.send_message(
                "يجب أن تكون داخل 0 Hz أولاً.",
                ephemeral=True
            )
            return

        freq = self.children[0].value.strip()

        try:
            f = float(freq)
        except:
            await interaction.response.send_message("تردد غير صالح.", ephemeral=True)
            return

        if f <= 0 or f > 999.9:
            await interaction.response.send_message("التردد يجب أن يكون بين 0.1 و 999.9", ephemeral=True)
            return

        if freq in GOV_CHANNELS:
            if freq in ["1","2","3","4","5","6","7"]:
                if not has_role(member, POLICE_ROLE_ID):
                    await interaction.response.send_message("موجة الشرطة فقط.", ephemeral=True)
                    return

            elif freq == "8":
                if not has_role(member, EMS_ROLE_ID):
                    await interaction.response.send_message("موجة الإسعاف فقط.", ephemeral=True)
                    return

            elif freq == "9":
                if not has_role(member, JUSTICE_ROLE_ID):
                    await interaction.response.send_message("موجة العدل فقط.", ephemeral=True)
                    return

            elif freq == "10":
                if not (
                    has_role(member, POLICE_ROLE_ID)
                    or has_role(member, EMS_ROLE_ID)
                    or has_role(member, JUSTICE_ROLE_ID)
                ):
                    await interaction.response.send_message("ليست لديك صلاحية.", ephemeral=True)
                    return

            channel = interaction.guild.get_channel(GOV_CHANNELS[freq])
            await member.move_to(channel)
            await interaction.response.send_message(f"تم الاتصال بالموجة {freq}", ephemeral=True)
            return

        category = interaction.guild.get_channel(RADIO_CATEGORY_ID)
        room_name = f"📻 {freq}"

        voice = discord.utils.get(category.voice_channels, name=room_name)

        if voice is None:
            voice = await interaction.guild.create_voice_channel(
                room_name,
                category=category
            )

        await member.move_to(voice)
        await interaction.response.send_message(
            f"تم الاتصال بالموجة {freq}",
            ephemeral=True
        )

class RadioView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Connect", style=discord.ButtonStyle.primary)
    async def connect_button(self, button, interaction):
        await interaction.response.send_modal(FrequencyModal())

@bot.command()
async def radio(ctx):
    if ctx.author.id != ctx.guild.owner_id:
        return

    embed = discord.Embed(title="Radio", description="اضغط Connect للاتصال.")
    embed.set_image(url="attachment://radio.png")

    file = discord.File("radio.png", filename="radio.png")

    await ctx.send(embed=embed, view=RadioView(), file=file)

@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel is None:
        return

    name = before.channel.name

    if not name.startswith("📻 "):
        return

    if len(before.channel.members) != 0:
        return

    await before.channel.delete()

bot.run(BOT_TOKEN)
