# inkscape-svg2ass

Inkscape extension to export selected objects Advanced SubStation Alpha (.ass) format

## Install

Copy extension files `multipage_export.inx` and `multipage_export.py` into your extension directory. This is the directory listed at `Edit > Preferences > System: User extensions.` in Inkscape.

## Usage

Select the objects you want to export and from the Extensions menu choose `Export` and `Convert to ASS`.

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
