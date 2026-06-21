#!/usr/bin/env python3
"""
SAM-based pseudo-labeling pipeline for sky segmentation.

Usage:
    python sam_pseudo_label.py --input-dir ./images --output-dir ./masks \
        --method point --prompt auto

References:
    - SAM: https://segment-anything.com/
    - SAM 2: https://ai.meta.com/sam2/
"""

import argparse
import os
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
from PIL import Image
import json


def load_sam_model(model_type: str = "vit_h", checkpoint: Optional[str] = None):
    """Load SAM model."""
    try:
        from segment_anything import sam_model_registry, SamPredictor
    except ImportError:
        raise ImportError("segment_anything not installed. Run: pip install segment-anything")
    
    if checkpoint is None:
        checkpoint = f"sam_{model_type}.pth"
    
    sam = sam_model_registry[model_type](checkpoint=checkpoint)
    predictor = SamPredictor(sam)
    return predictor


def generate_sky_mask_sam(
    image: np.ndarray,
    predictor,
    method: str = "point",
    prompt: Optional[dict] = None
) -> np.ndarray:
    """
    Generate sky mask using SAM.
    
    Args:
        image: RGB image (H, W, 3)
        predictor: SAM predictor
        method: "point", "box", or "auto"
        prompt: Dict with "points" or "boxes" depending on method
    
    Returns:
        Binary mask (H, W) with 0/255
    """
    predictor.set_image(image)
    
    if method == "auto":
        # Automatic sky detection: sample points from top portion
        h, w = image.shape[:2]
        input_points = np.array([
            [w * 0.2, h * 0.1],
            [w * 0.5, h * 0.1],
            [w * 0.8, h * 0.1],
            [w * 0.3, h * 0.2],
            [w * 0.7, h * 0.2],
        ])
        input_labels = np.ones(len(input_points))
        masks, scores, logits = predictor.predict(
            point_coords=input_points,
            point_labels=input_labels,
            multimask_output=True,
        )
    elif method == "point":
        input_points = np.array(prompt["points"])
        input_labels = np.array(prompt.get("labels", [1] * len(input_points)))
        masks, scores, logits = predictor.predict(
            point_coords=input_points,
            point_labels=input_labels,
            multimask_output=True,
        )
    elif method == "box":
        input_box = np.array(prompt["box"])
        masks, scores, logits = predictor.predict(
            box=input_box,
            multimask_output=True,
        )
    else:
        raise ValueError(f"Unknown method: {method}")
    
    # Select best mask
    best_idx = np.argmax(scores)
    mask = masks[best_idx].astype(np.uint8) * 255
    
    return mask


def refine_mask_with_sam(
    image: np.ndarray,
    initial_mask: np.ndarray,
    predictor
) -> np.ndarray:
    """
    Refine existing mask using SAM.
    Uses the initial mask boundary as prompt.
    
    Args:
        image: RGB image
        initial_mask: Binary mask (0/255)
        predictor: SAM predictor
    
    Returns:
        Refined binary mask
    """
    from skimage import measure
    
    predictor.set_image(image)
    
    # Find contours in initial mask
    contours = measure.find_contours(initial_mask > 127, 0.5)
    
    if len(contours) == 0:
        return initial_mask
    
    # Sample points along largest contour
    largest_contour = max(contours, key=len)
    indices = np.linspace(0, len(largest_contour) - 1, min(10, len(largest_contour)), dtype=int)
    input_points = largest_contour[indices][:, [1, 0]]  # (y, x) -> (x, y)
    input_labels = np.ones(len(input_points))
    
    masks, scores, logits = predictor.predict(
        point_coords=input_points,
        point_labels=input_labels,
        multimask_output=True,
    )
    
    best_idx = np.argmax(scores)
    refined_mask = masks[best_idx].astype(np.uint8) * 255
    
    return refined_mask


def process_dataset(
    input_dir: Path,
    output_dir: Path,
    predictor,
    method: str = "auto",
    refine: bool = False,
    quality_check: bool = True
):
    """
    Process entire dataset with SAM.
    
    Args:
        input_dir: Directory containing images
        output_dir: Output directory for masks
        predictor: SAM predictor
        method: "auto", "point", or "box"
        refine: Whether to refine existing masks
        quality_check: Whether to filter low-quality masks
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    image_files = list(input_dir.glob("*.jpg")) + list(input_dir.glob("*.png"))
    
    quality_report = {
        "total": len(image_files),
        "success": 0,
        "rejected": 0,
        "rejected_files": []
    }
    
    for img_path in image_files:
        print(f"Processing: {img_path.name}")
        
        # Load image
        image = np.array(Image.open(img_path).convert("RGB"))
        
        # Generate or refine mask
        mask_path = output_dir / f"{img_path.stem}_mask.png"
        
        if refine and mask_path.exists():
            # Refine existing mask
            initial_mask = np.array(Image.open(mask_path))
            mask = refine_mask_with_sam(image, initial_mask, predictor)
        else:
            # Generate new mask
            mask = generate_sky_mask_sam(image, predictor, method=method)
        
        # Quality check
        if quality_check:
            sky_ratio = np.sum(mask > 127) / mask.size
            if sky_ratio < 0.05 or sky_ratio > 0.95:
                print(f"  Rejected: sky ratio = {sky_ratio:.2%}")
                quality_report["rejected"] += 1
                quality_report["rejected_files"].append(img_path.name)
                continue
        
        # Save mask
        Image.fromarray(mask).save(mask_path)
        quality_report["success"] += 1
        print(f"  Saved: {mask_path}")
    
    # Save quality report
    report_path = output_dir / "quality_report.json"
    with open(report_path, "w") as f:
        json.dump(quality_report, f, indent=2)
    
    print(f"\nQuality Report:")
    print(f"  Total: {quality_report['total']}")
    print(f"  Success: {quality_report['success']}")
    print(f"  Rejected: {quality_report['rejected']}")


def main():
    parser = argparse.ArgumentParser(description="SAM-based pseudo-labeling for sky segmentation")
    parser.add_argument("--input-dir", type=Path, required=True, help="Input image directory")
    parser.add_argument("--output-dir", type=Path, required=True, help="Output mask directory")
    parser.add_argument("--model-type", type=str, default="vit_h", choices=["vit_h", "vit_l", "vit_b"])
    parser.add_argument("--checkpoint", type=str, default=None, help="SAM checkpoint path")
    parser.add_argument("--method", type=str, default="auto", choices=["auto", "point", "box"])
    parser.add_argument("--refine", action="store_true", help="Refine existing masks")
    parser.add_argument("--no-quality-check", action="store_true", help="Skip quality check")
    
    args = parser.parse_args()
    
    print("Loading SAM model...")
    predictor = load_sam_model(args.model_type, args.checkpoint)
    
    print(f"Processing dataset from {args.input_dir}")
    process_dataset(
        args.input_dir,
        args.output_dir,
        predictor,
        method=args.method,
        refine=args.refine,
        quality_check=not args.no_quality_check
    )


if __name__ == "__main__":
    main()
