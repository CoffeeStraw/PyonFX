# PyonFX: An easy way to create KFX (Karaoke Effects) and complex typesetting using the ASS format (Advanced Substation Alpha).
# Copyright (C) 2019-2025 Antonio Strippoli (CoffeeStraw/YellowFlash)
#                         and contributors (https://github.com/CoffeeStraw/PyonFX/graphs/contributors)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyonFX is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see http://www.gnu.org/licenses/.

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Callable, Iterator, Literal


@dataclass(frozen=True, slots=True)
class Pixel:
    x: int
    y: int
    color: str | tuple[int, int, int] = "&HFFFFFF&"
    alpha: str | int = "&H00&"

    def with_color(self, color: str | tuple[int, int, int]) -> "Pixel":
        return Pixel(self.x, self.y, color, self.alpha)

    def with_alpha(self, alpha: str | int) -> "Pixel":
        return Pixel(self.x, self.y, self.color, alpha)

    def with_position(self, x: int, y: int) -> "Pixel":
        return Pixel(x, y, self.color, self.alpha)


class PixelCollection:
    def __init__(self, pixels: Iterable[Pixel]):
        self._pixels = list(pixels)

    def __iter__(self) -> Iterator[Pixel]:
        return iter(self._pixels)

    def __len__(self) -> int:
        return len(self._pixels)

    def __getitem__(self, index: int | slice) -> "Pixel | PixelCollection":
        if isinstance(index, slice):
            return PixelCollection(self._pixels[index])
        return self._pixels[index]

    def __bool__(self) -> bool:
        return bool(self._pixels)

    def __repr__(self) -> str:
        return f"PixelCollection({len(self._pixels)} pixels)"

    # Bounds and properties
    @property
    def bounds(self) -> tuple[int, int, int, int]:
        """Returns (min_x, min_y, max_x, max_y)"""
        if not self._pixels:
            return (0, 0, 0, 0)
        xs = [p.x for p in self._pixels]
        ys = [p.y for p in self._pixels]
        return (min(xs), min(ys), max(xs), max(ys))

    @property
    def width(self) -> int:
        min_x, _, max_x, _ = self.bounds
        return max_x - min_x + 1

    @property
    def height(self) -> int:
        _, min_y, _, max_y = self.bounds
        return max_y - min_y + 1

    def is_empty(self) -> bool:
        return len(self._pixels) == 0

    # Filtering and selection
    def filter(self, predicate: Callable[[Pixel], bool]) -> "PixelCollection":
        return PixelCollection(p for p in self._pixels if predicate(p))

    def filter_by_region(self, x1: int, y1: int, x2: int, y2: int) -> "PixelCollection":
        return self.filter(lambda p: x1 <= p.x <= x2 and y1 <= p.y <= y2)

    def filter_by_color(self, color: str | tuple[int, int, int]) -> "PixelCollection":
        return self.filter(lambda p: p.color == color)

    def at_position(self, x: int, y: int) -> list[Pixel]:
        """Get all pixels at a specific position (there could be multiple)"""
        return [p for p in self._pixels if p.x == x and p.y == y]

    # Transformations
    def map(self, transform: Callable[[Pixel], Pixel]) -> "PixelCollection":
        return PixelCollection(transform(p) for p in self._pixels)

    def move(self, dx: int, dy: int) -> "PixelCollection":
        return self.map(lambda p: p.with_position(p.x + dx, p.y + dy))

    # Texture operations
    def apply_texture(
        self,
        texture: "str | PixelCollection",
        mode: Literal["stretch", "repeat", "repeat_h", "repeat_v"] = "stretch",
        skip_transparent: bool = False,
        output_rgba: bool = False,
        blend_mode: Literal["replace", "multiply"] = "replace",
        missing_pixel: Literal["default", "skip"] = "default",
    ) -> "PixelCollection":
        """Applies a texture onto this pixel collection.

        This method maps the provided texture (from image or another PixelCollection) onto
        the current pixels using the specified mapping mode.

        Parameters:
            texture (str | PixelCollection): Path to texture image or a PixelCollection to use as texture.
            mode (str): Texture mapping mode:
                - "stretch": Scale texture to exactly cover the pixel collection's bounding box.
                - "repeat": Use texture's natural resolution and tile it across both dimensions.
                - "repeat_h": Scale texture height to fit bounding box and tile horizontally.
                - "repeat_v": Scale texture width to fit bounding box and tile vertically.
            skip_transparent (bool): Whether to skip transparent pixels in the texture.
            output_rgba (bool): If True, returns texture pixels in RGBA tuple format; otherwise in ASS color format.
            blend_mode (str): How to blend texture with existing pixels:
                - "replace": Replace color, keep original alpha
                - "multiply": Multiply colors together
            missing_pixel (str): Behavior when the corresponding texture pixel is missing. 'default' uses a default white pixel; 'skip' leaves the base pixel unchanged.

        Returns:
            PixelCollection: A new PixelCollection with the texture applied.
        """
        # Import here to avoid circular dependencies
        from .convert import Convert

        def _load_texture_from_image(
            image_path: str, mode: str, skip_transparent: bool, output_rgba: bool
        ) -> "PixelCollection":
            """Load texture pixels from image file based on the mapping mode."""
            min_x, min_y, max_x, max_y = self.bounds
            bb_width = max_x - min_x if (max_x - min_x) != 0 else 1
            bb_height = max_y - min_y if (max_y - min_y) != 0 else 1

            # Load image with appropriate dimensions based on mode
            if mode == "stretch":
                return Convert.image_to_pixels(
                    image_path,
                    width=bb_width,
                    height=bb_height,
                    skip_transparent=skip_transparent,
                    output_rgba=output_rgba,
                )
            elif mode == "repeat_h":
                return Convert.image_to_pixels(
                    image_path,
                    height=bb_height,
                    skip_transparent=skip_transparent,
                    output_rgba=output_rgba,
                )
            elif mode == "repeat_v":
                return Convert.image_to_pixels(
                    image_path,
                    width=bb_width,
                    skip_transparent=skip_transparent,
                    output_rgba=output_rgba,
                )
            elif mode == "repeat":
                return Convert.image_to_pixels(
                    image_path,
                    skip_transparent=skip_transparent,
                    output_rgba=output_rgba,
                )
            else:
                raise ValueError(
                    f"Unknown texture mode: {mode}. Use 'stretch', 'repeat', 'repeat_h' or 'repeat_v'."
                )

        def _map_to_texture_coords(
            pixel_x: int,
            pixel_y: int,
            min_x: int,
            min_y: int,
            bb_width: int,
            bb_height: int,
            tex_width: int,
            tex_height: int,
            mode: str,
        ) -> tuple[int, int]:
            """Map pixel coordinates to texture coordinates based on mode."""
            if mode == "stretch":
                u = (pixel_x - min_x) / bb_width
                v = (pixel_y - min_y) / bb_height
                tex_x = int(u * (tex_width - 1))
                tex_y = int(v * (tex_height - 1))
            elif mode == "repeat":
                tex_x = (pixel_x - min_x) % tex_width
                tex_y = (pixel_y - min_y) % tex_height
            elif mode == "repeat_h":
                v = (pixel_y - min_y) / bb_height
                tex_y = int(v * (tex_height - 1))
                tex_x = (pixel_x - min_x) % tex_width
            elif mode == "repeat_v":
                u = (pixel_x - min_x) / bb_width
                tex_x = int(u * (tex_width - 1))
                tex_y = (pixel_y - min_y) % tex_height
            else:
                raise ValueError(
                    f"Unknown texture mode: {mode}. Use 'stretch', 'repeat', 'repeat_h' or 'repeat_v'."
                )

            return tex_x, tex_y

        def _blend_colors(
            base_color: str | tuple[int, int, int],
            texture_color: str | tuple[int, int, int],
            blend_mode: str,
        ) -> str | tuple[int, int, int]:
            """Blend base color with texture color using specified blend mode."""
            if blend_mode == "replace":
                return texture_color

            # Convert input colors to RGB tuples if they are in ASS format strings
            if isinstance(base_color, str):
                base_rgb = Convert.color_ass_to_rgb(base_color, as_str=False)
            else:
                base_rgb = base_color
            if isinstance(texture_color, str):
                texture_rgb = Convert.color_ass_to_rgb(texture_color, as_str=False)
            else:
                texture_rgb = texture_color

            r1, g1, b1 = int(base_rgb[0]), int(base_rgb[1]), int(base_rgb[2])
            r2, g2, b2 = int(texture_rgb[0]), int(texture_rgb[1]), int(texture_rgb[2])

            if blend_mode == "multiply":
                new_r = int((r1 * r2) / 255)
                new_g = int((g1 * g2) / 255)
                new_b = int((b1 * b2) / 255)
            else:
                raise ValueError(
                    f"Unknown blend mode: {blend_mode}. Use 'replace' or 'multiply'."
                )

            new_rgb = (min(new_r, 255), min(new_g, 255), min(new_b, 255))

            # Return in the same format as the base color
            if isinstance(base_color, str):
                return Convert.color_rgb_to_ass(new_rgb)
            return new_rgb

        if self.is_empty():
            return PixelCollection([])

        # Load texture pixels
        if isinstance(texture, str):
            # Load from image file
            texture_pixels = _load_texture_from_image(
                texture, mode, skip_transparent, output_rgba
            )
        else:
            # Use provided PixelCollection as texture
            texture_pixels = texture

        if texture_pixels.is_empty():
            raise ValueError("Texture did not produce any pixels.")

        # Get bounds for mapping
        min_x, min_y, _, _ = self.bounds
        bb_width = self.width
        bb_height = self.height

        # Get texture bounds
        tex_min_x, tex_min_y, _, _ = texture_pixels.bounds
        tex_width = texture_pixels.width
        tex_height = texture_pixels.height

        # Build texture lookup dictionary for efficiency
        tex_dict = {(p.x - tex_min_x, p.y - tex_min_y): p for p in texture_pixels}

        # Apply texture to each pixel
        textured_pixels = []
        for pixel in self._pixels:
            # Map pixel to texture coordinates based on mode
            tex_x, tex_y = _map_to_texture_coords(
                pixel.x,
                pixel.y,
                min_x,
                min_y,
                bb_width,
                bb_height,
                tex_width,
                tex_height,
                mode,
            )

            # Get texture pixel (with fallback based on missing_pixel behavior)
            texture_pixel = tex_dict.get((tex_x, tex_y))
            if texture_pixel is None:
                if missing_pixel == "default":
                    if output_rgba:
                        texture_pixel = Pixel(
                            x=tex_x, y=tex_y, color=(255, 255, 255), alpha=255
                        )
                    else:
                        texture_pixel = Pixel(
                            x=tex_x, y=tex_y, color="&HFFFFFF&", alpha="&HFF&"
                        )
                elif missing_pixel == "skip":
                    continue

            # Apply blending
            new_color = _blend_colors(pixel.color, texture_pixel.color, blend_mode)

            # Keep original alpha (texture affects color, not transparency of the shape)
            textured_pixels.append(
                Pixel(x=pixel.x, y=pixel.y, color=new_color, alpha=pixel.alpha)
            )

        return PixelCollection(textured_pixels)
