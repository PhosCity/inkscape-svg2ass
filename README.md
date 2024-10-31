# inkscape-svg2ass

Inkscape extension to export selected objects Advanced SubStation Alpha (.ass) format.

![Screenshot_2024-10-31-11-44-54](https://github.com/user-attachments/assets/ef106948-1bc0-4c42-a91a-0e3b481e5e05)

## Install

Copy extension files `convert_to_ass.inx` and `convert_to_ass.py` into your extension directory. This is the directory listed at `Edit > Preferences > System: User extensions.` in Inkscape.

## Usage

Select the objects you want to export and from the Extensions menu choose `Export` and `Convert to ASS`. If the svg was not authored in Inkscape or gimp, I cannot guarantee correct output.

## Supported SVG elements

- g(roup)
- line
- rect
- circle, ellipse
- polyline, polygon
- path

## Supported SVG attributes

- attributes essential to the elements listed above
- select presentation attributes and inline CSS style attributes
  (colors/alpha for fill and stroke; stroke width)
- transform (translate, scale, rotate, skewX, skewY, matrix)

## Output format

There are four output formats:

### Drawing

This only outputs the ass tags and drawing in the format:

```
{\tags}m ...
```

### clip

This outputs the shape inside clip tag in the format:

```
\clip(m ...)
```

### iclip

This outputs the shape inside iclip tag in the format:

```
\iclip(m ...)
```

### Lines

This outputs the full line in the format:

```
Dialogue: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
```
