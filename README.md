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

### 1. Download the OSM PBF File

Download the latest Western Zone OSM extract (Mumbai area) using `wget`:

```bash
wget -O western-zone-latest.osm.pbf https://download.geofabrik.de/asia/india/western-zone-latest.osm.pbf
```

### 2. **Install PostgreSQL, PostGIS and osm2pgsql**

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib postgis osm2pgsql
```

### 3. Connect to PostgreSQL

Switch to the `postgres` system user and open the PostgreSQL shell:

```bash
sudo -u postgres psql
```

You should see the psql prompt:
```bash
postgres=#
```

### 4. Create a PostgreSQL User and Database

Inside the `psql` shell, run the following commands to create a new user, give them permissions to create databases, and create the `mumbai` database:

```sql
CREATE USER your_username WITH PASSWORD 'your_password';
ALTER USER your_username CREATEDB;
CREATE DATABASE mumbai OWNER your_username;
```

### 5. Connect to the `mumbai` Database

Inside the `psql` shell, connect to the newly created database:

```sql
\c mumbai
```

You should now see the prompt change to indicate you are connected to the mumbai database:
```bash
mumbai=#
```

### 6. Enable Required PostgreSQL Extensions

While connected to the `mumbai` database, run the following commands to enable the necessary extensions:

```sql
CREATE EXTENSION postgis;
CREATE EXTENSION hstore;
CREATE EXTENSION pg_trgm;
```

### 7. Import the OSM Data into PostgreSQL

Use `osm2pgsql` to populate the `mumbai` database with the downloaded OSM PBF file. Replace `osm_user` with the database user you created and connect via `127.0.0.1`:

```bash
osm2pgsql -d mumbai -U your_username -W -H 127.0.0.1 --create --slim -G --hstore western-zone-latest.osm.pbf
```
> This will populate the database with tables: `planet_osm_point`, `planet_osm_polygon`, `planet_osm_line`.

### 8. **Verify tables**

Open the PostgreSQL shell: 

```bash
sudo -u postgres psql
```

Connect to `mumbai` database:

```bash
\c mumbai
```

List Tables:

```bash
\dt
```

You should see `planet_osm_point`, `planet_osm_polygon`, `planet_osm_line`.

---

## Python Setup (Virtual Environment)

### It is recommended to use a virtual environment for installing dependencies:

```bash
# Create a virtual environment
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Upgrade pip inside the environment
pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt
```

### 8. Set Up the `.env` File

Create a `.env` file in the root of your project:

```env
# Google Gemini AI API key
GEMINI_API_KEY=your_gemini_api_key_here

# PostgreSQL database credentials
USERNAME=your_username
PASSWORD=your_password
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
