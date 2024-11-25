#!/usr/bin/env python3
"""
Given an SVG template and a table,
generate a set of SVG files with the table data.
"""

import argparse
import math
import csv
import os
import re
import re

def write_files(templatetext, data, outdir):
    """
    Write SVG files based on template and data records.
    
    Args:
        templatetext (str): The SVG template text containing PXTAG_XXX[N] tags
        data (list): List of dictionaries containing the data records
        outdir (str): Output directory path
    """
    # First find the number of records per page by analyzing tags
    parts = re.split(r'<[^>]+>', templatetext)
    # Get any tag to check its max number
    tag_match = re.search(r'PXTAG_[A-Z]+\d+', templatetext)
    if not tag_match:
        raise ValueError("No numbered tags found in template")
    
    # Find all numbers for this tag
    numbers = []
    for part in parts:
        matches = re.findall(rf'{tag_match.group(0)[:-1]}(\d+)', part)
        numbers.extend(int(n) for n in matches)
    
    records_per_page = max(numbers)
    total_pages = math.ceil(len(data) / records_per_page)
    
    # Process each page
    for page in range(total_pages):
        pagetext = templatetext
        start_idx = page * records_per_page
        
        # Get records for this page
        page_records = data[start_idx:start_idx + records_per_page]
        
        # Pad with empty records if needed for last page
        while len(page_records) < records_per_page:
            page_records.append({key: '' for key in data[0].keys()})
            
        # For each record position in the page
        for pos in range(1, records_per_page + 1):
            record = page_records[pos - 1]
            
            # Find all tags for this position and replace them
            for key in record.keys():
                # Replace all instances of PXTAG_KEY{pos} with the record value
                pattern = rf'PXTAG_{key}{pos}'
                pagetext = pagetext.replace(pattern, str(record[key]))
        
        # Write the page to a file
        outfile = os.path.join(outdir, f'page_{page + 1}.svg')
        with open(outfile, 'w') as f:
            f.write(pagetext)
        
    return total_pages

def get_tags(filename):
    """ 
    Read a SVG file and return a list of tags and page count.
    Tags are strings in format PXTAG_XXX where XXX is alphabetic.
    Returns the list of unique base tags and the highest number found in the numbered series.
    Each tag can appear multiple times with the same number, e.g.:
    PXTAG_NAMSUR1 PXTAG_NAMSUR1 PXTAG_NAMSUR2 PXTAG_NAMSUR2 ... PXTAG_NAMSUR5 PXTAG_NAMSUR5
    """
    with open(filename) as f:
        content = f.read()

    # Split content by XML tags and only process text outside them
    parts = re.split(r'<[^>]+>', content)
    base_tags = []
    for part in parts:
        matches = re.findall(r'PXTAG_[A-Z]+', part)
        base_tags.extend(matches)
    
    unique_tags = [tag[6:] for tag in set(base_tags)]
    if not unique_tags:
        raise ValueError('No tags found')

    # Find highest number for first tag
    first_tag = unique_tags[0]
    numbers = []
    for part in parts:
        matches = re.findall(rf'PXTAG_{first_tag}(\d+)', part)
        numbers.extend(int(n) for n in matches)
    
    if not numbers:
        raise ValueError(f'No numbered instances found for tag {first_tag}')
    
    reference_max = max(numbers)

    # Verify all tags have the same highest number
    for tag in unique_tags[1:]:
        numbers = []
        for part in parts:
            matches = re.findall(rf'PXTAG_{tag}(\d+)', part)
            numbers.extend(int(n) for n in matches)
        
        if not numbers:
            raise ValueError(f'No numbered instances found for tag {tag}')
        
        tag_max = max(numbers)
        if tag_max != reference_max:
            raise ValueError(f'Tag {tag} has max number {tag_max}, expected {reference_max}')

    return unique_tags, reference_max, content
    

def readtable(filename):
    """
    Read a TSV file. The first row is the header, return it as list (header).
    Then return each record in a second list [(x,y,z), (a,b,c), ...]

    """

    with open(filename) as f:
        reader = csv.reader(f, delimiter='\t')
        header = next(reader)
        # remove empty columns
        header = [col for col in header if col]


        data = [row for row in reader]
        # keep only the columns that have a header
        data = [[cell for cell in row if cell] for row in data]

        # make data a list of dictionaries, using the header as keys
        data = [dict(zip(header, row)) for row in data]



    return header, data
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('template', help='SVG template file')
    parser.add_argument('table', help='CSV table file')
    parser.add_argument('output', help='Output directory')
    args = parser.parse_args()

    # Read the template file
    tags, pages, template_text = get_tags(args.template)
    print(tags)

    # Read the table file
    columns, data = readtable(args.table)
    print(data)

    # write
    if not os.path.exists(args.output):
        try:   
            os.makedirs(args.output)
        except OSError:
            print ("Creation of the directory %s failed" % args.output)
    
    pages = write_files(template_text, data, args.output)
    print(f'Wrote {pages} pages to {args.output}')