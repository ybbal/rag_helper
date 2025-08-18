import sys

from dotenv import load_dotenv


if __name__ == '__main__':
    load_dotenv("config.env", verbose=True)

    sys.path.append("src")

    from tg_bot.bot import get_app
    app = get_app()
    app.run_polling()
