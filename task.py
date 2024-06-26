import ast
import functools
import logging
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from collections import defaultdict


logging.basicConfig(level = logging.INFO)
logger = logging.getLogger()


def dataset_info(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        logger.info(f'Size of dataset: {result.shape[0]}')
        logger.info(f'Size of dataset without duplicates: {result.drop_duplicates().shape[0]}')
        return result
    return wrapper


@dataset_info
def prepare_metadata(path: str) -> pd.DataFrame:
    logger.info('\n---- Metadata')

    metadata = pd.read_csv(path, 
                       converters={'genres': ast.literal_eval},
                       low_memory=False)
    metadata = metadata[['id', 'title', 'release_date', 'genres', 'imdb_id']]

    # getting a year release and genres
    metadata['release_year'] = pd.to_datetime(metadata['release_date'], errors='coerce').apply(lambda x: x.date().year)
    metadata['genre_list'] = metadata['genres'].apply(lambda g: '|'.join(sorted([x['name'].lower() for x in g])))
    metadata['genre_list'] = metadata['genre_list'].replace('', np.nan)
    metadata = metadata[['id', 'title', 'release_year', 'genre_list', 'imdb_id']]
    logger.info(f'The number of release_date is nan: {metadata['release_year'].isna().sum()}')
    logger.info(f'The number of genres is nan: {metadata['genre_list'].isna().sum()}')

    # transforming id and imdbId to a valid format
    metadata = metadata[metadata['id'].apply(lambda x: 0 if '-' in x else 1) == 1]
    metadata.rename(columns={'imdb_id': 'imdbId'}, inplace=True)
    metadata['imdbId'] = metadata['imdbId'].apply(lambda x: np.int64(x[2:]) if type(x).__name__ == 'str' else x)
    metadata = metadata.astype({'id': 'int64', 'release_year': 'int64'}, errors='ignore')

    logger.info(f'Check id for nan: {metadata['id'].isna().sum()}')
    logger.info(f'Check imdbId for nan: {metadata['imdbId'].isna().sum()}')
    metadata = metadata[~metadata['imdbId'].isna()]

    logger.info(f'Count of unique id: {metadata['id'].nunique()}')

    return metadata


@dataset_info
def prepare_credits(path: str) -> pd.DataFrame:
    logger.info('\n---- Credits')
    credits = pd.read_csv(path, converters={'crew': ast.literal_eval})
    credits = credits[['id', 'crew']]
    credits['director'] = credits['crew'].apply(lambda info: '|'.join(sorted([x['name'] for x in info if x['job'] == 'Director'])))
    logger.info(f'Count of unique id: {credits['id'].nunique()}')
    return credits[['id', 'director']]


@dataset_info
def prepare_ratings(path: str) -> pd.DataFrame:
    logger.info('\n---- Ratings')
    ratings = pd.read_csv(path)
    logger.info(f'Check how many users have several votes for one movie: {ratings.shape[0] == ratings.groupby(['movieId', 'userId'])['timestamp'].max().shape[0]}')
    ratings = ratings.groupby('movieId')['rating'].mean().reset_index()
    logger.info(f'Count of unique movieId: {ratings['movieId'].nunique()}')
    return ratings


@dataset_info
def prepare_links(path: str) -> pd.DataFrame:
    logger.info('\n---- Links')
    return pd.read_csv(path)


@dataset_info
def create_final_dataset(metadata: pd.DataFrame, credits: pd.DataFrame, ratings: pd.DataFrame, links: pd.DataFrame) -> pd.DataFrame:
    data = metadata.merge(credits, on='id', how='left').drop_duplicates()
    data = data.astype({'imdbId': 'int64'})
    ratings = ratings.merge(links, on='movieId', how='left')[['imdbId', 'rating']]
    data = data.merge(ratings, on='imdbId', how='left')
    logger.info(f'Count of unique id: {data['id'].nunique()}')
    return data


def info_for_task(data: pd.DataFrame, ntop: int = 5):
    data = data.sort_values(by=['rating', 'genre_list'], na_position='last', ascending=False)

    logger.info('\nInfo for the task')
    logger.info(f'The number of the unique movies: {data['id'].nunique()} \n')
    logger.info(f'The average rating of all the movies: {round(data['rating'].mean(), 2)} \n')

    logger.info(f'The top {ntop} highest rated movies:')
    max_rating = data['rating']
    top_movies = data[data['rating'] == max_rating]
    if top_movies.shape[0] > ntop:
        top_movies = top_movies.dropna().sample(n=ntop)

    for movie in top_movies.to_dict('index').values():
        logger.info(f'{movie['title']} - {int(movie['release_year'])} - {movie['genre_list']} by {movie['director']}')

    logger.info('\nCount of movies per year:')
    stat_per_year = data.groupby('release_year')['id'].count().reset_index()
    for year in stat_per_year.to_dict('index').values():
        logger.info(f'{int(year['release_year'])} year - {year['id']} movies')
    
    p = sns.barplot(stat_per_year, x='release_year', y='id')
    for ind, label in enumerate(p.get_xticklabels()):
        if not ind % 10:
            label.set_visible(True)
        else:
            label.set_visible(False)
    _ = plt.xticks(rotation=30)
    plt.xlabel('Year')
    plt.ylabel('The count of movies')
    plt.show()

    movies_in_genres = defaultdict(int)
    for movie in data['genre_list'].values:
        if movie is np.nan:
            continue
        if len(movie) != 1:
            movie =  movie.split('|')
        for g in movie:
            movies_in_genres[g] += 1

    movies_in_genres = dict(sorted(movies_in_genres.items(), key=lambda item: item[1], reverse=True))

    logger.info('\nThe number of movies in each genre: ')
    for genre, n in movies_in_genres.items():
        logger.info(f'{genre} - {n}')

