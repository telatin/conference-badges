# conference-badges

Generate conference badges based on a list of attendees and an SVG template.

## Data file

A TSV file with a set of columns. For example: Name, Affiliation

## Template

The template is an SVG file with placeholders for the attendee name and the conference name.
Placeholders should be defined by a prefix and the name of the column.

For example, if the template has a text element the content as `prefix_name1`, the script will replace the content of the text element with the value of the column `name`.

This is because we expect to place multiple badges in the same SVG file, so you can use `prefix_name1`, `prefix_name2`, etc.

## Usage

```bash
python namer.py template.svg list.tsv outdir
```
