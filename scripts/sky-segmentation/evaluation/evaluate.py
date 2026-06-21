#!/usr/bin/env python3
"""
Evaluation script for segmentation models with comprehensive metrics.

Metrics:
    - mIoU (mean Intersection over Union)
    - Boundary IoU
    - HD95 (Hausdorff Distance 95th percentile)
    - Gradient error

Usage:
    python evaluate.py --model-path ./checkpoints/best_model.pth \
        --model-name deeplabv3_mobilenet --data-dir ./data

References:
    - Boundary IoU: https://github.com/bowenc0221/boundary-iou-api
    - HD95: https://github.com/deepmind/surface-distance
"""

import argparse
from pathlib import Path
import json
from typing import Dict, List, Tuple

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import transforms
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt
from skimage import measure
from tqdm import tqdm


class SegmentationEvaluator:
    """Evaluator for segmentation models."""
    
    def __init__(self, num_classes: int = 2):
        self.num_classes = num_classes
    
    def compute_iou(self, pred: np.ndarray, target: np.ndarray) -> Dict[int, float]:
        """Compute IoU per class and mean IoU."""
        ious = {}
        
        for cls in range(self.num_classes):
            pred_mask = (pred == cls)
            target_mask = (target == cls)
            
            intersection = np.logical_and(pred_mask, target_mask).sum()
            union = np.logical_or(pred_mask, target_mask).sum()
            
            if union == 0:
                ious[cls] = np.nan
            else:
                ious[cls] = intersection / union
        
        ious["mean"] = np.nanmean([v for v in ious.values()])
        return ious
    
    def compute_boundary_iou(
        self,
        pred: np.ndarray,
        target: np.ndarray,
        dilation_ratio: float = 0.02
    ) -> float:
        """
        Compute Boundary IoU.
        
        Args:
            pred: Predicted mask (H, W)
            target: Ground truth mask (H, W)
            dilation_ratio: Ratio of image diagonal for boundary dilation
        """
        h, w = pred.shape
        diagonal = np.sqrt(h ** 2 + w ** 2)
        dilation = int(round(dilation_ratio * diagonal))
        
        # Get boundaries
        pred_boundary = self._mask_to_boundary(pred, dilation)
        target_boundary = self._mask_to_boundary(target, dilation)
        
        # Compute IoU of boundaries
        intersection = np.logical_and(pred_boundary, target_boundary).sum()
        union = np.logical_or(pred_boundary, target_boundary).sum()
        
        if union == 0:
            return 1.0 if intersection == 0 else 0.0
        
        return intersection / union
    
    def _mask_to_boundary(self, mask: np.ndarray, dilation: int) -> np.ndarray:
        """Convert mask to boundary mask."""
        # Find boundaries using contour detection
        boundary = np.zeros_like(mask, dtype=bool)
        
        for cls in range(1, self.num_classes):  # Skip background
            cls_mask = (mask == cls).astype(np.uint8)
            
            if cls_mask.sum() == 0:
                continue
            
            # Erode and find boundary
            from scipy import ndimage
            eroded = ndimage.binary_erosion(cls_mask, iterations=1)
            cls_boundary = np.logical_and(cls_mask, np.logical_not(eroded))
            boundary = np.logical_or(boundary, cls_boundary)
        
        # Dilate boundary
        if dilation > 0:
            boundary = ndimage.binary_dilation(boundary, iterations=dilation)
        
        return boundary
    
    def compute_hausdorff_distance(
        self,
        pred: np.ndarray,
        target: np.ndarray,
        percentile: float = 95
    ) -> float:
        """
        Compute Hausdorff Distance (HD95).
        
        Args:
            pred: Predicted mask
            target: Ground truth mask
            percentile: Percentile for HD95 (default: 95)
        """
        # Get surface points
        pred_surface = self._get_surface_points(pred)
        target_surface = self._get_surface_points(target)
        
        if len(pred_surface) == 0 or len(target_surface) == 0:
            return 0.0 if len(pred_surface) == len(target_surface) else np.inf
        
        # Compute distances
        from scipy.spatial.distance import directed_hausdorff
        
        d1 = directed_hausdorff(pred_surface, target_surface)[0]
        d2 = directed_hausdorff(target_surface, pred_surface)[0]
        
        return max(d1, d2)
    
    def _get_surface_points(self, mask: np.ndarray) -> np.ndarray:
        """Get surface points from mask."""
        points = []
        
        for cls in range(1, self.num_classes):
            cls_mask = (mask == cls).astype(np.uint8)
            
            if cls_mask.sum() == 0:
                continue
            
            # Find contour
            contours = measure.find_contours(cls_mask, 0.5)
            
            for contour in contours:
                points.extend(contour)
        
        if len(points) == 0:
            return np.array([])
        
        return np.array(points)
    
    def compute_gradient_error(
        self,
        pred: np.ndarray,
        target: np.ndarray,
        sigma: float = 1.4
    ) -> float:
        """
        Compute gradient error (soft boundary quality).
        
        Args:
            pred: Predicted mask
            target: Ground truth mask
            sigma: Gaussian sigma for gradient computation
        """
        from scipy.ndimage import gaussian_gradient_magnitude
        
        # Compute gradients
        pred_grad = gaussian_gradient_magnitude(pred.astype(float), sigma)
        target_grad = gaussian_gradient_magnitude(target.astype(float), sigma)
        
        # Compute L1 error
        error = np.abs(pred_grad - target_grad).mean()
        
        return error
    
    def evaluate_sample(
        self,
        pred: np.ndarray,
        target: np.ndarray
    ) -> Dict[str, float]:
        """Evaluate a single sample."""
        metrics = {}
        
        # mIoU
        ious = self.compute_iou(pred, target)
        metrics["miou"] = ious["mean"]
        
        # Boundary IoU
        metrics["boundary_iou"] = self.compute_boundary_iou(pred, target)
        
        # HD95
        metrics["hd95"] = self.compute_hausdorff_distance(pred, target)
        
        # Gradient error
        metrics["gradient_error"] = self.compute_gradient_error(pred, target)
        
        return metrics
    
    def evaluate_dataset(
        self,
        predictions: List[np.ndarray],
        targets: List[np.ndarray]
    ) -> Dict[str, float]:
        """Evaluate entire dataset."""
        all_metrics = {
            "miou": [],
            "boundary_iou": [],
            "hd95": [],
            "gradient_error": []
        }
        
        for pred, target in zip(predictions, targets):
            metrics = self.evaluate_sample(pred, target)
            for key in all_metrics:
                all_metrics[key].append(metrics[key])
        
        # Aggregate
        results = {}
        for key, values in all_metrics.items():
            results[key] = np.nanmean(values)
            results[f"{key}_std"] = np.nanstd(values)
        
        return results


def evaluate_model(args):
    """Main evaluation function."""
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # Load model
    from train_segmentation import get_model, SkySegmentationDataset
    
    model = get_model(args.model_name, num_classes=args.num_classes)
    
    checkpoint = torch.load(args.model_path, map_location=device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model = model.to(device)
    model.eval()
    
    print(f"Loaded model from {args.model_path}")
    print(f"Best validation mIoU from training: {checkpoint.get('val_iou', 'N/A')}")
    
    # Data
    val_transform = transforms.Compose([
        transforms.Resize((args.input_size, args.input_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    target_transform = transforms.Compose([
        transforms.Resize((args.input_size, args.input_size), interpolation=transforms.InterpolationMode.NEAREST),
        transforms.ToTensor()
    ])
    
    dataset = SkySegmentationDataset(
        Path(args.data_dir),
        split=args.split,
        transform=val_transform,
        target_transform=target_transform
    )
    
    dataloader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers
    )
    
    # Evaluate
    evaluator = SegmentationEvaluator(num_classes=args.num_classes)
    
    all_predictions = []
    all_targets = []
    
    print(f"\nEvaluating on {len(dataset)} samples...")
    
    with torch.no_grad():
        for images, masks in tqdm(dataloader, desc="Evaluating"):
            images = images.to(device)
            
            # Forward
            outputs = model(images)
            
            if isinstance(outputs, dict):
                outputs = outputs["out"]
            
            preds = torch.argmax(outputs, dim=1)
            
            # Collect
            all_predictions.extend(preds.cpu().numpy())
            all_targets.extend(masks.squeeze(1).cpu().numpy().astype(np.uint8))
    
    # Compute metrics
    results = evaluator.evaluate_dataset(all_predictions, all_targets)
    
    # Print results
    print("\n" + "=" * 50)
    print("Evaluation Results")
    print("=" * 50)
    print(f"mIoU:            {results['miou']:.4f} ± {results['miou_std']:.4f}")
    print(f"Boundary IoU:    {results['boundary_iou']:.4f} ± {results['boundary_iou_std']:.4f}")
    print(f"HD95:            {results['hd95']:.4f} ± {results['hd95_std']:.4f}")
    print(f"Gradient Error:  {results['gradient_error']:.4f} ± {results['gradient_error_std']:.4f}")
    print("=" * 50)
    
    # Save results
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {output_path}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Evaluate segmentation model")
    
    parser.add_argument("--model-path", type=str, required=True, help="Path to model checkpoint")
    parser.add_argument("--model-name", type=str, required=True,
                        choices=["deeplabv3_mobilenet", "fast_scnn", "bisenetv2", "segformer_b0"])
    parser.add_argument("--data-dir", type=str, required=True, help="Data directory")
    parser.add_argument("--split", type=str, default="test", choices=["train", "val", "test"])
    parser.add_argument("--num-classes", type=int, default=2)
    parser.add_argument("--input-size", type=int, default=512)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--output-path", type=str, default="./results.json")
    
    args = parser.parse_args()
    
    evaluate_model(args)


if __name__ == "__main__":
    main()
