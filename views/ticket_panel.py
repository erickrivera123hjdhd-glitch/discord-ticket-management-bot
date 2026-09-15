import discord
from discord.ui import View, Select
from db import create_ticket, get_guild_config, get_user_open_ticket


class TicketPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CategorySelect())


class CategorySelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Support", description="Support related issues"),
            discord.SelectOption(label="Purchase", description="Purchase related questions"),
            discord.SelectOption(label="Report", description="Report a user or issue"),
            discord.SelectOption(label="Partnership", description="Partnership inquiries"),
            discord.SelectOption(label="Other", description="Other"),
        ]
        super().__init__(
            placeholder="Select a category",
            options=options,
            custom_id="ticket_category_select",
        )

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        user = interaction.user

        row = get_user_open_ticket(interaction.guild.id, user.id, category)
        if row:
            await interaction.response.send_message(
                f"You already have an open {category} ticket.",
                ephemeral=True,
            )
            return

        cfg = get_guild_config(interaction.guild.id)
        staff_role_id = cfg[3] if cfg else None

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        if staff_role_id:
            staff_role = interaction.guild.get_role(staff_role_id)
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                )

        ticket_name = f"ticket-{category.lower()}-{user.name}"[:100]

        category_obj = next(
            (cat for cat in interaction.guild.categories if cat.name.lower() == "tickets"),
            None,
        )

        ticket_channel = await interaction.guild.create_text_channel(
            ticket_name,
            category=category_obj,
            overwrites=overwrites,
        )

        create_ticket(interaction.guild.id, ticket_channel.id, category, user.id)

        from views.ticket_buttons import TicketButtonsView
        view = TicketButtonsView()

        embed = discord.Embed(
            title=f"Ticket – {category}",
            description=f"Hello {user.mention}, this is your private ticket.",
            color=discord.Color.blue(),
        )

        await ticket_channel.send(embed=embed, view=view)
        await interaction.response.send_message(
            f"Your {category} ticket has been created!",
            ephemeral=True,
        )
