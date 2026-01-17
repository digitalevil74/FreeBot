## FreeBot

import argparse, sys, os, re
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
        help="Define destination path to rename")

    parser.add_argument(
        "-m", "--mode",
        type=str,
        choices=['test', 'rename', 'copy', 'move', 'hardlink', 'softlink'],
        required=True,
        help="Define source path to rename")

    # Parse the arguments
    args = parser.parse_args()

    ## Get all files in the path
    path = Path(args.input)
    if not path.exists():
        sys.exit("Input path does not exist, exiting...")

    files = [f for f in path.iterdir() if f.is_file() and f.suffix in {".mkv", ".mp4", ".avi"}]
    if len(files) > 1:
        sys.exit("Multiple video files found, exiting...")

    print("Video file found:\n")
    filename = files[0].name
    print(filename)
    m = re.search(r"(?:\((\d{4})\)|(?<!\d)(\d{4})(?!\d))", filename)
    if m:
        year = m.group(1) or m.group(2)
        print(f"Year found on filename:{year}")
        #year = m.group()
    else:
        print("Year not found on filename")

    movie_name = filename[:m.start()-1]
    print(f"File to probe: {files[0]}")
    ## Get Duration
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

    #height, field, runtime = out.stdout.strip().split(",")
    #runtime = float(runtime) / 60
    print(f"Runtime extracted: {runtime}")
    if field == "progressive":
        print(f"Resolution: {height}p")
    else:
        print(f"Resolution: {height}i")

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

    movie_id = data["results"][0]["id"]

    movie_details = f"https://api.themoviedb.org/3/movie/{movie_id}"
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

if __name__ == "__main__":
    main()
