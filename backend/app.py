import os
import sys
import json
import tempfile
import threading
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from diploma_handle import process_video, create_output_folder

app = Flask(__name__, static_folder='output')
CORS(app)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'records')
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'MOV', 'MP4', 'AVI', 'MKV'}

processing_status = {
    'is_processing': False,
    'current_file': None,
    'progress': 0,
    'current_stage': '',
    'estimated_time': 0,
    'partial_subtitles': []
}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

print("Проверка структуры выходных файлов:")
print(f"UPLOAD_FOLDER: {UPLOAD_FOLDER} - {'✓' if os.path.exists(UPLOAD_FOLDER) else '✗'}")
print(f"OUTPUT_FOLDER: {OUTPUT_FOLDER} - {'✓' if os.path.exists(OUTPUT_FOLDER) else '✗'}")

if os.path.exists(OUTPUT_FOLDER):
    output_subfolders = [f for f in os.listdir(OUTPUT_FOLDER) if os.path.isdir(os.path.join(OUTPUT_FOLDER, f))]
    print(f"Количество обработанных видео: {len(output_subfolders)}")
    
    for folder in output_subfolders:
        folder_path = os.path.join(OUTPUT_FOLDER, folder)
        video_file = os.path.join(folder_path, f"{folder}.mp4")
        json_file = os.path.join(folder_path, f"{folder}_chunked.json")
        
        print(f"Проверка файлов для {folder}:")
        print(f"  Видео: {os.path.exists(video_file)}")
        print(f"  Субтитры: {os.path.exists(json_file)}")

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {ext.lower() for ext in ALLOWED_EXTENSIONS}

def process_video_async(filepath, filename):
    """Асинхронная обработка видео в отдельном потоке"""
    global processing_status
    
    try:
        if not os.path.exists(filepath):
            print(f"ОШИБКА: Исходный файл не найден: {filepath}")
            processing_status['is_processing'] = False
            processing_status['current_stage'] = 'Ошибка: файл не найден'
            processing_status['progress'] = 0
            return
        
        print(f"Начало обработки файла: {filepath}")
        print(f"Размер файла: {os.path.getsize(filepath) / (1024 * 1024):.2f} MB")
        
        base_name = os.path.splitext(filename)[0]
        expected_output_dir = os.path.join(OUTPUT_FOLDER, base_name)
        expected_video = os.path.join(expected_output_dir, f"{base_name}.mp4")
        expected_json = os.path.join(expected_output_dir, f"{base_name}_chunked.json")
        
        print(f"Ожидаемый выходной каталог: {expected_output_dir}")
        print(f"Ожидаемое видео: {expected_video}")
        print(f"Ожидаемые субтитры: {expected_json}")
        
        if process_video(filepath, processing_status):
            base_name = os.path.splitext(filename)[0]
            
            output_dir = os.path.join(OUTPUT_FOLDER, base_name)
            output_video = os.path.join(output_dir, f"{base_name}.mp4")
            output_json = os.path.join(output_dir, f"{base_name}_chunked.json")
            
            print(f"Проверка созданных файлов:")
            print(f"Выходной каталог: {output_dir} - {'✓' if os.path.exists(output_dir) else '✗'}")
            print(f"Видео: {output_video} - {'✓' if os.path.exists(output_video) else '✗'}")
            print(f"Субтитры: {output_json} - {'✓' if os.path.exists(output_json) else '✗'}")
            
            processing_status = {
                'is_processing': False,
                'current_file': filename,
                'progress': 100,
                'current_stage': 'Обработка завершена',
                'estimated_time': 0,
                'partial_subtitles': [],
                'video': f'/api/files/{base_name}/{base_name}.mp4',
                'subtitles': f'/api/files/{base_name}/{base_name}_chunked.json'
            }
            print(f"Обработка завершена успешно. Файлы доступны по путям:")
            print(f"Видео: {processing_status['video']}")
            print(f"Субтитры: {processing_status['subtitles']}")
        else:
            processing_status['is_processing'] = False
            processing_status['current_stage'] = 'Обработка не удалась'
            processing_status['progress'] = 0
            print("Обработка видео не удалась.")
    except Exception as e:
        processing_status['is_processing'] = False
        processing_status['current_stage'] = f'Ошибка: {str(e)}'
        processing_status['progress'] = 0
        print(f"Обработка видео завершилась с ошибкой: {e}")
        import traceback
        traceback.print_exc()

@app.route('/api/upload', methods=['POST'])
def upload_file():
    global processing_status
    
    if 'file' not in request.files:
        return jsonify({'error': 'Нет файла в запросе'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Нет выбранного файла'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        processing_status = {
            'is_processing': True,
            'current_file': filename,
            'progress': 0,
            'current_stage': 'Инициализация обработки видео',
            'estimated_time': 0,
            'partial_subtitles': []
        }
        
        base_name = os.path.splitext(filename)[0]
        
        try:
            processing_thread = threading.Thread(
                target=process_video_async,
                args=(filepath, filename)
            )
            processing_thread.daemon = True
            processing_thread.start()
            
            response = {
                'status': 'processing',
                'message': 'Обработка видео запущена',
                'filename': filename,
                'progress_url': '/api/progress'
            }
            return jsonify(response), 202
            
        except Exception as e:
            processing_status['is_processing'] = False
            return jsonify({'error': f'Произошла ошибка при запуске обработки: {str(e)}'}), 500
    
    return jsonify({'error': 'Недопустимый тип файла'}), 400

@app.route('/api/files/<folder>/<filename>', methods=['GET'])
def get_file(folder, filename):
    folder_path = os.path.join(OUTPUT_FOLDER, folder)
    file_path = os.path.join(folder_path, filename)
    
    print(f"Запрос файла: {file_path}")
    if os.path.exists(file_path):
        print(f"Файл найден: {file_path}")
    else:
        print(f"ОШИБКА: Файл не найден: {file_path}")
        print(f"Содержимое папки {folder_path}:")
        if os.path.exists(folder_path):
            for f in os.listdir(folder_path):
                print(f"- {f}")
        else:
            print(f"Папка {folder_path} не существует")
    
    return send_from_directory(folder_path, filename)

@app.route('/api/videos', methods=['GET'])
def list_videos():
    processed_videos = []
    
    for folder in os.listdir(OUTPUT_FOLDER):
        folder_path = os.path.join(OUTPUT_FOLDER, folder)
        if os.path.isdir(folder_path):
            mp4_file = os.path.join(folder_path, f"{folder}.mp4")
            json_file = os.path.join(folder_path, f"{folder}_chunked.json")
            
            print(f"Проверка файлов в папке {folder}:")
            print(f"- Видео: {mp4_file} - {'✓' if os.path.exists(mp4_file) else '✗'}")
            print(f"- Субтитры: {json_file} - {'✓' if os.path.exists(json_file) else '✗'}")
            
            if os.path.exists(mp4_file) and os.path.exists(json_file):
                processed_videos.append({
                    'name': folder,
                    'video': f'/api/files/{folder}/{folder}.mp4',
                    'subtitles': f'/api/files/{folder}/{folder}_chunked.json'
                })
    
    return jsonify(processed_videos), 200

@app.route('/api/progress', methods=['GET'])
def check_progress():
    global processing_status
    
    if (not processing_status['is_processing'] and 
        processing_status['progress'] == 100 and
        processing_status['current_file']):
        
        base_name = os.path.splitext(processing_status['current_file'])[0]
        processed_response = {
            'is_processing': False,
            'progress': 100,
            'current_stage': 'Обработка завершена',
            'video': f'/api/files/{base_name}/{base_name}.mp4',
            'subtitles': f'/api/files/{base_name}/{base_name}_chunked.json'
        }
        return jsonify(processed_response), 200
    
    return jsonify(processing_status), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 