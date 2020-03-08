import os
os.environ = {} # Remove env variables to give os.system a semblance of security
import sys
import asyncio
import time
import inspect
import logging
from math import ceil
from random import choice

import utilities
import message_parser
import dynamo_helper
from discord import errors
from discord.ext import commands
from discord.member import Member

## Config
CONFIG_OPTIONS = utilities.load_config()

## Logging
logger = utilities.initialize_logging(logging.getLogger(__name__))


class TTSController:
    ## Keys
    TTS_FILE_KEY = "tts_file"
    TTS_FILE_PATH_KEY = "tts_file_path"
    TTS_OUTPUT_DIR_KEY = "tts_output_dir"
    TTS_OUTPUT_DIR_PATH_KEY = "tts_output_dir_path"
    ARGS_KEY = "args"
    PREPEND_KEY = "prepend"
    APPEND_KEY = "append"
    CHAR_LIMIT_KEY = "char_limit"
    NEWLINE_REPLACEMENT_KEY = "newline_replacement"
    OUTPUT_EXTENSION_KEY = "output_extension"
    WINE_KEY = "wine"
    XVFB_PREPEND_KEY = "XVFB_prepend"
    HEADLESS_KEY = "headless"

    ## Defaults
    TTS_FILE = CONFIG_OPTIONS.get(TTS_FILE_KEY, "say.exe")
    TTS_FILE_PATH = CONFIG_OPTIONS.get(TTS_FILE_PATH_KEY, os.sep.join([os.path.dirname(os.path.abspath(__file__)), TTS_FILE]))
    TTS_OUTPUT_DIR = CONFIG_OPTIONS.get(TTS_OUTPUT_DIR_KEY, "temp")
    TTS_OUTPUT_DIR_PATH = CONFIG_OPTIONS.get(TTS_OUTPUT_DIR_PATH_KEY, os.sep.join([utilities.get_root_path(), TTS_OUTPUT_DIR]))
    PREPEND = CONFIG_OPTIONS.get(PREPEND_KEY, "[:phoneme on]")
    APPEND = CONFIG_OPTIONS.get(APPEND_KEY, "")
    CHAR_LIMIT = CONFIG_OPTIONS.get(CHAR_LIMIT_KEY, 1250)
    NEWLINE_REPLACEMENT = CONFIG_OPTIONS.get(NEWLINE_REPLACEMENT_KEY, "[_<250,10>]")
    OUTPUT_EXTENSION = CONFIG_OPTIONS.get(OUTPUT_EXTENSION_KEY, "wav")
    WINE = CONFIG_OPTIONS.get(WINE_KEY, "wine")
    XVFB_PREPEND = CONFIG_OPTIONS.get(XVFB_PREPEND_KEY, "DISPLAY=:0.0")
    HEADLESS = CONFIG_OPTIONS.get(HEADLESS_KEY, False)


    def __init__(self, exe_path=None, **kwargs):
        self.exe_path = exe_path or kwargs.get(self.TTS_FILE_PATH_KEY, self.TTS_FILE_PATH)
        self.output_dir_path = kwargs.get(self.TTS_OUTPUT_DIR_PATH_KEY, self.TTS_OUTPUT_DIR_PATH)
        self.args = kwargs.get(self.ARGS_KEY, {})
        self.prepend = kwargs.get(self.PREPEND_KEY, self.PREPEND)
        self.append = kwargs.get(self.APPEND_KEY, self.APPEND)
        self.char_limit = int(kwargs.get(self.CHAR_LIMIT_KEY, self.CHAR_LIMIT))
        self.newline_replacement = kwargs.get(self.NEWLINE_REPLACEMENT_KEY, self.NEWLINE_REPLACEMENT)
        self.output_extension = kwargs.get(self.OUTPUT_EXTENSION_KEY, self.OUTPUT_EXTENSION)
        self.wine = kwargs.get(self.WINE_KEY, self.WINE)
        self.xvfb_prepend = kwargs.get(self.XVFB_PREPEND_KEY, self.XVFB_PREPEND)
        self.is_headless = kwargs.get(self.HEADLESS_KEY, self.HEADLESS)

        self.paths_to_delete = []

        if(self.output_dir_path):
            self._init_dir()


    def __del__(self):
        self._init_dir()


    def _init_dir(self):
        if(not os.path.exists(self.output_dir_path)):
            os.makedirs(self.output_dir_path)
        else:
            for root, dirs, files in os.walk(self.output_dir_path, topdown=False):
                for file in files:
                    try:
                        os.remove(os.sep.join([root, file]))
                    except OSError as e:
                        logger.exception("Error removing file: {}".format(file))


    def _generate_unique_file_name(self, extension):
        time_ms = int(time.time() * 1000)
        file_name = "{}.{}".format(time_ms, extension)

        while(os.path.isfile(file_name)):
            time_ms -= 1
            file_name = "{}.{}".format(time_ms, extension)

        return file_name


    def check_length(self, message):
        return (len(message) <= self.char_limit)


    def _parse_message(self, message):
        if(self.newline_replacement):
            message = message.replace("\n", self.newline_replacement)

        if(self.prepend):
            message = self.prepend + message

        if(self.append):
            message = message + self.append

        message = message.replace('"', "")
        return message


    def delete(self, file_path):
        ## Basically, windows spits out a 'file in use' error when speeches are deleted after 
        ## being skipped, probably because of the file being loaded into the ffmpeg player. So
        ## if the deletion fails, just pop it into a list of paths to delete on the next go around.

        if(os.path.isfile(file_path)):
            self.paths_to_delete.append(file_path)

        to_delete = []
        for path in self.paths_to_delete:
            try:
                os.remove(path)
            except FileNotFoundError:
                ## The goal was to remove the file, and as long as it doesn't exist then we're good.
                continue
            except Exception:
                logger.exception("Error deleting file: {}".format(path))
                to_delete.append(path)

        self.paths_to_delete = to_delete[:]

        return True


    async def save(self, message, ignore_char_limit=False):
        ## Validate output directory
        if(not self.output_dir_path):
            logger.warning("Unable to save without output_dir_path set.")
            return None

        ## Check message size
        if(not self.check_length(message) and not ignore_char_limit):
            return None

        ## Generate and validate filename
        output_file_path = os.sep.join([self.output_dir_path, 
                                        self._generate_unique_file_name(self.output_extension)])

        ## Parse options and message
        save_option = '-w "{}"'.format(output_file_path)
        message = self._parse_message(message)

        ## Format and invoke
        args = '{} {} "{}"'.format(
            self.exe_path,
            save_option,
            message
        )

        ## Prepend the windows emulator if using linux (I'm aware of what WINE means)
        if(utilities.is_linux()):
            args = "{} {}".format(self.wine, args)

        ## Prepend the fake display created with Xvfb if running headless
        if(self.is_headless):
            args = "{} {}".format(self.xvfb_prepend, args)

        retval = os.system(args)

        if(retval == 0):
            return output_file_path
        else:
            return None


# class Speech:
#     ## Keys
#     DELETE_COMMANDS_KEY = "delete_commands"
#     SKIP_VOTES_KEY = "skip_votes"
#     SKIP_PERCENTAGE_KEY = "skip_percentage"
#     SPEECH_STATES_KEY = "speech_states"
#     FFMPEG_BEFORE_OPTIONS_KEY = "ffmpeg_before_options"
#     FFMPEG_OPTIONS_KEY = "ffmpeg_options"
#     CHANNEL_TIMEOUT_KEY = "channel_timeout"
#     CHANNEL_TIMEOUT_PHRASES_KEY = "channel_timeout_phrases"

#     ## Defaults
#     DELETE_COMMANDS = CONFIG_OPTIONS.get(DELETE_COMMANDS_KEY, False)
#     SKIP_VOTES = CONFIG_OPTIONS.get(SKIP_VOTES_KEY, 3)
#     SKIP_PERCENTAGE = CONFIG_OPTIONS.get(SKIP_PERCENTAGE_KEY, 33)
#     # Before options are command line options (ex. "-ac 2") inserted before FFMpeg's -i flag
#     FFMPEG_BEFORE_OPTIONS = CONFIG_OPTIONS.get(FFMPEG_BEFORE_OPTIONS_KEY, "")
#     # Options are command line options inserted after FFMpeg's -i flag
#     FFMPEG_OPTIONS = CONFIG_OPTIONS.get(FFMPEG_OPTIONS_KEY, "")
#     CHANNEL_TIMEOUT = CONFIG_OPTIONS.get(CHANNEL_TIMEOUT_KEY, 15 * 60)


#     def __init__(self, bot, tts_controller=None, **kwargs):
#         self.bot = bot
#         self.tts_controller = tts_controller or TTSController()
#         self.speech_states = {}
#         self.save = self.tts_controller.save
#         self.delete = self.tts_controller.delete
#         self.delete_commands = kwargs.get(self.DELETE_COMMANDS_KEY, self.DELETE_COMMANDS)
#         self.skip_votes = int(kwargs.get(self.SKIP_VOTES_KEY, self.SKIP_VOTES))
#         self.skip_percentage = int(kwargs.get(self.SKIP_PERCENTAGE_KEY, self.SKIP_PERCENTAGE))
#         self.ffmpeg_before_options = kwargs.get(self.FFMPEG_BEFORE_OPTIONS_KEY, self.FFMPEG_BEFORE_OPTIONS)
#         self.ffmpeg_options = kwargs.get(self.FFMPEG_OPTIONS_KEY, self.FFMPEG_OPTIONS)
#         self.channel_timeout = int(kwargs.get(self.CHANNEL_TIMEOUT_KEY, self.CHANNEL_TIMEOUT))

#         ## Beginning config cleanup, hence no extra kwargs.get junk
#         self.channel_timeout_phrases = CONFIG_OPTIONS.get(self.CHANNEL_TIMEOUT_PHRASES_KEY, [])

#         self.message_parser = message_parser.MessageParser()
#         self.dynamo_db = dynamo_helper.DynamoHelper()

#     ## REMOVE EVERYTHING BELOW

#     ## Commands

#     ## Initiate/Continue a vote to skip on the currently playing speech
#     # @commands.command(pass_context=True, no_pm=True)
#     # async def skip(self, ctx):
#     #     """Vote to skip the current speech."""

#     #     state = self.get_speech_state(ctx.message.server)
#     #     if(not state.is_speaking()):
#     #         await self.bot.say("I'm not speaking at the moment.")
#     #         self.dynamo_db.put(dynamo_helper.DynamoItem(ctx, ctx.message.content, inspect.currentframe().f_code.co_name, False))
#     #         return False
#     #     else:
#     #         self.dynamo_db.put(dynamo_helper.DynamoItem(ctx, ctx.message.content, inspect.currentframe().f_code.co_name, True))

#     #     voter = ctx.message.author
#     #     if(voter == state.current_speech.requester):
#     #         await self.bot.say("<@{}> skipped their own speech.".format(voter.id))
#     #         await state.skip_speech(voter.voice_channel)
#     #         ## Attempt to delete the command message
#     #         await self.attempt_delete_command_message(ctx.message)
#     #         return False
#     #     elif(voter.id not in state.skip_votes):
#     #         state.skip_votes.add(voter)

#     #         total_votes = len([voter for voter in state.skip_votes if voter.voice_channel == state.voice_client.channel])
#     #         total_members = len([member for member in await state.get_members() if not member.bot])
#     #         vote_percentage = ceil((total_votes / total_members) * 100)

#     #         if(total_votes >= self.skip_votes or vote_percentage >= self.skip_percentage):
#     #             await self.bot.say("Skip vote passed by {}% of members. I'll skip the current speech.".format(vote_percentage))
#     #             await state.skip_speech()
#     #             return True
#     #         else:
#     #             raw = "Skip vote added, currently at {}/{} or {}%"
#     #             await self.bot.say(raw.format(total_votes, total_members, vote_percentage))

#     #     else:
#     #         await self.bot.say("<@{}> has already voted!".format(voter.id))


#     # ## Starts the TTS process! Creates and stores a ffmpeg player for the message to be played
#     # @commands.command(pass_context=True, no_pm=True)
#     # async def say(self, ctx, *, message, ignore_char_limit=False, target_member=None):
#     #     """Speaks your text aloud to your channel."""

#     #     ## Todo: look into memoization of speech. Phrases.py's speech is a perfect candidate

#     #     ## Verify that the target/requester is in a channel
#     #     if (not target_member or not isinstance(target_member, Member)):
#     #         target_member = ctx.message.author

#     #     voice_channel = target_member.voice_channel
#     #     if(voice_channel is None):
#     #         await self.bot.say("<@{}> isn't in a voice channel.".format(target_member.id))
#     #         self.dynamo_db.put(dynamo_helper.DynamoItem(ctx, ctx.message.content, inspect.currentframe().f_code.co_name, False))
#     #         return False

#     #     ## Make sure the message isn't too long
#     #     if(not self.tts_controller.check_length(message) and not ignore_char_limit):
#     #         await self.bot.say("Keep phrases less than {} characters.".format(self.tts_controller.char_limit))
#     #         self.dynamo_db.put(dynamo_helper.DynamoItem(ctx, ctx.message.content, inspect.currentframe().f_code.co_name, False))
#     #         return False

#     #     state = self.get_speech_state(ctx.message.server)
#     #     if(state.voice_client is None):
#     #         ## Todo: Handle exception if unable to create a voice client
#     #         await self.create_voice_client(voice_channel)

#     #     ## Parse down the message before sending it to the TTS service
#     #     message = self.message_parser.parse_message(message, ctx.message)

#     #     try:
#     #         ## Create a .wav file of the message
#     #         wav_path = await self.save(message, ignore_char_limit)
#     #         if(wav_path):
#     #             ## Create a player for the .wav
#     #             player = state.voice_client.create_ffmpeg_player(
#     #                 wav_path,
#     #                 before_options=self.ffmpeg_before_options,
#     #                 options=self.ffmpeg_options,
#     #                 after=state.next_speech
#     #             )
#     #         else:
#     #             raise RuntimeError("Unable to save a proper .wav file.")
#     #     except Exception as e:
#     #         utilities.debug_print("Exception in say():", e, debug_level=0)
#     #         await self.bot.say("Unable to say the last message. Sorry, <@{}>.".format(ctx.message.author.id))
#     #         self.dynamo_db.put(dynamo_helper.DynamoItem(ctx, ctx.message.content, inspect.currentframe().f_code.co_name, False))
#     #         return False
#     #     else:
#     #         ## On successful player creation, build a SpeechEntry and push it into the queue
#     #         await state.speech_queue.put(SpeechEntry(ctx.message.author, voice_channel, player, wav_path))
#     #         self.dynamo_db.put(dynamo_helper.DynamoItem(ctx, ctx.message.content, inspect.currentframe().f_code.co_name, True))

#     #         ## Attempt to delete the command message
#     #         await self.attempt_delete_command_message(ctx.message)

#     #         ## Start a timeout to disconnect the bot if the bot hasn't spoken in a while
#     #         await self.attempt_leave_channel(state)

#     #         return True


#     # async def _announce(self, state, message, callback=None):
#     #     """Internal way to speak text to a specific speech_state """
#     #     try:
#     #         ## Create a .wav file of the message
#     #         wav_path = await self.save(message, True)
#     #         if(wav_path):
#     #             ## Create a player for the .wav
#     #             player = state.voice_client.create_ffmpeg_player(
#     #                 wav_path,
#     #                 before_options=self.ffmpeg_before_options,
#     #                 options=self.ffmpeg_options,
#     #                 after=state.next_speech
#     #             )
#     #         else:
#     #             raise RuntimeError("Unable to save a proper .wav file.")
#     #     except Exception as e:
#     #         utilities.debug_print("Exception in _announce():", e, debug_level=0)
#     #         return False
#     #     else:
#     #         ## On successful player creation, build a SpeechEntry and push it into the queue
#     #         await state.speech_queue.put(SpeechEntry(None, state.voice_client.channel, player, wav_path, callback))

#     #         ## Start a timeout to disconnect the bot if the bot hasn't spoken in a while
#     #         await self.attempt_leave_channel(state)

#     #         return True