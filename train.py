import argparse
import os
import torch

from owl_vaes.configs import Config
from owl_vaes.trainers import get_trainer_cls
from owl_vaes.utils.ddp import cleanup, setup

if __name__ == "__main__":
    # torch compile flag to convert conv with 1x1 kernel to matrix multiplication
    torch._inductor.config.conv_1x1_as_mm = True
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cuda.matmul.allow_fp16_accumulation = True
    torch.backends.cudnn.benchmark = True
    # enable below if logging (.item call in LogHelper) doesn't happen with dynamic shape tensors, otherwise recompilation adds overhead.
    # torch._dynamo.config.capture_scalar_outputs = True
    # to enable print statements in torch.compile. Doesn't play well with max-tune and fullgraph though.
    # torch._dynamo.config.reorderable_logging_functions.add(print)

    parser = argparse.ArgumentParser()

    parser.add_argument("--config_path", type=str, help="Path to config YAML file")
    parser.add_argument('--device', type=str, default=None)
    args = parser.parse_args()

    cfg = Config.from_yaml(args.config_path)

    global_rank, local_rank, world_size = setup()

    device = args.device
    if device is None:
        if torch.cuda.is_available():
            device = f"cuda:{local_rank}" if world_size > 1 else "cuda"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"

    trainer = get_trainer_cls(cfg.train.trainer_id)(
        cfg.train, cfg.wandb, cfg.model, global_rank, local_rank, world_size, device
    )

    trainer.train()
    cleanup()
