#!/usr/bin/env python3
"""
Mobile optimization: quantization and profiling.

Features:
    - Post-training INT8 quantization
    - Dynamic quantization
    - Model profiling (params, FLOPs, latency)
    - ONNX export for mobile deployment

Usage:
    python quantize_and_profile.py --model-path ./checkpoints/best_model.pth \
        --model-name deeplabv3_mobilenet --output-dir ./optimized

References:
    - PyTorch Quantization: https://pytorch.org/docs/stable/quantization.html
    - ONNX Runtime: https://onnxruntime.ai/
"""

import argparse
from pathlib import Path
import json
import time
from typing import Dict, Tuple

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import transforms
import numpy as np


def count_parameters(model: nn.Module) -> Tuple[int, int]:
    """Count total and trainable parameters."""
    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    return total, trainable


def count_flops(model: nn.Module, input_size: Tuple[int, int, int, int]) -> float:
    """
    Estimate FLOPs using thop or ptflops.
    
    Args:
        model: PyTorch model
        input_size: (batch, channels, height, width)
    
    Returns:
        FLOPs in GFLOPs
    """
    try:
        from thop import profile
        dummy_input = torch.randn(input_size)
        flops, params = profile(model, inputs=(dummy_input,), verbose=False)
        return flops / 1e9  # Convert to GFLOPs
    except ImportError:
        print("Warning: thop not installed. Install with: pip install thop")
        return -1


def measure_latency(
    model: nn.Module,
    input_size: Tuple[int, int, int, int],
    device: torch.device,
    num_runs: int = 100,
    warmup: int = 10
) -> Dict[str, float]:
    """
    Measure inference latency.
    
    Args:
        model: PyTorch model
        input_size: (batch, channels, height, width)
        device: Device to run on
        num_runs: Number of runs for averaging
        warmup: Number of warmup runs
    
    Returns:
        Dict with latency statistics (ms)
    """
    model.eval()
    dummy_input = torch.randn(input_size).to(device)
    
    # Warmup
    with torch.no_grad():
        for _ in range(warmup):
            _ = model(dummy_input)
    
    # Synchronize
    if device.type == "cuda":
        torch.cuda.synchronize()
    
    # Measure
    latencies = []
    with torch.no_grad():
        for _ in range(num_runs):
            start = time.time()
            _ = model(dummy_input)
            
            if device.type == "cuda":
                torch.cuda.synchronize()
            
            end = time.time()
            latencies.append((end - start) * 1000)  # Convert to ms
    
    return {
        "mean": np.mean(latencies),
        "std": np.std(latencies),
        "min": np.min(latencies),
        "max": np.max(latencies),
        "p50": np.percentile(latencies, 50),
        "p95": np.percentile(latencies, 95),
        "p99": np.percentile(latencies, 99)
    }


def export_onnx(
    model: nn.Module,
    output_path: Path,
    input_size: Tuple[int, int, int, int] = (1, 3, 512, 512)
):
    """Export model to ONNX format."""
    model.eval()
    dummy_input = torch.randn(input_size)
    
    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        export_params=True,
        opset_version=11,
        do_constant_folding=True,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={
            "input": {0: "batch_size"},
            "output": {0: "batch_size"}
        }
    )
    
    print(f"Exported ONNX model to: {output_path}")


def apply_static_quantization(
    model: nn.Module,
    calibration_loader: DataLoader,
    device: torch.device
) -> nn.Module:
    """
    Apply post-training static INT8 quantization.
    
    Args:
        model: FP32 model
        calibration_loader: DataLoader for calibration
        device: Device
    
    Returns:
        Quantized model
    """
    model.eval()
    model.cpu()  # Quantization only works on CPU
    
    # Prepare model for quantization
    model.qconfig = torch.quantization.get_default_qconfig("fbgemm")
    torch.quantization.prepare(model, inplace=True)
    
    # Calibrate
    print("Calibrating...")
    with torch.no_grad():
        for images, _ in calibration_loader:
            images = images.cpu()
            _ = model(images)
    
    # Convert
    torch.quantization.convert(model, inplace=True)
    
    return model


def apply_dynamic_quantization(model: nn.Module) -> nn.Module:
    """
    Apply dynamic quantization (weights only).
    
    Args:
        model: FP32 model
    
    Returns:
        Quantized model
    """
    model.eval()
    model.cpu()
    
    quantized_model = torch.quantization.quantize_dynamic(
        model,
        {nn.Linear, nn.Conv2d},
        dtype=torch.qint8
    )
    
    return quantized_model


def profile_model(args):
    """Main profiling and optimization function."""
    
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    print(f"Using device: {device}")
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load model
    import sys
    sys.path.append(str(Path(__file__).parent.parent / "training"))
    from train_segmentation import get_model
    
    model = get_model(args.model_name, num_classes=args.num_classes)
    
    if args.model_path:
        checkpoint = torch.load(args.model_path, map_location="cpu")
        model.load_state_dict(checkpoint["model_state_dict"])
        print(f"Loaded model from {args.model_path}")
    
    model = model.to(device)
    model.eval()
    
    # Profile baseline model
    print("\n" + "=" * 50)
    print("Baseline Model Profiling")
    print("=" * 50)
    
    input_size = (1, 3, args.input_size, args.input_size)
    
    # Parameters
    total_params, trainable_params = count_parameters(model)
    print(f"Total parameters:      {total_params:,}")
    print(f"Trainable parameters:  {trainable_params:,}")
    print(f"Model size (FP32):     {total_params * 4 / 1024 / 1024:.2f} MB")
    
    # FLOPs
    gflops = count_flops(model, input_size)
    if gflops > 0:
        print(f"FLOPs:                 {gflops:.2f} GFLOPs")
    
    # Latency
    latency = measure_latency(model, input_size, device, args.num_runs, args.warmup)
    print(f"\nLatency (FP32):")
    print(f"  Mean:  {latency['mean']:.2f} ms")
    print(f"  Std:   {latency['std']:.2f} ms")
    print(f"  P95:   {latency['p95']:.2f} ms")
    
    # Save baseline results
    baseline_results = {
        "model_name": args.model_name,
        "input_size": args.input_size,
        "total_params": total_params,
        "trainable_params": trainable_params,
        "model_size_mb": total_params * 4 / 1024 / 1024,
        "gflops": gflops,
        "latency_ms": latency
    }
    
    with open(output_dir / "baseline_profile.json", "w") as f:
        json.dump(baseline_results, f, indent=2)
    
    # Export ONNX
    if args.export_onnx:
        export_onnx(model, output_dir / "model.onnx", input_size)
    
    # Quantization
    if args.quantize:
        print("\n" + "=" * 50)
        print("Quantization")
        print("=" * 50)
        
        if args.quantization_type == "static":
            # Prepare calibration data
            from train_segmentation import SkySegmentationDataset
            
            cal_transform = transforms.Compose([
                transforms.Resize((args.input_size, args.input_size)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ])
            
            cal_dataset = SkySegmentationDataset(
                Path(args.data_dir),
                split="val",
                transform=cal_transform
            )
            
            cal_loader = DataLoader(
                cal_dataset,
                batch_size=args.batch_size,
                shuffle=False,
                num_workers=0  # Quantization requires num_workers=0
            )
            
            quantized_model = apply_static_quantization(model, cal_loader, device)
            
        else:  # dynamic
            quantized_model = apply_dynamic_quantization(model)
        
        # Profile quantized model
        quantized_model.eval()
        quantized_model.cpu()
        
        # Save quantized model
        torch.save(quantized_model.state_dict(), output_dir / "model_quantized.pth")
        
        # Measure quantized latency
        quantized_latency = measure_latency(
            quantized_model,
            input_size,
            torch.device("cpu"),
            args.num_runs,
            args.warmup
        )
        
        print(f"\nLatency (INT8):")
        print(f"  Mean:  {quantized_latency['mean']:.2f} ms")
        print(f"  Speedup: {latency['mean'] / quantized_latency['mean']:.2f}x")
        
        # Save quantized results
        quantized_results = {
            "quantization_type": args.quantization_type,
            "latency_ms": quantized_latency,
            "speedup": latency["mean"] / quantized_latency["mean"]
        }
        
        with open(output_dir / "quantized_profile.json", "w") as f:
            json.dump(quantized_results, f, indent=2)
    
    print("\n" + "=" * 50)
    print(f"Optimization complete! Results saved to: {output_dir}")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description="Quantize and profile segmentation model")
    
    parser.add_argument("--model-path", type=str, default=None, help="Path to model checkpoint")
    parser.add_argument("--model-name", type=str, required=True,
                        choices=["deeplabv3_mobilenet", "fast_scnn", "bisenetv2", "segformer_b0"])
    parser.add_argument("--data-dir", type=str, default="./data", help="Data directory for calibration")
    parser.add_argument("--num-classes", type=int, default=2)
    parser.add_argument("--input-size", type=int, default=512)
    parser.add_argument("--batch-size", type=int, default=8)
    
    # Quantization
    parser.add_argument("--quantize", action="store_true", help="Apply quantization")
    parser.add_argument("--quantization-type", type=str, default="static",
                        choices=["static", "dynamic"])
    
    # Profiling
    parser.add_argument("--num-runs", type=int, default=100, help="Number of runs for latency")
    parser.add_argument("--warmup", type=int, default=10, help="Number of warmup runs")
    parser.add_argument("--cpu", action="store_true", help="Force CPU for profiling")
    
    # Export
    parser.add_argument("--export-onnx", action="store_true", help="Export to ONNX")
    parser.add_argument("--output-dir", type=str, default="./optimized", help="Output directory")
    
    args = parser.parse_args()
    
    profile_model(args)


if __name__ == "__main__":
    main()
