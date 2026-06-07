# main.py
# Discord Radio Bot (Pycord) v8
# Admin Panel via text channel

import discord
from discord.ext import commands
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

RADIO_CATEGORY_ID = 1512840439638528061
TEXT_CHANNEL_ID = 1512842208091443270
ZERO_HZ_CHANNEL_ID = 1512955973202087936
ADMIN_PANEL_CHANNEL_ID = 1513008587704897578

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

channel_data = {}

def has_role(member, role_id):
    return any(r.id == role_id for r in member.roles)

def get_active_channels(guild):
    rows = []
    for ch_id, data in channel_data.items():
        channel = guild.get_channel(ch_id)
        if channel:
            commander = guild.get_member(data["commander"])
            locked = "🔒" if data["locked"] else "🔓"
            members = len(channel.members)
            commander_name = commander.display_name if commander else "غير معروف"
            rows.append(f"{locked} **{channel.name}** | القائد: {commander_name} | الأعضاء: {members}")
    return rows if rows else ["لا توجد موجات نشطة حالياً."]

# ===== Admin Panel =====

class AdminPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="الموجات النشطة", emoji="📋", style=discord.ButtonStyle.primary, custom_id="admin_list")
    async def list_channels(self, button, interaction):
        rows = get_active_channels(interaction.guild)
        embed = discord.Embed(title="📋 الموجات النشطة", description="\n".join(rows), color=0x5865f2)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="قفل موجة", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="admin_lock")
    async def lock_channel(self, button, interaction):
        if not channel_data:
            await interaction.response.send_message("لا توجد موجات نشطة.", ephemeral=True)
            return
        options = []
        for ch_id, data in channel_data.items():
            channel = interaction.guild.get_channel(ch_id)
            if channel:
                locked = "🔒" if data["locked"] else "🔓"
                options.append(discord.SelectOption(label=f"{locked} {channel.name}", value=str(ch_id)))
        view = AdminLockSelect(options)
        await interaction.response.send_message("اختر الموجة:", view=view, ephemeral=True)

    @discord.ui.button(label="طرد عضو", emoji="👢", style=discord.ButtonStyle.secondary, custom_id="admin_kick")
    async def kick_member(self, button, interaction):
        if not channel_data:
            await interaction.response.send_message("لا توجد موجات نشطة.", ephemeral=True)
            return
        options = []
        for ch_id in channel_data:
            channel = interaction.guild.get_channel(ch_id)
            if channel:
                for m in channel.members:
                    options.append(discord.SelectOption(
                        label=f"{m.display_name} ({channel.name})",
                        value=f"{ch_id}:{m.id}"
                    ))
        if not options:
            await interaction.response.send_message("لا يوجد أعضاء في الموجات.", ephemeral=True)
            return
        view = AdminKickSelect(options)
        await interaction.response.send_message("اختر العضو:", view=view, ephemeral=True)

    @discord.ui.button(label="تفريغ موجة", emoji="🗑️", style=discord.ButtonStyle.danger, custom_id="admin_clear")
    async def clear_channel(self, button, interaction):
        if not channel_data:
            await interaction.response.send_message("لا توجد موجات نشطة.", ephemeral=True)
            return
        options = []
        for ch_id in channel_data:
            channel = interaction.guild.get_channel(ch_id)
            if channel:
                options.append(discord.SelectOption(label=channel.name, value=str(ch_id)))
        view = AdminClearSelect(options)
        await interaction.response.send_message("اختر الموجة للتفريغ:", view=view, ephemeral=True)


class AdminLockSelect(discord.ui.View):
    def __init__(self, options):
        super().__init__(timeout=30)
        select = discord.ui.Select(placeholder="اختر موجة...", options=options)
        select.callback = self.callback
        self.add_item(select)

    async def callback(self, interaction: discord.Interaction):
        ch_id = int(self.children[0].values[0])
        data = channel_data.get(ch_id)
        channel = interaction.guild.get_channel(ch_id)
        if not data or not channel:
            await interaction.response.send_message("الموجة غير موجودة.", ephemeral=True)
            return
        if data["locked"]:
            await channel.set_permissions(interaction.guild.default_role, connect=True)
            data["locked"] = False
            await interaction.response.send_message(f"✅ تم **فتح** {channel.name}", ephemeral=True)
        else:
            await channel.set_permissions(interaction.guild.default_role, connect=False)
            for m in channel.members:
                await channel.set_permissions(m, connect=True)
            data["locked"] = True
            await interaction.response.send_message(f"🔒 تم **قفل** {channel.name}", ephemeral=True)


class AdminKickSelect(discord.ui.View):
    def __init__(self, options):
        super().__init__(timeout=30)
        select = discord.ui.Select(placeholder="اختر عضو...", options=options)
        select.callback = self.callback
        self.add_item(select)

    async def callback(self, interaction: discord.Interaction):
        ch_id, member_id = self.children[0].values[0].split(":")
        member = interaction.guild.get_member(int(member_id))
        if member and member.voice:
            await member.move_to(None)
            await interaction.response.send_message(f"✅ تم طرد {member.display_name}", ephemeral=True)
        else:
            await interaction.response.send_message("العضو لم يعد في الموجة.", ephemeral=True)


class AdminClearSelect(discord.ui.View):
    def __init__(self, options):
        super().__init__(timeout=30)
        select = discord.ui.Select(placeholder="اختر موجة...", options=options)
        select.callback = self.callback
        self.add_item(select)

    async def callback(self, interaction: discord.Interaction):
        ch_id = int(self.children[0].values[0])
        channel = interaction.guild.get_channel(ch_id)
        if channel:
            for m in list(channel.members):
                await m.move_to(None)
            await interaction.response.send_message(f"✅ تم تفريغ {channel.name}", ephemeral=True)
        else:
            await interaction.response.send_message("الموجة غير موجودة.", ephemeral=True)


# ===== Radio Modal & View =====

class FrequencyModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Radio Frequency")
        self.add_item(discord.ui.InputText(label="Frequency", placeholder="99.1", required=True))

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


# ===== Commands =====

@bot.command()
async def radio(ctx):
    if ctx.author.id != ctx.guild.owner_id:
        return
    embed = discord.Embed(title="📻 Radio", description="اضغط Connect للاتصال بالموجة.", color=0x2b2d31)
    await ctx.send(embed=embed, view=RadioView())

@bot.command()
async def panel(ctx):
    # فقط في قناة الأدمن والمشرفين
    if ctx.channel.id != ADMIN_PANEL_CHANNEL_ID:
        return
    if not (ctx.author.guild_permissions.administrator or
            has_role(ctx.author, POLICE_ROLE_ID) or
            has_role(ctx.author, EMS_ROLE_ID) or
            has_role(ctx.author, JUSTICE_ROLE_ID)):
        return
    embed = discord.Embed(title="🎛️ لوحة تحكم الراديو", description="اختر الإجراء المطلوب:", color=0x5865f2)
    await ctx.send(embed=embed, view=AdminPanel())


# ===== Events =====

@bot.event
async def on_ready():
    bot.add_view(RadioView())
    bot.add_view(AdminPanel())
    await bot.change_presence(activity=discord.Game(name="Powered By FTRP ."))
    print(f"Bot is online: {bot.user}")


@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel and after.channel.name.startswith("📻 "):
        ch_id = after.channel.id
        if ch_id not in channel_data:
            channel_data[ch_id] = {"commander": member.id, "locked": False, "queue": [member.id]}
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
            if data["locked"]:
                try:
                    await before.channel.set_permissions(member, overwrite=None)
                except:
                    pass


bot.run(BOT_TOKEN)
