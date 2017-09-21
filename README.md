# hawking
A retro text-to-speech interface bot for Discord, designed to work with all of the stuff you might've seen in Moonbase Alpha, using the existing commands.

## Installation
- Make sure you've got [Python 3.5](https://www.python.org/downloads/) or greater, and virtualenv installed (`pip install virtualenv`)
- `cd` into the directoy that you'd like the project to go
- `git clone https://github.com/naschorr/hawking`
- `virtualenv hawking`
- Activate your newly created virtualenv
- `pip install -r requirements.txt`
- Make sure the [FFmpeg executable](https://www.ffmpeg.org/download.html) is in your system's `PATH` variable
- Create a [Discord app](https://discordapp.com/developers/applications/me), flag it as a bot, and put the bot token inside `hawking/token.json`
- Register the Bot with your server. Go to: `https://discordapp.com/oauth2/authorize?client_id=CLIENT_ID&scope=bot&permissions=0`, but make sure to replace CLIENT_ID with your bot's client id.
- Select your server, and hit "Authorize"
- Check out `config.json` for any configuration you might want to do. It's set up to work well out of the box, but you may want to add admins, change pathing, or modify the number of votes required for a skip.

#### Windows Installation
- Nothing else to do! Everything should work just fine.

#### Linux Installation
- Install [Wine](https://www.winehq.org/) to get the TTS executable working.

#### Headless Installation
- Install Xvfb with with your preferred package manager (`apt install xvfb` on Ubuntu, for example)
- Invoke Xvfb automatically on reboot with a cron job (`sudo crontab -e`), by adding `@reboot Xvfb :0 -screen 0 1024x768x16 &` to your list of jobs.
- Set `headless` to be `true` in `config.json`

## Usage
- `cd` into the project's root
- Activate the virtualenv
- `cd` into `hawking/code/` (Note, you need `hawking.py` to be in your current working directory, as theres some weird pathing issues with the required files for `say.exe`
- `python hawking.py`

## Commands
These commands allow for the basic operation of the bot, by anyone.
- `\say [text]` - Tells the bot to speak [text] in the voice channel that you're currently in.
- `\skip` - Skip a phrase that you've requested, or start a vote to skip on someone else's phrase.
- `\music [options] [notes]` - Sings the [notes] aloud. See music.py's music() command docstring for more info about music structure. Currently rewriting to be even more flexible.
- `\summon` - Summons the bot to join your voice channel.
- `\help` - Show the help screen.

## Admin Commands
Admin commands allow for some users to have a little more control over the bot. For these to work, the `admin` array in `config.json` needs to have the desired usernames added to it. Usernames should be in the `Username#1234` format that Discord uses.
- `\admin skip` - Skip whatever's being spoken at the moment, regardless of who requested it.
- `\admin reload_phrases` - Unloads, and then reloads the preset phrases (found in `phrases.json`). This is handy for quickly adding new presets on the fly.
- `\admin reload_cogs` - Unloads, and then reloads the cogs registered to the bot (see admin.py's register_module() method). Useful for debugging.
- `\help admin` - Show the help screen for the admin commands.


## Lastly...
Also included are some built-in phrases from [this masterpiece](https://www.youtube.com/watch?v=1B488z1MmaA). Check out the `Phrases` section in the `\help` screen.

Lastly, be sure to check out the [Moonbase Alpa](https://steamcommunity.com/sharedfiles/filedetails/?id=482628855) moon tunes guide on Steam.

Tested on Windows 10, and Ubuntu 16.04.
