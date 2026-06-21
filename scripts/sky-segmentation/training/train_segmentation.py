#!/usr/bin/env python3
"""
Training script for lightweight segmentation models.

Supported models:
    - DeepLabV3+MobileNetV3
    - Fast-SCNN
    - BiSeNetV2
    - DDRNet
    - PIDNet
    - SegFormer-B0

Usage:
    python train_segmentation.py --model deeplabv3_mobilenet \
        --data-dir ./data --output-dir ./checkpoints

References:
    - https://github.com/VainF/DeepLabV3Plus-Pytorch
    - https://github.com/Tramac/Fast-SCNN-pytorch
    - https://github.com/CoinCheung/BiSeNet
    - https://github.com/ydhongHIT/DDRNet
    - https://github.com/XuJiacong/PIDNet
    - https://github.com/NVlabs/SegFormer
"""

import argparse
import os
from pathlib import Path
import json
import time
from typing import Dict, Optional

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
import numpy as np
from PIL import Image
from tqdm import tqdm


class SkySegmentationDataset(Dataset):
    """Dataset for sky segmentation with unified format."""
    
    def __init__(
        self,
        data_dir: Path,
        split: str = "train",
        transform=None,
        target_transform=None
    ):
        self.data_dir = data_dir
        self.split = split
        self.transform = transform
        self.target_transform = target_transform
        
        # Load splits.json
        with open(data_dir / "splits.json") as f:
            splits = json.load(f)
        
        self.samples = splits.get(split, [])
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        sample = self.samples[idx]
        
        # Load image and mask
        image = Image.open(self.data_dir / sample["image"]).convert("RGB")
        mask = Image.open(self.data_dir / sample["mask"]).convert("L")
        
        if self.transform:
            image = self.transform(image)
        if self.target_transform:
            mask = self.target_transform(mask)
        
        return image, mask


def get_model(model_name: str, num_classes: int = 2, pretrained: bool = True):
    """Load segmentation model."""
    
    if model_name == "deeplabv3_mobilenet":
        import torchvision.models.segmentation as segmentation
        model = segmentation.deeplabv3_mobilenet_v3_large(
            weights="DEFAULT" if pretrained else None,
            num_classes=num_classes
        )
    
    elif model_name == "fast_scnn":
        # Fast-SCNN implementation
        try:
            from model.fast_scnn import FastSCNN
            model = FastSCNN(num_classes=num_classes)
        except ImportError:
            raise ImportError("Fast-SCNN model not found. Please implement or install.")
    
    elif model_name == "bisenetv2":
        try:
            from model.bisenetv2 import BiSeNetV2
            model = BiSeNetV2(num_classes=num_classes)
        except ImportError:
            raise ImportError("BiSeNetV2 model not found. Please implement or install.")
    
    elif model_name == "segformer_b0":
        try:
            from transformers import SegformerForSemanticSegmentation
            model = SegformerForSemanticSegmentation.from_pretrained(
                "nvidia/segformer-b0-finetuned-ade-512-512" if pretrained else None,
                num_labels=num_classes,
                ignore_mismatched_sizes=True
            )
        except ImportError:
            raise ImportError("transformers not installed. Run: pip install transformers")
    
    else:
        raise ValueError(f"Unknown model: {model_name}")
    
    return model


def get_optimizer(model, optimizer_name: str, lr: float, weight_decay: float):
    """Get optimizer."""
    if optimizer_name == "sgd":
        return optim.SGD(
            model.parameters(),
            lr=lr,
            momentum=0.9,
            weight_decay=weight_decay
        )
    elif optimizer_name == "adamw":
        return optim.AdamW(
            model.parameters(),
            lr=lr,
            weight_decay=weight_decay
        )
    else:
        raise ValueError(f"Unknown optimizer: {optimizer_name}")


def get_scheduler(optimizer, scheduler_name: str, epochs: int, warmup_epochs: int = 0):
    """Get learning rate scheduler."""
    if scheduler_name == "poly":
        lambda_fn = lambda epoch: (1 - epoch / epochs) ** 0.9
        return optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=lambda_fn)
    
    elif scheduler_name == "cosine":
        return optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    
    elif scheduler_name == "cosine_warmup":
        def lr_lambda(epoch):
            if epoch < warmup_epochs:
                return (epoch + 1) / warmup_epochs
            else:
                progress = (epoch - warmup_epochs) / (epochs - warmup_epochs)
                return 0.5 * (1 + np.cos(np.pi * progress))
        return optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)
    
    else:
        return None


def compute_iou(pred: torch.Tensor, target: torch.Tensor, num_classes: int = 2) -> float:
    """Compute mean IoU."""
    ious = []
    pred = pred.view(-1)
    target = target.view(-1)
    
    for cls in range(num_classes):
        pred_inds = pred == cls
        target_inds = target == cls
        intersection = (pred_inds[target_inds]).sum().float()
        union = pred_inds.sum() + target_inds.sum() - intersection
        
        if union == 0:
            ious.append(float('nan'))
        else:
            ious.append((intersection / union).item())
    
    return np.nanmean(ious)


def train_epoch(model, dataloader, criterion, optimizer, device):
    """Train one epoch."""
    model.train()
    total_loss = 0
    total_iou = 0
    
    pbar = tqdm(dataloader, desc="Training")
    for images, masks in pbar:
        images = images.to(device)
        masks = masks.to(device).long()
        
        optimizer.zero_grad()
        
        # Forward
        outputs = model(images)
        
        # Handle different output formats
        if isinstance(outputs, dict):
            outputs = outputs["out"]
        
        loss = criterion(outputs, masks)
        
        # Backward
        loss.backward()
        optimizer.step()
        
        # Metrics
        preds = torch.argmax(outputs, dim=1)
        iou = compute_iou(preds, masks)
        
        total_loss += loss.item()
        total_iou += iou
        
        pbar.set_postfix({"loss": loss.item(), "mIoU": iou})
    
    return total_loss / len(dataloader), total_iou / len(dataloader)


def validate(model, dataloader, criterion, device):
    """Validate."""
    model.eval()
    total_loss = 0
    total_iou = 0
    
    with torch.no_grad():
        for images, masks in tqdm(dataloader, desc="Validation"):
            images = images.to(device)
            masks = masks.to(device).long()
            
            outputs = model(images)
            
            if isinstance(outputs, dict):
                outputs = outputs["out"]
            
            loss = criterion(outputs, masks)
            preds = torch.argmax(outputs, dim=1)
            iou = compute_iou(preds, masks)
            
            total_loss += loss.item()
            total_iou += iou
    
    return total_loss / len(dataloader), total_iou / len(dataloader)


def train(args):
    """Main training function."""
    
    # Setup
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save config
    with open(output_dir / "config.json", "w") as f:
        json.dump(vars(args), f, indent=2)
    
    # Data transforms
    train_transform = transforms.Compose([
        transforms.Resize((args.input_size, args.input_size)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(10),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    val_transform = transforms.Compose([
        transforms.Resize((args.input_size, args.input_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    target_transform = transforms.Compose([
        transforms.Resize((args.input_size, args.input_size), interpolation=transforms.InterpolationMode.NEAREST),
        transforms.ToTensor()
    ])
    
    # Datasets
    train_dataset = SkySegmentationDataset(
        Path(args.data_dir),
        split="train",
        transform=train_transform,
        target_transform=target_transform
    )
    
    val_dataset = SkySegmentationDataset(
        Path(args.data_dir),
        split="val",
        transform=val_transform,
        target_transform=target_transform
    )
    
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=True
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=True
    )
    
    print(f"Train samples: {len(train_dataset)}, Val samples: {len(val_dataset)}")
    
    # Model
    model = get_model(args.model, num_classes=args.num_classes, pretrained=args.pretrained)
    model = model.to(device)
    
    # Count parameters
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Total params: {total_params:,}, Trainable: {trainable_params:,}")
    
    # Loss
    if args.loss == "ce":
        criterion = nn.CrossEntropyLoss()
    elif args.loss == "ce_dice":
        # Combined CE + Dice loss
        from loss import CEDiceLoss
        criterion = CEDiceLoss()
    else:
        raise ValueError(f"Unknown loss: {args.loss}")
    
    # Optimizer
    optimizer = get_optimizer(model, args.optimizer, args.lr, args.weight_decay)
    
    # Scheduler
    scheduler = get_scheduler(optimizer, args.scheduler, args.epochs, args.warmup_epochs)
    
    # Training loop
    best_iou = 0
    history = {"train_loss": [], "train_iou": [], "val_loss": [], "val_iou": []}
    
    for epoch in range(args.epochs):
        print(f"\nEpoch {epoch + 1}/{args.epochs}")
        print("-" * 50)
        
        # Train
        train_loss, train_iou = train_epoch(model, train_loader, criterion, optimizer, device)
        print(f"Train Loss: {train_loss:.4f}, Train mIoU: {train_iou:.4f}")
        
        # Validate
        val_loss, val_iou = validate(model, val_loader, criterion, device)
        print(f"Val Loss: {val_loss:.4f}, Val mIoU: {val_iou:.4f}")
        
        # Update scheduler
        if scheduler:
            scheduler.step()
            print(f"LR: {optimizer.param_groups[0]['lr']:.6f}")
        
        # Save history
        history["train_loss"].append(train_loss)
        history["train_iou"].append(train_iou)
        history["val_loss"].append(val_loss)
        history["val_iou"].append(val_iou)
        
        # Save best model
        if val_iou > best_iou:
            best_iou = val_iou
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_iou": val_iou,
                "args": vars(args)
            }, output_dir / "best_model.pth")
            print(f"Saved best model (mIoU: {val_iou:.4f})")
        
        # Save checkpoint
        if (epoch + 1) % args.save_interval == 0:
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_iou": val_iou,
                "args": vars(args)
            }, output_dir / f"checkpoint_epoch_{epoch + 1}.pth")
    
    # Save final history
    with open(output_dir / "history.json", "w") as f:
        json.dump(history, f, indent=2)
    
    print(f"\nTraining complete! Best mIoU: {best_iou:.4f}")
    print(f"Results saved to: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Train segmentation model")
    
    # Data
    parser.add_argument("--data-dir", type=str, required=True, help="Data directory with splits.json")
    parser.add_argument("--input-size", type=int, default=512, help="Input image size")
    
    # Model
    parser.add_argument("--model", type=str, required=True,
                        choices=["deeplabv3_mobilenet", "fast_scnn", "bisenetv2", "segformer_b0"],
                        help="Model architecture")
    parser.add_argument("--num-classes", type=int, default=2, help="Number of classes")
    parser.add_argument("--pretrained", action="store_true", help="Use pretrained weights")
    
    # Training
    parser.add_argument("--epochs", type=int, default=100, help="Number of epochs")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size")
    parser.add_argument("--lr", type=float, default=0.01, help="Learning rate")
    parser.add_argument("--weight-decay", type=float, default=1e-4, help="Weight decay")
    parser.add_argument("--optimizer", type=str, default="sgd", choices=["sgd", "adamw"])
    parser.add_argument("--scheduler", type=str, default="poly", choices=["poly", "cosine", "cosine_warmup"])
    parser.add_argument("--warmup-epochs", type=int, default=5, help="Warmup epochs for cosine_warmup")
    parser.add_argument("--loss", type=str, default="ce", choices=["ce", "ce_dice"])
    
    # System
    parser.add_argument("--num-workers", type=int, default=4, help="DataLoader workers")
    parser.add_argument("--output-dir", type=str, default="./checkpoints", help="Output directory")
    parser.add_argument("--save-interval", type=int, default=10, help="Save checkpoint every N epochs")
    
    args = parser.parse_args()
    
    train(args)


if __name__ == "__main__":
    main()
