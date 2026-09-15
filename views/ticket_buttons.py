```python
import io
import discord
from discord.ui import View, Button

from db import (
    close_ticket,
    delete_ticket,
    set_claim,
    get_ticket_by_channel,
    get_guild_config,
)


class TicketButtonsView(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def create_transcript(self, channel):
        lines = []

        async for msg in channel.history(limit=None, oldest_first=True):
            timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            author = f"{msg.author.display_name} ({msg.author.id})"
            content = msg.content or "[No text content]"

            if msg.attachments:
                attachments = " | ".join(a.url for a in msg.attachments)
                content += f" | Attachments: {attachments}"

            lines.append(f"[{timestamp}] {author}: {content}")

        if not lines:
            lines.append("No messages found.")

        return "\n".join(lines)

    @discord.ui.button(
        label="Close",
        style=discord.ButtonStyle.red,
        custom_id="ticket_close",
    )
    async def close(self, interaction: discord.Interaction, button: discord.Button):
        row = get_ticket_by_channel(
            interaction.guild.id,
            interaction.channel.id,
        )

        if not row:
            await interaction.response.send_message(
                "Not a ticket channel.",
                ephemeral=True,
            )
            return

        t_id = row[0]
        close_ticket(t_id)

        await interaction.channel.send(
            embed=discord.Embed(
                description=f"Ticket closed by {interaction.user.mention}",
                color=discord.Color.red(),
            )
        )

        cfg = get_guild_config(interaction.guild.id)

        staff_role_id = cfg[3] if cfg else None
        staff_role = (
            interaction.guild.get_role(staff_role_id)
            if staff_role_id
            else None
        )

        creator = interaction.guild.get_member(row[3])

        if creator:
            await interaction.channel.set_permissions(
                creator,
                read_messages=True,
                send_messages=True,
            )

        if staff_role:
            await interaction.channel.set_permissions(
                staff_role,
                read_messages=True,
                send_messages=True,
            )

        transcript = await self.create_transcript(interaction.channel)

        log_channel_id = cfg[1] if cfg else None

        if log_channel_id:
            log_channel = interaction.guild.get_channel(log_channel_id)

            if log_channel:
                file = discord.File(
                    io.BytesIO(transcript.encode("utf-8")),
                    filename=f"ticket-{t_id}-transcript.txt",
                )

                await log_channel.send(
                    content=f"📄 Transcript for ticket `{t_id}`",
                    file=file,
                )

        await interaction.channel.edit(name=f"closed-{t_id}")

        await interaction.response.send_message(
            "Ticket closed.",
            ephemeral=True,
        )

    @discord.ui.button(
        label="Claim",
        style=discord.ButtonStyle.green,
        custom_id="ticket_claim",
    )
    async def claim(self, interaction: discord.Interaction, button: discord.Button):
        cfg = get_guild_config(interaction.guild.id)

        staff_role_id = cfg[3] if cfg else None
        staff_role = (
            interaction.guild.get_role(staff_role_id)
            if staff_role_id
            else None
        )

        if not staff_role or staff_role not in interaction.user.roles:
            await interaction.response.send_message(
                "You don't have permission.",
                ephemeral=True,
            )
            return

        row = get_ticket_by_channel(
            interaction.guild.id,
            interaction.channel.id,
        )

        if not row:
            await interaction.response.send_message(
                "Not a ticket channel.",
                ephemeral=True,
            )
            return

        set_claim(row[0], interaction.user.id)

        await interaction.response.send_message(
            f"Ticket claimed by {interaction.user.mention}",
            ephemeral=True,
        )

    @discord.ui.button(
        label="Transcript",
        style=discord.ButtonStyle.blurple,
        custom_id="ticket_transcript",
    )
    async def transcript(
        self,
        interaction: discord.Interaction,
        button: discord.Button,
    ):
        row = get_ticket_by_channel(
            interaction.guild.id,
            interaction.channel.id,
        )

        if not row:
            await interaction.response.send_message(
                "Not a ticket channel.",
                ephemeral=True,
            )
            return

        cfg = get_guild_config(interaction.guild.id)

        if not cfg:
            await interaction.response.send_message(
                "Ticket configuration was not found.",
                ephemeral=True,
            )
            return

        log_channel_id = cfg[1] if len(cfg) > 1 else None

        if not log_channel_id:
            await interaction.response.send_message(
                "No transcript/log channel is configured.",
                ephemeral=True,
            )
            return

        log_channel = interaction.guild.get_channel(log_channel_id)

        if not log_channel:
            await interaction.response.send_message(
                "The configured transcript/log channel no longer exists or I cannot access it.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        transcript = await self.create_transcript(interaction.channel)

        file = discord.File(
            io.BytesIO(transcript.encode("utf-8")),
            filename=f"ticket-{row[0]}-transcript.txt",
        )

        await log_channel.send(
            content=(
                f"📄 **Ticket Transcript**\n"
                f"Ticket ID: `{row[0]}`\n"
                f"Channel: {interaction.channel.mention}\n"
                f"Created by: {interaction.user.mention}"
            ),
            file=file,
        )

        await interaction.followup.send(
            f"✅ Transcript sent to {log_channel.mention}.",
            ephemeral=True,
        )

    @discord.ui.button(
        label="Delete",
        style=discord.ButtonStyle.grey,
        custom_id="ticket_delete",
    )
    async def delete(self, interaction: discord.Interaction, button: discord.Button):
        row = get_ticket_by_channel(
            interaction.guild.id,
            interaction.channel.id,
        )

        if not row:
            await interaction.response.send_message(
                "Not a ticket channel.",
                ephemeral=True,
            )
            return

        delete_ticket(row[0])

        await interaction.channel.delete(
            reason=f"Ticket deleted by {interaction.user}",
        )
```
