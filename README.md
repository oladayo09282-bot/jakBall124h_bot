# BookRecBot

Tell the bot a genre, get a book recommendation back. No external API —
recommendations come from a curated list built into the bot.

## Deploy steps:
1. Create bot with @BotFather, get BOT_TOKEN
2. Push all files to GitHub (git init, add, commit, push)
3. Deploy on Railway from the GitHub repo (worker service)
4. Set BOT_TOKEN and DB_PATH variables
5. Test by sending /start then typing a genre like "fantasy"
