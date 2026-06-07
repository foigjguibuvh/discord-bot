# main.py
# Discord Radio Bot (Pycord)
# v7 - Fixed

import discord
from discord.ext import commands
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

RADIO_CATEGORY_ID = 1512840439638528061
TEXT_CHANNEL_ID = 1512842208091443270
ZERO_HZ_CHANNEL_ID = 1512955973202087936

POLICE_ROLE_ID = 1512956243046564022
EMS_ROLE_ID = 1512956510311944343
JUSTICE_ROLE_ID = 1512956334641778708

GOV_CHANNELS = {
    "1": 1512956869268996278,
    "2": 1512957001750151179,
    "3": 1512956927502717069,
    "4": 1512956951909105674,
    "5": 1512956977569992874,
    "6": 1512957001750151179,
    "7": 1512957025611546835,
    "8": 1512957048328032267,
    "9": 1512957068603166931,
    "10": 1512957095962611763,
}

GOV_POLICE = ["1", "2", "3", "4"]
GOV_EMS = ["5", "6"]
GOV_JUSTICE = ["7", "8", "9", "10"]

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# { channel_id: { "commander": member_id, "locked": bool, "queue": [member_id] } }
channel_data = {}

def has_role(member, role_id):
    return any(r.id == role_id for r in member.roles)

# ===== Commander Panel =====

class CommanderPanel(discord.ui.View):
    def __init__(self, channel_id):
        super().__init__(timeout=None)
        self.channel_id = channel_id

    @discord.ui.button(label="قفل الموجة", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="lock_channel")
    async def lock_channel(self, button, interaction):
        data = channel_data.get(self.channel_id)
        if not data or interaction.user.id != data["commander"]:
            await interaction.response.send_message("أنت لست قائد هذه الموجة.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(self.channel_id)
        if channel is None:
            await interaction.response.send_message("الموجة غير موجودة.", ephemeral=True)
            return

        if data["locked"]:
            await channel.set_permissions(interaction.guild.default_role, connect=True)
            data["locked"] = False
            button.label = "قفل الموجة"
            button.emoji = "🔒"
            button.style = discord.ButtonStyle.danger
            await interaction.response.edit_message(content="✅ تم **فتح** الموجة. 🔓", view=self)
        else:
            await channel.set_permissions(interaction.guild.default_role, connect=False)
            for member in channel.members:
                await channel.set_permissions(member, connect=True)
            data["locked"] = True
            button.label = "فتح الموجة"
            button.emoji = "🔓"
            button.style = discord.ButtonStyle.success
            await interaction.response.edit_message(content="🔒 تم **قفل** الموجة.", view=self)

    @discord.ui.button(label="طرد عضو", emoji="👢", style=discord.ButtonStyle.secondary, custom_id="kick_member")
    async def kick_member(self, button, interaction):
        data = channel_data.get(self.channel_id)
        if not data or interaction.user.id != data["commander"]:
            await interaction.response.send_message("أنت لست قائد هذه الموجة.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(self.channel_id)
        members = [m for m in channel.members if m.id != interaction.user.id]

        if not members:
            await interaction.response.send_message("لا يوجد أعضاء لطردهم.", ephemeral=True)
            return

        options = [discord.SelectOption(label=m.display_name, value=str(m.id)) for m in members]
        view = KickSelectView(self.channel_id, options)
        await interaction.response.send_message("اختر العضو الذي تريد طرده:", view=view, ephemeral=True)

    @discord.ui.button(label="نقل القيادة", emoji="📢", style=discord.ButtonStyle.primary, custom_id="transfer_command")
    async def transfer_command(self, button, interaction):
        data = channel_data.get(self.channel_id)
        if not data or interaction.user.id != data["commander"]:
            await interaction.response.send_message("أنت لست قائد هذه الموجة.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(self.channel_id)
        members = [m for m in channel.members if m.id != interaction.user.id]

        if not members:
            await interaction.response.send_message("لا يوجد أعضاء لنقل القيادة إليهم.", ephemeral=True)
            return

        options = [discord.SelectOption(label=m.display_name, value=str(m.id)) for m in members]
        view = TransferSelectView(self.channel_id, options)
        await interaction.response.send_message("اختر العضو الذي ستنقل إليه القيادة:", view=view, ephemeral=True)


class KickSelectView(discord.ui.View):
    def __init__(self, channel_id, options):
        super().__init__(timeout=30)
        self.channel_id = channel_id
        select = discord.ui.Select(placeholder="اختر عضو...", options=options)
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        member_id = int(self.children[0].values[0])
        channel = interaction.guild.get_channel(self.channel_id)
        member = interaction.guild.get_member(member_id)
        if member and member.voice and member.voice.channel.id == self.channel_id:
            await member.move_to(None)
            await interaction.response.send_message(f"✅ تم طرد {member.display_name} من الموجة.", ephemeral=True)
        else:
            await interaction.response.send_message("العضو لم يعد في الموجة.", ephemeral=True)


class TransferSelectView(discord.ui.View):
    def __init__(self, channel_id, options):
        super().__init__(timeout=30)
        self.channel_id = channel_id
        select = discord.ui.Select(placeholder="اختر عضو...", options=options)
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        member_id = int(self.children[0].values[0])
        data = channel_data.get(self.channel_id)
        if data:
            data["commander"] = member_id
            member = interaction.guild.get_member(member_id)
            await interaction.response.send_message(f"✅ تم نقل القيادة إلى {member.display_name}.", ephemeral=True)
            panel_view = CommanderPanel(self.channel_id)
            try:
                await member.send("👑 أنت الآن قائد الموجة! استخدم الأزرار للتحكم:", view=panel_view)
            except:
                pass


# ===== Radio Modal & View =====

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
            await interaction.response.send_message("يجب أن تكون داخل 0 Hz أولاً.", ephemeral=True)
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

        if f == int(f):
            freq = str(int(f))

        if freq in GOV_CHANNELS:
            if freq in GOV_POLICE:
                if not has_role(member, POLICE_ROLE_ID):
                    await interaction.response.send_message("🚫 موجة الشرطة فقط.", ephemeral=True)
                    return
            elif freq in GOV_EMS:
                if not has_role(member, EMS_ROLE_ID):
                    await interaction.response.send_message("🚫 موجة الإسعاف فقط.", ephemeral=True)
                    return
            elif freq in GOV_JUSTICE:
                if not has_role(member, JUSTICE_ROLE_ID):
                    await interaction.response.send_message("🚫 موجة العدل فقط.", ephemeral=True)
                    return

            channel = interaction.guild.get_channel(GOV_CHANNELS[freq])
            if channel is None:
                await interaction.response.send_message("القناة غير موجودة.", ephemeral=True)
                return
            await member.move_to(channel)
            await interaction.response.send_message(f"✅ تم الاتصال بالموجة {freq}", ephemeral=True)
            return

        category = interaction.guild.get_channel(RADIO_CATEGORY_ID)
        room_name = f"📻 {freq}"
        voice = discord.utils.get(category.voice_channels, name=room_name)

        if voice and voice.id in channel_data and channel_data[voice.id]["locked"]:
            await interaction.response.send_message("🔒 هذه الموجة مقفولة.", ephemeral=True)
            return

        if voice is None:
            voice = await interaction.guild.create_voice_channel(room_name, category=category)

        await member.move_to(voice)
        await interaction.response.send_message(f"✅ تم الاتصال بالموجة {freq}", ephemeral=True)


class RadioView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Connect", style=discord.ButtonStyle.primary, custom_id="radio_connect")
    async def connect_button(self, button, interaction):
        await interaction.response.send_modal(FrequencyModal())


@bot.command()
async def radio(ctx):
    if ctx.author.id != ctx.guild.owner_id:
        return
    embed = discord.Embed(title="📻 Radio", description="اضغط Connect للاتصال بالموجة.", color=0x2b2d31)
    await ctx.send(embed=embed, view=RadioView())


# ===== Events =====

@bot.event
async def on_ready():
    bot.add_view(RadioView())
    await bot.change_presence(activity=discord.Game(name="Powered By FTRP ."))
    print(f"Bot is online: {bot.user}")


@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel and after.channel.name.startswith("📻 "):
        ch_id = after.channel.id
        if ch_id not in channel_data:
            channel_data[ch_id] = {
                "commander": member.id,
                "locked": False,
                "queue": [member.id]
            }
            panel_view = CommanderPanel(ch_id)
            try:
                await member.send("👑 أنت قائد هذه الموجة! استخدم الأزرار للتحكم:", view=panel_view)
            except:
                pass
        else:
            if member.id not in channel_data[ch_id]["queue"]:
                channel_data[ch_id]["queue"].append(member.id)

    if before.channel and before.channel.name.startswith("📻 "):
        ch_id = before.channel.id

        if len(before.channel.members) == 0:
            channel_data.pop(ch_id, None)
            try:
                await before.channel.delete()
            except:
                pass
            return

        if ch_id in channel_data:
            data = channel_data[ch_id]
            if member.id in data["queue"]:
                data["queue"].remove(member.id)

            if data["commander"] == member.id:
                if data["queue"]:
                    new_commander_id = data["queue"][0]
                    data["commander"] = new_commander_id
                    new_commander = before.channel.guild.get_member(new_commander_id)
                    if new_commander:
                        panel_view = CommanderPanel(ch_id)
                        try:
                            await new_commander.send("👑 أنت الآن قائد الموجة!", view=panel_view)
                        except:
                            pass

            if data.get("locked"):
                try:
                    await before.channel.set_permissions(member, overwrite=None)
                except:
                    pass


bot.run(BOT_TOKEN)
