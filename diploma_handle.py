# final smart chunking

import json
import torch
import librosa
import numpy as np
from transformers import WhisperForConditionalGeneration, WhisperProcessor
import moviepy.editor as mp
import os
import time
import shutil
import re
import tkinter as tk
from tkinter import filedialog

def create_output_folder(video_path):
    """Create organized output folder structure"""
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    output_dir = f"./output/{base_name}"
    
    os.makedirs(output_dir, exist_ok=True)
    return {
        'base_dir': output_dir,
        'video': os.path.join(output_dir, f"{base_name}.mp4"),
        'audio': os.path.join(output_dir, f"{base_name}.wav"),
        'transcription_json': os.path.join(output_dir, f"{base_name}_transcription.json"),
        'transcription_txt': os.path.join(output_dir, f"{base_name}_transcription.txt"),
        'chunked_json': os.path.join(output_dir, f"{base_name}_chunked.json")
    }

def initialize_whisper():
    """Initialize Whisper model with optimized settings"""
    processor = WhisperProcessor.from_pretrained("openai/whisper-medium")
    model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-medium")
    model.config.forced_decoder_ids = processor.get_decoder_prompt_ids(
        language="kazakh", 
        task="transcribe"
    )
    return processor, model.to("cuda" if torch.cuda.is_available() else "cpu")

def copy_video_and_extract_audio(video_path, output_paths):
    """Copy original video and extract audio"""
    try:
        # Copy original video to output folder
        shutil.copy2(video_path, output_paths['video'])
        
        # Extract audio
        with mp.VideoFileClip(video_path) as video:
            video.audio.write_audiofile(
                output_paths['audio'],
                fps=16000,
                codec='pcm_s16le',
                verbose=False
            )
        return True
    except Exception as e:
        print(f"Video/audio processing failed: {e}")
        return False

def transcribe_with_timestamps(audio_path, processor, model):
    """Efficient transcription with JSON-ready output"""
    try:
        audio = librosa.load(audio_path, sr=16000)[0].astype(np.float32)
        inputs = processor(audio, sampling_rate=16000, return_tensors="pt").to(model.device)
        
        outputs = model.generate(
            inputs.input_features,
            return_timestamps=True,
            language="kazakh",
            task="transcribe"
        )
        
        result = processor.batch_decode(outputs, output_offsets=True)[0]
        
        segments = []
        if 'chunks' in result:
            for idx, chunk in enumerate(result['chunks']):
                segments.append({
                    "id": idx,
                    "start": round(float(chunk['timestamp'][0]), 2),
                    "end": round(float(chunk['timestamp'][1] if chunk['timestamp'][1] else 
                               chunk['timestamp'][0] + 1.0), 2),
                    "text": chunk['text'].strip()
                })
        else:
            duration = round(len(audio)/16000, 2)
            segments.append({
                "id": 0,
                "start": 0.0,
                "end": duration,
                "text": result['text'].strip()
            })
            
        return result['text'].strip(), segments
    
    except Exception as e:
        print(f"Transcription failed: {e}")
        return None, None

def smart_chunking(segments, max_duration=8.0, max_sentences=3):
    """Hybrid approach combining sentence structure and duration limits"""
    chunks = []
    current_chunk = []
    
    for seg in segments:
        # Split segment into sentences
        sentences = re.split(r'(?<=[.!?])\s+', seg['text'])
        time_per_char = (seg['end'] - seg['start']) / len(seg['text']) if seg['text'] else 0
        
        for sentence in sentences:
            if not sentence:
                continue
                
            # Calculate sentence timings
            sentence_start = seg['start'] + (time_per_char * seg['text'].find(sentence))
            sentence_end = sentence_start + (time_per_char * len(sentence))
            
            sentence_data = {
                "text": sentence,
                "start": round(float(sentence_start), 2),
                "end": round(float(sentence_end), 2)
            }
            
            # Start new chunk if:
            # 1. Exceeds max duration OR
            # 2. Reaches max sentences OR 
            # 3. Natural paragraph break
            if (current_chunk and 
                ((sentence_end - current_chunk[0]['start'] > max_duration) or
                 (len(current_chunk) >= max_sentences) or
                 sentence.endswith(('.', '!', '?')))):
                
                chunks.append({
                    "id": len(chunks),
                    "start": current_chunk[0]['start'],
                    "end": current_chunk[-1]['end'],
                    "text": " ".join(s['text'] for s in current_chunk)
                })
                current_chunk = []
                
            current_chunk.append(sentence_data)
    
    # Add last chunk if exists
    if current_chunk:
        chunks.append({
            "id": len(chunks),
            "start": current_chunk[0]['start'],
            "end": current_chunk[-1]['end'],
            "text": " ".join(s['text'] for s in current_chunk)
        })
    
    return chunks

def save_output_files(text, segments, chunked_segments, output_paths):
    """Save all output files"""
    try:
        # Save raw JSON transcription
        with open(output_paths['transcription_json'], 'w', encoding='utf-8') as f:
            json.dump(segments, f, ensure_ascii=False, indent=2)
        
        # Save chunked JSON transcription
        with open(output_paths['chunked_json'], 'w', encoding='utf-8') as f:
            json.dump(chunked_segments, f, ensure_ascii=False, indent=2)
        
        # Save plain text transcription
        with open(output_paths['transcription_txt'], 'w', encoding='utf-8') as f:
            f.write(text)
        
        return True
    except Exception as e:
        print(f"Failed to save output files: {e}")
        return False

def process_video(video_path):
    """Complete processing pipeline"""
    start_time = time.time()
    
    # Create output folder structure
    output_paths = create_output_folder(video_path)
    print(f"Created output folder: {output_paths['base_dir']}")
    
    # Initialize model
    print("Initializing Whisper model...")
    processor, model = initialize_whisper()
    
    # Handle video and audio
    print("Processing video and audio...")
    if not copy_video_and_extract_audio(video_path, output_paths):
        return False
    
    # Transcribe
    print("Transcribing audio...")
    text, segments = transcribe_with_timestamps(output_paths['audio'], processor, model)
    if not text:
        return False
    
    # Apply smart chunking
    print("Processing chunks...")
    chunked_segments = smart_chunking(segments)
    
    # Save outputs
    print("Saving results...")
    if not save_output_files(text, segments, chunked_segments, output_paths):
        return False
    
    print("\n=== Processing complete ===")
    print(f"Total time: {time.time() - start_time:.2f} seconds")
    print("\nOutput files:")
    for key, path in output_paths.items():
        if key != 'base_dir':
            print(f"- {os.path.basename(path)}")
    
    # Print sample chunk
    print("\nSample chunk:")
    print(json.dumps(chunked_segments[0], indent=2, ensure_ascii=False))
    
    return True

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    
    records_dir = "./records"
    if not os.path.exists(records_dir):
        os.makedirs(records_dir)
    
    video_file = filedialog.askopenfilename(
        title="Выберите видеофайл для обработки",
        initialdir=records_dir,
        filetypes=(
            ("Видеофайлы", "*.mp4 *.avi *.mov *.mkv"), 
            ("Все файлы", "*.*")
        )
    )
    
    if not video_file:
        print("Файл не выбран. Выход из программы.")
        exit()
    
    print(f"Выбран файл: {video_file}")
    
    if process_video(video_file):
        print("\nВсе файлы сохранены в ./output/")
    else:
        print("\nОбработка не удалась - проверьте сообщения об ошибках выше")