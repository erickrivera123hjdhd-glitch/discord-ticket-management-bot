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
        user_ids = set()

        async for msg in channel.history(
            limit=None,
            oldest_first=True
        ):
            timestamp = msg.created_at.strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            author = (
                f"{msg.author.display_name} "
                f"({msg.author.id})"
            )

            content = msg.content or "[No text content]"

            if not msg.author.bot:
                user_ids.add(msg.author.id)

            if msg.attachments:
                attachments = " | ".join(
                    attachment.url
                    for attachment in msg.attachments
                )

                content += (
                    f" | Attachments: {attachments}"
                )

            lines.append(
                f"[{timestamp}] {author}: {content}"
            )

        transcript = (
            "\n".join(lines)
            if lines
            else "No messages found."
        )

        return transcript, user_ids

    async def send_transcript_to_users(
        self,
        guild,
        transcript,
        user_ids,
        ticket_id
    ):
        sent = 0
        failed = 0

        for user_id in user_ids:
            try:
                user = guild.get_member(user_id)

                if user is None:
                    user = await guild.fetch_member(user_id)

                file = discord.File(
                    io.BytesIO(
                        transcript.encode("utf-8")
                    ),
                    filename=(
                        f"ticket-{ticket_id}-transcript.txt"
                    )
                )

                await user.send(
                    content=(
                        "📄 **Ticket Transcript**\n"
                        f"Server: **{guild.name}**\n"
                        f"Ticket ID: `{ticket_id}`"
                    ),
                    file=file
                )

                sent += 1

            except (
                discord.Forbidden,
                discord.NotFound,
                discord.HTTPException
            ):
                failed += 1

        return sent, failed

    @discord.ui.button(
        label="Close",
        style=discord.ButtonStyle.red,
        custom_id="ticket_close"
    )
    async def close(
        self,
        interaction: discord.Interaction,
        button: Button
    ):
        row = get_ticket_by_channel(
            interaction.guild.id,
            interaction.channel.id
        )

        if not row:
            await interaction.response.send_message(
                "Not a ticket channel.",
                ephemeral=True
            )
            return

        await interaction.response.defer(
            ephemeral=True
        )

        ticket_id = row[0]

        transcript, user_ids = await self.create_transcript(
            interaction.channel
        )

        if len(row) > 3 and row[3]:
            user_ids.add(row[3])

        user_ids.add(interaction.user.id)

        close_ticket(ticket_id)

        await interaction.channel.send(
            embed=discord.Embed(
                description=(
                    f"Ticket closed by "
                    f"{interaction.user.mention}"
                ),
                color=discord.Color.red()
            )
        )

        cfg = get_guild_config(
            interaction.guild.id
        )

        staff_role_id = cfg[3] if cfg else None

        staff_role = (
            interaction.guild.get_role(staff_role_id)
            if staff_role_id
            else None
        )

        creator = None

        if len(row) > 3 and row[3]:
            creator = interaction.guild.get_member(row[3])

        if creator:
            await interaction.channel.set_permissions(
                creator,
                read_messages=True,
                send_messages=True
            )

        if staff_role:
            await interaction.channel.set_permissions(
                staff_role,
                read_messages=True,
                send_messages=True
            )

        sent, failed = await self.send_transcript_to_users(
            interaction.guild,
            transcript,
            user_ids,
            ticket_id
        )

        await interaction.channel.edit(
            name=f"closed-{ticket_id}"
        )

        message = (
            "Ticket closed. 📄 "
            f"Transcript sent to {sent} user(s)."
        )

        if failed:
            message += (
                f" {failed} user(s) could not "
                "receive the DM."
            )

        await interaction.followup.send(
            message,
            ephemeral=True
        )

    @discord.ui.button(
        label="Claim",
        style=discord.ButtonStyle.green,
        custom_id="ticket_claim"
    )
    async def claim(
        self,
        interaction: discord.Interaction,
        button: Button
    ):
        cfg = get_guild_config(
            interaction.guild.id
        )

        staff_role_id = cfg[3] if cfg else None

        staff_role = (
            interaction.guild.get_role(staff_role_id)
            if staff_role_id
            else None
        )

        if (
            not staff_role
            or staff_role not in interaction.user.roles
        ):
            await interaction.response.send_message(
                "You don't have permission.",
                ephemeral=True
            )
            return

        row = get_ticket_by_channel(
            interaction.guild.id,
            interaction.channel.id
        )

        if not row:
            await interaction.response.send_message(
                "Not a ticket channel.",
                ephemeral=True
            )
            return

        set_claim(
            row[0],
            interaction.user.id
        )

        await interaction.response.send_message(
            (
                f"Ticket claimed by "
                f"{interaction.user.mention}"
            ),
            ephemeral=True
        )

    @discord.ui.button(
        label="Transcript",
        style=discord.ButtonStyle.blurple,
        custom_id="ticket_transcript"
    )
    async def transcript(
        self,
        interaction: discord.Interaction,
        button: Button
    ):
        row = get_ticket_by_channel(
            interaction.guild.id,
            interaction.channel.id
        )

        if not row:
            await interaction.response.send_message(
                "Not a ticket channel.",
                ephemeral=True
            )
            return

        await interaction.response.defer(
            ephemeral=True
        )

        ticket_id = row[0]

        transcript, user_ids = await self.create_transcript(
            interaction.channel
        )

        if len(row) > 3 and row[3]:
            user_ids.add(row[3])

        user_ids.add(interaction.user.id)

        sent, failed = await self.send_transcript_to_users(
            interaction.guild,
            transcript,
            user_ids,
            ticket_id
        )

        message = (
            f"📄 Transcript sent to {sent} user(s)."
        )

        if failed:
            message += (
                f" {failed} user(s) could not "
                "receive the DM."
            )

        await interaction.followup.send(
            message,
            ephemeral=True
        )

    @discord.ui.button(
        label="Delete",
        style=discord.ButtonStyle.grey,
        custom_id="ticket_delete"
    )
    async def delete(
        self,
        interaction: discord.Interaction,
        button: Button
    ):
        row = get_ticket_by_channel(
            interaction.guild.id,
            interaction.channel.id
        )

        if not row:
            await interaction.response.send_message(
                "Not a ticket channel.",
                ephemeral=True
            )
            return

        delete_ticket(row[0])

        await interaction.response.send_message(
            "Deleting ticket...",
            ephemeral=True
        )

        await interaction.channel.delete(
            reason=(
                f"Ticket deleted by "
                f"{interaction.user}"
            )
        )
