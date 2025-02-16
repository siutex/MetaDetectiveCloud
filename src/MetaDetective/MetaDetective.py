#!/usr/bin/env python3
"""
Unleash Metadata Intelligence with MetaDetective. Your Assistant Beyond Metagoofil.

Created By  : Franck FERMAN @franckferman
Created Date: 27/08/23
Version     : 1.0.9 (09/11/23) - Fully fixed version (with browser-like headers)

Modifications:
  - Updated web scraping functions to use CloudScraper with a common browser user agent
    and additional headers to bypass anti-bot measures.
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
from urllib.parse import urlparse, urljoin, quote

# Import CloudScraper for bypassing anti-bot measures
import cloudscraper  # <--

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

NOMINATIM_HOST = "nominatim.openstreetmap.org"
USER_AGENT = 'MetaDetective/1.0.9'  # Used for exiftool-related requests
# New browser-like User-Agent for web scraping:
BROWSER_USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/105.0.0.0 Safari/537.36")

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

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/ui/search.html?q="

SENTINEL = None


def show_banner() -> None:
    """Print the banner."""
    print(BANNER)


def check_exiftool_installed() -> None:
    """Verify exiftool installation and exit the program if absent or on execution error."""
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
        deg, min, sec, dir = match.groups()

        if dir.upper() not in ['N', 'S', 'E', 'W']:
            raise ValueError(f"Invalid direction: {dir}")

        return int(deg), int(min), float(sec), dir.upper()

    raise ValueError(f"Invalid DMS format: {dms_str}")


def get_metadata(file_path: str, fields: List[str]) -> dict:
    """
    Retrieve specified metadata fields from a file using exiftool.
    """
    try:
        exiftool_output = subprocess.run(["exiftool", file_path], capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing exiftool: {e}")
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
        if key in field_set and value.strip():
            metadata[key] = value.strip()

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
    Check if a string matches any of the provided patterns.
    """
    compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    return any(pattern.search(value) for pattern in compiled_patterns)


def valid_directory(path: str) -> str:
    """
    Validate directory path.
    """
    if not os.path.exists(path):
        raise argparse.ArgumentTypeError(f"Directory path '{path}' does not exist.")

    if not os.path.isdir(path):
        raise argparse.ArgumentTypeError(f"Path '{path}' is not a directory.")

    return path


def filter_files_by_extension(files: List[str], extensions: List[str]) -> List[str]:
    """
    Filter a list of files to return only those that match the provided extensions.
    """
    if not isinstance(files, list) or not all(isinstance(f, str) for f in files):
        raise TypeError("The 'files' argument must be a list of strings.")

    if not isinstance(extensions, list) or not all(isinstance(ext, str) for ext in extensions):
        raise TypeError("The 'extensions' argument must be a list of strings.")

    ext_set = set(extensions)
    return [file for file in files if file.endswith(tuple(ext_set))]


def get_files(args) -> List[str]:
    """
    Retrieve a list of files based on the provided arguments.
    """
    if args.directory:
        try:
            valid_directory(args.directory)
        except argparse.ArgumentTypeError as e:
            raise ValueError(str(e))

        files = [os.path.join(args.directory, file) for file in os.listdir(args.directory)]
        if args.type != ['all']:
            files = filter_files_by_extension(files, args.type)
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
    Update the provided metadata dictionary with address and map link derived from the "Formatted GPS Position", if present.
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
    Display all metadata fields for each metadata entry.
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
    Display unique metadata fields from a list of metadata entries based on user's display preference.
    """
    unique_values = defaultdict(set)

    for metadata in all_metadata:
        format_gps_data(metadata)
        for field in UNIQUE_FIELDS:
            value = metadata.get(field, None)
            if field == "Hyperlinks" and value:
                links = [link.strip() for link in value.split(',')]
                valid_links = [link for link in links if not matches_any_pattern(link, ignore_patterns)]
                if valid_links:
                    unique_values[field].add(', '.join(valid_links))
            elif value and not matches_any_pattern(value, ignore_patterns):
                unique_values[field].add(value)

    for field, values in unique_values.items():
        unique_cased_values = {next(v for v in values if v.lower() == value.lower()): None for value in values}.keys()
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
    Display metadata based on user's display preference.
    """
    if args.display == "all":
        display_all_metadata(all_metadata, ignore_patterns)
    elif args.display == "singular":
        display_singular_metadata(all_metadata, args, ignore_patterns)
    else:
        raise ValueError(f"Unrecognized display preference: {args.display}")


def export_metadata_to_html(args: Namespace, all_metadata: List[Dict[str, str]], ignore_patterns: List[str]) -> str:
    """
    Convert and export metadata to a beautiful HTML page.
    """
    html_parts = [
        '<html>',
        '<head>',
        '<title>MetaDetective Export</title>',
        CSS_STYLE,
        '</head>',
        '<body>',
        '<div class="header">',
        '<h1>MetaDetective Export Report</h1>',
        '</div>'
    ]

    if args.display == "all":
        for metadata in all_metadata:
            html_parts.append('<div class="metadata-entry">')

            formatted_gps = metadata.get("Formatted GPS Position")
            if formatted_gps:
                lat, lon = formatted_gps.split(", ")
                address = get_address_from_coords(lat, lon)
                if address:
                    encoded_address = quote(address)
                    link_to_address = f"{NOMINATIM_SEARCH_URL}{encoded_address}"
                    metadata["Address"] = f"<a href='{link_to_address}' target='_blank' rel='noopener noreferrer'>{address}</a>"
                metadata["Map Link"] = f"<a href='https://nominatim.openstreetmap.org/ui/reverse.html?lat={lat}&lon={lon}' target='_blank' rel='noopener noreferrer'>View on Map</a>"

            displayed_fields = 0
            for field, value in metadata.items():
                if field in FIELDS and value and not matches_any_pattern(value, ignore_patterns):
                    html_parts.append(f'<p><strong>{field}:</strong> {value}</p>')
                    displayed_fields += 1

            if displayed_fields == 1:
                html_parts.append('<p>No relevant metadata found.</p>')

            html_parts.append('<hr></div>')
    elif args.display == "singular":
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
                    valid_links = [link for link in links if not matches_any_pattern(link, ignore_patterns)]
                    if valid_links:
                        unique_values[field].add(', '.join(valid_links))
                elif value and not matches_any_pattern(value, ignore_patterns):
                    unique_values[field].add(value)

        for field, values in unique_values.items():
            unique_cased_values = {next(v for v in values if v.lower() == value.lower()): None for value in values}.keys()
            if unique_cased_values:
                html_parts.append(f'<h3>{field}:</h3>')
                if args.format == 'formatted':
                    for unique_value in unique_cased_values:
                        html_parts.append(f'<p>    - {unique_value}</p>')
                else:
                    html_parts.append(f"<p>{', '.join(unique_cased_values)}</p>")
                html_parts.append('<hr>')

    html_parts.append('</body></html>')
    return ''.join(html_parts)


def generate_all_metadata_txt(all_metadata: List[Dict[str, Any]], ignore_patterns: List[str]) -> List[str]:
    """
    Generate a list of text strings representing the complete metadata for each entry.
    """
    text_parts = []
    for metadata in all_metadata:
        format_gps_data(metadata)

        displayed_fields = 0
        for field, value in metadata.items():
            if field in FIELDS and value and not matches_any_pattern(value, ignore_patterns):
                text_parts.append(f"{field}: {value}")
                displayed_fields += 1

        if displayed_fields == 1:
            text_parts.append("No relevant metadata found.")
        text_parts.append("-" * 40)

    return text_parts


def generate_singular_metadata_txt(all_metadata: List[Dict[str, Any]],
                                   args: Namespace,
                                   ignore_patterns: List[str]) -> List[str]:
    """
    Generate a list of text strings representing unique metadata values.
    """
    text_parts = []
    unique_values = defaultdict(set)

    for metadata in all_metadata:
        format_gps_data(metadata)
        for field in UNIQUE_FIELDS:
            value = metadata.get(field, None)
            if field == "Hyperlinks" and value:
                links = [link.strip() for link in value.split(',')]
                valid_links = [link for link in links if not matches_any_pattern(link, ignore_patterns)]
                if valid_links:
                    unique_values[field].add(', '.join(valid_links))
            elif value and not matches_any_pattern(value, ignore_patterns):
                unique_values[field].add(value)

    for field, values in unique_values.items():
        unique_cased_values = {next(v for v in values if v.lower() == value.lower()): None for value in values}.keys()
        if unique_cased_values:
            if args.format == 'formatted':
                text_parts.append(f"{field}:")
                for unique_value in unique_cased_values:
                    text_parts.append(f"    - {unique_value}")
            else:
                text_parts.append(f"{field}: {', '.join(unique_cased_values)}")
            text_parts.append("")

    return text_parts


def export_metadata_to_txt(args: Namespace, all_metadata: List[Dict[str, Any]], ignore_patterns: List[str]) -> str:
    """
    Export the provided metadata to a text format.
    """
    if args.display == "all":
        text_parts = generate_all_metadata_txt(all_metadata, ignore_patterns)
    elif args.display == "singular":
        text_parts = generate_singular_metadata_txt(all_metadata, args, ignore_patterns)

    return '\n'.join(text_parts)


def valid_filename(value: str) -> str:
    """
    Check if the filename is alphanumeric, less than 16 characters, and can contain symbols '-' or '_', but not at the end.
    """
    if not value or len(value) > 16:
        raise argparse.ArgumentTypeError("Filename suffix must be non-empty and less than 16 characters.")

    pattern = r'^[a-zA-Z0-9_-]*[a-zA-Z0-9]$'

    if not re.match(pattern, value):
        raise argparse.ArgumentTypeError("Invalid filename suffix. It should be alphanumeric, can contain '-' or '_', but not end with them.")

    return value


class LinkParser(HTMLParser):
    """HTML Parser to extract links from a web page."""
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
    Fetch all links from a given URL using CloudScraper.
    Updated to use a browser-like profile and headers to avoid 403 errors.
    """
    pattern = re.compile(r"\.(css|js)($|\?|#)")

    try:
        # Create a CloudScraper session with a browser profile
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )

        # Use additional headers including a common browser User-Agent
        headers = {
            'User-Agent': BROWSER_USER_AGENT,
            'Accept-Language': 'en-US,en;q=0.9'
        }

        response = scraper.get(url, headers=headers)

        # Optional: log if status code is not 200
        if response.status_code != 200:
            print(f"ERROR: Received status code {response.status_code} for {url}")
            return []

        content_type = response.headers.get('Content-Type', '').split(';')[0]
        if 'text' not in content_type:
            return []

        data = response.text
        parser = LinkParser()
        parser.feed(data)
        return [link for link in parser.links if not link.startswith("javascript:") and not pattern.search(link)]

    except Exception as e:
        if url.startswith("mailto:"):
            print(f"INFO: Found mailto link {url}")
        else:
            print(f"ERROR: Unable to open {url}. Reason: {e}")
        return []


def is_valid_file_link(link: str) -> bool:
    """
    Check if the link is a valid file link based on its extension.
    """
    path = urllib.parse.urlsplit(link).path
    return any(path.endswith(f".{ext}") for ext in EXTENSIONS)


def process_url(url: str, depth: int, base_domain: str, q, seen: Set[str],
                lock: threading.Lock, rate_limiter, file_stats: Dict[str, int],
                download_dir: Optional[str] = None, scan: bool = False,
                follow_extern: bool = False) -> None:
    """
    Process a URL, fetch its links, and perform download or scanning actions.
    """
    if url in seen:
        return

    with lock:
        seen.add(url)

    print(f"INFO: Accessing {url}")

    rate_limiter.wait()

    links = fetch_links_from_url(url)

    file_links = [urljoin(url, link) for link in links if is_valid_file_link(link)]

    if download_dir and not scan:
        if not file_links:
            print("\nNo files found or no files with specified extensions.")
            return

        for file_link in file_links:
            download_file(file_link, download_dir)
    elif scan:
        for file_link in file_links:
            file_url = urljoin(url, file_link)
            file_name = os.path.basename(urlparse(file_url).path)
            extension = os.path.splitext(file_name)[-1].lstrip('.')
            with lock:
                if extension not in file_stats:
                    file_stats[extension] = set()
                file_stats[extension].add((file_url, file_name))

    if depth > 0:
        for link in links:
            parsed_link = urlparse(link)
            joined_link = urljoin(url, link)

            if not follow_extern and parsed_link.netloc and parsed_link.netloc != base_domain:
                continue

            q.put((joined_link, depth - 1, base_domain, follow_extern))


class RateLimiter:
    """Rate limiter class to control the frequency of function calls."""
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
    Calculate the SHA-256 hash of the given data.
    """
    sha256_hash = hashlib.sha256()
    sha256_hash.update(data)
    return sha256_hash.hexdigest()


def find_unique_filename(path: str) -> str:
    """
    Generate a unique filename in the directory of the provided path.
    """
    counter = 2
    base, ext = os.path.splitext(path)
    while os.path.exists(path):
        path = f"{base}-{counter}{ext}"
        counter += 1
    return path


def download_file(url: str, download_dir: str) -> None:
    """
    Download a file from a specified URL using CloudScraper and save it to the given directory.
    Updated to pass browser-like headers.
    """
    try:
        encoded_url = quote(url, safe=":/?&=")
        local_filename = os.path.join(download_dir, os.path.basename(urlparse(encoded_url).path))

        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
        headers = {
            'User-Agent': BROWSER_USER_AGENT,
            'Accept-Language': 'en-US,en;q=0.9'
        }
        response = scraper.get(encoded_url, headers=headers)
        data = response.content
        file_hash = calculate_hash(data)

        if os.path.exists(local_filename):
            with open(local_filename, 'rb') as existing_file:
                existing_file_hash = calculate_hash(existing_file.read())

            if file_hash == existing_file_hash:
                print(f"WARNING: Duplicate file detected for '{local_filename}'. Both have the same hash: {file_hash}.")
                return
            else:
                new_local_filename = find_unique_filename(local_filename)
                print(f"INFO: File '{local_filename}' already exists with a different hash. Saving the new file as '{new_local_filename}'.")
                local_filename = new_local_filename

        with open(local_filename, 'wb') as out_file:
            out_file.write(data)
        print(f"INFO: Downloaded {url} to {local_filename}. SHA-256: {file_hash}.")
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
    Worker thread function to process URLs from the queue.
    """
    while True:
        task = get_task_from_queue(q)
        if task is SENTINEL:
            break

        process_task(task, q, seen, lock, rate_limiter, file_stats, download_dir, scan)

        q.task_done()


def get_task_from_queue(q: queue.Queue[Tuple[str, int, str, bool]]) -> Tuple[str, int, str, bool]:
    """
    Fetches the next task from the provided queue.
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
    Processes a given task by extracting the relevant information and invoking the appropriate URL processing function.
    """
    url, depth, base_domain, follow_extern = task
    process_url(url, depth, base_domain, q, seen, lock, rate_limiter, file_stats, download_dir, scan, follow_extern)


def valid_url(url: str) -> str:
    """
    Validates if the provided value is a valid URL.
    """
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    if not url_pattern.match(url):
        raise argparse.ArgumentTypeError(f"'{url}' is not a valid URL.")
    return url


def main():
    show_banner()
    check_exiftool_installed()

    parser = argparse.ArgumentParser(description="Retrieve and display metadata from files using exiftool.",
                                     epilog="Example commands:\n\n"
                                            "# Analysis:\n"
                                            "python3 MetaDetective.py -d path/to/directory\n"
                                            "python3 MetaDetective.py -d directory -i ^admin anonymous -t doc pdf\n"
                                            "python3 MetaDetective.py -d directory -t all -display singular -format formatted\n"
                                            "\n"
                                            "python3 MetaDetective.py -d directory --export\n"
                                            "\n"
                                            "# Scraping:\n"
                                            "python3 MetaDetective.py --scraping --scan --url https://example.com/\n"
                                            "python3 MetaDetective.py --scraping --download-dir directory --url https://example.com/\n"
                                            "python3 MetaDetective.py --scraping --depth 1 --download-dir directory --url https://example.com/\n",
                                     formatter_class=argparse.RawTextHelpFormatter
                                     )

    scraping_group = parser.add_argument_group('scraping options', 'Options for scraping files containing potential metadata from a website.')
    scraping_group.add_argument('-s', '--scraping', action='store_true', help="Argument required to activate scraping mode.")
    scraping_group.add_argument('-u', "--url", type=valid_url, help="Site url for scraping.")
    scraping_group.add_argument("--scan", action="store_true", help="Scans the website and displays information and statistics without downloading files.")
    scraping_group.add_argument('--extensions', nargs='+', type=str.lower, help='File extensions to filter by, e.g., --extensions pdf jpg png')
    scraping_group.add_argument("--depth", type=int, default=0, help="Depth of links to follow on the site.")
    scraping_group.add_argument("--download-dir", type=valid_directory, help="Directory where files that have been scraped should be stored.")
    scraping_group.add_argument("--follow-extern", action="store_true", help="Follow external links.")
    scraping_group.add_argument("--threads", type=int, default=4, help="Number of threads to use.")
    scraping_group.add_argument("--rate", type=int, default=5, help="Maximum number of requests per second.")

    analysis_group = parser.add_argument_group('analysis options', 'Main analysis options.')
    analysis_group.add_argument('-d', '--directory', type=valid_directory, help="Directory containing the files to be analyzed.")
    analysis_group.add_argument('-f', '--files', nargs='+', help="File or space-separated list of files to be analyzed.")

    analysis_group.add_argument('-t', '--type', nargs='+', default=['all'], help="File types (extensions) to be analyzed (all by default).")

    display_group = parser.add_argument_group('display options', 'Options for displaying results.')
    display_group.add_argument('-i', '--ignore', nargs='+', help="Ignore one or more results separated by spaces for keywords or regexes.")
    display_group.add_argument('--display', choices=['all', 'singular'], default='singular', help="Display options:\n'all' to display all relevant results for each file one by one.\n'singular' to display condensed results.'")
    display_group.add_argument('--format', choices=['formatted', 'concise'], help="Display format ('singular' display required):\n'formatted' for a formatted (stylized) display.\n'concise' for more classic (basic) formatting.")

    export_group = parser.add_argument_group('export options', 'Options for exporting results.')
    export_group.add_argument('-e', '--export', nargs='?', const='html', choices=['html', 'txt'], default=None, help="Export results. Default format is HTML. Text export (txt) is also possible.")
    export_group.add_argument('-c', '--custom', type=valid_filename, help="Custom file name. The name is generated with default values, but you can add a suffix.")
    export_group.add_argument('-o', '--out', type=valid_directory, default=os.getcwd(), help="Specify file export directory.")

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    if args.scraping:
        if args.directory or args.files or args.ignore:
            parser.error("Analysis arguments (--directory/-d, --files/-f, and --ignore/-i) cannot be used with scrapping options (--scraping/-s).")

        if args.scan and args.download_dir:
            parser.error("The scan (--scan) and download (--download-dir) arguments cannot be specified together. Choose between one or the other mode in scraping mode, but not both.")
        elif not args.scan and not args.download_dir:
            parser.error("You must choose at least between the scan (--scan) or download (--download-dir) argument in scraping mode.")

        if not args.url:
            parser.error("The url choice argument (-u or --url) is required for scraping mode.")

        if args.extensions:
            global EXTENSIONS
            EXTENSIONS = args.extensions

        base_domain = urlparse(args.url).netloc

        seen = set()
        lock = threading.Lock()
        q = queue.Queue()
        rate_limiter = RateLimiter(args.rate)
        file_stats = {}

        q.put((args.url, args.depth, base_domain, args.follow_extern))

        threads = []
        for _ in range(args.threads):
            t = threading.Thread(target=worker_thread, args=(q, seen, lock, rate_limiter, file_stats, args.download_dir, args.scan))
            t.start()
            threads.append(t)

        q.join()

        for _ in range(args.threads):
            q.put(None)
        for t in threads:
            t.join()

        if args.scan:
            if not any(file_stats.values()):
                print("\nNo files found or no files with specified extensions.")
                sys.exit(0)

            print("\nScan results:\n")
            print("+---------------+-----------------------------------+")
            print("| File Extension | Estimated Number of Unique Files |")
            print("+---------------+-----------------------------------+")
            for ext, files in file_stats.items():
                print(f"| {ext.ljust(14)} | {str(len(files)).ljust(32)} |")
            print("+---------------+-----------------------------------+")
            print(f"\nINFO: Total URLs processed (followed): {len(seen)}")
            print("NOTE: These results provide an estimation and do not guarantee the uniqueness of the files.")

        sys.exit(0)

    elif args.directory or args.files:
        if args.directory and args.files:
            parser.error("The directory (--directory/-d) and files (--files/-f) arguments cannot be specified together. Choose between one or the other mode in analysis mode, but not both.")

        ignore_patterns = args.ignore if args.ignore else []

        if args.display == 'all' and args.format:
            parser.error("The formatting (--format) argument is not compatible with the 'all' display mode (--display all).")

        if args.display == 'singular' and args.format is None:
            args.format = 'concise'

        files = get_files(args)
        all_metadata = [get_metadata(file, FIELDS) for file in files]

        if args.export:
            if args.export == 'html':
                content = export_metadata_to_html(args, all_metadata, ignore_patterns)
                file_extension = '.html'
            else:
                content = export_metadata_to_txt(args, all_metadata, ignore_patterns)
                file_extension = '.txt'

            timestamp = datetime.datetime.now().strftime('%Y_%m_%d-%H_%M_%S')
            custom_suffix = f"{args.custom}-" if args.custom else ""
            filename = f"MetaDetective_Export-{custom_suffix}{timestamp}{file_extension}"

            full_path = os.path.join(args.out, filename)

            with open(full_path, "w") as f:
                f.write(content)
            print(f"Results file exported to {full_path}")
        else:
            display_metadata(args, all_metadata, ignore_patterns)

    else:
        parser.error("You must specify either --scraping or --directory or --files.")


if __name__ == "__main__":
    main()
