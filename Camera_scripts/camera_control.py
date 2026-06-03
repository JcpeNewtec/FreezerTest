# /root/scripts/camera_control.py

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path


class CameraError(Exception):
    pass


class CameraController:
    def __init__(
        self,
        device: str,
        width: int,
        height: int,
        pixel_format: str,
        frame_rate: int | None = None,
        exposure_time_absolute: int | None = None,
        gain: int | None = None,
    ):
        self.device = device
        self.width = width
        self.height = height
        self.pixel_format = pixel_format
        self.frame_rate = frame_rate
        self.exposure_time_absolute = exposure_time_absolute
        self.gain = gain

    def _run(self, cmd: list[str]) -> subprocess.CompletedProcess:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise CameraError(
                f"Command failed:\n{' '.join(cmd)}\n\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            )
        return result

    def set_frame_rate(self, frame_rate: int):
        self._run([
            "v4l2-ctl",
            "-d", self.device,
            f"--set-parm={frame_rate}"
        ])

    def set_exposure(self, exposure_time_absolute: int):
        self._run([
            "v4l2-ctl",
            "-d", self.device,
            "-c", f"exposure_time_absolute={exposure_time_absolute}"
        ])

    def set_gain(self, gain: int):
        self._run([
            "v4l2-ctl",
            "-d", self.device,
            "-c", f"gain={gain}"
        ])

    def get_control_value(self, control_name: str) -> str:
        result = self._run([
            "v4l2-ctl",
            "-d", self.device,
            "-C", control_name
        ])
        return result.stdout.strip()

    def get_stream_parameters(self) -> str:
        result = self._run([
            "v4l2-ctl",
            "-d", self.device,
            "--get-parm"
        ])
        return result.stdout.strip()

    def apply_camera_settings(self):
        if self.frame_rate is not None:
            self.set_frame_rate(self.frame_rate)

        if self.exposure_time_absolute is not None:
            self.set_exposure(self.exposure_time_absolute)

        if self.gain is not None:
            self.set_gain(self.gain)

        time.sleep(0.1)

    def capture_png_frame(self, output_path: str | Path, extra_metadata: dict | None = None) -> tuple[Path, Path]:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_path.suffix.lower() != ".png":
            output_path = output_path.with_suffix(".png")

        # Apply settings before capture
        self.apply_camera_settings()

        before_stream_parameters = self.get_stream_parameters()
        before_exposure = self.get_control_value("exposure_time_absolute")
        before_gain = self.get_control_value("gain")

        caps = (
            f"video/x-raw,"
            f"format={self.pixel_format},"
            f"width={self.width},"
            f"height={self.height},"
            f"framerate={self.frame_rate}/1"
        )

        cmd = [
            "gst-launch-1.0",
            "-e",
            "v4l2src", f"device={self.device}", "num-buffers=1",
            "!",
            caps,
            "!",
            "pngenc",
            "!",
            "filesink", f"location={str(output_path)}"
        ]

        capture_time = datetime.now().isoformat(timespec="seconds")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise CameraError(
                f"Capture failed.\n"
                f"Command: {' '.join(cmd)}\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            )

        if not output_path.exists():
            raise CameraError(f"Capture failed: file was not created: {output_path}")

        actual_size = output_path.stat().st_size
        if actual_size <= 0:
            raise CameraError(f"Capture failed: file is empty: {output_path}")

        after_stream_parameters = self.get_stream_parameters()
        after_exposure = self.get_control_value("exposure_time_absolute")
        after_gain = self.get_control_value("gain")

        metadata = {
            "timestamp": capture_time,
            "image_file": output_path.name,
            "image_path": str(output_path),
            "metadata_file": output_path.with_suffix(".json").name,
            "camera_device": self.device,
            "width": self.width,
            "height": self.height,
            "pixel_format": self.pixel_format,
            "image_encoding": "PNG",
            "actual_size_bytes": actual_size,
            "capture_status": "success",
            "requested_frame_rate": self.frame_rate,
            "requested_exposure_time_absolute": self.exposure_time_absolute,
            "requested_gain": self.gain,
            "stream_parameters_before_capture": before_stream_parameters,
            "stream_parameters_after_capture": after_stream_parameters,
            "applied_exposure_before_capture": before_exposure,
            "applied_exposure_after_capture": after_exposure,
            "applied_gain_before_capture": before_gain,
            "applied_gain_after_capture": after_gain,
            "gst_command": cmd,
        }

        if extra_metadata:
            metadata.update(extra_metadata)

        metadata_path = output_path.with_suffix(".json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4)

        return output_path, metadata_path