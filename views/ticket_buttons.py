import discord
from discord.ui import View, Button
from db import (
    close_ticket,
    delete_ticket,
    set_claim,
    get_ticket_by_channel,
    reopen_ticket,
    get_guild_config,
)
import time


class TicketButtonsView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.Button):
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

        t_id = row[0]
        close_ticket(t_id)

        embed = discord.Embed(
            description=f"Ticket closed by {interaction.user.mention}",
            color=discord.Color.red()
        )
        await interaction.channel.send(embed=embed)

        # Overwrite permissions
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
                send_messages=True
            )

        if staff_role:
            await interaction.channel.set_permissions(
                staff_role,
                read_messages=True,
                send_messages=True
            )

        # Generate transcript
        lines = []

        async for msg in interaction.channel.history(limit=None):
            author = msg.author.display_name
            ts = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            content = msg.content.replace("\n", " ")
            lines.append(f"[{ts}] {author}: {content}")

        transcript = "\n".join(lines)

        log_cfg = cfg[1] if cfg else None

        if log_cfg:
            log_ch = interaction.guild.get_channel(log_cfg)

            if log_ch:
                await log_ch.send(
                    f"Transcript for ticket {t_id}:\n"
                    f"```{transcript}```"
                )

        await interaction.channel.edit(name=f"closed-{t_id}")

        await interaction.response.send_message(
            "Ticket closed.",
            ephemeral=True
        )

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.green)
    async def claim(
        self,
        interaction: discord.Interaction,
        button: discord.Button
    ):
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

        set_claim(row[0], interaction.user.id)

        await interaction.response.send_message(
            f"Ticket claimed by {interaction.user.mention}",
            ephemeral=True
        )

    @discord.ui.button(
        label="Transcript",
        style=discord.ButtonStyle.blurple
    )
    async def transcript(
        self,
        interaction: discord.Interaction,
        button: discord.Button
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

        lines = []

        async for msg in interaction.channel.history(limit=None):
            author = msg.author.display_name
            ts = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            content = msg.content.replace("\n", " ")
            lines.append(f"[{ts}] {author}: {content}")

        transcript = "\n".join(lines)

        cfg = get_guild_config(interaction.guild.id)
        log_cfg = cfg[1] if cfg else None

        if log_cfg:
            log_ch = interaction.guild.get_channel(log_cfg)

            if log_ch:
                await log_ch.send(
                    f"Transcript for ticket {row[0]}:\n"
                    f"```{transcript}```"
                )

        await interaction.response.send_message(
            "Transcript sent.",
            ephemeral=True
        )

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.grey)
    async def delete(
        self,
        interaction: discord.Interaction,
        button: discord.Button
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

        await interaction.channel.delete(
            reason="Ticket deleted"
        )
