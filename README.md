# Book Recommender

[English](README.md) | [Magyar](README.hu.md)

A Flask web application that recommends books from a Neo4j graph. It combines
catalog metadata, popularity, content similarity, and collaborative filtering.
This is an experimental prototype developed as part of a thesis, not a
production-ready application. Its purpose is to demonstrate and evaluate a
hybrid book-recommendation approach.

The repository contains the application and model-building code, but does not
include a database import or seed dataset: Neo4j must already contain data in
the shape described below.

> **Database required:** The application is not runnable as a working
> recommender without a reachable Neo4j database populated with the required
> schema and data. This repository does not include a database or sample data.
> Without Neo4j configured and running, recommendations and search will not
> work.

## Project status

This is a thesis research prototype intended to demonstrate and evaluate a
hybrid recommendation approach, not a finished, production-ready service. It
combines Neo4j graph filtering with content-based TF-IDF similarity and
item-based k-nearest-neighbor collaborative filtering. The thesis prototype
used English-language book data; supporting Hungarian-language content is
identified as future work.

The results below are the measurements recorded in [`tests/results/`](tests/results/),
not guarantees for other data, machines, or deployments. The benchmark ran 20
requests per scenario:

| Scenario | Average latency | Min–max latency | Average CPU | Peak CPU | Average RAM | Peak RAM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | 185.99 ms | 168.93–233.59 ms | 2.9% | 8.0% | 719.00 MB | 719.05 MB |
| Complex graph filtering | 25.10 ms | 18.77–98.52 ms | 2.6% | 6.0% | 719.05 MB | 719.05 MB |
| Hybrid (full load) | 236.61 ms | 180.70–445.88 ms | 41.9% | 57.9% | 760.10 MB | 874.21 MB |

The separate offline collaborative evaluation used a sample of 500 and
recorded Precision 6.35%, Recall 4.43%, F1 0.0500, nDCG 0.0598, and MRR 0.1320
on 2025-12-14. Offline rating data is incomplete: a relevant book that a user
has not rated may be counted as a false negative. These local test results do
not represent a live deployment or user study.

The current app requires a separately configured and populated Neo4j database,
builds or loads local recommendation-model caches, and runs with Flask's
development server and debug mode enabled. Before production use, it would
need appropriate deployment configuration, security and privacy review,
operational monitoring, and validation with the intended data and users.
Possible future directions discussed in the thesis include Hungarian-language
catalog data, live-environment testing, deeper content analysis, and
distributed deployment.

## Requirements and configuration

- Python with the packages used by the project: `Flask`, `python-dotenv`,
  `neo4j`, `numpy`, `pandas`, `scipy`, and `scikit-learn`.
- A running Neo4j database reachable by the application.
- For the optional benchmark scripts, `requests` and `psutil` are also used.

Install the Python dependencies from the project root:

```powershell
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and edit the Neo4j connection settings:

```dotenv
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=change-me
```

`app.py` loads this file at startup and reports an error if any of these
variables is missing. Do not commit real credentials. The root `.gitignore`
excludes `.env`; `.env.example` contains placeholders only.

Start the application from the project root:

```powershell
python app.py
```

Starting the Flask server is not enough to use the recommender: Neo4j must be
running, the `.env` connection settings must be valid, and the database must be
populated with the schema and data described below. The app currently catches
model-initialization errors and may start despite a database connection
failure, but its database-dependent features will not be operational.

The Flask development server listens on `http://127.0.0.1:5000`. Its debug mode
is enabled in `app.py`; do not expose this development server directly to an
untrusted network.

## Neo4j graph model

The application uses these labels, properties, and relationship directions:

| Node label | Required properties used by the app | Purpose |
| --- | --- | --- |
| `Book` | `book_id`, `title` | Catalog entries and recommendation candidates. |
| `Author` | `author_id`, `name` | Book authors and author searches/preferences. |
| `Tag` | `tag_id`, `tag_name` | Genres/tags and genre searches/preferences. |
| `User` | `user_id` | Users who have rated books. |
| `AgeGroup` | `id` | Age-range values used to filter books. |

| Relationship | Required property | Direction and purpose |
| --- | --- | --- |
| `(:Author)-[:AUTHOR_OF]->(:Book)` | None | Associates authors with books. |
| `(:Book)-[:HAS_TAG]->(:Tag)` | None | Associates books with genres/tags. |
| `(:AgeGroup)-[:READ_BY]->(:Book)` | None | Associates age ranges with suitable books. |
| `(:User)-[:RATED]->(:Book)` | `rating` | A user's numeric rating for a book. |

Use stable, non-null identifiers for `book_id`, `author_id`, and `tag_id`.
Their values must be consistent between the graph and the IDs submitted by the
web interface. In particular, liked-book IDs are used to look up both
recommendation models, while author and tag IDs are used in graph filters.
`User.user_id` must also be populated for collaborative model training. Ratings
should be numeric and on a consistent scale.

Additional `Book` properties used by filtering and ranking are:

| Property | Expected value | Used for |
| --- | --- | --- |
| `average_rating` | Numeric (or numeric text) | Minimum-rating filter and popularity. |
| `ratings_count` | Integer (or integer text) | Popularity calculation. |
| `original_publication_year` | Integer | Publication-year range filter. |

Books without a `title` are excluded from recommendations and the content
model. Missing rating/count values are treated as zero for popularity. Book
authors and tags can have multiple relationships; the recommender collects all
matching authors and tags.

### Example schema setup

The following Cypher creates useful uniqueness constraints and the full-text
indexes required by autocomplete search. Run it in Neo4j Browser or another
Neo4j Cypher client. Constraints do not create or import catalog data.

```cypher
CREATE CONSTRAINT book_id_unique IF NOT EXISTS
FOR (b:Book) REQUIRE b.book_id IS UNIQUE;

CREATE CONSTRAINT author_id_unique IF NOT EXISTS
FOR (a:Author) REQUIRE a.author_id IS UNIQUE;

CREATE CONSTRAINT tag_id_unique IF NOT EXISTS
FOR (t:Tag) REQUIRE t.tag_id IS UNIQUE;

CREATE CONSTRAINT user_id_unique IF NOT EXISTS
FOR (u:User) REQUIRE u.user_id IS UNIQUE;

CREATE CONSTRAINT age_group_id_unique IF NOT EXISTS
FOR (ag:AgeGroup) REQUIRE ag.id IS UNIQUE;

CREATE FULLTEXT INDEX bookTitleIndex IF NOT EXISTS
FOR (b:Book) ON EACH [b.title];

CREATE FULLTEXT INDEX authorNameIndex IF NOT EXISTS
FOR (a:Author) ON EACH [a.name];

CREATE FULLTEXT INDEX genreNameIndex IF NOT EXISTS
FOR (t:Tag) ON EACH [t.tag_name];
```

The age-group IDs must match the values sent by the UI exactly:
`0-12`, `13-17`, `18-25`, `26-40`, `41-60`, and `60+`. For example, the
corresponding graph shape is:

```cypher
(:AgeGroup {id: "18-25"})-[:READ_BY]->(:Book {book_id: "book-123"})
```

An example rating relationship is:

```cypher
(:User {user_id: "user-1"})-[:RATED {rating: 4.5}]->
(:Book {book_id: "book-123"})
```

The sample IDs above are illustrative only. Import or create real books,
authors, tags, age groups, users, ratings, and relationships for the
application to return useful results.

## How the application works

1. **Startup and database connection.** `app.py` reads the Neo4j connection
   settings from `.env`, creates the database driver, and initializes the
   recommendation services.
2. **Model loading or training.** The content model reads each titled book,
   its tag names, and author names. It builds a TF-IDF representation and saves
   it to `data/vector_model.pkl`. The collaborative model reads
   `(:User)-[:RATED]->(:Book)` records, builds a sparse book/user rating
   matrix, fits cosine-distance nearest neighbors, and saves
   `data/collab_model.pkl`. Existing cache files are loaded on later starts;
   delete the relevant cache file after changing the underlying graph data if
   you want that model rebuilt.
3. **Search/autocomplete.** The browser calls `GET /api/search?q=...&type=...`.
   Search uses the `bookTitleIndex`, `authorNameIndex`, and `genreNameIndex`
   full-text indexes. It returns at most ten matches. Search terms shorter
   than two characters return an empty list.
4. **Recommendation request.** The browser posts the user's constraints,
   preferences, and result settings to `POST /recommend`. The server filters
   out books without titles, applies enabled age/year/author/tag filters and
   exclusions, and ranks the remaining books.
5. **Hybrid ranking.** The score combines matching preferred genres and
   authors with optional content-based and collaborative scores. A book with
   no personal score is ordered by popularity, calculated as
   `average_rating * log10(ratings_count + 1)`. Otherwise popularity adds a
   small tie-breaking contribution. A configurable random component can vary
   ordering slightly. The result limit is controlled by the request settings.
6. **Result page.** The matching books, author names, and scores are rendered
   using `templates/result.html`.

Content-based and collaborative scores require selected liked books and
successfully loaded/fitted models. The content model compares book title,
author, and tag text. The collaborative model finds books rated similarly by
users. If there are no usable liked books or the corresponding weight is zero,
that component contributes no score.

At startup, model initialization failures are printed as a warning and the
Flask application continues running. A missing `.env` setting, on the other
hand, stops startup with an explicit configuration error.

## HTTP routes

| Route | Method | Description |
| --- | --- | --- |
| `/` | `GET` | Displays the recommendation form. |
| `/recommend` | `POST` | Accepts JSON preferences/constraints and renders the results page. |
| `/api/search` | `GET` | Returns JSON autocomplete results for `book`, `author`, or `genre` searches. |

The recommendation request has this general shape:

```json
{
  "constraints": {
    "age": {"active": false, "values": []},
    "period": {"active": false, "custom_min": "", "custom_max": ""},
    "authors": {"active": false, "values": []},
    "genres": {"active": false, "values": []},
    "excluded_authors": {"active": false, "values": []},
    "excluded_genres": {"active": false, "values": []}
  },
  "preferences": {
    "genres": {"weight": 0, "values": []},
    "authors": {"weight": 0, "values": []},
    "books": {"values": [], "weight_content": 0, "weight_collab": 0}
  },
  "settings": {"min_rating": 0, "randomness": 0.1, "limit": 35}
}
```

IDs in `values` are the `tag_id`, `author_id`, or `book_id` values returned by
search. The frontend constructs this payload and normally provides its own
weight and settings values.

## Evaluation scripts

- `tests/evaluate_collaborative.py` loads the same root `.env`, queries ratings,
  and evaluates a nearest-neighbor recommender using a train/test split. It
  reports precision, recall, F1, nDCG, and MRR. The evaluation needs enough
  users/ratings to form the split and find neighbors.
- `tests/benchmark_suite.py` sends repeated requests to a running Flask server
  and records response-time and process-resource measurements.
