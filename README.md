Simple discord bot with some utilities. Mostly an experiment in understanding how the discord python
API works and to automate some simple tasks.


# To do.
- Replace the json database file with a proper database and/or ORM implementation.
- EntryBanner
    - Add proper user access control instead of hiding behind admin users.
- Switch to tox for testing?


# How to run.
Starting froma fresh checkout, the bot can simply be run by making the virtual env with it's dependecies
and running it from source. This can all be done using make commands:

```
# Make virtual env.
> make venv

# Set config envvars and run the bot.
env IKA_DISCORD_TOKEN=$DISCORD_BOT_TOKEN IKA_LOG_PATH=$LOG_DIRECTORY IKA_DATA_PATH=$DATA_DIRECTORY make run
```
