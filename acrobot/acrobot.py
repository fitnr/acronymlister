from argparse import ArgumentParser
import twitter_bot_utils as tbu
from . import Acrobot, __version__ as version

def main():
    parent = tbu.args.parent(version=version)
    parser = ArgumentParser(parents=[parent])
    parser.add_argument('database')
    parser.set_defaults(screen_name='acronymlister')
    args = parser.parse_args()

    api = tbu.API(args)
    bot = Acrobot(args.database, log=api.logger)

    try:
        update = bot.compose()
        if not args.dry_run:
            api.update_status(**update)
            bot.checkoff_page()

    except Exception as e:
        api.logger.error("{}".format(e))


if __name__ == '__main__':
    main()
