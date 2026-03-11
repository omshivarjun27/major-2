"""
Depth Calibration Tool for Spatial Perception Pipeline
=======================================================

Calibrates depth estimation by correlating pipeline output with ground-truth
measurements. Supports both manual and marker-based calibration.

Usage:
    python calibrate_depth.py                    # Interactive calibration
    python calibrate_depth.py --mode marker      # ArUco marker calibration
    python calibrate_depth.py --load calib.json  # Load existing calibration
    python calibrate_depth.py --export calib.json  # Export calibration

Author: Ally Vision Team
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("depth-calibration")


# =============================================================================
# CALIBRATION DATA STRUCTURES
# =============================================================================

@dataclass
class CalibrationPoint:
    """A single calibration point"""
    id: int
    measured_distance_m: float  # Ground truth distance
    estimated_distance_m: float  # Pipeline estimated distance
    pixel_y: int  # Y position in frame
    pixel_x: int  # X position in frame
    frame_height: int
    frame_width: int
    timestamp: float = 0.0
    notes: str = ""

    @property
    def relative_y(self) -> float:
        """Y position as ratio (0=top, 1=bottom)"""
        return self.pixel_y / self.frame_height

    @property
    def error_m(self) -> float:
        """Error in meters"""
        return abs(self.estimated_distance_m - self.measured_distance_m)

    @property
    def error_percent(self) -> float:
        """Error as percentage"""
        if self.measured_distance_m == 0:
            return 0.0
        return 100 * self.error_m / self.measured_distance_m


@dataclass
class CalibrationResult:
    """Calibration result with correction parameters"""
    # Linear regression parameters: corrected = slope * estimated + intercept
    slope: float = 1.0
    intercept: float = 0.0

    # Y-position based correction: distance = y_scale * y_position + y_offset
    y_scale: float = 3.0
    y_offset: float = 0.3

    # Statistics
    num_points: int = 0
    mean_error_m: float = 0.0
    max_error_m: float = 0.0
    rmse_m: float = 0.0
    r_squared: float = 0.0

    # Metadata
    calibration_date: str = ""
    depth_estimator: str = ""
    camera_model: str = ""
    notes: str = ""

    # Raw calibration points
    calibration_points: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def apply_correction(self, estimated: float) -> float:
        """Apply calibration correction to estimated distance"""
        return self.slope * estimated + self.intercept

    def estimate_from_y(self, y_ratio: float) -> float:
        """Estimate distance from Y position (0=top, 1=bottom)"""
        # Objects at bottom of frame are closer
        distance = self.y_scale * (1 - y_ratio) + self.y_offset
        return max(0.3, distance)  # Minimum 0.3m


# =============================================================================
# CALIBRATION PROCESSOR
# =============================================================================

class DepthCalibrator:
    """
    Depth calibration processor.

    Performs calibration using either:
    1. Manual point collection - user clicks objects and enters real distances
    2. ArUco marker detection - uses known marker size for distance calculation
    """

    def __init__(self, depth_estimator_type: str = "simple"):
        self.depth_estimator_type = depth_estimator_type
        self.calibration_points: List[CalibrationPoint] = []
        self.result: Optional[CalibrationResult] = None

        # For marker-based calibration
        self.aruco_dict = None
        self.aruco_params = None
        self.marker_size_m = 0.1  # 10cm markers by default

        self._init_aruco()

    def _init_aruco(self):
        """Initialize ArUco detector"""
        try:
            self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
            self.aruco_params = cv2.aruco.DetectorParameters()
        except Exception as e:
            logger.warning(f"ArUco not available: {e}")

    def add_calibration_point(
        self,
        measured_distance_m: float,
        estimated_distance_m: float,
        pixel_x: int,
        pixel_y: int,
        frame_width: int,
        frame_height: int,
        notes: str = ""
    ):
        """Add a calibration point"""
        point = CalibrationPoint(
            id=len(self.calibration_points) + 1,
            measured_distance_m=measured_distance_m,
            estimated_distance_m=estimated_distance_m,
            pixel_x=pixel_x,
            pixel_y=pixel_y,
            frame_width=frame_width,
            frame_height=frame_height,
            timestamp=time.time(),
            notes=notes
        )
        self.calibration_points.append(point)
        logger.info(f"Added point {point.id}: measured={measured_distance_m:.2f}m, "
                    f"estimated={estimated_distance_m:.2f}m, error={point.error_percent:.1f}%")

    def detect_aruco_markers(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Detect ArUco markers in frame"""
        if self.aruco_dict is None:
            return []

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        try:
            detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
            corners, ids, rejected = detector.detectMarkers(gray)
        except:
            corners, ids, rejected = cv2.aruco.detectMarkers(
                gray, self.aruco_dict, parameters=self.aruco_params
            )

        markers = []
        if ids is not None:
            for i, marker_id in enumerate(ids.flatten()):
                corner = corners[i][0]
                center_x = int(np.mean(corner[:, 0]))
                center_y = int(np.mean(corner[:, 1]))

                # Calculate marker size in pixels
                width = np.linalg.norm(corner[0] - corner[1])
                height = np.linalg.norm(corner[1] - corner[2])
                size_px = (width + height) / 2

                # Estimate distance from marker size
                # Using simple pinhole model: distance = (marker_size * focal_length) / size_in_pixels
                # Assuming focal length ~= frame width (approximation)
                focal_length = frame.shape[1]
                distance_m = (self.marker_size_m * focal_length) / size_px

                markers.append({
                    "id": int(marker_id),
                    "center": (center_x, center_y),
                    "corners": corner.tolist(),
                    "size_px": size_px,
                    "estimated_distance_m": distance_m
                })

        return markers

    def compute_calibration(self) -> CalibrationResult:
        """Compute calibration parameters from collected points"""
        if len(self.calibration_points) < 2:
            logger.warning("Need at least 2 calibration points")
            self.result = CalibrationResult(
                calibration_date=datetime.now().isoformat(),
                depth_estimator=self.depth_estimator_type
            )
            return self.result

        # Extract data
        measured = np.array([p.measured_distance_m for p in self.calibration_points])
        estimated = np.array([p.estimated_distance_m for p in self.calibration_points])
        y_ratios = np.array([p.relative_y for p in self.calibration_points])

        # Linear regression for correction
        if len(set(estimated)) > 1:  # Avoid division by zero
            slope, intercept = np.polyfit(estimated, measured, 1)
        else:
            slope, intercept = 1.0, 0.0

        # Corrected estimates
        corrected = slope * estimated + intercept

        # Y-position based model
        # Fit: distance = y_scale * (1 - y_ratio) + y_offset
        if len(set(y_ratios)) > 1:
            # Transform: distance = y_scale - y_scale * y_ratio + y_offset
            #          = (y_scale + y_offset) - y_scale * y_ratio
            # Let A = y_scale, B = y_offset
            # distance = (A + B) - A * y_ratio = B + A * (1 - y_ratio)
            A = np.column_stack([1 - y_ratios, np.ones_like(y_ratios)])
            coeffs, residuals, rank, s = np.linalg.lstsq(A, measured, rcond=None)
            y_scale, y_offset = coeffs[0], coeffs[1]
        else:
            y_scale, y_offset = 3.0, 0.3

        # Calculate statistics
        errors = np.abs(corrected - measured)
        mean_error = np.mean(errors)
        max_error = np.max(errors)
        rmse = np.sqrt(np.mean(errors**2))

        # R-squared
        ss_res = np.sum((measured - corrected)**2)
        ss_tot = np.sum((measured - np.mean(measured))**2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        self.result = CalibrationResult(
            slope=float(slope),
            intercept=float(intercept),
            y_scale=float(y_scale),
            y_offset=float(y_offset),
            num_points=len(self.calibration_points),
            mean_error_m=float(mean_error),
            max_error_m=float(max_error),
            rmse_m=float(rmse),
            r_squared=float(r_squared),
            calibration_date=datetime.now().isoformat(),
            depth_estimator=self.depth_estimator_type,
            calibration_points=[asdict(p) for p in self.calibration_points]
        )

        logger.info(f"Calibration complete: slope={slope:.3f}, intercept={intercept:.3f}")
        logger.info(f"Y-model: distance = {y_scale:.2f} * (1 - y) + {y_offset:.2f}")
        logger.info(f"Mean error: {mean_error:.3f}m, R²: {r_squared:.3f}")

        return self.result

    def save_calibration(self, filepath: str):
        """Save calibration to file"""
        if self.result is None:
            self.compute_calibration()

        with open(filepath, "w") as f:
            json.dump(self.result.to_dict(), f, indent=2)

        logger.info(f"Calibration saved to: {filepath}")

    def load_calibration(self, filepath: str) -> CalibrationResult:
        """Load calibration from file"""
        with open(filepath, "r") as f:
            data = json.load(f)

        # Reconstruct calibration points
        points = data.pop("calibration_points", [])
        self.result = CalibrationResult(**data)
        self.result.calibration_points = points

        # Reconstruct calibration points list
        self.calibration_points = [
            CalibrationPoint(**p) for p in points
        ]

        logger.info(f"Loaded calibration with {self.result.num_points} points")
        return self.result


# =============================================================================
# INTERACTIVE CALIBRATION UI
# =============================================================================

class InteractiveCalibrationUI:
    """Interactive UI for manual depth calibration"""

    def __init__(
        self,
        camera_index: int = 0,
        depth_estimator: str = "simple",
        marker_mode: bool = False,
        marker_size_m: float = 0.1
    ):
        self.camera_index = camera_index
        self.depth_estimator = depth_estimator
        self.marker_mode = marker_mode

        self.calibrator = DepthCalibrator(depth_estimator)
        self.calibrator.marker_size_m = marker_size_m

        # UI state
        self.current_frame: Optional[np.ndarray] = None
        self.click_point: Optional[Tuple[int, int]] = None
        self.selected_marker: Optional[Dict[str, Any]] = None
        self.is_running = True

        # Window
        self.window_name = "Depth Calibration"

    def _mouse_callback(self, event, x, y, flags, param):
        """Handle mouse events"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.click_point = (x, y)
            logger.info(f"Selected point: ({x}, {y})")

    def _draw_ui(self, frame: np.ndarray, markers: List[Dict]) -> np.ndarray:
        """Draw calibration UI overlay"""
        overlay = frame.copy()
        height, width = frame.shape[:2]

        # Draw markers if in marker mode
        if self.marker_mode and markers:
            for marker in markers:
                corners = np.array(marker["corners"], dtype=np.int32)
                cv2.polylines(overlay, [corners], True, (0, 255, 0), 2)

                cx, cy = marker["center"]
                cv2.circle(overlay, (cx, cy), 5, (0, 255, 0), -1)

                # Show marker ID and distance
                text = f"ID:{marker['id']} d={marker['estimated_distance_m']:.2f}m"
                cv2.putText(overlay, text, (cx - 50, cy - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Draw click point
        if self.click_point:
            cv2.circle(overlay, self.click_point, 10, (0, 0, 255), 2)
            cv2.line(overlay, (self.click_point[0] - 15, self.click_point[1]),
                     (self.click_point[0] + 15, self.click_point[1]), (0, 0, 255), 2)
            cv2.line(overlay, (self.click_point[0], self.click_point[1] - 15),
                     (self.click_point[0], self.click_point[1] + 15), (0, 0, 255), 2)

        # Draw Y-position grid
        for i in range(1, 5):
            y_pos = int(height * i / 5)
            cv2.line(overlay, (0, y_pos), (width, y_pos), (100, 100, 100), 1)

            # Estimated distance from Y
            y_ratio = y_pos / height
            if self.calibrator.result:
                est_dist = self.calibrator.result.estimate_from_y(y_ratio)
            else:
                est_dist = 3.0 * (1 - y_ratio) + 0.3
            cv2.putText(overlay, f"~{est_dist:.1f}m", (5, y_pos - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)

        # Info panel
        panel_height = 120
        cv2.rectangle(overlay, (0, 0), (400, panel_height), (0, 0, 0), -1)

        y = 25
        lines = [
            f"Mode: {'MARKER' if self.marker_mode else 'MANUAL'}",
            f"Calibration points: {len(self.calibrator.calibration_points)}",
            "Click object, then enter distance",
            "Keys: C=calibrate, S=save, R=reset, Q=quit"
        ]

        for line in lines:
            cv2.putText(overlay, line, (10, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y += 25

        # Show calibration result if available
        if self.calibrator.result and self.calibrator.result.num_points > 0:
            result_text = f"Error: {self.calibrator.result.mean_error_m:.2f}m R²={self.calibrator.result.r_squared:.2f}"
            cv2.putText(overlay, result_text, (10, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        return overlay

    def _prompt_distance(self) -> Optional[float]:
        """Prompt user to enter distance"""
        print("\n" + "=" * 40)
        print("Enter the MEASURED distance in meters")
        print("(or 'skip' to cancel)")
        print("=" * 40)

        try:
            user_input = input("Distance (m): ").strip()
            if user_input.lower() == 'skip':
                return None
            return float(user_input)
        except ValueError:
            print("Invalid input")
            return None

    def _estimate_distance_at_point(self, x: int, y: int, height: int) -> float:
        """Estimate distance at point using current model"""
        y_ratio = y / height

        if self.calibrator.result:
            return self.calibrator.result.estimate_from_y(y_ratio)
        else:
            # Default Y-based estimation
            return 3.0 * (1 - y_ratio) + 0.3

    async def run(self):
        """Run interactive calibration"""
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            logger.error("Failed to open camera")
            return

        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(self.window_name, self._mouse_callback)

        print("\n" + "=" * 60)
        print("DEPTH CALIBRATION")
        print("=" * 60)
        print("Instructions:")
        print("1. Click on an object in the frame")
        print("2. Measure the actual distance to that object")
        print("3. Enter the distance when prompted")
        print("4. Repeat for multiple points at different distances")
        print("5. Press 'C' to compute calibration")
        print("=" * 60 + "\n")

        try:
            while self.is_running:
                ret, frame = cap.read()
                if not ret:
                    continue

                self.current_frame = frame.copy()
                height, width = frame.shape[:2]

                # Detect markers if in marker mode
                markers = []
                if self.marker_mode:
                    markers = self.calibrator.detect_aruco_markers(frame)

                # Draw UI
                display = self._draw_ui(frame, markers)
                cv2.imshow(self.window_name, display)

                # Handle input
                key = cv2.waitKey(1) & 0xFF

                if key == ord('q') or key == 27:
                    self.is_running = False

                elif key == ord('c'):
                    # Compute calibration
                    result = self.calibrator.compute_calibration()
                    self._print_calibration_result(result)

                elif key == ord('s'):
                    # Save calibration
                    filepath = f"calibration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    self.calibrator.save_calibration(filepath)

                elif key == ord('r'):
                    # Reset
                    self.calibrator.calibration_points.clear()
                    self.calibrator.result = None
                    self.click_point = None
                    print("Calibration reset")

                elif key == ord('m'):
                    # Toggle marker mode
                    self.marker_mode = not self.marker_mode
                    print(f"Marker mode: {'ON' if self.marker_mode else 'OFF'}")

                elif key == 13:  # Enter key
                    if self.click_point:
                        # Add calibration point
                        estimated = self._estimate_distance_at_point(
                            self.click_point[0], self.click_point[1], height
                        )

                        print(f"\nEstimated distance: {estimated:.2f}m")
                        measured = self._prompt_distance()

                        if measured is not None:
                            self.calibrator.add_calibration_point(
                                measured_distance_m=measured,
                                estimated_distance_m=estimated,
                                pixel_x=self.click_point[0],
                                pixel_y=self.click_point[1],
                                frame_width=width,
                                frame_height=height
                            )

                        self.click_point = None

                # Auto-add marker points in marker mode
                if self.marker_mode and markers and key == ord('a'):
                    for marker in markers:
                        measured = self._prompt_distance()
                        if measured:
                            self.calibrator.add_calibration_point(
                                measured_distance_m=measured,
                                estimated_distance_m=marker["estimated_distance_m"],
                                pixel_x=marker["center"][0],
                                pixel_y=marker["center"][1],
                                frame_width=width,
                                frame_height=height,
                                notes=f"Marker ID: {marker['id']}"
                            )

        finally:
            cap.release()
            cv2.destroyAllWindows()

            # Final calibration if we have points
            if self.calibrator.calibration_points:
                result = self.calibrator.compute_calibration()
                self._print_calibration_result(result)

                save = input("\nSave calibration? (y/n): ").strip().lower()
                if save == 'y':
                    filepath = f"calibration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    self.calibrator.save_calibration(filepath)

    def _print_calibration_result(self, result: CalibrationResult):
        """Print calibration result"""
        print("\n" + "=" * 50)
        print("CALIBRATION RESULT")
        print("=" * 50)
        print(f"Points: {result.num_points}")
        print("\nLinear Correction:")
        print(f"  corrected = {result.slope:.4f} * estimated + {result.intercept:.4f}")
        print("\nY-Position Model:")
        print(f"  distance = {result.y_scale:.2f} * (1 - y_ratio) + {result.y_offset:.2f}")
        print("\nStatistics:")
        print(f"  Mean Error: {result.mean_error_m:.3f} m")
        print(f"  Max Error:  {result.max_error_m:.3f} m")
        print(f"  RMSE:       {result.rmse_m:.3f} m")
        print(f"  R²:         {result.r_squared:.4f}")
        print("=" * 50)


# =============================================================================
# CALIBRATION VALIDATION
# =============================================================================

async def validate_calibration(
    calibration_path: str,
    camera_index: int = 0,
    num_frames: int = 100
):
    """Validate calibration accuracy"""
    calibrator = DepthCalibrator()
    result = calibrator.load_calibration(calibration_path)

    print(f"\nLoaded calibration with {result.num_points} points")
    print(f"Correction: y = {result.slope:.3f}x + {result.intercept:.3f}")

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        logger.error("Failed to open camera")
        return

    window_name = "Calibration Validation"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    print("\nRunning validation...")
    print("Click on objects and verify distance estimates")
    print("Press Q to quit\n")

    click_point = None

    def mouse_callback(event, x, y, flags, param):
        nonlocal click_point
        if event == cv2.EVENT_LBUTTONDOWN:
            click_point = (x, y)

    cv2.setMouseCallback(window_name, mouse_callback)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            height, width = frame.shape[:2]
            overlay = frame.copy()

            # Draw distance grid
            for i in range(1, 10):
                y_pos = int(height * i / 10)
                y_ratio = y_pos / height
                distance = result.estimate_from_y(y_ratio)

                cv2.line(overlay, (0, y_pos), (width, y_pos), (100, 100, 100), 1)
                cv2.putText(overlay, f"{distance:.1f}m", (5, y_pos - 3),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

            # Show click point distance
            if click_point:
                cv2.circle(overlay, click_point, 10, (0, 0, 255), 2)
                y_ratio = click_point[1] / height
                distance = result.estimate_from_y(y_ratio)
                cv2.putText(overlay, f"Est: {distance:.2f}m",
                            (click_point[0] + 15, click_point[1]),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            cv2.imshow(window_name, overlay)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()


# =============================================================================
# CLI
# =============================================================================

def parse_args():
    parser = argparse.ArgumentParser(description="Depth Calibration Tool")

    parser.add_argument("--mode", choices=["manual", "marker", "validate"],
                        default="manual", help="Calibration mode")
    parser.add_argument("--camera", type=int, default=0,
                        help="Camera index")
    parser.add_argument("--depth", choices=["simple", "midas"],
                        default="simple", help="Depth estimator type")
    parser.add_argument("--load", type=str,
                        help="Load existing calibration file")
    parser.add_argument("--export", type=str,
                        help="Export calibration to file")
    parser.add_argument("--marker-size", type=float, default=0.1,
                        help="ArUco marker size in meters (default: 0.1)")

    return parser.parse_args()


async def main():
    args = parse_args()

    if args.mode == "validate" and args.load:
        await validate_calibration(args.load, args.camera)
        return

    ui = InteractiveCalibrationUI(
        camera_index=args.camera,
        depth_estimator=args.depth,
        marker_mode=(args.mode == "marker"),
        marker_size_m=args.marker_size
    )

    if args.load:
        ui.calibrator.load_calibration(args.load)

    await ui.run()

    if args.export and ui.calibrator.result:
        ui.calibrator.save_calibration(args.export)


if __name__ == "__main__":
    asyncio.run(main())
