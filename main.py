## FreeBot

import argparse, sys, os, re, string
import requests, subprocess
from pathlib import Path

def main():

    # Parser
    parser = argparse.ArgumentParser(description="FreeBot file renamer for Movies and TV Shows")

    # Add arguments
    parser.add_argument(
        "-t", "--type",
        type=str,
        choices=['movie', 'serie'],
        required=True,
        help="Define movie or serie to rename")

    parser.add_argument(
        "-i", "--input",
        type=str,
        required=True,
        help="Define source path to rename")

    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Define destination path to rename, optional")

    parser.add_argument(
        "-mf", "--movieformat",
        type=str,
        default="{n} ({y}) [tbdbid-{id}] [{res}] [{run} mins]",
        help="Define naming format, optional")

    parser.add_argument(
        "-m", "--mode",
        type=str,
        choices=['test', 'rename', 'copy', 'move', 'hardlink', 'softlink'],
        required=True,
        help="Define source path to rename")

    # Parse the arguments
    args = parser.parse_args()

    ## check format
    context ={
        "id": None,
        "y": None,
        "n": None,
        "res": None,
        "run": None
    }
    formatter = string.Formatter()
    try:
        keys = {fname for _, fname, _, _ in formatter.parse(args.movieformat) if fname}
        missing = keys - context.keys()
        if missing:
            sys.exit(f"Movie Format not recognized: {', '.join(missing)}")
    except ValueError as e:
        sys.exit(f"Bad format: {e}")


    ## Get all files in the path
    path = Path(args.input)
    if not path.exists():
        sys.exit("Input path does not exist, exiting...")

    files = [f for f in path.iterdir() if f.is_file() and f.suffix in {".mkv", ".mp4", ".avi"}]
    if len(files) > 1:
        sys.exit("Multiple video files found, exiting...")

    print("Video file found:\n")
    filename = files[0].name
    ext = files[0].suffix
    print(filename)
    m = re.search(r"(?:\((\d{4})\)|(?<!\d)(\d{4})(?!\d))", filename)
    if m:
        year = m.group(1) or m.group(2)
        print(f"Year found on filename:{year}")
    else:
        print("Year not found on filename")

    movie_name = filename[:m.start()-1]
    print(f"File to probe: {files[0]}")

    ## Get Runtime, Resolution
    out = subprocess.run(
        ["ffprobe", "-v", "error",
         "-select_streams", "v:0",
         "-show_entries", "stream=height,field_order",
         "-show_entries", "format=duration",
         "-of", "csv=p=0",
         files[0]],
        capture_output=True,
        text=True
    )
    lines = out.stdout.strip().splitlines()
    height, field = lines[0].split(",")
    runtime = float(lines[1]) / 60

    print(f"Runtime extracted: {runtime}")
    if field == "progressive":
        height = str(height)+"p"
    else:
        height = str(height)+"i"
    print(f"Resolution: {height}")

    ## TMDB stuff
    ACCESS_TOKEN = os.environ.get("TMDB")
    search_url = "https://api.themoviedb.org/3/search/movie"
    headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "accept": "application/json"
    }
    if "year" in locals():
        params = {
        "query": movie_name,
        "primary_release_year": year
        }
    else:
        params = {
            "query": movie_name
        }
    print(f"Query: {movie_name}")

    response = requests.get(search_url, headers=headers, params=params)
    print(response.status_code)
    data = (response.json())
    print(data)

    for n in data["results"]:
        print(n["release_date"], n["original_title"], n["vote_average"], n["vote_count"])

    tmdb_id = data["results"][0]["id"]
    tmdb_title = data["results"][0]["original_title"]
    tmdb_year = data["results"][0]["release_date"][:4]

    movie_details = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
    response = requests.get(movie_details, headers=headers)
    print(response.status_code)
    details = (response.json())

    print(f"Runtime from TMDB: {details['runtime']}")
    runtime_diff = abs(details['runtime'] - runtime)
    print(f"Difference: {runtime_diff}")
    if runtime_diff < 2:
        print("Match!")
    else:
        print("Not Match")

    ## Renaming
    context ={
        "id": tmdb_id,
        "y": tmdb_year,
        "n": tmdb_title,
        "res": height,
        "run": int(runtime)
    }

    print(f"Format: {args.movieformat.format(**context)}")
    dest_name = args.movieformat.format(**context) + ext

    if args.mode is not None:
        op = input("Mode not specified: Test, Rename, Copy, Move, Hardlink, Softlink")
    else:
        op = args.mode

    if op in("t", "test"):
        pass
    elif op in("h", "hardlink"):
        if args.output is None:
            dest_path = args.input
        else:
            dest_path = args.output
        dest_file = Path(dest_path) / dest_name
        confirm = input(f"Will hardlink {files[0]} to {dest_file}, confirm? y/n")
        if confirm in("y", "Y"):
            Path(dest_path).mkdir(parents=True, exist_ok=True)
            #Path(dest_file).hardlink_to(files[0])
            os.link(files[0], dest_file)
        else:
            sys.exit()
if __name__ == "__main__":
    main()
