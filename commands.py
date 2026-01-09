import discord
from db import ensure_user_registered, check_user_registered, log_drink, execute_query
import logging
from discord import app_commands

async def register_command(interaction: discord.Interaction):
    try:
        await interaction.response.defer(thinking=True)
        ensure_user_registered(
            interaction.user.id,
            str(interaction.user),
            interaction.guild.id,
            interaction.guild.name
        )
        await interaction.followup.send(f"✅ {interaction.user} registered for this server!")
    except Exception as e:
        logging.error(f"Error in register_command: {e}")
        try:
            await interaction.followup.send(f"⚠️ Registration failed: {e}")
        except Exception as e2:
            logging.error(f"Failed to send followup: {e2}")

async def drink_command(interaction: discord.Interaction, drink_name: str, quantity: int = 1):
    try:
        await interaction.response.defer(thinking=True)

        user_id = check_user_registered(interaction.user.id)
        if not user_id:
            await interaction.followup.send(
                f"⚠️ You are not registered yet! Please use `/register` first."
            )
            return

        # Ensure server exists
        execute_query(
            "INSERT INTO servers (id, name) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
            (interaction.guild.id, interaction.guild.name)
        )

        # Link user to server if missing
        execute_query(
            "INSERT INTO server_members (user_id, server_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
            (user_id, interaction.guild.id)
        )

        log_drink(user_id, interaction.guild.id, drink_name, quantity)
        await interaction.followup.send(f"🍺 Logged {quantity} x {drink_name} for {interaction.user}!")

    except Exception as e:
        logging.error(f"Error in drink_command: {e}")
        try:
            await interaction.followup.send(f"⚠️ Could not log drink due to an error: {e}")
        except Exception as e2:
            logging.error(f"Failed to send followup: {e2}")

async def hello_command(interaction: discord.Interaction):
    await interaction.response.send_message(f"👋 Hello {interaction.user}! BeerBot is here 🍻")
