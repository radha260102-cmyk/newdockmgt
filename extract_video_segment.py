"""
Video Segment Extraction Script
Extracts a portion of video from start_time to end_time
"""
import cv2
import sys
import os


def extract_video_segment(input_video, output_video, start_minutes, end_minutes):
    """
    Extract a segment from a video file
    
    Args:
        input_video: Path to input video file
        output_video: Path to output video file
        start_minutes: Start time in minutes
        end_minutes: End time in minutes
    """
    # Check if input file exists
    if not os.path.exists(input_video):
        print(f"Error: Input video file '{input_video}' not found")
        return False
    
    # Open input video
    cap = cv2.VideoCapture(input_video)
    if not cap.isOpened():
        print(f"Error: Could not open video file '{input_video}'")
        return False
    
    # Get video properties
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    total_duration_seconds = total_frames / fps if fps > 0 else 0
    
    print(f"Video properties:")
    print(f"  Resolution: {width}x{height}")
    print(f"  FPS: {fps}")
    print(f"  Total duration: {total_duration_seconds/60:.2f} minutes")
    
    # Calculate frame numbers
    start_seconds = start_minutes * 60
    end_seconds = end_minutes * 60
    start_frame = int(start_seconds * fps)
    end_frame = int(end_seconds * fps)
    
    # Validate times
    if start_seconds >= total_duration_seconds:
        print(f"Error: Start time ({start_minutes} min) is beyond video duration ({total_duration_seconds/60:.2f} min)")
        cap.release()
        return False
    
    if end_seconds > total_duration_seconds:
        print(f"Warning: End time ({end_minutes} min) is beyond video duration. Using video end.")
        end_seconds = total_duration_seconds
        end_frame = total_frames
    
    if start_seconds >= end_seconds:
        print(f"Error: Start time must be less than end time")
        cap.release()
        return False
    
    print(f"\nExtracting segment:")
    print(f"  Start: {start_minutes} minutes ({start_seconds} seconds, frame {start_frame})")
    print(f"  End: {end_minutes} minutes ({end_seconds} seconds, frame {end_frame})")
    print(f"  Duration: {end_minutes - start_minutes} minutes")
    
    # Set starting position
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    
    # Define codec and create VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video, fourcc, fps, (width, height))
    
    if not out.isOpened():
        print(f"Error: Could not create output video file '{output_video}'")
        cap.release()
        return False
    
    # Extract frames
    current_frame = start_frame
    frame_count = 0
    
    print(f"\nProcessing frames...")
    while current_frame < end_frame:
        ret, frame = cap.read()
        if not ret:
            print(f"Warning: Could not read frame {current_frame}")
            break
        
        out.write(frame)
        current_frame += 1
        frame_count += 1
        
        # Progress indicator
        if frame_count % (fps * 10) == 0:  # Every 10 seconds
            progress = ((current_frame - start_frame) / (end_frame - start_frame)) * 100
            print(f"  Progress: {progress:.1f}% ({frame_count} frames processed)")
    
    # Release everything
    cap.release()
    out.release()
    
    print(f"\n✓ Successfully extracted {frame_count} frames")
    print(f"✓ Output saved to: {output_video}")
    return True


def main():
    """Main function"""
    input_video = "C:/Users/yashp/OneDrive/Desktop/Tata_Dock4/good_video/4.mp4"
    output_video = "C:/Users/yashp/OneDrive/Desktop/Tata_Dock4/good_video/crop_4.mp4"
    start_minutes = 15
    end_minutes = 19
    
    # Allow command line arguments
    if len(sys.argv) >= 2:
        input_video = sys.argv[1]
    if len(sys.argv) >= 3:
        output_video = sys.argv[2]
    if len(sys.argv) >= 4:
        start_minutes = float(sys.argv[3])
    if len(sys.argv) >= 5:
        end_minutes = float(sys.argv[4])
    
    print("=" * 60)
    print("Video Segment Extraction Tool")
    print("=" * 60)
    print(f"Input: {input_video}")
    print(f"Output: {output_video}")
    print(f"Time range: {start_minutes} - {end_minutes} minutes")
    print("=" * 60)
    
    success = extract_video_segment(input_video, output_video, start_minutes, end_minutes)
    
    if success:
        print("\n✓ Extraction completed successfully!")
    else:
        print("\n✗ Extraction failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()

