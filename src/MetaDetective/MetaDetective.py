#!/usr/bin/env python3

"""Unleash Metadata Intelligence with MetaDetective. Your Assistant Beyond Metagoofil.

Created By  : Franck FERMAN @franckferman
Created Date: 27/08/23
Version     : 1.0.9 (09/11/23)
"""

import argparse
import datetime
import hashlib
import http.client
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
import urllib.request
from argparse import Namespace
from collections import defaultdict
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse, urljoin, quote, urlsplit


BANNER = r"""
___  ___     _       ______     _            _   _     	 	 _==\/==_
|  \/  |    | |      |  _  \   | |          | | (_)    		/________\
| .  . | ___| |_ __ _| | | |___| |_ ___  ___| |_ ___   _____	/ 0 \ o b
| |\/| |/ _ \ __/ _` | | | / _ \ __/ _ \/ __| __| \ \ / / _ \	\___/'  |
| |  | |  __/ || (_| | |/ /  __/ ||  __/ (__| |_| |\ V /  __/	  H\__/'
\_|  |_/\___|\__\__,_|___/ \___|\__\___|\___|\__|_| \_/ \___|	  H
"""

FIELDS = [
    "File Name", "Title", "Creator", "Author", "Last Modified By", "Create Date", "Modify Date",
    "Hyperlinks", "Company", "Creator Tool", "Producer", "Software", "Camera Model Name", "Image Description",
    "Make", "Camera ID", "Camera Type 2", "Serial Number", "Internal Serial Number", "GPS Status", "GPS Altitude",
    "GPS Latitude", "GPS Longitude", "GPS Position", "Formatted GPS Position", "Address", "Map Link"
]
UNIQUE_FIELDS = [
    "Creator", "Author", "Last Modified By", "Hyperlinks", "Creator Tool",
    "Producer", "Software", "Camera Model Name", "Image Description", "Make",
    "Camera ID", "GPS Position", "Formatted GPS Position", "Map Link"
]

EXTENSIONS = [
    "csv", "xml",
    "email", "eml", "emlx", "msg", "oft", "ost", "pst", "vcf",
    "ai", "bmp", "gif", "ico", "jpeg", "jpg", "png", "ps", "psd", "svg", "tif", "tiff", "wepb",
    "key", "odp", "pps", "ppt", "pptx",
    "odf", "xls", "xlsm", "xlsx",
    "ico", "mp4", "mov",
    "doc", "docx", "odt", "pdf", "rtf", "tex", "wpd"
]

EXIFTOOL_NOT_INSTALLED = "Error: exiftool is not installed. Please install it to continue."
EXIFTOOL_EXECUTION_ERROR = "Error: exiftool encountered an error."

# Global debug mode flag (set from args.debug in main()):
DEBUG_MODE = True

NOMINATIM_HOST = "nominatim.openstreetmap.org"
USER_AGENT = 'MetaDetective/1.0.9'
NOMINATIM_ENDPOINT = "/reverse?format=jsonv2&lat={lat}&lon={lon}"

NOMINATIM_LINK = "https://nominatim.openstreetmap.org/ui/reverse.html?lat={lat}&lon={lon}"

CSS_STYLE = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500&display=swap');

    body {
        font-family: 'Roboto', 'Helvetica', 'Arial', sans-serif;
        color: #EAEAEA;
        padding: 20px;
        margin: 0;
        background: linear-gradient(120deg, #121212, #1E1E1E, #121212);
        background-size: 300% 300%;
        animation: gradientBG 15s ease infinite;
    }

    @keyframes gradientBG {
        0% {
            background-position: 0% 50%;
        }
        50% {
            background-position: 100% 50%;
        }
        100% {
            background-position: 0% 50%;
        }
    }

    .header {
        background-color: rgba(51, 51, 51, 0.8);
        color: white;
        padding: 10px 0;
        text-align: center;
        border-radius: 5px;
        margin-bottom: 20px;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.5);
        text-shadow: 2px 2px 2px rgba(0, 0, 0, 0.2);
    }

    .metadata-entry {
        background-color: rgba(30, 30, 30, 0.8);
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 15px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.6);
        transition: all 0.3s ease;
        opacity: 0;
        transform: translateY(-20px);
        animation: fadeInUp 0.5s forwards 0.2s ease-out;
    }

    @keyframes fadeInUp {
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .metadata-entry:hover {
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.8);
        transform: scale(1.02);
    }

    p {
        margin: 5px 0;
        text-shadow: 1px 1px 1px rgba(0, 0, 0, 0.1);
    }

    strong {
        color: #EAEAEA;
    }

    h3 {
        color: #BBB;
        border-bottom: 1px solid #444;
        padding-bottom: 10px;
        text-shadow: 1px 1px 1px rgba(0, 0, 0, 0.1);
    }

    hr {
        border: 0;
        border-top: 1px solid #333;
        margin-top: 10px;
    }

    a {
        transition: all 0.3s;
    }

    a:link, a:visited {
        color: #BBB;
        text-decoration: none;
    }

    a:hover {
        color: #FFF;
        text-shadow: 1px 1px 1px rgba(0, 0, 0, 0.2);
        text-decoration: underline;
    }

    a:focus {
        outline: none;
        box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.5);
    }
    </style>
"""

SENTINEL = None


def show_banner() -> None:
    """Print the banner."""
    print(BANNER)


def check_exiftool_installed() -> None:
    """Verify exiftool installation and exit if absent or on execution error."""
    try:
        subprocess.run(["exiftool", "-ver"], capture_output=True, check=True, text=True)
    except FileNotFoundError:
        sys.exit(EXIFTOOL_NOT_INSTALLED)
    except subprocess.CalledProcessError:
        sys.exit(EXIFTOOL_EXECUTION_ERROR)


def dms_to_dd(degrees: int, minutes: int, seconds: float, direction: str) -> float:
    """
    Convert coordinates from DMS (Degree-Minute-Second) to DD (Decimal Degrees).
    """
    if not (0 <= degrees < 180) or not (0 <= minutes < 60) or not (0 <= seconds < 60):
        raise ValueError("Invalid DMS values provided.")

    direction = direction.upper()
    if direction not in ['N', 'S', 'E', 'W']:
        raise ValueError("Invalid direction. Expected one of ['N', 'S', 'E', 'W'].")

    dd = float(degrees) + float(minutes) / 60 + float(seconds) / 3600
    if direction in ['S', 'W']:
        dd *= -1
    return dd


def parse_dms(dms_str: str) -> Optional[Tuple[int, int, float, str]]:
    """
    Parse a DMS (Degree-Minute-Second) string into its components.
    """
    match = re.search(r"(\d+)\s*deg\s*(\d+)'\s*([\d.]+)\"\s*(\w)", dms_str)
    if match:
        deg, min_val, sec, dir_val = match.groups()
        return int(deg), int(min_val), float(sec), dir_val.upper()

    raise ValueError(f"Invalid DMS format: {dms_str}")


def get_metadata(file_path: str, fields: List[str]) -> dict:
    """
    Retrieve specified metadata fields from a file using exiftool.
    """
    try:
        exiftool_output = subprocess.run(
            ["exiftool", file_path],
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error executing exiftool on {file_path}: {e}")
        print()
        return {}
    except UnicodeDecodeError as e:
        print(f"Error decoding output for file {file_path}: {e}")
        print()
        return {}

    field_set = set(fields)
    metadata = {}

    for line in exiftool_output.stdout.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key in field_set and value:
            metadata[key] = value

    # Check for GPS data:
    lat_dd, lon_dd = None, None
    gps_position = metadata.get("GPS Position", None)
    if gps_position:
        lat_str, lon_str = gps_position.split(", ")
        lat_dd = dms_to_dd(*parse_dms(lat_str))
        lon_dd = dms_to_dd(*parse_dms(lon_str))
    else:
        gps_lat = metadata.get("GPS Latitude", None)
        gps_lon = metadata.get("GPS Longitude", None)
        if gps_lat and gps_lon:
            lat_dd = dms_to_dd(*parse_dms(gps_lat))
            lon_dd = dms_to_dd(*parse_dms(gps_lon))

    if lat_dd is not None and lon_dd is not None:
        metadata["Formatted GPS Position"] = f"{lat_dd:.6f}, {lon_dd:.6f}"

    return metadata


def matches_any_pattern(value: str, patterns: List[str]) -> bool:
    """
    Check if a string matches any of the provided regex patterns.
    """
    compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    return any(pattern.search(value) for pattern in compiled_patterns)


def valid_directory(path: str) -> str:
    """
    Validate directory path for argparse.
    """
    if not os.path.exists(path):
        raise argparse.ArgumentTypeError(f"Directory path '{path}' does not exist.")
    if not os.path.isdir(path):
        raise argparse.ArgumentTypeError(f"Path '{path}' is not a directory.")
    return path


def filter_files_by_extension(files: List[str], extensions: List[str]) -> List[str]:
    """
    Filter a list of files to keep only those matching the given extensions.
    """
    if not isinstance(files, list) or not all(isinstance(f, str) for f in files):
        raise TypeError("The 'files' argument must be a list of strings.")
    if not isinstance(extensions, list) or not all(isinstance(ext, str) for ext in extensions):
        raise TypeError("The 'extensions' argument must be a list of strings.")

    ext_set = set(extensions)
    return [file for file in files if file.endswith(tuple(ext_set))]


def get_files(args) -> List[str]:
    """
    Retrieve a list of files from either --directory or --files.
    """
    if args.directory:
        try:
            valid_directory(args.directory)
        except argparse.ArgumentTypeError as e:
            raise ValueError(str(e))

        all_in_dir = [os.path.join(args.directory, f) for f in os.listdir(args.directory)]
        if args.type != ['all']:
            files = filter_files_by_extension(all_in_dir, args.type)
        else:
            files = all_in_dir
    else:
        files = args.files

    if not files:
        raise ValueError("Error: No files found.")

    return files


def get_address_from_coords(lat: str, lon: str) -> str:
    """
    Fetch address from latitude and longitude using the Nominatim API.
    """
    try:
        conn = http.client.HTTPSConnection(NOMINATIM_HOST)
        headers = {'User-Agent': USER_AGENT}
        conn.request("GET", NOMINATIM_ENDPOINT.format(lat=lat, lon=lon), headers=headers)

        res = conn.getresponse()
        data = res.read()

        parsed_data = json.loads(data.decode("utf-8"))
        return parsed_data.get("display_name", "")

    except http.client.HTTPException as e:
        print(f"HTTP error occurred: {e}")
        raise
    except json.JSONDecodeError:
        print("Error decoding JSON response.")
        raise
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise


def format_gps_data(metadata: Dict[str, str]) -> None:
    """
    If 'Formatted GPS Position' exists, fetch the address & map link using Nominatim.
    """
    formatted_gps = metadata.get("Formatted GPS Position")
    if not formatted_gps:
        return

    try:
        lat, lon = formatted_gps.split(", ")
    except ValueError:
        raise ValueError("The 'Formatted GPS Position' data is not in the expected 'lat, lon' format.")

    address = get_address_from_coords(lat, lon)
    if address:
        metadata["Address"] = address

    metadata["Map Link"] = NOMINATIM_LINK.format(lat=lat, lon=lon)


def display_all_metadata(all_metadata: List[Dict[str, Any]], ignore_patterns: List[str]) -> None:
    """
    Print all metadata fields for each file, excluding ignored patterns.
    """
    for metadata in all_metadata:
        format_gps_data(metadata)

        displayed_fields = 0
        for field, value in metadata.items():
            if field in FIELDS and value and not matches_any_pattern(value, ignore_patterns):
                print(f"{field}: {value}")
                displayed_fields += 1

        if displayed_fields == 1:
            print("No relevant metadata found.")
        print("-" * 40)


def display_singular_metadata(all_metadata: List[Dict[str, Any]],
                              args: Namespace,
                              ignore_patterns: List[str]) -> None:
    """
    Print unique metadata fields from the entire set of files,
    either in 'formatted' or 'concise' mode.
    """
    unique_values = defaultdict(set)

    for metadata in all_metadata:
        format_gps_data(metadata)

        for field in UNIQUE_FIELDS:
            value = metadata.get(field, None)
            if field == "Hyperlinks" and value:
                links = [link.strip() for link in value.split(',')]
                valid_links = [l for l in links if not matches_any_pattern(l, ignore_patterns)]
                if valid_links:
                    unique_values[field].add(', '.join(valid_links))
            elif value and not matches_any_pattern(value, ignore_patterns):
                unique_values[field].add(value)

    # Now display them:
    for field, values in unique_values.items():
        # We want to unify them in a case-insensitive manner but preserve the original text
        unique_cased_values = {
            next(v for v in values if v.lower() == val.lower()): None
            for val in values
        }.keys()
        if unique_cased_values:
            if args.format == 'formatted':
                print(f"{field}:")
                for unique_value in unique_cased_values:
                    print(f"    - {unique_value}")
            else:
                print(f"{field}: {', '.join(unique_cased_values)}")
            print()


def display_metadata(args: Namespace,
                     all_metadata: List[Dict[str, Any]],
                     ignore_patterns: List[str]) -> None:
    """
    Dispatch to correct display function: 'all' or 'singular'.
    """
    if args.display == "all":
        display_all_metadata(all_metadata, ignore_patterns)
    elif args.display == "singular":
        display_singular_metadata(all_metadata, args, ignore_patterns)
    else:
        raise ValueError(f"Unrecognized display type: {args.display}")


def export_metadata_to_html(args: Namespace, all_metadata: List[Dict[str, str]], ignore_patterns: List[str]) -> str:
    """
    Convert the metadata to an HTML string (with minimal styling).
    """
    html_parts = [
        "<html><head>",
        "<title>MetaDetective Export</title>",
        CSS_STYLE,
        "</head><body>",
        '<div class="header"><h1>MetaDetective Export Report</h1></div>'
    ]

    if args.display == "all":
        # For each file's metadata, display everything
        for metadata in all_metadata:
            html_parts.append('<div class="metadata-entry">')

            formatted_gps = metadata.get("Formatted GPS Position")
            if formatted_gps:
                lat, lon = formatted_gps.split(", ")
                address = get_address_from_coords(lat, lon)
                if address:
                    encoded_address = quote(address)
                    link_to_address = f"https://nominatim.openstreetmap.org/ui/search.html?q={encoded_address}"
                    metadata["Address"] = f"<a href='{link_to_address}' target='_blank' rel='noopener noreferrer'>{address}</a>"
                metadata["Map Link"] = f"<a href='https://nominatim.openstreetmap.org/ui/reverse.html?lat={lat}&lon={lon}' target='_blank' rel='noopener noreferrer'>View on Map</a>"

            displayed_fields = 0
            for field, value in metadata.items():
                if field in FIELDS and value and not matches_any_pattern(value, ignore_patterns):
                    html_parts.append(f"<p><strong>{field}:</strong> {value}</p>")
                    displayed_fields += 1

            if displayed_fields == 1:
                html_parts.append("<p>No relevant metadata found.</p>")

            html_parts.append("<hr></div>")

    elif args.display == "singular":
        # We gather unique values
        unique_values = defaultdict(set)

        for metadata in all_metadata:
            formatted_gps = metadata.get("Formatted GPS Position")
            if formatted_gps:
                lat, lon = formatted_gps.split(", ")
                map_link = f"https://nominatim.openstreetmap.org/ui/reverse.html?lat={lat}&lon={lon}"
                metadata["Map Link"] = f"<a href='{map_link}'>View on Map</a>"

            for field in UNIQUE_FIELDS:
                value = metadata.get(field, None)
                if field == "Hyperlinks" and value:
                    links = [link.strip() for link in value.split(',')]
                    valid_links = [l for l in links if not matches_any_pattern(l, ignore_patterns)]
                    if valid_links:
                        unique_values[field].add(', '.join(valid_links))
                elif value and not matches_any_pattern(value, ignore_patterns):
                    unique_values[field].add(value)

        # Now output the unique sets
        for field, values in unique_values.items():
            unique_cased_values = {
                next(v for v in values if v.lower() == val.lower()): None
                for val in values
            }.keys()
            if unique_cased_values:
                html_parts.append(f"<h3>{field}:</h3>")
                if args.format == 'formatted':
                    for unique_value in unique_cased_values:
                        html_parts.append(f"<p>    - {unique_value}</p>")
                else:
                    html_parts.append(f"<p>{', '.join(unique_cased_values)}</p>")
                html_parts.append("<hr>")

    html_parts.append("</body></html>")
    return ''.join(html_parts)


def generate_all_metadata_txt(all_metadata: List[Dict[str, Any]], ignore_patterns: List[str]) -> List[str]:
    """
    Generate text lines representing full metadata for each file.
    """
    text_lines = []

    for metadata in all_metadata:
        format_gps_data(metadata)

        displayed_fields = 0
        for field, value in metadata.items():
            if field in FIELDS and value and not matches_any_pattern(value, ignore_patterns):
                text_lines.append(f"{field}: {value}")
                displayed_fields += 1

        if displayed_fields == 1:
            text_lines.append("No relevant metadata found.")
        text_lines.append("-" * 40)

    return text_lines


def generate_singular_metadata_txt(all_metadata: List[Dict[str, Any]],
                                   args: Namespace,
                                   ignore_patterns: List[str]) -> List[str]:
    """
    Generate text lines for unique metadata fields across all files.
    """
    text_lines = []
    unique_values = defaultdict(set)

    for metadata in all_metadata:
        format_gps_data(metadata)

        for field in UNIQUE_FIELDS:
            value = metadata.get(field, None)
            if field == "Hyperlinks" and value:
                links = [link.strip() for link in value.split(',')]
                valid_links = [l for l in links if not matches_any_pattern(l, ignore_patterns)]
                if valid_links:
                    unique_values[field].add(', '.join(valid_links))
            elif value and not matches_any_pattern(value, ignore_patterns):
                unique_values[field].add(value)

    # Output the aggregated unique values
    for field, values in unique_values.items():
        unique_cased_values = {
            next(v for v in values if v.lower() == val.lower()): None
            for val in values
        }.keys()
        if unique_cased_values:
            if args.format == 'formatted':
                text_lines.append(f"{field}:")
                for unique_value in unique_cased_values:
                    text_lines.append(f"    - {unique_value}")
            else:
                text_lines.append(f"{field}: {', '.join(unique_cased_values)}")
            text_lines.append("")

    return text_lines


def export_metadata_to_txt(args: Namespace, all_metadata: List[Dict[str, Any]], ignore_patterns: List[str]) -> str:
    """
    Convert metadata to text output (either 'all' or 'singular' display).
    """
    if args.display == "all":
        lines = generate_all_metadata_txt(all_metadata, ignore_patterns)
    else:
        lines = generate_singular_metadata_txt(all_metadata, args, ignore_patterns)
    return "\n".join(lines)


def valid_filename(value: str) -> str:
    """
    Validate custom filename suffix (alphanumeric, up to 16 chars, optional '-' or '_').
    """
    if not value or len(value) > 16:
        raise argparse.ArgumentTypeError("Filename suffix must be non-empty and less than 16 characters.")

    pattern = r'^[a-zA-Z0-9_-]*[a-zA-Z0-9]$'
    if not re.match(pattern, value):
        raise argparse.ArgumentTypeError(
            "Invalid filename suffix. It must be alphanumeric, can contain '-' or '_', but not end with them."
        )
    return value


class LinkParser(HTMLParser):
    """
    HTML Parser to extract <a href>, <img src>, <script src>, <link href> from a page.
    """

    def __init__(self) -> None:
        super().__init__()
        self.links: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str]]) -> None:
        tag_to_attr = {
            'a': 'href',
            'img': 'src',
            'script': 'src',
            'link': 'href'
        }
        target_attr = tag_to_attr.get(tag)
        if target_attr:
            for name, value in attrs:
                if name == target_attr:
                    self.links.append(value)


def fetch_links_from_url(url: str) -> List[str]:
    """
    Fetch all links from a URL using a browser-like User-Agent to reduce 403 rejections.

    If a 403 error occurs and DEBUG_MODE is enabled, print debug info.
    """
    pattern = re.compile(r"\.(css|js)($|\?|#)")

    # Custom "browser-like" User-Agent:
    headers = {
        'User-Agent': (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        )
    }

    req = urllib.request.Request(url, headers=headers)
    try:
        response = urllib.request.urlopen(req)

        content_type = response.headers.get('Content-Type', '').split(';')[0]
        if 'text' not in content_type:
            return []

        data = response.read().decode()
        parser = LinkParser()
        parser.feed(data)
        return [
            link for link in parser.links
            if not link.startswith("javascript:") and not pattern.search(link)
        ]
    except urllib.error.HTTPError as e:
        # If we get 403 or other code, show debug if needed:
        if DEBUG_MODE:
            print(f"[DEBUG] HTTPError in fetch_links_from_url('{url}') => {e.code} {e.reason}")
            if e.code == 403:
                print("[DEBUG] This typically means the server blocked our request (Cloudflare or similar).")
        return []
    except urllib.error.URLError as e:
        if url.startswith("mailto:"):
            # Not a real URL to open, but let's mention it
            print(f"INFO: Found mailto link {url}")
        else:
            print(f"ERROR: Unable to open {url} Reason: {e}")
        return []
    except ValueError as e:
        print(f"ERROR: Unable to decode data from {url} Reason: {e}")
        return []


def is_valid_file_link(link: str) -> bool:
    """
    Check if 'link' ends with a valid extension from EXTENSIONS.
    """
    path = urlsplit(link).path
    return any(path.endswith(f".{ext}") for ext in EXTENSIONS)


def process_url(url: str, depth: int, base_domain: str, q, seen: Set[str],
                lock: threading.Lock, rate_limiter,
                file_stats: Dict[str, int],
                download_dir: Optional[str] = None, scan: bool = False,
                follow_extern: bool = False) -> None:
    """
    Crawl/scrape a single URL: fetch links, optionally download or collect stats.
    """
    if url in seen:
        return

    with lock:
        seen.add(url)

    print(f"INFO: Accessing {url}")
    rate_limiter.wait()

    links = fetch_links_from_url(url)
    file_links = [urljoin(url, l) for l in links if is_valid_file_link(l)]

    if download_dir and not scan:
        # Download mode
        if not file_links:
            print("\nNo files found or no files with specified extensions.")
            return
        for file_link in file_links:
            download_file(file_link, download_dir)

    elif scan:
        # Just gather stats, no download
        for file_link in file_links:
            file_url = urljoin(url, file_link)
            file_name = os.path.basename(urlparse(file_url).path)
            extension = os.path.splitext(file_name)[-1].lstrip('.')
            with lock:
                if extension not in file_stats:
                    file_stats[extension] = set()
                file_stats[extension].add((file_url, file_name))

    # If we still have depth, keep scraping deeper links
    if depth > 0:
        for l in links:
            parsed_link = urlparse(l)
            joined_link = urljoin(url, l)
            # If follow_extern is False, skip external domains
            if not follow_extern and parsed_link.netloc and parsed_link.netloc != base_domain:
                continue
            q.put((joined_link, depth - 1, base_domain, follow_extern))


class RateLimiter:
    """
    Simple rate limiter to limit requests to 'rate' per second.
    """
    def __init__(self, rate: float):
        self.rate = rate
        self.last_call = 0.0
        self.lock = threading.Lock()

    def wait(self) -> None:
        with self.lock:
            elapsed = time.time() - self.last_call
            left_to_wait = 1.0 / self.rate - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            self.last_call = time.time()


def calculate_hash(data: bytes) -> str:
    """
    Return SHA-256 of the given bytes.
    """
    sha256_hash = hashlib.sha256()
    sha256_hash.update(data)
    return sha256_hash.hexdigest()


def find_unique_filename(path: str) -> str:
    """
    If 'path' exists, keep appending '-2', '-3', etc. until we find a free name.
    """
    counter = 2
    base, ext = os.path.splitext(path)
    while os.path.exists(path):
        path = f"{base}-{counter}{ext}"
        counter += 1
    return path


def download_file(url: str, download_dir: str) -> None:
    """
    Download a file from 'url' to 'download_dir' with a custom User-Agent.

    If 403 occurs and debug is on, we print more info.
    """
    try:
        # "Browser-like" header:
        headers = {
            'User-Agent': (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/114.0.0.0 Safari/537.36"
            )
        }
        encoded_url = quote(url, safe=":/?&=")
        local_filename = os.path.join(download_dir, os.path.basename(urlparse(encoded_url).path))

        req = urllib.request.Request(encoded_url, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = response.read()
            file_hash = calculate_hash(data)

            # If there's already a file with that name, compare hashes
            if os.path.exists(local_filename):
                with open(local_filename, 'rb') as existing_file:
                    existing_file_hash = calculate_hash(existing_file.read())

                if file_hash == existing_file_hash:
                    print(f"WARNING: Duplicate file detected for '{local_filename}'. "
                          f"Both have the same hash: {file_hash}.")
                    return
                else:
                    new_local_filename = find_unique_filename(local_filename)
                    print(f"INFO: File '{local_filename}' already exists with a different hash. "
                          f"Saving the new file as '{new_local_filename}'.")
                    local_filename = new_local_filename

            # Write the new file
            with open(local_filename, 'wb') as out_file:
                out_file.write(data)
            print(f"INFO: Downloaded {url} to {local_filename}. SHA-256: {file_hash}.")

    except urllib.error.HTTPError as e:
        if DEBUG_MODE:
            print(f"[DEBUG] HTTPError in download_file('{url}') => {e.code} {e.reason}")
            if e.code == 403:
                print("[DEBUG] The server returned 403 Forbidden. Possibly blocked by Cloudflare or the site.")
        else:
            print(f"ERROR: Failed to download {url}. HTTPError: {e.code} {e.reason}")

    except Exception as e:
        print(f"ERROR: Failed to download {url}. Reason: {e}")


def worker_thread(q: queue.Queue[Tuple[str, int, str, bool]],
                  seen: Set[str],
                  lock: threading.Lock,
                  rate_limiter: RateLimiter,
                  file_stats: Dict[str, int],
                  download_dir: Optional[str] = None,
                  scan: bool = False) -> None:
    """
    Thread entry point. Pull tasks from queue and process them until we see SENTINEL.
    """
    while True:
        task = get_task_from_queue(q)
        if task is SENTINEL:
            break
        process_task(task, q, seen, lock, rate_limiter, file_stats, download_dir, scan)
        q.task_done()


def get_task_from_queue(q: queue.Queue[Tuple[str, int, str, bool]]) -> Tuple[str, int, str, bool]:
    """
    A small helper to fetch from the queue. 
    """
    return q.get()


def process_task(task: Tuple[str, int, str, bool],
                 q: queue.Queue[Tuple[str, int, str, bool]],
                 seen: Set[str],
                 lock: threading.Lock,
                 rate_limiter: RateLimiter,
                 file_stats: Dict[str, int],
                 download_dir: Optional[str] = None,
                 scan: bool = False) -> None:
    """
    Execute a scraping task (process_url).
    """
    url, depth, base_domain, follow_extern = task
    process_url(url, depth, base_domain, q, seen, lock, rate_limiter, file_stats,
                download_dir, scan, follow_extern)


def valid_url(url: str) -> str:
    """
    Validate user-provided URL for argparse.
    """
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|'
        r'(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    if not url_pattern.match(url):
        raise argparse.ArgumentTypeError(f"'{url}' is not a valid URL.")
    return url


def main():
    global DEBUG_MODE  # So we can set the global debug flag if needed

    show_banner()
    check_exiftool_installed()

    parser = argparse.ArgumentParser(
        description="Retrieve and display metadata from files using exiftool.",
        epilog="Example commands:\n\n"
               "# Analysis:\n"
               "   # Analyze metadata in a specified directory:\n"
               "python3 MetaDetective.py -d path/to/directory\n"
               "   # Analyze specific file types in a directory and ignore certain patterns:\n"
               "python3 MetaDetective.py -d directory -i ^admin anonymous -t doc pdf\n"
               "   # Analyze all file types in a directory with formatted display:\n"
               "python3 MetaDetective.py -d directory -t all -display singular -format formatted\n"
               "\n"
               "   # Export metadata analysis of a directory (by default in HTML):\n"
               "python3 MetaDetective.py -d directory --export\n"
               "\n"
               "# Scraping:\n"
               "   # Scan a website without downloading files:\n"
               "python3 MetaDetective.py --scraping --scan --url https://example.com/\n"
               "   # Download files from a website to a specified directory:\n"
               "python3 MetaDetective.py --scraping --download-dir directory --url https://example.com/\n"
               "   # Download files from a website with specified depth:\n"
               "python3 MetaDetective.py --scraping --depth 1 --download-dir directory --url https://example.com/\n",
        formatter_class=argparse.RawTextHelpFormatter
    )

    # Debug mode argument:
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug mode to display detailed information on 403/HTTP errors.")

    # Scraping group:
    scraping_group = parser.add_argument_group('scraping options')
    scraping_group.add_argument('-s', '--scraping', action='store_true', help="Activate scraping mode.")
    scraping_group.add_argument('-u', "--url", type=valid_url, help="Site URL for scraping.")
    scraping_group.add_argument("--scan", action="store_true", help="Scan the website without downloading files (just gather stats).")
    scraping_group.add_argument('--extensions', nargs='+', type=str.lower,
                                help='File extensions to filter by, e.g., --extensions pdf jpg png')
    scraping_group.add_argument("--depth", type=int, default=0, help="Depth of links to follow on the site.")
    scraping_group.add_argument("--download-dir", type=valid_directory,
                                help="Directory to store files that have been scraped.")
    scraping_group.add_argument("--follow-extern", action="store_true", help="Follow external links.")
    scraping_group.add_argument("--threads", type=int, default=4, help="Number of threads to use.")
    scraping_group.add_argument("--rate", type=int, default=5, help="Max requests per second.")

    # Analysis group:
    analysis_group = parser.add_argument_group('analysis options')
    analysis_group.add_argument('-d', '--directory', type=valid_directory,
                                help="Directory containing the files to be analyzed.")
    analysis_group.add_argument('-f', '--files', nargs='+',
                                help="File(s) to be analyzed (space-separated).")
    analysis_group.add_argument('-t', '--type', nargs='+', default=['all'],
                                help="File types (extensions) to be analyzed (all by default).")

    # Display group:
    display_group = parser.add_argument_group('display options')
    display_group.add_argument('-i', '--ignore', nargs='+',
                               help="Ignore one or more keyword/regex patterns in the results.")
    display_group.add_argument('--display', choices=['all', 'singular'], default='singular',
                               help="'all' = show all results per file; 'singular' = condensed/unique results.")
    display_group.add_argument('--format', choices=['formatted', 'concise'],
                               help="Valid only with '--display singular': 'formatted' or 'concise'.")

    # Export group:
    export_group = parser.add_argument_group('export options')
    export_group.add_argument('-e', '--export', nargs='?', const='html', choices=['html', 'txt'], default=None,
                              help="Export results. Default is HTML; can also do --export txt.")
    export_group.add_argument('-c', '--custom', type=valid_filename,
                              help="Add a custom suffix to the exported filename.")
    export_group.add_argument('-o', '--out', type=valid_directory, default=os.getcwd(),
                              help="Specify export directory (default current directory).")

    args = parser.parse_args()

    # If no args, show help and exit
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    # Set global DEBUG_MODE:
    if args.debug:
        DEBUG_MODE = True
        print("[DEBUG] Debug mode enabled.")

    # Scraping mode
    if args.scraping:
        if args.directory or args.files or args.ignore:
            parser.error("Analysis arguments (--directory/-d, --files/-f, or --ignore/-i) "
                         "cannot be used with scraping mode (--scraping).")

        if args.scan and args.download_dir:
            parser.error("Cannot use both --scan and --download-dir together in scraping mode.")
        elif not args.scan and not args.download_dir:
            parser.error("Must specify either --scan or --download-dir in scraping mode.")

        if not args.url:
            parser.error("Scraping mode requires --url.")

        # Set any custom extension filters
        if args.extensions:
            global EXTENSIONS
            EXTENSIONS = args.extensions

        base_domain = urlparse(args.url).netloc
        seen = set()
        lock = threading.Lock()
        q = queue.Queue()
        rate_limiter = RateLimiter(args.rate)
        file_stats = {}

        # Put initial task in the queue
        q.put((args.url, args.depth, base_domain, args.follow_extern))

        # Start the threads
        threads = []
        for _ in range(args.threads):
            t = threading.Thread(
                target=worker_thread,
                args=(q, seen, lock, rate_limiter, file_stats, args.download_dir, args.scan)
            )
            t.start()
            threads.append(t)

        q.join()

        # Stop threads
        for _ in range(args.threads):
            q.put(SENTINEL)
        for t in threads:
            t.join()

        if args.scan:
            # Summarize
            if not any(file_stats.values()):
                print("\nNo files found or no files with specified extensions.")
                sys.exit(0)

            print("\nScan results:\n")
            print("+---------------+-----------------------------------+")
            print("| File Extension | Estimated Number of Unique Files |")
            print("+---------------+-----------------------------------+")
            for ext, files_set in file_stats.items():
                print(f"| {ext.ljust(14)} | {str(len(files_set)).ljust(32)} |")
            print("+---------------+-----------------------------------+")
            print(f"\nINFO: Total URLs processed (followed): {len(seen)}")
            print("NOTE: These results are an estimate and do not guarantee uniqueness.")

        sys.exit(0)

    # Analysis mode
    elif args.directory or args.files:
        if args.directory and args.files:
            parser.error("Cannot specify both --directory and --files in analysis mode.")

        ignore_patterns = args.ignore if args.ignore else []

        if args.display == 'all' and args.format:
            parser.error("The '--format' argument is not compatible with '--display all'.")

        # If user chooses 'singular' but no --format, default to 'concise'
        if args.display == 'singular' and args.format is None:
            args.format = 'concise'

        # Gather files
        files = get_files(args)
        # Extract metadata
        all_metadata = [get_metadata(f, FIELDS) for f in files]

        # Export or just display
        if args.export:
            if args.export == 'html':
                content = export_metadata_to_html(args, all_metadata, ignore_patterns)
                file_extension = '.html'
            else:  # txt
                content = export_metadata_to_txt(args, all_metadata, ignore_patterns)
                file_extension = '.txt'

            timestamp = datetime.datetime.now().strftime('%Y_%m_%d-%H_%M_%S')
            custom_suffix = f"{args.custom}-" if args.custom else ""
            filename = f"MetaDetective_Export-{custom_suffix}{timestamp}{file_extension}"

            full_path = os.path.join(args.out, filename)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Results file exported to {full_path}")

        else:
            # Print to stdout
            display_metadata(args, all_metadata, ignore_patterns)

    else:
        parser.error("You must specify either --scraping or --directory or --files.")


if __name__ == "__main__":
    main()
