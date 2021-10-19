import json
from pathlib import Path
from operator import itemgetter

PATH = Path(__file__).resolve().parent.parent


def main():
    with open(PATH / 'config.json') as config_file:
        config = json.load(config_file)
        config['equipment_families'] = sorted(config['equipment_families'], key=itemgetter('model'))
        config['consumable_families'] = sorted(config['consumable_families'], key=itemgetter('model'))

    with open(PATH / 'config.json', 'w') as config_file:
        json.dump(config, config_file, indent=2)


if __name__ == '__main__':
    main()
