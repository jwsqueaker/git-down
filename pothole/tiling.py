"""
Image tiling utilities for processing large rasters.
"""

import numpy as np
from typing import List, Tuple, Iterator
import rasterio
from rasterio.windows import Window


class ImageTiler:
    """
    Split large images into tiles for inference, with overlap support.
    """

    def __init__(self, tile_size: int = 512, overlap: int = 64):
        """
        Args:
            tile_size: Size of each tile (square)
            overlap: Number of pixels to overlap between tiles
        """
        self.tile_size = tile_size
        self.overlap = overlap
        self.step = tile_size - overlap

    def get_tiles(self, height: int, width: int) -> List[Tuple[int, int, int, int]]:
        """
        Calculate tile coordinates for an image.

        Args:
            height: Image height
            width: Image width

        Returns:
            List of tuples (row_start, col_start, tile_height, tile_width)
        """
        tiles = []

        for row in range(0, height, self.step):
            for col in range(0, width, self.step):
                # Calculate actual tile dimensions (may be smaller at edges)
                tile_h = min(self.tile_size, height - row)
                tile_w = min(self.tile_size, width - col)

                tiles.append((row, col, tile_h, tile_w))

        return tiles

    def extract_tile(self, image: np.ndarray, row: int, col: int, tile_h: int, tile_w: int) -> np.ndarray:
        """
        Extract a tile from an image array.

        Args:
            image: Image array (H, W, C) or (C, H, W)
            row: Starting row
            col: Starting column
            tile_h: Tile height
            tile_w: Tile width

        Returns:
            Tile array, padded to tile_size if necessary
        """
        # Handle both (H, W, C) and (C, H, W) formats
        if image.ndim == 3 and image.shape[0] <= 4:  # (C, H, W)
            tile = image[:, row:row + tile_h, col:col + tile_w]
            # Pad if necessary
            if tile.shape[1] < self.tile_size or tile.shape[2] < self.tile_size:
                padded = np.zeros((image.shape[0], self.tile_size, self.tile_size), dtype=image.dtype)
                padded[:, :tile.shape[1], :tile.shape[2]] = tile
                return padded
            return tile
        else:  # (H, W, C) or (H, W)
            tile = image[row:row + tile_h, col:col + tile_w]
            # Pad if necessary
            if tile.shape[0] < self.tile_size or tile.shape[1] < self.tile_size:
                if image.ndim == 3:
                    padded = np.zeros((self.tile_size, self.tile_size, image.shape[2]), dtype=image.dtype)
                else:
                    padded = np.zeros((self.tile_size, self.tile_size), dtype=image.dtype)
                padded[:tile.shape[0], :tile.shape[1]] = tile
                return padded
            return tile

    def merge_tiles(
        self,
        tiles: List[np.ndarray],
        tile_coords: List[Tuple[int, int, int, int]],
        output_shape: Tuple[int, int],
        blend: bool = True,
    ) -> np.ndarray:
        """
        Merge tiles back into a full image.

        Args:
            tiles: List of tile arrays
            tile_coords: List of (row, col, tile_h, tile_w) for each tile
            output_shape: (height, width) of output image
            blend: Use weighted blending in overlap regions

        Returns:
            Merged output array
        """
        height, width = output_shape
        output = np.zeros((height, width), dtype=np.float32)
        weight_map = np.zeros((height, width), dtype=np.float32)

        for tile, (row, col, tile_h, tile_w) in zip(tiles, tile_coords):
            # Handle tile shape (may be padded)
            if tile.ndim == 3:
                tile = tile.squeeze()

            # Use actual tile dimensions
            actual_tile = tile[:tile_h, :tile_w]

            if blend and self.overlap > 0:
                # Create weight ramp for blending
                weight = self._create_weight_ramp(tile_h, tile_w)
            else:
                weight = np.ones((tile_h, tile_w), dtype=np.float32)

            # Add to output with weights
            output[row:row + tile_h, col:col + tile_w] += actual_tile * weight
            weight_map[row:row + tile_h, col:col + tile_w] += weight

        # Normalize by weight map
        output = np.divide(output, weight_map, out=output, where=weight_map > 0)

        return output

    def _create_weight_ramp(self, height: int, width: int) -> np.ndarray:
        """Create a weight ramp that fades to zero at edges for smooth blending."""
        # Create 1D ramps
        ramp_h = np.minimum(np.arange(height), np.arange(height)[::-1])
        ramp_w = np.minimum(np.arange(width), np.arange(width)[::-1])

        # Normalize to [0, 1]
        ramp_h = ramp_h / max(ramp_h.max(), 1)
        ramp_w = ramp_w / max(ramp_w.max(), 1)

        # Combine into 2D weight map
        weight = np.minimum(ramp_h[:, None], ramp_w[None, :])

        return weight.astype(np.float32)


def tile_geotiff(
    geotiff_path: str,
    tile_size: int = 512,
    overlap: int = 64,
) -> Iterator[Tuple[np.ndarray, Window, dict]]:
    """
    Generator that yields tiles from a GeoTIFF with their geospatial context.

    Args:
        geotiff_path: Path to input GeoTIFF
        tile_size: Size of each tile
        overlap: Overlap between tiles

    Yields:
        Tuple of (tile_array, rasterio_window, metadata)
    """
    tiler = ImageTiler(tile_size=tile_size, overlap=overlap)

    with rasterio.open(geotiff_path) as src:
        height = src.height
        width = src.width

        tile_coords = tiler.get_tiles(height, width)

        for row, col, tile_h, tile_w in tile_coords:
            # Create rasterio window
            window = Window(col, row, tile_w, tile_h)

            # Read tile
            tile_data = src.read(window=window)  # Returns (C, H, W)

            # Get window transform
            transform = src.window_transform(window)

            metadata = {
                "window": window,
                "transform": transform,
                "crs": src.crs,
                "row": row,
                "col": col,
                "tile_h": tile_h,
                "tile_w": tile_w,
            }

            yield tile_data, window, metadata
