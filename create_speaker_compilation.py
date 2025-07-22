import os
import pickle
import numpy
import subprocess
import argparse

# --- Configuration ---
parser = argparse.ArgumentParser(description="TalkNet Post-Processor: Create One Video Per Speaker Track")
parser.add_argument('--videoName',          type=str,   default="001",   help='The name of the video you processed with TalkNet')
parser.add_argument('--videoFolder',        type=str,   default="demo/video",  help='The folder containing your video and its result folder')
parser.add_argument('--outputFolder',       type=str,   default="speakers_output", help='Name of the folder to save the final speaker videos')
parser.add_argument('--speaking_threshold', type=float, default=0.0,     help='Average score threshold to consider a track as "speaking"')
args = parser.parse_args()

# --- Define Paths ---
base_path = os.path.join(args.videoFolder, args.videoName)
pycrop_path = os.path.join(base_path, 'pycrop')
pywork_path = os.path.join(base_path, 'pywork')
scores_path = os.path.join(pywork_path, 'scores.pckl')
# Final output directory will be inside the video's result folder
final_output_dir = os.path.join(base_path, args.outputFolder)

print(f"Reading TalkNet results from: {base_path}")

# --- Create Output Directory ---
os.makedirs(final_output_dir, exist_ok=True)
print(f"Final videos will be saved in: {final_output_dir}")

# --- Load the Scores ---
print("Loading speaker scores...")
try:
    with open(scores_path, 'rb') as fil:
        all_scores = pickle.load(fil)
except FileNotFoundError:
    print(f"FATAL: Could not find scores file at {scores_path}")
    print("Please ensure you have run the main talknet.py script first.")
    exit()

# --- Process Each Track ---
print("Checking each face track for speaking activity...")
videos_created_count = 0
for track_index, scores in enumerate(all_scores):
    # Calculate the average score for the entire track
    average_score = numpy.mean(scores)
    
    print(f"  - Processing Track #{track_index}: Average Score = {average_score:.2f}")

    # Check if the track's average score is above our speaking threshold
    if average_score > args.speaking_threshold:
        video_clip_path = os.path.join(pycrop_path, f'{track_index:05d}.avi')
        audio_clip_path = os.path.join(pycrop_path, f'{track_index:05d}.wav')
        output_file_path = os.path.join(final_output_dir, f'speaker_track_{track_index:05d}.mp4')

        # Crucially, check that BOTH the video and audio source files exist
        if os.path.exists(video_clip_path) and os.path.exists(audio_clip_path):
            print(f"    -> Speaker detected! Creating video: {os.path.basename(output_file_path)}")
            
            # --- FFmpeg Command to Combine One Video and One Audio ---
            ffmpeg_command = [
                'ffmpeg',
                '-y',                       # Overwrite output file if it exists
                '-i', video_clip_path,      # Input 1: The silent video
                '-i', audio_clip_path,      # Input 2: The audio
                '-c:v', 'copy',             # Copy the video stream as-is (fast)
                '-c:a', 'aac',              # Re-encode audio to AAC (standard for MP4)
                '-b:a', '192k',             # Set a good audio bitrate
                '-shortest',                # Finish encoding when the shortest input ends
                output_file_path
            ]
            
            try:
                # Execute the command
                subprocess.run(ffmpeg_command, check=True, capture_output=True, text=True)
                videos_created_count += 1
            except subprocess.CalledProcessError as e:
                print(f"    -> ERROR: FFmpeg failed for track #{track_index}.")
                print(f"       FFmpeg stderr:\n{e.stderr}")
            except FileNotFoundError:
                print("FATAL: 'ffmpeg' command not found. Please ensure FFmpeg is installed and in your system's PATH.")
                exit()
        else:
            print(f"    -> WARNING: Speaker detected, but missing source files for track #{track_index}.")

# --- Final Summary ---
print("\n--------------------")
print("Processing Complete.")
print(f"{videos_created_count} speaker videos were created in:")
print(final_output_dir)
print("--------------------")

