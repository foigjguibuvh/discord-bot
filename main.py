# main.py
# Discord Radio Bot (Pycord) v8
# Admin Panel via text channel

import discord
from discord.ext import commands
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

RADIO_CATEGORY_ID = 1513116461177241722
TEXT_CHANNEL_ID = 1513116719793569862
ZERO_HZ_CHANNEL_ID = 1513117560319770624
ADMIN_PANEL_CHANNEL_ID = 1513008587704897578
LOG_CHANNEL_ID = 1517132779207528501
ADMIN_ROLE_ID = 1347259726227964015

POLICE_ROLE_ID = 1346799169213304913
EMS_ROLE_ID = 1346796797292707891
JUSTICE_ROLE_ID = 1346798143618154566

GOV_CHANNELS = {
    "1": 1513118346629877840,
    "2": 1513118381761495261,
    "3": 1513118426455867402,
    "4": 1513118459859566592,
    "5": 1513118495443783841,
    "6": 1513118527924469841,
    "7": 1513118558526373958,
    "8": 1513118613710573710,
    "9": 1513118651845312593,
    "10": 1513118713392664687,
}

GOV_POLICE = ["1", "2", "3", "4", "5", "6", "7"]
GOV_EMS = ["8"]
GOV_JUSTICE = ["9"]
GOV_SHARED = ["10"]  # مشتركة بين الثلاثة

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

channel_data = {}
banned_members = set()  # أعضاء محظورون من الراديو

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

    @discord.ui.select(
        placeholder="اختر الإجراء المطلوب...",
        custom_id="admin_main_select",
        options=[
            discord.SelectOption(label="الموجات النشطة", emoji="📋", value="list"),
            discord.SelectOption(label="قفل موجة", emoji="🔒", value="lock"),
            discord.SelectOption(label="قفل كل الموجات", emoji="🔐", value="lockall"),
            discord.SelectOption(label="إسكات موجة", emoji="🔇", value="mute"),
            discord.SelectOption(label="نقل عضو", emoji="↗️", value="move"),
            discord.SelectOption(label="حظر من الراديو", emoji="🚫", value="ban"),
            discord.SelectOption(label="رسالة إذاعية", emoji="📢", value="broadcast"),
            discord.SelectOption(label="طرد عضو", emoji="👢", value="kick"),
            discord.SelectOption(label="تفريغ موجة", emoji="🗑️", value="clear"),
        ]
    )
    async def select_action(self, select, interaction):
        action = select.values[0]

        if action == "list":
            rows = get_active_channels(interaction.guild)
            embed = discord.Embed(title="📋 الموجات النشطة", description="\n".join(rows), color=0x5865f2)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if action == "lock":
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
            return

        if action == "lockall":
            if not channel_data:
                await interaction.response.send_message("لا توجد موجات نشطة.", ephemeral=True)
                return
            count = 0
            for ch_id, data in channel_data.items():
                channel = interaction.guild.get_channel(ch_id)
                if channel and not data["locked"]:
                    await channel.set_permissions(interaction.guild.default_role, connect=False)
                    for m in channel.members:
                        await channel.set_permissions(m, connect=True)
                    data["locked"] = True
                    count += 1
            await interaction.response.send_message(f"🔐 تم قفل {count} موجة.", ephemeral=True)
            return

        if action == "mute":
            if not channel_data:
                await interaction.response.send_message("لا توجد موجات نشطة.", ephemeral=True)
                return
            options = []
            for ch_id in channel_data:
                channel = interaction.guild.get_channel(ch_id)
                if channel and channel.members:
                    options.append(discord.SelectOption(label=channel.name, value=str(ch_id)))
            if not options:
                await interaction.response.send_message("لا يوجد أعضاء في الموجات.", ephemeral=True)
                return
            view = AdminMuteSelect(options)
            await interaction.response.send_message("اختر الموجة للإسكات:", view=view, ephemeral=True)
            return

        if action == "move":
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
                            value=f"{m.id}"
                        ))
            if not options:
                await interaction.response.send_message("لا يوجد أعضاء.", ephemeral=True)
                return
            view = AdminMoveSelect(options, interaction.guild)
            await interaction.response.send_message("اختر العضو للنقل:", view=view, ephemeral=True)
            return

        if action == "ban":
            options = []
            seen = set()
            for ch_id in channel_data:
                channel = interaction.guild.get_channel(ch_id)
                if channel:
                    for m in channel.members:
                        if m.id not in seen:
                            seen.add(m.id)
                            status = "🚫" if m.id in banned_members else "✅"
                            options.append(discord.SelectOption(label=f"{status} {m.display_name}", value=str(m.id)))
            if not options:
                await interaction.response.send_message("لا يوجد أعضاء في الموجات حالياً.", ephemeral=True)
                return
            view = AdminBanSelect(options)
            await interaction.response.send_message("اختر العضو للحظر/رفع الحظر:", view=view, ephemeral=True)
            return

        if action == "broadcast":
            await interaction.response.send_modal(BroadcastModal())
            return

        if action == "kick":
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
            return

        if action == "clear":
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
            return


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



# ===== Personal Commander Panel =====

class PersonalCommanderPanel(discord.ui.View):
    def __init__(self, channel_id):
        super().__init__(timeout=120)
        self.channel_id = channel_id

    @discord.ui.button(label="فتح/قفل الموجة", emoji="🔒", style=discord.ButtonStyle.danger)
    async def toggle_lock(self, button, interaction):
        if interaction.user.id != channel_data.get(self.channel_id, {}).get("commander"):
            await interaction.response.send_message("❌ هذه اللوحة ليست لك.", ephemeral=True)
            return
        data = channel_data.get(self.channel_id)
        channel = interaction.guild.get_channel(self.channel_id)
        if not data or not channel:
            await interaction.response.send_message("الموجة غير موجودة.", ephemeral=True)
            return
        if data["locked"]:
            await channel.set_permissions(interaction.guild.default_role, connect=True)
            data["locked"] = False
            await interaction.response.send_message("✅ تم **فتح** الموجة. 🔓", ephemeral=True)
        else:
            await channel.set_permissions(interaction.guild.default_role, connect=False)
            for m in channel.members:
                await channel.set_permissions(m, connect=True)
            data["locked"] = True
            await interaction.response.send_message("🔒 تم **قفل** الموجة.", ephemeral=True)

    @discord.ui.button(label="طرد عضو", emoji="👢", style=discord.ButtonStyle.secondary)
    async def kick_member(self, button, interaction):
        if interaction.user.id != channel_data.get(self.channel_id, {}).get("commander"):
            await interaction.response.send_message("❌ هذه اللوحة ليست لك.", ephemeral=True)
            return
        channel = interaction.guild.get_channel(self.channel_id)
        members = [m for m in channel.members if m.id != interaction.user.id]
        if not members:
            await interaction.response.send_message("لا يوجد أعضاء لطردهم.", ephemeral=True)
            return
        options = [discord.SelectOption(label=m.display_name, value=str(m.id)) for m in members]
        view = KickSelectView(self.channel_id, options)
        await interaction.response.send_message("اختر العضو:", view=view, ephemeral=True)

    @discord.ui.button(label="نقل القيادة", emoji="📢", style=discord.ButtonStyle.primary)
    async def transfer(self, button, interaction):
        if interaction.user.id != channel_data.get(self.channel_id, {}).get("commander"):
            await interaction.response.send_message("❌ هذه اللوحة ليست لك.", ephemeral=True)
            return
        channel = interaction.guild.get_channel(self.channel_id)
        members = [m for m in channel.members if m.id != interaction.user.id]
        if not members:
            await interaction.response.send_message("لا يوجد أعضاء.", ephemeral=True)
            return
        options = [discord.SelectOption(label=m.display_name, value=str(m.id)) for m in members]
        view = TransferSelectView(self.channel_id, options)
        await interaction.response.send_message("اختر العضو:", view=view, ephemeral=True)


class AdminMuteSelect(discord.ui.View):
    def __init__(self, options):
        super().__init__(timeout=30)
        select = discord.ui.Select(placeholder="اختر موجة...", options=options)
        select.callback = self.callback
        self.add_item(select)

    async def callback(self, interaction: discord.Interaction):
        ch_id = int(self.children[0].values[0])
        channel = interaction.guild.get_channel(ch_id)
        if channel:
            count = 0
            for m in channel.members:
                try:
                    await m.edit(mute=True)
                    count += 1
                except:
                    pass
            await interaction.response.send_message(f"🔇 تم إسكات {count} عضو في {channel.name}", ephemeral=True)
        else:
            await interaction.response.send_message("الموجة غير موجودة.", ephemeral=True)


class AdminMoveSelect(discord.ui.View):
    def __init__(self, options, guild):
        super().__init__(timeout=60)
        self.guild = guild
        self.selected_member_id = None
        select = discord.ui.Select(placeholder="اختر عضو...", options=options)
        select.callback = self.member_callback
        self.add_item(select)

    async def member_callback(self, interaction: discord.Interaction):
        self.selected_member_id = int(self.children[0].values[0])
        # عرض قائمة الموجات للنقل إليها
        options = []
        for ch_id in channel_data:
            channel = self.guild.get_channel(ch_id)
            if channel:
                options.append(discord.SelectOption(label=channel.name, value=str(ch_id)))
        if not options:
            await interaction.response.send_message("لا توجد موجات للنقل إليها.", ephemeral=True)
            return
        view = AdminMoveDestSelect(self.selected_member_id, options)
        await interaction.response.send_message("اختر الموجة للنقل إليها:", view=view, ephemeral=True)


class AdminMoveDestSelect(discord.ui.View):
    def __init__(self, member_id, options):
        super().__init__(timeout=30)
        self.member_id = member_id
        select = discord.ui.Select(placeholder="اختر موجة...", options=options)
        select.callback = self.callback
        self.add_item(select)

    async def callback(self, interaction: discord.Interaction):
        ch_id = int(self.children[0].values[0])
        channel = interaction.guild.get_channel(ch_id)
        member = interaction.guild.get_member(self.member_id)
        if member and channel:
            await member.move_to(channel)
            await interaction.response.send_message(f"✅ تم نقل {member.display_name} إلى {channel.name}", ephemeral=True)
        else:
            await interaction.response.send_message("حدث خطأ.", ephemeral=True)


class AdminBanSelect(discord.ui.View):
    def __init__(self, options):
        super().__init__(timeout=30)
        select = discord.ui.Select(placeholder="اختر عضو...", options=options)
        select.callback = self.callback
        self.add_item(select)

    async def callback(self, interaction: discord.Interaction):
        member_id = int(self.children[0].values[0])
        member = interaction.guild.get_member(member_id)
        if member_id in banned_members:
            banned_members.remove(member_id)
            await interaction.response.send_message(f"✅ تم رفع الحظر عن {member.display_name if member else member_id}", ephemeral=True)
        else:
            banned_members.add(member_id)
            if member and member.voice:
                await member.move_to(None)
            await interaction.response.send_message(f"🚫 تم حظر {member.display_name if member else member_id} من الراديو", ephemeral=True)


class BroadcastModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="رسالة إذاعية")
        self.add_item(discord.ui.InputText(label="الرسالة", placeholder="اكتب رسالتك هنا...", required=True, style=discord.InputTextStyle.paragraph))

    async def callback(self, interaction: discord.Interaction):
        message = self.children[0].value
        text_channel = interaction.guild.get_channel(TEXT_CHANNEL_ID)
        if text_channel:
            embed = discord.Embed(title="📢 رسالة إذاعية", description=message, color=0xff0000)
            embed.set_footer(text=f"من: {interaction.user.display_name}")
            await text_channel.send(embed=embed)
        await interaction.response.send_message("✅ تم إرسال الرسالة الإذاعية.", ephemeral=True)

# ===== Radio Modal & View =====

class FrequencyModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Radio Frequency")
        self.add_item(discord.ui.InputText(label="Frequency", placeholder="99.1", required=True))

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user

        if member.id in banned_members:
            await interaction.response.send_message("🚫 أنت محظور من استخدام الراديو.", ephemeral=True)
            return

        if not member.voice or member.voice.channel.id != ZERO_HZ_CHANNEL_ID:
            await interaction.response.send_message("يجب أن تكون داخل 0 Hz أولاً. https://discord.gg/Neh9m2SHAM", ephemeral=True)
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
                    await interaction.response.send_message("🔐 هذه الموجة مشفرة.", ephemeral=True)
                    return
            elif freq in GOV_EMS:
                if not has_role(member, EMS_ROLE_ID):
                    await interaction.response.send_message("🔐 هذه الموجة مشفرة.", ephemeral=True)
                    return
            elif freq in GOV_JUSTICE:
                if not has_role(member, JUSTICE_ROLE_ID):
                    await interaction.response.send_message("🔐 هذه الموجة مشفرة.", ephemeral=True)
                    return
            elif freq in GOV_SHARED:
                if not (has_role(member, POLICE_ROLE_ID) or has_role(member, EMS_ROLE_ID) or has_role(member, JUSTICE_ROLE_ID)):
                    await interaction.response.send_message("🔐 هذه الموجة مشفرة.", ephemeral=True)
                    return

            channel = interaction.guild.get_channel(GOV_CHANNELS[freq])
            if channel is None:
                await interaction.response.send_message("القناة غير موجودة.", ephemeral=True)
                return
            await member.move_to(channel)
            await interaction.response.send_message(f"🔘 تـم الأتــصـال بـالـمـوجـة {channel.name}", ephemeral=True)
            return

        category = interaction.guild.get_channel(RADIO_CATEGORY_ID)
        room_name = f"🔘 | Hz {freq}"
        voice = discord.utils.get(category.voice_channels, name=room_name)

        if voice and voice.id in channel_data and channel_data[voice.id]["locked"]:
            await interaction.response.send_message("🔒 هذه الموجة مقفولة.", ephemeral=True)
            return

        if voice is None:
            voice = await interaction.guild.create_voice_channel(room_name, category=category)

        await member.move_to(voice)
        await interaction.response.send_message(f"🔘 تـم الأتــصـال بـالـمـوجـة {freq}", ephemeral=True)


class RadioView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Connect", style=discord.ButtonStyle.primary, custom_id="radio_connect")
    async def connect_button(self, button, interaction):
        await interaction.response.send_modal(FrequencyModal())


# ===== Commands =====

@bot.command()
async def radio(ctx):
    if not has_role(ctx.author, ADMIN_ROLE_ID):
        return
    embed = discord.Embed(title="FTRP -- RP Radio .", description="من 1 الى 10 ,, موجات حكومية", color=0x5865f2)
    embed.set_image(url="attachment://radio.png")
    file = discord.File("radio.png", filename="radio.png")
    await ctx.send(embed=embed, view=RadioView(), file=file)

@bot.command()
async def ad(ctx):
    if not has_role(ctx.author, ADMIN_ROLE_ID):
        return
    await ctx.message.delete()
    embed = discord.Embed(title="🎛️ لوحة تحكم الراديو", description="اختر الإجراء المطلوب:", color=0x5865f2)
    await ctx.send(embed=embed, view=AdminPanel())


# ===== Events =====

@bot.event
async def on_ready():
    bot.add_view(RadioView())
    bot.add_view(AdminPanel())
    await bot.change_presence(activity=discord.Game(name="Powered By FTRP ."))
    print(f"Bot is online: {bot.user}")


def is_radio_channel(channel):
    if channel is None:
        return False
    if channel.name.startswith("🔘 | Hz"):
        return True
    if channel.id in GOV_CHANNELS.values():
        return True
    if channel.id == ZERO_HZ_CHANNEL_ID:
        return True
    return False

async def send_log(guild, member, channel, action):
    log_channel = guild.get_channel(LOG_CHANNEL_ID)
    if not log_channel:
        return
    emoji = "📥" if action == "دخل" else "📤"
    embed = discord.Embed(
        description=f"{emoji} **{member.display_name}** {action} **{channel.name}**",
        color=0x2ecc71 if action == "دخل" else 0xe74c3c
    )
    embed.set_footer(text=f"ID: {member.id}")
    embed.timestamp = discord.utils.utcnow()
    try:
        await log_channel.send(embed=embed)
    except:
        pass


@bot.event
async def on_voice_state_update(member, before, after):
    # تسجيل الدخول
    if is_radio_channel(after.channel) and before.channel != after.channel:
        await send_log(member.guild, member, after.channel, "دخل")

    # تسجيل الخروج
    if is_radio_channel(before.channel) and before.channel != after.channel:
        await send_log(member.guild, member, before.channel, "خرج من")

    if after.channel and after.channel.name.startswith("🔘 | Hz"):
        ch_id = after.channel.id
        if ch_id not in channel_data:
            channel_data[ch_id] = {"commander": member.id, "locked": False, "queue": [member.id]}
        else:
            if member.id not in channel_data[ch_id]["queue"]:
                channel_data[ch_id]["queue"].append(member.id)

    if before.channel and before.channel.name.startswith("🔘 | Hz"):
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
