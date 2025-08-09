"""
Video effects processing engine - adapted for Flask backend
"""
import cv2
import numpy as np
from moviepy import ImageSequenceClip
import os
import random
import textwrap
from typing import Tuple, List, Optional, Dict, Any
import tempfile
import logging

logger = logging.getLogger(__name__)


class BaseEffect:
    """Base class for all video effects"""
    
    def __init__(self, **kwargs):
        self.fps = kwargs.get('fps', 30)
        self.duration = kwargs.get('duration', 3.0)
        self.output_width = kwargs.get('output_width')
        self.output_height = kwargs.get('output_height')
        self.total_frames = int(self.fps * self.duration)
    
    def prepare_image(self, image_path: str) -> np.ndarray:
        """Load and prepare image for processing"""
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image from {image_path}")
        return image
    
    def generate_video(self, image_path: str, output_path: str, **params) -> bool:
        """Generate video - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement generate_video method")


class Rotation3DEffect(BaseEffect):
    """3D Rotation effect"""
    
    def apply_3d_rotation(self, image: np.ndarray, angle_x: float, angle_y: float, 
                         angle_z: float, zoom_factor: float = 1.0) -> np.ndarray:
        """Apply 3D rotation to image using perspective transformation"""
        height, width = image.shape[:2]
        center_x, center_y = width / 2, height / 2
        
        # Convert angles to radians
        ax = np.radians(angle_x)
        ay = np.radians(angle_y)
        az = np.radians(angle_z)
        
        # Define the 3D coordinates of the image corners
        corners_3d = np.array([
            [-width/2, -height/2, 0],  # top-left
            [width/2, -height/2, 0],   # top-right
            [width/2, height/2, 0],    # bottom-right
            [-width/2, height/2, 0]    # bottom-left
        ], dtype=np.float32)
        
        # Rotation matrices
        Rx = np.array([
            [1, 0, 0],
            [0, np.cos(ax), -np.sin(ax)],
            [0, np.sin(ax), np.cos(ax)]
        ])
        
        Ry = np.array([
            [np.cos(ay), 0, np.sin(ay)],
            [0, 1, 0],
            [-np.sin(ay), 0, np.cos(ay)]
        ])
        
        Rz = np.array([
            [np.cos(az), -np.sin(az), 0],
            [np.sin(az), np.cos(az), 0],
            [0, 0, 1]
        ])
        
        # Combined rotation
        R = Rz @ Ry @ Rx
        
        # Apply rotation to corners
        rotated_corners_3d = corners_3d @ R.T
        
        # Project to 2D using perspective projection
        focal_length = max(width, height) * 1.5
        z_offset = focal_length * 0.5
        
        # Apply zoom
        rotated_corners_3d *= zoom_factor
        
        # Perspective projection
        projected_corners = np.zeros((4, 2), dtype=np.float32)
        for i in range(4):
            x, y, z = rotated_corners_3d[i]
            projected_x = focal_length * x / (focal_length + z + z_offset)
            projected_y = focal_length * y / (focal_length + z + z_offset)
            projected_corners[i] = [projected_x + center_x, projected_y + center_y]
        
        # Original corners in image coordinates
        original_corners = np.array([
            [0, 0],
            [width, 0],
            [width, height],
            [0, height]
        ], dtype=np.float32)
        
        # Calculate perspective transformation matrix
        M = cv2.getPerspectiveTransform(original_corners, projected_corners)
        
        # Apply perspective transformation
        rotated_image = cv2.warpPerspective(image, M, (width, height),
                                          borderMode=cv2.BORDER_CONSTANT,
                                          borderValue=(0, 0, 0))
        
        return rotated_image
    
    def generate_video(self, image_path: str, output_path: str, **params) -> bool:
        """Generate 3D rotation video"""
        try:
            image = self.prepare_image(image_path)
            height, width = image.shape[:2]
            
            # Parameters
            axis = params.get('axis', 'y')
            rotation_angle = params.get('rotation_angle', 45.0)
            
            frames = []
            
            for frame_idx in range(self.total_frames):
                progress = frame_idx / (self.total_frames - 1)
                
                # Apply smooth easing
                if progress < 0.5:
                    eased_progress = 4 * progress * progress * progress
                else:
                    eased_progress = 1 - pow(-2 * progress + 2, 3) / 2
                
                # Calculate rotation angles
                angle_x = angle_y = angle_z = 0.0
                
                if "x" in axis.lower():
                    angle_x = rotation_angle * np.sin(eased_progress * np.pi)
                if "y" in axis.lower():
                    angle_y = rotation_angle * np.sin(eased_progress * np.pi)
                if "z" in axis.lower():
                    angle_z = rotation_angle * eased_progress
                
                current_zoom = 1.0 + 0.2 * np.sin(eased_progress * np.pi)
                
                # Apply 3D rotation
                rotated_image = self.apply_3d_rotation(image, angle_x, angle_y, angle_z, current_zoom)
                
                # Convert BGR to RGB for MoviePy
                rgb_frame = cv2.cvtColor(rotated_image, cv2.COLOR_BGR2RGB)
                frames.append(rgb_frame)
            
            # Create video
            clip = ImageSequenceClip(frames, fps=self.fps)
            clip.write_videofile(output_path, 
                                codec="libx264", 
                                audio_codec="aac",
                                temp_audiofile='temp-audio.m4a', 
                                remove_temp=True,
                                preset='medium',
                                ffmpeg_params=['-pix_fmt', 'yuv420p'])
            
            return True
            
        except Exception as e:
            logger.error(f"Error in 3D rotation effect: {str(e)}")
            return False


class RippleZoomEffect(BaseEffect):
    """Ripple zoom effect"""
    
    def create_ripple_effect(self, image: np.ndarray, frame_idx: int, 
                           ripple_strength: float = 20.0, ripple_frequency: float = 0.05) -> np.ndarray:
        """Apply ripple distortion effect"""
        height, width = image.shape[:2]
        
        # Create coordinate grids
        y_coords, x_coords = np.mgrid[0:height, 0:width]
        
        # Calculate center point
        center_x, center_y = width // 2, height // 2
        
        # Calculate distance from center
        distance = np.sqrt((x_coords - center_x)**2 + (y_coords - center_y)**2)
        
        # Time-based animation factor
        time_factor = frame_idx / self.total_frames
        
        # Create ripple effect
        ripple_radius = time_factor * max(width, height) * 0.8
        wave = np.sin((distance - ripple_radius) * ripple_frequency) * ripple_strength
        
        # Apply falloff
        falloff = np.exp(-np.abs(distance - ripple_radius) / (max(width, height) * 0.1))
        wave *= falloff
        wave *= (1.0 - time_factor * 0.7)
        
        # Calculate new coordinates
        angle = np.arctan2(y_coords - center_y, x_coords - center_x)
        new_x = x_coords + wave * np.cos(angle)
        new_y = y_coords + wave * np.sin(angle)
        
        # Ensure coordinates are within bounds
        new_x = np.clip(new_x, 0, width - 1)
        new_y = np.clip(new_y, 0, height - 1)
        
        # Apply distortion
        rippled_image = cv2.remap(image, 
                                new_x.astype(np.float32), 
                                new_y.astype(np.float32), 
                                cv2.INTER_LINEAR,
                                borderMode=cv2.BORDER_REFLECT)
        
        return rippled_image
    
    def apply_zoom(self, image: np.ndarray, zoom_factor: float) -> np.ndarray:
        """Apply zoom effect"""
        height, width = image.shape[:2]
        
        crop_width = int(width / zoom_factor)
        crop_height = int(height / zoom_factor)
        
        start_x = (width - crop_width) // 2
        start_y = (height - crop_height) // 2
        
        cropped = image[start_y:start_y + crop_height, start_x:start_x + crop_width]
        zoomed = cv2.resize(cropped, (width, height), interpolation=cv2.INTER_CUBIC)
        
        return zoomed
    
    def generate_video(self, image_path: str, output_path: str, **params) -> bool:
        """Generate ripple zoom video"""
        try:
            image = self.prepare_image(image_path)
            
            # Parameters
            zoom_factor = params.get('zoom_factor', 2.0)
            ripple_strength = params.get('ripple_strength', 0.5) * 30.0  # Scale for visibility
            
            frames = []
            
            for frame_idx in range(self.total_frames):
                progress = frame_idx / (self.total_frames - 1)
                
                # Ease-out cubic for zoom
                eased_progress = 1 - (1 - progress) ** 3
                current_zoom = zoom_factor + (1.0 - zoom_factor) * eased_progress
                
                # Apply zoom
                zoomed_image = self.apply_zoom(image, current_zoom)
                
                # Apply ripple
                rippled_image = self.create_ripple_effect(zoomed_image, frame_idx, ripple_strength)
                
                # Convert to RGB
                rgb_frame = cv2.cvtColor(rippled_image, cv2.COLOR_BGR2RGB)
                frames.append(rgb_frame)
            
            # Create video
            clip = ImageSequenceClip(frames, fps=self.fps)
            clip.write_videofile(output_path, 
                                codec="libx264", 
                                audio_codec="aac",
                                temp_audiofile='temp-audio.m4a', 
                                remove_temp=True,
                                preset='medium',
                                ffmpeg_params=['-pix_fmt', 'yuv420p'])
            
            return True
            
        except Exception as e:
            logger.error(f"Error in ripple zoom effect: {str(e)}")
            return False


class ZoomHighlightEffect(BaseEffect):
    """Zoom with highlighting effect"""
    
    def generate_video(self, image_path: str, output_path: str, **params) -> bool:
        """Generate zoom with highlight video"""
        try:
            image = self.prepare_image(image_path)
            height, width = image.shape[:2]
            
            # Parameters
            zoom_factor = params.get('zoom_factor', 1.8)
            highlight_color = params.get('highlight_color', 'yellow')
            
            # Convert color name to BGR
            color_map = {
                'yellow': (0, 255, 255),
                'red': (0, 0, 255),
                'green': (0, 255, 0),
                'blue': (255, 0, 0),
                'cyan': (255, 255, 0),
                'magenta': (255, 0, 255)
            }
            highlighter_color = color_map.get(highlight_color.lower(), (0, 255, 255))
            
            # Default highlight area (center portion of image)
            padding = 50
            x1, y1 = width // 4, height // 4
            x2, y2 = 3 * width // 4, 3 * height // 4
            
            # Calculate padded ROI
            x1p = max(x1 - padding, 0)
            y1p = max(y1 - padding, 0)
            x2p = min(x2 + padding, width)
            y2p = min(y2 + padding, height)
            
            roi_w, roi_h = x2p - x1p, y2p - y1p
            cx, cy = (x1p + x2p) / 2, (y1p + y2p) / 2
            
            # Calculate maximum zoom
            calculated_max_zoom = min(width / roi_w, height / roi_h) * 0.999
            max_zoom = max(1.0, min(calculated_max_zoom, zoom_factor))
            
            frames = []
            
            for i, z in enumerate(np.linspace(1.0, max_zoom, self.total_frames)):
                crop_w, crop_h = width / z, height / z
                tlx = int(max(cx - crop_w/2, 0))
                tly = int(max(cy - crop_h/2, 0))
                brx = int(min(cx + crop_w/2, width))
                bry = int(min(cy + crop_h/2, height))
                
                # Ensure valid crop
                if brx <= tlx:
                    brx = tlx + 1
                if bry <= tly:
                    bry = tly + 1
                
                brx = min(brx, width)
                bry = min(bry, height)
                
                crop = image[tly:bry, tlx:brx]
                
                if crop.shape[0] > 0 and crop.shape[1] > 0:
                    enlarged = cv2.resize(crop, (width, height), interpolation=cv2.INTER_CUBIC)
                else:
                    enlarged = image.copy()
                
                # Progressive highlight
                scale = z
                rx1 = int((x1p - tlx) * scale)
                ry1 = int((y1p - tly) * scale)
                rx2 = int((x2p - tlx) * scale)
                ry2 = int((y2p - tly) * scale)
                
                # Clamp rectangle bounds
                rx1 = max(0, min(rx1, width-1))
                ry1 = max(0, min(ry1, height-1))
                rx2 = max(1, min(rx2, width))
                ry2 = max(1, min(ry2, height))
                
                # Progress and highlight
                progress = i / (self.total_frames - 1)
                highlight_padding = 8
                highlight_x1 = rx1 + highlight_padding
                highlight_x2 = rx2 - highlight_padding
                highlight_width = highlight_x2 - highlight_x1
                
                drawn_width = int(highlight_width * progress)
                current_rx2 = highlight_x1 + drawn_width
                
                if drawn_width > 0 and current_rx2 > highlight_x1 and highlight_width > 0:
                    highlighter_alpha = 0.4
                    
                    overlay = enlarged.copy()
                    cv2.rectangle(overlay, (highlight_x1, ry1), (current_rx2, ry2), 
                                highlighter_color, -1)
                    cv2.addWeighted(overlay, highlighter_alpha, enlarged, 
                                  1 - highlighter_alpha, 0, enlarged)
                
                # Convert to RGB and ensure even dimensions
                rgb_frame = cv2.cvtColor(enlarged, cv2.COLOR_BGR2RGB)
                h, w = rgb_frame.shape[:2]
                
                if h % 2 == 1:
                    rgb_frame = np.pad(rgb_frame, ((0, 1), (0, 0), (0, 0)), mode='edge')
                if w % 2 == 1:
                    rgb_frame = np.pad(rgb_frame, ((0, 0), (0, 1), (0, 0)), mode='edge')
                
                frames.append(rgb_frame)
            
            # Create video
            clip = ImageSequenceClip(frames, fps=self.fps)
            clip.write_videofile(output_path, 
                                codec="libx264", 
                                audio_codec="aac",
                                temp_audiofile='temp-audio.m4a', 
                                remove_temp=True,
                                preset='medium',
                                ffmpeg_params=['-pix_fmt', 'yuv420p'])
            
            return True
            
        except Exception as e:
            logger.error(f"Error in zoom highlight effect: {str(e)}")
            return False


class WikipediaTextEffect(BaseEffect):
    """Wikipedia text generator effect"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Path to Wikipedia logo in Flask backend assets
        self.logo_path = os.path.join(os.path.dirname(__file__), 'assets', 'Wikipedia_logo.svg.png')
    
    def wrap_text(self, text: str, font, max_width: int) -> List[str]:
        """Wrap text to fit within specified width"""
        # Estimate character width (rough approximation)
        char_width = 20  # pixels per character (approximate)
        chars_per_line = max_width // char_width
        
        # Wrap text
        wrapped_lines = textwrap.wrap(text, width=chars_per_line)
        return wrapped_lines
    
    def create_text_image(self, text: str, width: int, height: int) -> np.ndarray:
        """Create image with Wikipedia logo and text"""
        # Create white background
        image = np.ones((height, width, 3), dtype=np.uint8) * 255
        
        try:
            # Load Wikipedia logo
            logo = cv2.imread(self.logo_path, cv2.IMREAD_UNCHANGED)
            if logo is not None:
                # Resize logo to fit in upper portion
                logo_height = height // 4
                logo_aspect = logo.shape[1] / logo.shape[0]
                logo_width = int(logo_height * logo_aspect)
                
                if logo_width > width:
                    logo_width = width
                    logo_height = int(logo_width / logo_aspect)
                
                logo_resized = cv2.resize(logo, (logo_width, logo_height))
                
                # Handle transparency if logo has alpha channel
                if logo_resized.shape[2] == 4:
                    # Convert BGRA to BGR
                    logo_bgr = logo_resized[:, :, :3]
                    alpha = logo_resized[:, :, 3] / 255.0
                    
                    # Position logo at top center
                    x_offset = (width - logo_width) // 2
                    y_offset = 50
                    
                    # Blend logo with background
                    for c in range(3):
                        image[y_offset:y_offset+logo_height, x_offset:x_offset+logo_width, c] = \
                            alpha * logo_bgr[:, :, c] + (1 - alpha) * image[y_offset:y_offset+logo_height, x_offset:x_offset+logo_width, c]
                else:
                    # No alpha channel, direct placement
                    x_offset = (width - logo_width) // 2
                    y_offset = 50
                    image[y_offset:y_offset+logo_height, x_offset:x_offset+logo_width] = logo_resized
                
                text_start_y = y_offset + logo_height + 100
            else:
                text_start_y = 100
                
        except Exception as e:
            logger.warning(f"Could not load Wikipedia logo: {e}")
            text_start_y = 100
        
        # Add text below logo
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.0
        font_thickness = 2
        text_color = (0, 0, 0)  # Black text
        
        # Wrap text to fit width
        lines = self.wrap_text(text, font, width - 100)  # Leave 50px margin on each side
        
        line_height = 40
        y_position = text_start_y
        
        for line in lines:
            # Calculate text size to center it
            text_size = cv2.getTextSize(line, font, font_scale, font_thickness)[0]
            x_position = (width - text_size[0]) // 2
            
            # Add text to image
            cv2.putText(image, line, (x_position, y_position), font, font_scale, text_color, font_thickness)
            y_position += line_height
            
            # Check if we're running out of space
            if y_position > height - 100:
                break
        
        return image
    
    def generate_video(self, image_path: str, output_path: str, **parameters) -> bool:
        """Generate Wikipedia text video"""
        try:
            # Extract parameters
            text_content = parameters.get('text_content', 'Wikipedia is a free online encyclopedia.')
            aspect_ratio = parameters.get('aspect_ratio', '9:16')
            
            # Calculate dimensions based on aspect ratio
            if aspect_ratio == '9:16':
                width, height = 1080, 1920
            elif aspect_ratio == '16:9':
                width, height = 1920, 1080
            else:
                width, height = 1080, 1920  # Default to 9:16
            
            # Create the text image
            text_image = self.create_text_image(text_content, width, height)
            
            frames = []
            
            # Generate frames (static image with fade-in effect)
            for frame_num in range(self.total_frames):
                frame = text_image.copy()
                
                # Add fade-in effect
                if frame_num < self.fps:  # First second
                    alpha = frame_num / self.fps
                    frame = (frame * alpha).astype(np.uint8)
                
                # Convert to RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(rgb_frame)
            
            # Create video
            clip = ImageSequenceClip(frames, fps=self.fps)
            clip.write_videofile(output_path, 
                                codec="libx264", 
                                audio_codec="aac",
                                temp_audiofile='temp-audio.m4a', 
                                remove_temp=True,
                                preset='medium',
                                ffmpeg_params=['-pix_fmt', 'yuv420p'])
            
            return True
            
        except Exception as e:
            logger.error(f"Error in Wikipedia text effect: {str(e)}")
            return False


class FontVideoEffect(BaseEffect):
    """Font video generator effect"""
    
    def get_random_font(self) -> int:
        """Get random OpenCV font"""
        fonts = [
            cv2.FONT_HERSHEY_SIMPLEX,
            cv2.FONT_HERSHEY_PLAIN,
            cv2.FONT_HERSHEY_DUPLEX,
            cv2.FONT_HERSHEY_COMPLEX,
            cv2.FONT_HERSHEY_TRIPLEX,
            cv2.FONT_HERSHEY_COMPLEX_SMALL,
            cv2.FONT_HERSHEY_SCRIPT_SIMPLEX,
            cv2.FONT_HERSHEY_SCRIPT_COMPLEX
        ]
        return random.choice(fonts)
    
    def create_text_frame(self, text: str, width: int, height: int, font: int, 
                         font_scale: float, color: tuple) -> np.ndarray:
        """Create a frame with text"""
        # Create black background
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Get text size
        text_size = cv2.getTextSize(text, font, font_scale, 2)[0]
        
        # Center the text
        x = (width - text_size[0]) // 2
        y = (height + text_size[1]) // 2
        
        # Add text
        cv2.putText(frame, text, (x, y), font, font_scale, color, 2)
        
        return frame
    
    def generate_video(self, image_path: str, output_path: str, **parameters) -> bool:
        """Generate font video"""
        try:
            # Extract parameters
            text_content = parameters.get('text_content', 'Sample Text')
            font_changes = parameters.get('font_changes', True)
            zoom_effect = parameters.get('zoom_effect', True)
            
            # Video dimensions
            width, height = 1920, 1080
            
            # Calculate frames
            frame_duration = 0.1  # Duration per font change
            frames_per_font = max(1, int(self.fps * frame_duration))
            
            frames = []
            current_font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 3.0
            color = (255, 255, 255)
            
            # Generate frames
            for frame_num in range(self.total_frames):
                if font_changes and frame_num % frames_per_font == 0:
                    current_font = self.get_random_font()
                    font_scale = random.uniform(2.0, 4.0)
                    color = (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
                
                # Create frame
                frame = self.create_text_frame(text_content, width, height, current_font, font_scale, color)
                
                # Apply zoom effect
                if zoom_effect:
                    zoom_factor = 1.0 + (frame_num / self.total_frames) * 0.5  # Gradual zoom
                    zoomed_width = int(width * zoom_factor)
                    zoomed_height = int(height * zoom_factor)
                    
                    if zoomed_width > width and zoomed_height > height:
                        # Zoom in and crop
                        frame_zoomed = cv2.resize(frame, (zoomed_width, zoomed_height))
                        x_start = (zoomed_width - width) // 2
                        y_start = (zoomed_height - height) // 2
                        frame = frame_zoomed[y_start:y_start+height, x_start:x_start+width]
                
                # Convert to RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(rgb_frame)
            
            # Create video
            clip = ImageSequenceClip(frames, fps=self.fps)
            clip.write_videofile(output_path, 
                                codec="libx264", 
                                audio_codec="aac",
                                temp_audiofile='temp-audio.m4a', 
                                remove_temp=True,
                                preset='medium',
                                ffmpeg_params=['-pix_fmt', 'yuv420p'])
            
            return True
            
        except Exception as e:
            logger.error(f"Error in font video effect: {str(e)}")
            return False


class PerspectiveEffect(BaseEffect):
    """Perspective transformation effect"""
    
    def apply_perspective_transform(self, image: np.ndarray, progress: float, strength: float) -> np.ndarray:
        """Apply perspective transformation based on progress (0-1)"""
        height, width = image.shape[:2]
        
        # Define source points (corners of the image)
        src_points = np.float32([
            [0, 0],                # top-left
            [width, 0],            # top-right
            [width, height],       # bottom-right
            [0, height]            # bottom-left
        ])
        
        # Define destination points for perspective transformation
        # Animate from flat to tilted perspective
        tilt_factor = progress * strength
        
        dst_points = np.float32([
            [width * tilt_factor, height * tilt_factor],                    # top-left
            [width * (1 - tilt_factor), height * tilt_factor],             # top-right
            [width, height],                                                # bottom-right
            [0, height]                                                     # bottom-left
        ])
        
        # Get perspective transformation matrix
        matrix = cv2.getPerspectiveTransform(src_points, dst_points)
        
        # Apply transformation
        transformed = cv2.warpPerspective(image, matrix, (width, height))
        
        return transformed
    
    def generate_video(self, image_path: str, output_path: str, **parameters) -> bool:
        """Generate perspective video"""
        try:
            # Extract parameters
            perspective_strength = parameters.get('perspective_strength', 0.5)
            zoom_factor = parameters.get('zoom_factor', 1.5)
            
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Could not load image: {image_path}")
                return False
            
            height, width = image.shape[:2]
            frames = []
            
            for frame_num in range(self.total_frames):
                progress = frame_num / self.total_frames
                
                # Apply perspective transformation
                transformed = self.apply_perspective_transform(image, progress, perspective_strength)
                
                # Apply zoom
                if zoom_factor > 1.0:
                    zoom_progress = progress * (zoom_factor - 1.0) + 1.0
                    zoomed_width = int(width * zoom_progress)
                    zoomed_height = int(height * zoom_progress)
                    
                    if zoomed_width > width and zoomed_height > height:
                        zoomed = cv2.resize(transformed, (zoomed_width, zoomed_height))
                        x_start = (zoomed_width - width) // 2
                        y_start = (zoomed_height - height) // 2
                        transformed = zoomed[y_start:y_start+height, x_start:x_start+width]
                
                # Convert to RGB
                rgb_frame = cv2.cvtColor(transformed, cv2.COLOR_BGR2RGB)
                frames.append(rgb_frame)
            
            # Create video
            clip = ImageSequenceClip(frames, fps=self.fps)
            clip.write_videofile(output_path, 
                                codec="libx264", 
                                audio_codec="aac",
                                temp_audiofile='temp-audio.m4a', 
                                remove_temp=True,
                                preset='medium',
                                ffmpeg_params=['-pix_fmt', 'yuv420p'])
            
            return True
            
        except Exception as e:
            logger.error(f"Error in perspective effect: {str(e)}")
            return False


class PerspectiveWithHighlightEffect(BaseEffect):
    """Perspective transformation with highlight effect"""
    
    def apply_perspective_transform(self, image: np.ndarray, progress: float, strength: float) -> np.ndarray:
        """Apply perspective transformation based on progress (0-1)"""
        height, width = image.shape[:2]
        
        # Define source points (corners of the image)
        src_points = np.float32([
            [0, 0],                # top-left
            [width, 0],            # top-right
            [width, height],       # bottom-right
            [0, height]            # bottom-left
        ])
        
        # Define destination points for perspective transformation
        tilt_factor = progress * strength
        
        dst_points = np.float32([
            [width * tilt_factor, height * tilt_factor],                    # top-left
            [width * (1 - tilt_factor), height * tilt_factor],             # top-right
            [width, height],                                                # bottom-right
            [0, height]                                                     # bottom-left
        ])
        
        # Get perspective transformation matrix
        matrix = cv2.getPerspectiveTransform(src_points, dst_points)
        
        # Apply transformation
        transformed = cv2.warpPerspective(image, matrix, (width, height))
        
        return transformed
    
    def add_highlight_overlay(self, image: np.ndarray, progress: float, 
                            highlight_area: tuple) -> np.ndarray:
        """Add progressive highlighting overlay"""
        if progress < 0.5:  # Only highlight in second half
            return image
        
        highlight_progress = (progress - 0.5) * 2.0  # Normalize to 0-1
        height, width = image.shape[:2]
        
        # Default highlight area if not provided
        if not highlight_area:
            highlight_area = (width//4, height//4, 3*width//4, 3*height//4)
        
        x1, y1, x2, y2 = highlight_area
        
        # Create highlight overlay
        overlay = image.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 255, 255), -1)  # Yellow highlight
        
        # Blend with original
        alpha = 0.3 * highlight_progress
        highlighted = cv2.addWeighted(image, 1 - alpha, overlay, alpha, 0)
        
        return highlighted
    
    def generate_video(self, image_path: str, output_path: str, **parameters) -> bool:
        """Generate perspective video with highlighting"""
        try:
            # Extract parameters
            perspective_strength = parameters.get('perspective_strength', 0.5)
            zoom_factor = parameters.get('zoom_factor', 1.5)
            highlight_area = parameters.get('highlight_area', None)
            
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Could not load image: {image_path}")
                return False
            
            height, width = image.shape[:2]
            frames = []
            
            for frame_num in range(self.total_frames):
                progress = frame_num / self.total_frames
                
                # Apply perspective transformation
                transformed = self.apply_perspective_transform(image, progress, perspective_strength)
                
                # Apply zoom
                if zoom_factor > 1.0:
                    zoom_progress = progress * (zoom_factor - 1.0) + 1.0
                    zoomed_width = int(width * zoom_progress)
                    zoomed_height = int(height * zoom_progress)
                    
                    if zoomed_width > width and zoomed_height > height:
                        zoomed = cv2.resize(transformed, (zoomed_width, zoomed_height))
                        x_start = (zoomed_width - width) // 2
                        y_start = (zoomed_height - height) // 2
                        transformed = zoomed[y_start:y_start+height, x_start:x_start+width]
                
                # Add highlighting
                highlighted = self.add_highlight_overlay(transformed, progress, highlight_area)
                
                # Convert to RGB
                rgb_frame = cv2.cvtColor(highlighted, cv2.COLOR_BGR2RGB)
                frames.append(rgb_frame)
            
            # Create video
            clip = ImageSequenceClip(frames, fps=self.fps)
            clip.write_videofile(output_path, 
                                codec="libx264", 
                                audio_codec="aac",
                                temp_audiofile='temp-audio.m4a', 
                                remove_temp=True,
                                preset='medium',
                                ffmpeg_params=['-pix_fmt', 'yuv420p'])
            
            return True
            
        except Exception as e:
            logger.error(f"Error in perspective with highlight effect: {str(e)}")
            return False


class RippleZoomWithHighlightEffect(BaseEffect):
    """Ripple zoom effect with highlighting"""
    
    def apply_ripple_effect(self, image: np.ndarray, progress: float, strength: float) -> np.ndarray:
        """Apply ripple distortion effect"""
        height, width = image.shape[:2]
        
        # Create coordinate matrices
        y, x = np.ogrid[:height, :width]
        
        # Calculate center
        center_x, center_y = width / 2, height / 2
        
        # Calculate distance from center
        distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)
        
        # Create ripple effect
        ripple_strength = strength * progress * 50
        angle = distance * 0.1 - progress * 10
        
        # Apply ripple distortion
        offset_x = ripple_strength * np.sin(angle) * np.exp(-distance / 200)
        offset_y = ripple_strength * np.cos(angle) * np.exp(-distance / 200)
        
        # Create new coordinates
        new_x = np.clip(x + offset_x, 0, width - 1).astype(np.int32)
        new_y = np.clip(y + offset_y, 0, height - 1).astype(np.int32)
        
        # Apply distortion
        rippled = image[new_y, new_x]
        
        return rippled
    
    def generate_video(self, image_path: str, output_path: str, **parameters) -> bool:
        """Generate ripple zoom video with highlighting"""
        try:
            # Extract parameters
            zoom_factor = parameters.get('zoom_factor', 2.0)
            ripple_strength = parameters.get('ripple_strength', 0.5)
            highlight_start = parameters.get('highlight_start', 0.7)
            
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Could not load image: {image_path}")
                return False
            
            height, width = image.shape[:2]
            frames = []
            
            for frame_num in range(self.total_frames):
                progress = frame_num / self.total_frames
                
                # Start with zoomed image and zoom out
                current_zoom = zoom_factor * (1.0 - progress) + 1.0
                
                if current_zoom > 1.0:
                    zoomed_width = int(width * current_zoom)
                    zoomed_height = int(height * current_zoom)
                    zoomed = cv2.resize(image, (zoomed_width, zoomed_height))
                    
                    # Crop to original size
                    x_start = (zoomed_width - width) // 2
                    y_start = (zoomed_height - height) // 2
                    frame = zoomed[y_start:y_start+height, x_start:x_start+width]
                else:
                    frame = image.copy()
                
                # Apply ripple effect
                if progress > 0.2:  # Start ripple after 20% of animation
                    ripple_progress = (progress - 0.2) / 0.8
                    frame = self.apply_ripple_effect(frame, ripple_progress, ripple_strength)
                
                # Add highlighting in the last portion
                if progress >= highlight_start:
                    highlight_progress = (progress - highlight_start) / (1.0 - highlight_start)
                    
                    # Create highlight overlay
                    overlay = frame.copy()
                    highlight_height = int(height * 0.1)  # 10% of image height
                    y_pos = int(height * 0.5 * highlight_progress)  # Move down progressively
                    
                    cv2.rectangle(overlay, (0, y_pos), (width, y_pos + highlight_height), (0, 255, 255), -1)
                    
                    # Blend
                    alpha = 0.3
                    frame = cv2.addWeighted(frame, 1 - alpha, overlay, alpha, 0)
                
                # Convert to RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(rgb_frame)
            
            # Create video
            clip = ImageSequenceClip(frames, fps=self.fps)
            clip.write_videofile(output_path, 
                                codec="libx264", 
                                audio_codec="aac",
                                temp_audiofile='temp-audio.m4a', 
                                remove_temp=True,
                                preset='medium',
                                ffmpeg_params=['-pix_fmt', 'yuv420p'])
            
            return True
            
        except Exception as e:
            logger.error(f"Error in ripple zoom with highlight effect: {str(e)}")
            return False


# Effect registry mapping effect types to classes
EFFECT_REGISTRY = {
    'rotation_3d': Rotation3DEffect,
    'ripple_zoom': RippleZoomEffect,
    'zoom_highlight': ZoomHighlightEffect,
    'wikipedia_text': WikipediaTextEffect,
    'font_video': FontVideoEffect,
    'perspective_transform': PerspectiveEffect,
    'perspective_with_highlight': PerspectiveWithHighlightEffect,
    'ripple_zoom_with_highlight': RippleZoomWithHighlightEffect,
}


def create_effect(effect_type: str, **kwargs) -> BaseEffect:
    """Factory function to create effect instances"""
    if effect_type not in EFFECT_REGISTRY:
        raise ValueError(f"Unknown effect type: {effect_type}")
    
    effect_class = EFFECT_REGISTRY[effect_type]
    return effect_class(**kwargs)


def process_video_effect(effect_type: str, image_path: str, output_path: str, 
                        parameters: Dict[str, Any]) -> bool:
    """Main function to process video effects"""
    try:
        effect = create_effect(effect_type, **parameters)
        return effect.generate_video(image_path, output_path, **parameters)
    except Exception as e:
        logger.error(f"Error processing video effect {effect_type}: {str(e)}")
        return False
