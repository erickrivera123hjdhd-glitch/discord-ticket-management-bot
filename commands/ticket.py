import discord
from discord import app_commands, Interaction, Embed, Member, Role
from discord.ext import commands
from discord.utils import format_dt
import sqlite3, time, os

from db import (
    get_guild_config, set_guild_config, create_ticket, get_user_open_ticket,
    close_ticket, delete_ticket, set_claim, reopen_ticket, get_ticket,
    get_ticket_by_channel,
)

from views.ticket_panel import TicketPanelView
from views.ticket_buttons import TicketButtonsView


def get_db():
    return sqlite3.connect("tickets.db")


async def setup(bot: commands.Bot):
    ticket_group = app_commands.Group(
        name="ticket",
        description="Ticket management commands"
    )

    # ---- setup ----
    @ticket_group.command(
        name="setup",
        description="Create/configure the ticket panel"
    )
    async def setup_cmd(interaction: Interaction):
        view = TicketPanelView()

        embed = Embed(
            title="Ticket System",
            description="Select a category to open a ticket.",
            color=discord.Color.green()
        )

        msg = await interaction.channel.send(embed=embed, view=view)

        cfg = get_guild_config(interaction.guild.id)

        if cfg is None:
            set_guild_config(
                interaction.guild.id,
                ticket_panel_message_id=msg.id,
                transcript_log_channel_id=0,
                staff_role_id=0,
                ticket_counter=0,
            )
        else:
            set_guild_config(
                interaction.guild.id,
                ticket_panel_message_id=msg.id
            )

        await interaction.response.send_message(
            "Panel sent!",
            ephemeral=True
        )

    # ---- close ----
    @ticket_group.command(
        name="close",
        description="Close the current ticket"
    )
    async def close_cmd(interaction: Interaction):
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

        t_id, ch_id, category, creator_id, claimed_by, opened_at, _ = row

        cfg = get_guild_config(interaction.guild.id)

        staff_role_id = cfg[3] if cfg else None
        staff_role = (
            interaction.guild.get_role(staff_role_id)
            if staff_role_id
            else None
        )

        is_creator = interaction.user.id == creator_id

        if (
            staff_role
            and staff_role not in interaction.user.roles
            and not is_creator
        ):
            await interaction.response.send_message(
                "You cannot close this ticket.",
                ephemeral=True
            )
            return

        close_ticket(t_id)

        embed = Embed(
            description=f"Ticket closed by {interaction.user.mention}",
            color=discord.Color.red()
        )

        await interaction.channel.send(embed=embed)

        # overwrite permissions
        creator = interaction.guild.get_member(creator_id)

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

        # generate transcript
        lines = []

        async for msg in interaction.channel.history(limit=None):
            author = msg.author.display_name
            ts = format_dt(msg.created_at, "R")
            content = msg.content.replace("\n", " ")

            lines.append(
                f"[{ts}] {author}: {content}"
            )

        transcript = "\n".join(lines)

        log_cfg = cfg[1] if cfg else None

        if log_cfg:
            log_ch = interaction.guild.get_channel(log_cfg)

            if log_ch:
                await log_ch.send(
                    f"Transcript for ticket {t_id}:\n"
                    f"```{transcript}```"
                )

        # rename channel
        await interaction.channel.edit(
            name=f"closed-{t_id}"
        )

        await interaction.response.send_message(
            "Ticket closed and transcript sent.",
            ephemeral=True
        )

    # ---- delete ----
    @ticket_group.command(
        name="delete",
        description="Permanently delete the ticket"
    )
    async def delete_cmd(interaction: Interaction):
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

    # ---- claim ----
    @ticket_group.command(
        name="claim",
        description="Claim the ticket"
    )
    async def claim_cmd(interaction: Interaction):
        cfg = get_guild_config(interaction.guild.id)

        staff_role_id = cfg[3] if cfg else None

        staff_role = (
            interaction.guild.get_role(staff_role_id)
            if staff_role_id
            else None
        )

        if not staff_role or staff_role not in interaction.user.roles:
            await interaction.response.send_message(
                "You don't have permission to claim tickets.",
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
            f"Ticket claimed by {interaction.user.mention}",
            ephemeral=True
        )

    # ---- unclaim ----
    @ticket_group.command(
        name="unclaim",
        description="Remove the claim"
    )
    async def unclaim_cmd(interaction: Interaction):
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

        conn = sqlite3.connect("tickets.db")
        c = conn.cursor()

        c.execute(
            "UPDATE tickets SET claimed_by=NULL WHERE ticket_id=?",
            (row[0],)
        )

        conn.commit()
        conn.close()

        await interaction.response.send_message(
            "Claim removed.",
            ephemeral=True
        )

    # ---- add ----
    @ticket_group.command(
        name="add",
        description="Add a user to the ticket"
    )
    async def add_cmd(
        interaction: Interaction,
        user: Member
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

        await interaction.channel.set_permissions(
            user,
            read_messages=True,
            send_messages=True
        )

        await interaction.response.send_message(
            f"{user.mention} added to ticket.",
            ephemeral=True
        )

    # ---- remove ----
    @ticket_group.command(
        name="remove",
        description="Remove a user from the ticket"
    )
    async def remove_cmd(
        interaction: Interaction,
        user: Member
    ):
        await interaction.channel.set_permissions(
            user,
            read_messages=False,
            send_messages=False
        )

        await interaction.response.send_message(
            f"{user.mention} removed from ticket.",
            ephemeral=True
        )

    # ---- rename ----
    @ticket_group.command(
        name="rename",
        description="Rename the ticket channel"
    )
    async def rename_cmd(
        interaction: Interaction,
        name: str
    ):
        await interaction.channel.edit(name=name)

        await interaction.response.send_message(
            f"Channel renamed to {name}.",
            ephemeral=True
        )

    # ---- transcript ----
    @ticket_group.command(
        name="transcript",
        description="Generate a transcript"
    )
    async def transcript_cmd(interaction: Interaction):
        lines = []

        async for msg in interaction.channel.history(limit=None):
            author = msg.author.display_name
            ts = format_dt(msg.created_at, "R")
            content = msg.content.replace("\n", " ")

            lines.append(
                f"[{ts}] {author}: {content}"
            )

        transcript = "\n".join(lines)

        cfg = get_guild_config(interaction.guild.id)

        log_cfg = cfg[1] if cfg else None

        if log_cfg:
            log_ch = interaction.guild.get_channel(log_cfg)

            if log_ch:
                await log_ch.send(
                    f"Transcript for ticket {interaction.channel.id}:\n"
                    f"```{transcript}```"
                )

        await interaction.response.send_message(
            "Transcript sent to log channel.",
            ephemeral=True
        )

    # ---- reopen ----
    @ticket_group.command(
        name="reopen",
        description="Reopen a closed ticket"
    )
    async def reopen_cmd(interaction: Interaction):
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

        reopen_ticket(row[0])

        await interaction.channel.set_permissions(
            interaction.guild.default_role,
            read_messages=True,
            send_messages=True
        )

        await interaction.response.send_message(
            "Ticket reopened.",
            ephemeral=True
        )

    # ---- stats ----
    @ticket_group.command(
        name="stats",
        description="Show ticket statistics"
    )
    async def stats_cmd(interaction: Interaction):
        conn = sqlite3.connect("tickets.db")
        c = conn.cursor()

        c.execute(
            "SELECT COUNT(*) FROM tickets "
            "WHERE guild_id=? AND closed_at IS NULL",
            (interaction.guild.id,)
        )

        open_tix = c.fetchone()[0]

        c.execute(
            "SELECT COUNT(*) FROM tickets "
            "WHERE guild_id=? AND closed_at IS NOT NULL",
            (interaction.guild.id,)
        )

        closed_tix = c.fetchone()[0]

        conn.close()

        embed = Embed(
            title="Ticket Stats",
            description=f"Open: {open_tix}\nClosed: {closed_tix}",
            color=discord.Color.blue()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    # ---- config ----
    @ticket_group.command(
        name="config",
        description="Configure ticket settings"
    )
    async def config_cmd(
        interaction: Interaction,
        *,
        setting: str = None
    ):
        if not setting:
            await interaction.response.send_message(
                "Usage: /ticket config staff_role <role>",
                ephemeral=True
            )
            return

        parts = setting.split()

        if parts[0] == "staff_role" and len(parts) >= 2:
            try:
                role_id = int(parts[1])

            except ValueError:
                await interaction.response.send_message(
                    "Invalid role ID.",
                    ephemeral=True
                )
                return

            role: Role = interaction.guild.get_role(role_id)

            if not role:
                await interaction.response.send_message(
                    "Role not found.",
                    ephemeral=True
                )
                return

            set_guild_config(
                interaction.guild.id,
                staff_role_id=role.id
            )

            await interaction.response.send_message(
                f"Staff role set to {role.name}.",
                ephemeral=True
            )

        else:
            await interaction.response.send_message(
                "Unknown setting.",
                ephemeral=True
            )

    bot.tree.add_command(ticket_group)
