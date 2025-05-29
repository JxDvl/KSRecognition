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
   base_name = os.path.splitext(os.path.basename(video_path))[0]
   backend_dir = os.path.dirname(os.path.abspath(__file__))
   if not os.path.basename(backend_dir) == 'backend':
       backend_dir = os.path.join(backend_dir, 'backend')
   output_dir = os.path.join(backend_dir, 'output', base_name)
   
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
    try:
        # # Пока закомментируем загрузку локальной модели для теста
        # model_path = "/Users/maru/Desktop/My Projects/University/Diploma/1400-1400 step"
        # print("Загрузка локальной модели Whisper...")
        # processor = WhisperProcessor.from_pretrained(model_path)
        # model = WhisperForConditionalGeneration.from_pretrained(model_path)
        # model.config.forced_decoder_ids = None
        # model.generation_config.forced_decoder_ids = None
        # model.generation_config.language = "kazakh"
        # model.generation_config.task = "transcribe"
        # device = "cuda" if torch.cuda.is_available() else "cpu"
        # print(f"Используется устройство: {device}")
        # return processor, model.to(device)
        
        # Принудительно вызываем исключение, чтобы загрузить стандартную модель
        print("Принудительное использование стандартной модели Whisper для диагностики...")
        raise Exception("Force fallback to standard model for testing")

    except Exception as e:
        print(f"Ошибка при инициализации локальной модели (или принудительный переход): {e}")
        # import traceback
        # traceback.print_exc() # Можно раскомментировать для детальной ошибки, если она будет не из-за принуждения
        
        print("Использую стандартную модель Whisper (openai/whisper-medium)...")
        model_name = "openai/whisper-medium"
        try:
            processor = WhisperProcessor.from_pretrained(model_name)
            model = WhisperForConditionalGeneration.from_pretrained(model_name)
        except Exception as model_load_err:
            print(f"КРИТИЧЕСКАЯ ОШИБКА: Не удалось загрузить даже стандартную модель {model_name}: {model_load_err}")
            print("Убедитесь, что есть интернет-соединение и модель доступна в Hugging Face.")
            return None, None # Возвращаем None, чтобы обработка прервалась корректно
            
        model.config.forced_decoder_ids = None
        model.generation_config.forced_decoder_ids = None
        model.generation_config.language = "kazakh" # Указываем язык для стандартной модели
        model.generation_config.task = "transcribe"
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Стандартная модель будет использовать устройство: {device}")
        return processor, model.to(device)
 
def copy_video_and_extract_audio(video_path, output_paths, status=None):
   try:
       if status:
           status['progress'] = 5
           status['current_stage'] = 'Копирование видео и извлечение аудио'
           status['estimated_time'] = 60
       
       shutil.copy2(video_path, output_paths['video'])
       
       if status:
           status['progress'] = 10
       
       with mp.VideoFileClip(video_path) as video:
           video.audio.write_audiofile(
               output_paths['audio'],
               fps=16000,
               codec='pcm_s16le',
               verbose=False
           )
           
       if status:
           status['progress'] = 20
           
       return True
   except Exception as e:
       print(f"Video/audio processing failed: {e}")
       return False
 
def transcribe_with_timestamps(audio_path, processor, model, status=None):
    """Efficient transcription with JSON-ready output, используя result['chunks']"""
    try:
        if status:
            status['progress'] = 25
            status['current_stage'] = 'Загрузка аудио для транскрибации'
            status['estimated_time'] = 120
            print("Начало транскрибации...")
        
        audio = librosa.load(audio_path, sr=16000)[0].astype(np.float32)
        audio_duration = len(audio) / 16000  # в секундах
        print(f"Загружено аудио длительностью {audio_duration:.1f} секунд")
        
        segment_duration = 15  # Вернем 15 секунд, т.к. будем полагаться на чанки модели
        segments = []
        
        for start_time in range(0, int(audio_duration), segment_duration):
            try:
                end_time = min(start_time + segment_duration, audio_duration)
                segment_start_sample = start_time * 16000
                segment_end_sample = int(end_time * 16000)
                audio_segment = audio[segment_start_sample:segment_end_sample]
                
                if status:
                    status['progress'] = 30 + int((start_time / audio_duration) * 40)
                    status['current_stage'] = f'Обработка сегментов'
                    print(f"Обработка сегмента {start_time}-{end_time} секунд")
                
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                input_features = processor(
                    audio_segment, 
                    sampling_rate=16000, 
                    return_tensors="pt"
                ).input_features.to(model.device)
                
                outputs = model.generate(
                    input_features,
                    max_length=448,
                    return_timestamps=True,
                    language="kazakh",
                    task="transcribe",
                    num_beams=3,          # Увеличили num_beams
                    temperature=0.2,      # Уменьшили temperature
                    # no_repeat_ngram_size=3, # Пока закомментируем
                    length_penalty=1.0,
                    repetition_penalty=1.0
                )
                
                result = processor.batch_decode(outputs, output_offsets=True)[0]
                print(f"Результат декодирования сегмента {start_time}-{end_time}: {result}")
                
                if 'chunks' in result and result['chunks']:
                    print(f"Найдено {len(result['chunks'])} чанков в сегменте")
                    for chunk in result['chunks']:
                        # Временные метки чанка относительны начала аудио_сегмента
                        chunk_start_relative = float(chunk['timestamp'][0])
                        chunk_end_relative = float(chunk['timestamp'][1] if chunk['timestamp'][1] else chunk['timestamp'][0] + 1.0)
                        
                        # Пересчитываем в абсолютные временные метки относительно всего аудио
                        chunk_start_absolute = chunk_start_relative + start_time
                        chunk_end_absolute = chunk_end_relative + start_time
                        
                        # Ограничиваем концом аудиофайла
                        chunk_end_absolute = min(chunk_end_absolute, audio_duration)

                        if chunk_start_absolute < chunk_end_absolute: # Убедимся, что чанк имеет длительность
                            segments.append({
                                "id": len(segments),
                                "start": round(chunk_start_absolute, 2),
                                "end": round(chunk_end_absolute, 2),
                                "text": chunk['text'].strip()
                            })
                            print(f"Добавлен чанк: [{round(chunk_start_absolute,2)}-{round(chunk_end_absolute,2)}] {chunk['text'].strip()}")
                elif 'text' in result and result['text'].strip(): # Если чанков нет, но есть общий текст
                    print(f"Чанки не найдены, используем полный текст сегмента: {result['text']}")
                    segments.append({
                        "id": len(segments),
                        "start": round(start_time, 2),
                        "end": round(end_time, 2),
                        "text": result['text'].strip()
                    })
                else:
                    print(f"В сегменте {start_time}-{end_time} не найдено ни чанков, ни текста.")

                del input_features
                del outputs
                del result
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
            except Exception as e:
                print(f"Ошибка при обработке сегмента {start_time}-{end_time}: {e}")
                import traceback
                traceback.print_exc() # Более подробный вывод ошибки
                continue
        
        if not segments:
            print("Не удалось получить ни одного сегмента после полной обработки")
            return None, None
        
        segments.sort(key=lambda x: x['start'])
        
        # Логика объединения близких сегментов (если потребуется, пока оставим простой список чанков)
        # merged_segments = []
        # current_segment = None
        # for segment in segments:
        #     if not current_segment:
        #         current_segment = segment
        #     else:
        #         if (segment['start'] - current_segment['end'] < 1.0 and 
        #             segment['end'] - current_segment['start'] < 10.0): # Макс. длина объединенного сегмента 10 сек
        #             current_segment['end'] = segment['end']
        #             current_segment['text'] = current_segment['text'] + " " + segment['text']
        #         else:
        #             merged_segments.append(current_segment)
        #             current_segment = segment
        # if current_segment:
        #     merged_segments.append(current_segment)
        # final_segments = merged_segments

        final_segments = segments # Пока используем直接 чанки

        if status:
            status['progress'] = 70
            status['current_stage'] = 'Обработка сегментов завершена (используя чанки модели)'
            status['partial_subtitles'] = final_segments
            print(f"Всего получено {len(final_segments)} чанков после обработки")
        
        full_text = " ".join(segment['text'] for segment in final_segments if segment['text'])
        
        return full_text, final_segments
    
    except Exception as e:
        print(f"Критическая ошибка транскрибации: {e}")
        import traceback
        traceback.print_exc()
        return None, None
 
def smart_chunking(segments, max_duration=8.0, max_sentences=3, status=None):
   """Hybrid approach combining sentence structure and duration limits"""
   if status:
       status['progress'] = 70
       status['current_stage'] = 'Создание умных чанков'
       status['estimated_time'] = 30
   
   chunks = []
   current_chunk = []
   
   total_segments = len(segments)
   processed_sentences = 0
   total_sentences = sum(len(re.split(r'(?<=[.!?])\s+', seg['text'])) for seg in segments)
   
   for i, seg in enumerate(segments):
       if status:
           segment_progress = min(15, 15 * (i / total_segments))
           status['progress'] = 70 + segment_progress
           status['current_stage'] = f'Создание умных чанков (сегмент {i+1}/{total_segments})'
       
       sentences = re.split(r'(?<=[.!?])\s+', seg['text'])
       time_per_char = (seg['end'] - seg['start']) / len(seg['text']) if seg['text'] else 0
       
       for j, sentence in enumerate(sentences):
           processed_sentences += 1
           
           if not sentence:
               continue
               
           sentence_start = seg['start'] + (time_per_char * seg['text'].find(sentence))
           sentence_end = sentence_start + (time_per_char * len(sentence))
           
           sentence_data = {
               "text": sentence,
               "start": round(float(sentence_start), 2),
               "end": round(float(sentence_end), 2)
           }
           
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
               
               if status:
                   sentence_progress = min(20, 20 * (processed_sentences / total_sentences))
                   status['progress'] = 70 + sentence_progress
                   status['partial_subtitles'] = chunks
                   status['current_stage'] = f'Создание умных чанков ({len(chunks)} чанков создано)'
               
               current_chunk = []
               
           current_chunk.append(sentence_data)
   
   if current_chunk:
       chunks.append({
           "id": len(chunks),
           "start": current_chunk[0]['start'],
           "end": current_chunk[-1]['end'],
           "text": " ".join(s['text'] for s in current_chunk)
       })
   
   if status:
       status['progress'] = 90
       status['current_stage'] = f'Умные чанки созданы ({len(chunks)} чанков)'
       status['partial_subtitles'] = chunks
   
   return chunks
 
def save_output_files(text, segments, chunked_segments, output_paths, status=None):
   try:
       if status:
           status['progress'] = 95
           status['current_stage'] = 'Сохранение результатов обработки'
           status['estimated_time'] = 5
       
       if status:
           status['current_stage'] = 'Сохранение исходных субтитров в JSON'
       
       with open(output_paths['transcription_json'], 'w', encoding='utf-8') as f:
           json.dump(segments, f, ensure_ascii=False, indent=2)
       
       if status:
           status['progress'] = 97
           status['current_stage'] = 'Сохранение умных чанков в JSON'
       
       with open(output_paths['chunked_json'], 'w', encoding='utf-8') as f:
           json.dump(chunked_segments, f, ensure_ascii=False, indent=2)
       
       if status:
           status['progress'] = 99
           status['current_stage'] = 'Сохранение текстовой транскрипции'
       
       with open(output_paths['transcription_txt'], 'w', encoding='utf-8') as f:
           f.write(text)
       
       if status:
           status['progress'] = 100
           status['current_stage'] = f'Обработка завершена, создано {len(chunked_segments)} субтитров'
           status['estimated_time'] = 0
       
       return True
   except Exception as e:
       if status:
           status['current_stage'] = f'Ошибка при сохранении: {str(e)}'
       
       print(f"Failed to save output files: {e}")
       return False
 
def process_video(video_path, status=None):
   start_time = time.time()
   
   try:
       output_paths = create_output_folder(video_path)
       print(f"Created output folder: {output_paths['base_dir']}")
       
       if status:
           video_size_mb = os.path.getsize(video_path) / (1024 * 1024)
           estimated_total_time = max(60, int(video_size_mb * 0.5))
           status['estimated_time'] = estimated_total_time
           status['current_stage'] = f'Инициализация обработки видео ({video_size_mb:.1f} MB)'
       
       print("Initializing Whisper model...")
       if status:
           status['progress'] = 2
           status['current_stage'] = 'Инициализация модели Whisper'
           status['estimated_time'] = 10
       
       processor, model = initialize_whisper()
       
       if status:
           elapsed_time = time.time() - start_time
           status['progress'] = 5
           status['current_stage'] = f'Модель Whisper инициализирована за {elapsed_time:.1f} сек'
       
       print("Processing video and audio...")
       if not copy_video_and_extract_audio(video_path, output_paths, status):
           return False
       
       if status:
           elapsed_time = time.time() - start_time
           remaining_percent = 100 - status['progress']
           if status['progress'] > 0:
               new_estimate = int((elapsed_time / status['progress']) * remaining_percent)
               status['estimated_time'] = max(10, new_estimate)
       
       print("Transcribing audio...")
       text, segments = transcribe_with_timestamps(output_paths['audio'], processor, model, status)
       if not text:
           return False
       
       if status:
           elapsed_time = time.time() - start_time
           remaining_percent = 100 - status['progress']
           if status['progress'] > 0:
               new_estimate = int((elapsed_time / status['progress']) * remaining_percent)
               status['estimated_time'] = max(5, new_estimate)
       
       print("Processing chunks...")
       chunked_segments = smart_chunking(segments, status=status)
       
       print("Saving results...")
       if not save_output_files(text, segments, chunked_segments, output_paths, status):
           return False
       
       if status:
           total_time = time.time() - start_time
           status['progress'] = 100
           status['current_stage'] = f'Обработка завершена за {total_time:.1f} секунд'
           status['estimated_time'] = 0
       
       print("\n=== Processing complete ===")
       print(f"Total time: {time.time() - start_time:.2f} seconds")
       print("\nOutput files:")
       for key, path in output_paths.items():
           if key != 'base_dir':
               print(f"- {os.path.basename(path)}")
       
       print("\nSample chunk:")
       print(json.dumps(chunked_segments[0], indent=2, ensure_ascii=False))
       
       return True
       
   except Exception as e:
       if status:
           status['is_processing'] = False
           status['current_stage'] = f'Ошибка: {str(e)}'
           status['progress'] = 0
       
       print(f"Processing failed: {e}")
       import traceback
       traceback.print_exc()
       return False
 
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