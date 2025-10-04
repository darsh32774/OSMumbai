# Mumbai OpenStreetMap Query Processor

A Python tool that allows you to query Mumbai OpenStreetMap (OSM) data using **natural language**. Powered by **Google Gemini AI**, this project converts English queries into SQL for a **PostgreSQL/PostGIS** database and visualizes results on interactive **Folium maps**.

---

## Features

* Natural language → SQL conversion using Gemini AI
* Spatial queries (`ST_Within`, `ST_DWithin`) for points, polygons, and lines
* Fuzzy text matching using `pg_trgm`
* Interactive map visualization of results using Folium
* Tabular output of query results
* Handles amenities, shops, education, tourism, and leisure features

---

## Requirements

* Python 3.10+
* PostgreSQL 14+
* PostGIS extension
* Python packages: see `requirements.txt`

`requirements.txt` includes:

```
psycopg2
tabulate
folium
python-dotenv
google-generativeai
```

> **Note:** PostgreSQL/PostGIS are system-level dependencies. Install via your OS package manager (e.g., `apt`, `brew`) and ensure PostGIS and `hstore` are enabled in your database.

---

## Database Setup

1. **Download OSM PBF file**

The `.pbf` file is too large for GitHub, so download it directly:

[Download Western Zone OSM PBF](https://download.geofabrik.de/asia/india/western-zone-latest.osm.pbf)

2. **Install PostgreSQL and PostGIS**

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib postgis postgresql-14-postgis-3
```

3. **Create a database**

```bash
sudo -u postgres psql
CREATE DATABASE mumbai;
\c mumbai
CREATE EXTENSION postgis;
CREATE EXTENSION hstore;
CREATE EXTENSION pg_trgm;
```

4. **Import OSM `.pbf` file using `osm2pgsql`**

```bash
sudo apt install osm2pgsql
osm2pgsql -d mumbai -U your_postgres_user --create --slim -G --hstore western-zone-latest.osm.pbf
```

> This will populate the database with tables: `planet_osm_point`, `planet_osm_polygon`, `planet_osm_line`.

5. **Verify tables**

```sql
\dt
```

You should see `planet_osm_point`, `planet_osm_polygon`, `planet_osm_line`.

---

## Setup Python Environment

1. **Clone this repository**

```bash
git clone <repo_url>
cd <repo_folder>
```

2. **Install Python dependencies**

```bash
pip install -r requirements.txt
```

3. **Set up Gemini API Key**

Create a `.env` file in the project root:

```
GEMINI_API_KEY=your_api_key_here
```

---

## Running the Query Processor

```bash
python your_script.py
```

* Enter queries in natural language, e.g.:

  * `"Find restaurants in Bandra West"`
  * `"Show hospitals near Andheri East"`
* The script generates SQL, executes it, displays results, and saves a Folium map.
* To exit, type `quit`, `exit`, or press `Ctrl+C`.

---

## Notes

* The script uses **LIMIT** to avoid overwhelming results.
* Geometry columns are automatically detected for mapping.
* Queries are executed directly; do not expose your database publicly without proper security.
* Make sure your coordinates fall within Mumbai (lat 18–20, lon 72–74) for correct map visualization.

---

## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.
