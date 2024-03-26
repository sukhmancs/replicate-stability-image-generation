import replicate
import discord
import os
from dotenv import load_dotenv
from discord.ext import commands
import asyncio
import time

load_dotenv()

os.environ['REPLICATE_API_TOKEN'] = os.getenv('REPLICATE_TOKEN')
os.environ['DISCORD_TOKEN'] = os.getenv('DISCORD_TOKEN')

class MyClient(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True        
        super().__init__(command_prefix='!', intents=intents)
        self.command_in_progress = False  # flag to check if a command is in progress

    async def on_ready(self):
        """
        This event triggered when the bot is ready.
        """
        print('Logged on as', self.user)

    async def on_message(self, message):
        """
        This event triggered when a message is created and sent.

        message: discord.Message
            The message that was created.
        """
        if message.author == self.user:
            return

        if message.content == '!help':
            await message.channel.send('To generate an image, type "!generate_image prompt,guidance_scale". For example: "!generate_image "mdjrny-v4 style portrait of female elf, intricate, elegant, highly detailed, digital painting, artstation, concept art, smooth, sharp focus, illustration, art by artgerm and greg rutkowski and alphonse mucha, 8k",5"')
            return

        await self.process_commands(message)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """
        This event triggered when an error is raised while invoking a command.

        ctx: commands.Context
            The context used for command invocation.
        error: commands.CommandError
            The Exception raised.            
        """
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send('Please provide the correct format. Type "!help" for more information.')
        elif isinstance(error, commands.CommandNotFound):
            await ctx.send('Please provide the correct format. Type "!help" for more information.')

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """
        This event triggered when a reaction is added to a message.

        reaction: discord.Reaction
            The reaction that was added or removed.

        user: Union[discord.User, discord.Member]
            The user who added or removed the reaction.
        """
        if reaction.emoji == '👍':
            await reaction.message.channel.send('Thank you for the feedback!')

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        """
        This event triggered when a reaction is removed from a message.

        reaction: discord.Reaction
            The reaction that was added or removed.

        user: Union[discord.User, discord.Member]
            The user who added or removed the reaction.
        """
        if reaction.emoji == '👎':
            await reaction.message.channel.send('Thank you for the feedback!')

client = MyClient()

async def countdown(ctx, countdown_message):
    """
    Countdown from 8 to 1 and delete the countdown message.

    ctx: commands.Context
        The context used for command invocation.
    
    countdown_message: discord.Message
        The message to edit.
    """
    for i in range(7, 0, -1):
        await countdown_message.edit(content=str(i))
        await asyncio.sleep(1)

    # delete the countdown message
    await countdown_message.delete()

# not the time took to generate the image
async def time_taken(ctx, start_time):
    """
    Calculate the time taken to generate the image.

    ctx: commands.Context
        The context used for command invocation.
    
    start_time: float
        The time when the image generation started.
    """
    end_time = time.time()
    await ctx.send(f"Time taken: {end_time - start_time} seconds")

@client.command()
async def generate_image(ctx, *, args):
    """
    This is a command to generate an image based on the prompt and guidance scale.

    ctx: commands.Context
        The context used for command invocation.
    
    args: str
        A single string containing the prompt and guidance scale.
    """
    if client.command_in_progress:
        await ctx.send('A command is already in progress. Please wait for the current command to finish.')
        return
    
    try:
        client.command_in_progress = True
        args = args.strip('"') # remove the quotes
        prompt, guidance_scale = args.split('",') # split the prompt and guidance scale based on the comma
        guidance_scale = int(guidance_scale) 

        if guidance_scale < 1 or guidance_scale > 10:
            await ctx.send('Please provide the correct guidance scale. It should be between 1 and 10.')
            return

        if len(prompt) < 1:
            await ctx.send('Please provide the correct prompt.')
            return

        if len(prompt) > 1024:
            await ctx.send('Please provide the correct prompt. It should be less than 1024 characters.')
            return

        try:

            # calculate time took
            start_time = time.time()

            input = {
                "prompt": prompt,
                "guidance_scale": guidance_scale
            }

            default_message = await ctx.send("Generating image...")
            countdown_message = await ctx.send("8")
            countdown_task = asyncio.create_task(countdown(ctx, countdown_message))

            output = replicate.run(
                "prompthero/openjourney:ad59ca21177f9e217b9075e7300cf6e14f7e5b4505b87b9689dbd866e9768969",
                input=input
            )

            # Wait for either the countdown to finish or the image to be generated
            done, pending = await asyncio.wait(
                {countdown_task},
                return_when=asyncio.FIRST_COMPLETED
            )

            # If the image generation finished before the countdown, cancel the countdown
            if countdown_task in pending:
                countdown_task.cancel()

            image_url = "".join(output)
            await default_message.edit(content="Image will be sent shortly...")
            await ctx.send(image_url)
            
            # not the time took to generate the image
            end_time = time.time()
            time_elapsed = end_time - start_time

            # throw an execution of the code if it is taking too long
            if time_elapsed > 60:
                raise Exception("The image generation is taking too long. This is likely due to the model being overloaded. Please try again later.")                            
            await ctx.send(f"Time elapsed: {time_elapsed:.2f} seconds")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")        
    except ValueError:
        await ctx.send('Please provide the correct format. Type "!help" for more information.')
    
    finally:
        # reset the flag
        client.command_in_progress = False

client.run(os.getenv('DISCORD_TOKEN'))