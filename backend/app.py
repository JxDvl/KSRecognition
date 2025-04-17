import os
import sys
import json
import tempfile
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Добавляем родительскую директорию в путь, чтобы иметь доступ к diploma_handle.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from diploma_handle import process_video, create_output_folder

app = Flask(__name__, static_folder='../output')
CORS(app)  # Разрешаем кросс-доменные запросы

# Конфигурация папок для загрузки файлов и выходных данных
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'records')
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'MOV', 'MP4', 'AVI', 'MKV'}  # Добавлен .MOV для совместимости со старыми проверками

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {ext.lower() for ext in ALLOWED_EXTENSIONS}

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Нет файла в запросе'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Нет выбранного файла'}), 400
    
    # Проверка расширения файла
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        try:
            # Обрабатываем видео с помощью нашего скрипта
            if process_video(filepath):
                # Получаем имя файла без расширения для поиска json-файла с субтитрами
                base_name = os.path.splitext(filename)[0]
                output_paths = create_output_folder(filepath)
                
                # Формируем ответ с путями к файлам
                response = {
                    'status': 'success',
                    'message': 'Файл успешно обработан',
                    'video': f'/api/files/{base_name}/{base_name}.mp4',
                    'subtitles': f'/api/files/{base_name}/{base_name}_chunked.json'
                }
                return jsonify(response), 200
            else:
                return jsonify({'error': 'Ошибка при обработке видео'}), 500
        except Exception as e:
            return jsonify({'error': f'Произошла ошибка: {str(e)}'}), 500
    
    return jsonify({'error': 'Недопустимый тип файла'}), 400

@app.route('/api/files/<folder>/<filename>', methods=['GET'])
def get_file(folder, filename):
    folder_path = os.path.join(OUTPUT_FOLDER, folder)
    return send_from_directory(folder_path, filename)

@app.route('/api/videos', methods=['GET'])
def list_videos():
    processed_videos = []
    
    # Проходим по всем папкам в OUTPUT_FOLDER
    for folder in os.listdir(OUTPUT_FOLDER):
        folder_path = os.path.join(OUTPUT_FOLDER, folder)
        if os.path.isdir(folder_path):
            # Проверяем наличие обработанных файлов
            mp4_file = os.path.join(folder_path, f"{folder}.mp4")
            json_file = os.path.join(folder_path, f"{folder}_chunked.json")
            
            if os.path.exists(mp4_file) and os.path.exists(json_file):
                processed_videos.append({
                    'name': folder,
                    'video': f'/api/files/{folder}/{folder}.mp4',
                    'subtitles': f'/api/files/{folder}/{folder}_chunked.json'
                })
    
    return jsonify(processed_videos), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 