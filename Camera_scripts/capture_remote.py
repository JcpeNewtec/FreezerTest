import sys
from pathlib import Path

from camera_config import (
    CAMERA_DEVICE,
    FRAME_WIDTH,
    FRAME_HEIGHT,
    FRAME_FORMAT,
    FRAME_RATE,
    EXPOSURE_TIME_ABSOLUTE,
    GAIN,
)
from camera_control import CameraController


def main():
    if len(sys.argv) < 2:
        raise RuntimeError("Usage: capture_remote.py <output_path>")

    output_file = Path(sys.argv[1])

    camera = CameraController(
        device=CAMERA_DEVICE,
        width=FRAME_WIDTH,
        height=FRAME_HEIGHT,
        pixel_format=FRAME_FORMAT,
        frame_rate=FRAME_RATE,
        exposure_time_absolute=EXPOSURE_TIME_ABSOLUTE,
        gain=GAIN,
    )

    image_path, metadata_path = camera.capture_png_frame(
        output_file,
        extra_metadata={"capture_type": "remote_trigger"}
    )

    print(image_path)
    print(metadata_path)


if __name__ == "__main__":
    main()