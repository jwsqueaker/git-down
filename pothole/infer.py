"""
Main inference pipeline for pothole detection.
"""

import os
from typing import Optional, Dict, Any, Tuple
import numpy as np
import torch
import rasterio
from tqdm import tqdm
import logging

from .model_unet import create_model
from .tiling import ImageTiler
from .vectorize import raster_to_polygons, polygons_to_geojson, add_area_m2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PotholeDetector:
    """
    End-to-end pothole detection from GeoTIFF imagery.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: Optional[str] = None,
        tile_size: int = 512,
        overlap: int = 64,
        threshold: float = 0.5,
        min_area: float = 1.0,
        batch_size: int = 4,
    ):
        """
        Args:
            model_path: Path to pretrained model weights (.pth)
            device: Device to run inference on ('cpu', 'cuda', or None for auto)
            tile_size: Size of tiles for processing
            overlap: Overlap between tiles
            threshold: Probability threshold for binary mask
            min_area: Minimum area for polygons (in CRS units)
            batch_size: Batch size for inference
        """
        self.model_path = model_path
        self.tile_size = tile_size
        self.overlap = overlap
        self.threshold = threshold
        self.min_area = min_area
        self.batch_size = batch_size

        # Set device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        logger.info(f"Using device: {self.device}")

        # Initialize model
        self.model = None
        self.tiler = ImageTiler(tile_size=tile_size, overlap=overlap)

    def load_model(self, n_channels: int = 3):
        """Load the U-Net model."""
        if self.model is None:
            self.model = create_model(
                n_channels=n_channels,
                pretrained_path=self.model_path,
                device=self.device,
            )
            logger.info("Model loaded successfully")

    def preprocess_tile(self, tile: np.ndarray) -> torch.Tensor:
        """
        Preprocess a tile for model input.

        Args:
            tile: Tile array (C, H, W) or (H, W, C)

        Returns:
            Preprocessed tensor (1, C, H, W)
        """
        # Ensure (C, H, W) format
        if tile.ndim == 2:
            tile = tile[None, :, :]  # Add channel dimension
        elif tile.shape[-1] in [3, 4]:  # (H, W, C)
            tile = np.transpose(tile, (2, 0, 1))

        # Take first 3 channels if RGBA
        if tile.shape[0] > 3:
            tile = tile[:3, :, :]

        # Normalize to [0, 1]
        tile = tile.astype(np.float32)
        if tile.max() > 1.0:
            tile = tile / 255.0

        # Convert to tensor
        tensor = torch.from_numpy(tile).unsqueeze(0)  # Add batch dimension

        return tensor

    def predict_tile(self, tile: np.ndarray) -> np.ndarray:
        """
        Run inference on a single tile.

        Args:
            tile: Input tile array

        Returns:
            Probability map (H, W)
        """
        # Preprocess
        input_tensor = self.preprocess_tile(tile).to(self.device)

        # Inference
        with torch.no_grad():
            output = self.model(input_tensor)
            prob = torch.sigmoid(output).squeeze().cpu().numpy()

        return prob

    def process_geotiff(
        self,
        geotiff_path: str,
        output_geojson_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a GeoTIFF and detect potholes.

        Args:
            geotiff_path: Path to input GeoTIFF
            output_geojson_path: Optional path to save output GeoJSON
            metadata: Optional metadata to add to features

        Returns:
            GeoJSON FeatureCollection with detected potholes
        """
        logger.info(f"Processing {geotiff_path}")

        with rasterio.open(geotiff_path) as src:
            height = src.height
            width = src.width
            transform = src.transform
            crs = src.crs
            n_channels = src.count

            logger.info(f"Image size: {width}x{height}, channels: {n_channels}, CRS: {crs}")

            # Load model if not loaded
            if self.model is None:
                self.load_model(n_channels=min(n_channels, 3))

            # Get tiles
            tile_coords = self.tiler.get_tiles(height, width)
            logger.info(f"Processing {len(tile_coords)} tiles")

            # Process tiles
            probability_tiles = []

            for row, col, tile_h, tile_w in tqdm(tile_coords, desc="Processing tiles"):
                # Read tile
                tile_data = src.read(window=rasterio.windows.Window(col, row, tile_w, tile_h))

                # Predict
                prob_map = self.predict_tile(tile_data)

                probability_tiles.append(prob_map)

            # Merge tiles
            logger.info("Merging tiles...")
            full_probability = self.tiler.merge_tiles(
                probability_tiles,
                tile_coords,
                (height, width),
                blend=True,
            )

            # Create binary mask
            binary_mask = (full_probability > self.threshold).astype(np.uint8)

            logger.info(f"Detected pixels: {binary_mask.sum()}")

            # Vectorize
            logger.info("Vectorizing detections...")
            polygons = raster_to_polygons(
                binary_mask,
                transform=transform,
                crs=crs,
                probability_map=full_probability,
                min_area=self.min_area,
            )

            logger.info(f"Found {len(polygons)} polygons after filtering")

            # Build GeoJSON
            geojson = polygons_to_geojson(polygons, crs=crs, metadata=metadata)

            # Add area in square meters
            geojson = add_area_m2(geojson, crs)

            # Save if path provided
            if output_geojson_path:
                self.save_geojson(geojson, output_geojson_path)

            return geojson

    def save_geojson(self, geojson: Dict[str, Any], output_path: str):
        """Save GeoJSON to file."""
        import json

        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(geojson, f, indent=2)

        logger.info(f"Saved GeoJSON to {output_path}")

    def process_with_custom_image(
        self,
        image: np.ndarray,
        transform: Any,
        crs: Any,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Process a custom image array.

        Args:
            image: Image array (C, H, W) or (H, W, C)
            transform: Affine transform
            crs: CRS

        Returns:
            Tuple of (probability_map, binary_mask)
        """
        # Ensure (C, H, W)
        if image.ndim == 3 and image.shape[-1] in [3, 4]:
            image = np.transpose(image, (2, 0, 1))

        height, width = image.shape[1], image.shape[2]

        # Load model
        if self.model is None:
            self.load_model(n_channels=image.shape[0])

        # Get tiles
        tile_coords = self.tiler.get_tiles(height, width)

        # Process tiles
        probability_tiles = []

        for row, col, tile_h, tile_w in tqdm(tile_coords, desc="Processing tiles"):
            # Extract tile
            tile = self.tiler.extract_tile(image, row, col, tile_h, tile_w)

            # Predict
            prob_map = self.predict_tile(tile)
            probability_tiles.append(prob_map)

        # Merge tiles
        full_probability = self.tiler.merge_tiles(
            probability_tiles,
            tile_coords,
            (height, width),
            blend=True,
        )

        # Create binary mask
        binary_mask = (full_probability > self.threshold).astype(np.uint8)

        return full_probability, binary_mask
