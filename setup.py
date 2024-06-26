import constants as const
import sys
import task


def main():
    metadata = task.prepare_metadata(const.PATH_METADATA)
    credits = task.prepare_credits(const.PATH_CREDITS)
    ratings = task.prepare_ratings(const.PATH_RATINGS)
    links = task.prepare_links(const.PATH_LINKS)
    data = task.create_final_dataset(metadata, credits, ratings, links)
    task.info_for_task(data)
    del data['imdbId']
    data.head().to_json(const.PATH_OUTPUT_JSON, orient='records')
    return 0


if __name__ == '__main__':
    sys.exit(main()) 
