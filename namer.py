#!/usr/bin/env python3
"""
Conference Badge Generator

Generate conference badges by combining an SVG template with attendee data.
The script takes a TSV file with attendee information and an SVG template with placeholders,
generating individual badge pages as both SVG and PDF files.

Usage:
    python badge_generator.py template.svg attendees.tsv output_dir [--prefix PREFIX] [--force]
"""

import argparse
import csv
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import subprocess
from xml.etree import ElementTree as ET

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Template:
    """Represents an SVG template with placeholder tags."""
    content: str
    tags: Set[str]
    records_per_page: int

@dataclass
class AttendeeData:
    """Represents the attendee data from TSV file."""
    headers: List[str]
    records: List[Dict[str, str]]

class BadgeGenerator:
    def __init__(self, prefix: str = "PXTAG_"):
        self.prefix = prefix
        self._inkscape_path = self._find_inkscape()

    def _find_inkscape(self) -> Optional[str]:
        """Find Inkscape executable path."""
        paths = ['inkscape', '/Applications/Inkscape.app/Contents/MacOS/inkscape']
        for path in paths:
            try:
                subprocess.run([path, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                return path
            except FileNotFoundError:
                continue
        return None

    def read_template(self, template_path: Path) -> Template:
        """
        Read and parse SVG template file.
        
        Args:
            template_path: Path to SVG template file
            
        Returns:
            Template object containing content and parsed tags
        """
        try:
            with open(template_path) as f:
                content = f.read()
    
            # Validate SVG
            try:
                ET.fromstring(content)
            except ET.ParseError as e:
                raise ValueError(f"Invalid SVG template: {e}")
    
            # Find all unique base tags and their highest number
            tag_pattern = rf'{self.prefix}([A-Z]+)(\d+)'
            matches = re.findall(tag_pattern, content)
            
            if not matches:
                raise ValueError(f"No tags found with prefix {self.prefix}")
            
            # Get unique tag types (NAME, AFFILIATION, etc.)
            tags = {match[0] for match in matches}
            
            # Find highest number used for any tag
            max_number = max(int(match[1]) for match in matches)
            
            # Verify that for each tag type, we have a continuous sequence from 1 to max_number
            for tag in tags:
                numbers_found = {int(num) for _, num in matches if _ == tag}
                expected_numbers = set(range(1, max_number + 1))
                if not numbers_found.issubset(expected_numbers):
                    raise ValueError(f"Tag {tag} is missing some numbers in sequence 1 to {max_number}")
            
            return Template(
                content=content,
                tags=tags,
                records_per_page=max_number
            )
    
        except FileNotFoundError:
            raise FileNotFoundError(f"Template file not found: {template_path}")
    def read_attendees(self, data_path: Path) -> AttendeeData:
        """
        Read attendee data from TSV file.
        
        Args:
            data_path: Path to TSV file
            
        Returns:
            AttendeeData object containing headers and records
        """
        try:
            with open(data_path) as f:
                reader = csv.reader(f, delimiter='\t')
                headers = next(reader)
                
                if not headers:
                    raise ValueError("Empty header row in data file")
                
                # Remove empty columns and whitespace
                headers = [h.strip() for h in headers if h.strip()]
                
                records = []
                for row_num, row in enumerate(reader, start=2):
                    # Skip empty rows
                    if not any(cell.strip() for cell in row):
                        continue
                        
                    # Clean and validate row data
                    row = [cell.strip() for cell in row[:len(headers)]]
                    if len(row) != len(headers):
                        logger.warning(
                            f"Row {row_num} has {len(row)} columns, expected {len(headers)}. "
                            "Row will be padded with empty strings."
                        )
                        row.extend([''] * (len(headers) - len(row)))
                    
                    records.append(dict(zip(headers, row)))
                
                return AttendeeData(headers=headers, records=records)

        except FileNotFoundError:
            raise FileNotFoundError(f"Data file not found: {data_path}")

    def generate_badges(self, template: Template, data: AttendeeData, output_dir: Path) -> int:
        """
        Generate badge pages from template and data.
        """
        # Validate that template tags match data headers
        template_tags = {tag.upper() for tag in template.tags}
        data_headers = {h.upper() for h in data.headers}
        
        missing_tags = data_headers - template_tags
        if missing_tags:
            logger.warning(f"Data columns missing from template: {', '.join(missing_tags)}")
        
        missing_required = template_tags - data_headers
        if missing_required:
            raise ValueError(
                f"Required template tags missing from data: {', '.join(missing_required)}. "
                f"Data must contain columns for all tags used in template."
            )
        # Calculate total pages needed
        total_pages = (len(data.records) + template.records_per_page - 1) // template.records_per_page
        
        # Generate each page
        for page in range(total_pages):
            logger.info(f"\tAdding page {page+1}/{total_pages}...")
            page_content = template.content
            start_idx = page * template.records_per_page
            page_records = data.records[start_idx:start_idx + template.records_per_page]
            
            # Pad with empty records if needed
            while len(page_records) < template.records_per_page:
                page_records.append({key: '' for key in data.headers})
            
            # Replace tags for each record position
            for pos in range(1, template.records_per_page + 1):
                record = page_records[pos - 1]
                for key in data.headers:
                    tag = f"{self.prefix}{key}{pos}"
                    # Use re.sub instead of string replace to get all occurrences
                    page_content = re.sub(re.escape(tag), str(record.get(key, '')), page_content)
            
            # Write SVG file
            output_path = output_dir / f'page_{page + 1}.svg'
            with open(output_path, 'w') as f:
                f.write(page_content)
            
            # Convert to PDF if Inkscape is available
            if self._inkscape_path:
                pdf_path = output_path.with_suffix('.pdf')
                try:
                    subprocess.run(
                        [self._inkscape_path, str(output_path), '--export-filename', str(pdf_path)],
                        stderr=subprocess.DEVNULL
                    )
                except Exception as e:
                    logger.error(f"Failed to convert {output_path} to PDF: {e}")
        
        return total_pages

def main():
    parser = argparse.ArgumentParser(description="Generate conference badges from SVG template and TSV data")
    parser.add_argument('template', help='SVG template file')
    parser.add_argument('data', help='TSV data file')
    parser.add_argument('output', help='Output directory')
    parser.add_argument('--prefix', default='PXTAG_', help='Tag prefix (default: PXTAG_)')
    parser.add_argument('--force', action='store_true', help='Overwrite existing output directory')
    
    args = parser.parse_args()
    
    # Convert paths
    template_path = Path(args.template)
    data_path = Path(args.data)
    output_dir = Path(args.output)
    
    # Validate output directory
    if output_dir.exists() and not args.force:
        logger.error(f"Output directory exists: {output_dir}. Use --force to overwrite.")
        return 1
        
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        generator = BadgeGenerator(prefix=args.prefix)
        
        # Read template
        logger.info(f"Reading template: {template_path}")
        template = generator.read_template(template_path)
        logger.info(f"Found tags: {', '.join(template.tags)}")
        
        # Read data
        logger.info(f"Reading data: {data_path}")
        data = generator.read_attendees(data_path)
        logger.info(f"Found {len(data.records)} records with columns: {', '.join(data.headers)}")
        
        # Generate badges
        logger.info(f"Generating badges in: {output_dir}")
        pages = generator.generate_badges(template, data, output_dir)
        logger.info(f"Generated {pages} pages")
        
        return 0
        
    except (ValueError, FileNotFoundError) as e:
        logger.error(str(e))
        return 1

if __name__ == '__main__':
    exit(main())