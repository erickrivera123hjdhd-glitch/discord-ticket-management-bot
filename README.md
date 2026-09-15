# Discord Ticket Management Bot

## Features
- Button‑based ticket panel with category selection
- Private ticket channels with proper permissions
- Close, Claim, Transcript, Delete buttons inside tickets
- Prevent multiple open tickets per user per category
- Staff claim system
- Ticket counters and configurable naming
- Transcript generation and logging
- Configurable staff roles and categories
- Slash commands for all actions

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Create a Discord application and bot at https://discord.com/developers/applications
3. Invite the bot to your server with the OAuth2 URL (scope: bot, permissions: manage_channels, manage_roles, read_messages, etc.)
4. Set environment variables in a `.env` file:
   - `DISCORD_BOT_TOKEN` – your bot token
   - `DISCORD_GUILD_ID` – optional guild ID for local command sync
5. Run: `python main.py`

## Environment Variables
| Variable | Description |
|---|---|
| `DISCORD_BOT_TOKEN` | Bot token from Discord Developer Portal |
| `DISCORD_GUILD_ID` | Guild ID to sync slash commands to (omit for global) |
