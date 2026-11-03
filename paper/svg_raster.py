"""Compact previews of the polygon/translate SVG subset from Three SVGRenderer.

Geometry and lighting come from the actual renderer, not a replacement drawing.
Unsupported drawing operations fail rather than inventing an approximation.
"""

from pathlib import Path
import re
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont


def rasterize(source, output, hide_text=False, scale=2):
    root = source if isinstance(source, ET.Element) else ET.parse(source).getroot()
    width, height = int(float(root.attrib["width"])), int(float(root.attrib["height"]))
    image = Image.new("RGB", (width * scale, height * scale), "white")
    draw = ImageDraw.Draw(image)
    number = r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?"

    def color(value):
        if value.startswith("rgb("):
            return tuple(int(float(v)) for v in value[4:-1].split(","))
        return value

    def visit(element, tx=0.0, ty=0.0):
        tag = element.tag.rsplit("}", 1)[-1]
        if tag == "svg" and element is not root:
            layer = rasterize(element, None, hide_text=hide_text, scale=scale)
            image.paste(
                layer.resize((layer.width * scale, layer.height * scale)),
                (
                    int((tx + float(element.attrib.get("x", 0))) * scale),
                    int((ty + float(element.attrib.get("y", 0))) * scale),
                ),
            )
            return
        transform = element.attrib.get("transform", "")
        if transform:
            match = re.fullmatch(r"translate\(([^)]+)\)", transform)
            if not match:
                raise ValueError("Unsupported SVG transform")
            values = [float(v) for v in re.findall(number, match[1])]
            tx += values[0]
            ty += values[1] if len(values) > 1 else 0
        attrs = dict(element.attrib)
        attrs.update(
            dict(part.split(":", 1) for part in attrs.get("style", "").split(";") if ":" in part)
        )
        fill = color(attrs.get("fill", "black"))
        if tag == "path":
            path = attrs["d"]
            commands = re.sub(number, "", path)
            if any(c.isalpha() and c not in "MLzZ" for c in commands):
                raise ValueError("Unsupported SVG path command")
            for polygon in re.findall(r"M([^zZ]+)[zZ]", path):
                values = [float(v) for v in re.findall(number, polygon)]
                points = [
                    ((values[i] + tx) * scale, (values[i + 1] + ty) * scale)
                    for i in range(0, len(values), 2)
                ]
                if fill != "none" and float(attrs.get("fill-opacity", 1)) != 0:
                    draw.polygon(points, fill=fill)
        elif tag == "rect":
            x, y = float(attrs.get("x", 0)) + tx, float(attrs.get("y", 0)) + ty
            w = width if attrs["width"] == "100%" else float(attrs["width"])
            h = height if attrs["height"] == "100%" else float(attrs["height"])
            draw.rectangle((x * scale, y * scale, (x + w) * scale, (y + h) * scale), fill=fill)
        elif tag == "text" and not hide_text:
            import matplotlib

            size = float(attrs.get("font-size", 12))
            font = ImageFont.truetype(
                str(Path(matplotlib.get_data_path()) / "fonts/ttf/DejaVuSans.ttf"),
                int(size * scale),
            )
            draw.text(
                (
                    (float(attrs.get("x", 0)) + tx) * scale,
                    (float(attrs.get("y", 0)) + ty - size) * scale,
                ),
                "".join(element.itertext()),
                font=font,
                fill=fill,
            )
        elif tag not in {"svg", "g", "text", "title", "desc"}:
            raise ValueError(f"Unsupported SVG element {tag}")
        for child in element:
            visit(child, tx, ty)

    view = [
        float(v)
        for v in root.attrib.get("viewBox", f"0 0 {width} {height}").replace(",", " ").split()
    ]
    if view[2:] != [float(width), float(height)]:
        raise ValueError("Preview requires an unscaled viewBox")
    visit(root, -view[0], -view[1])
    image = image.resize((width, height), Image.Resampling.LANCZOS)
    if output is not None:
        image.save(output, optimize=True)
    return image
