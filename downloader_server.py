import os
import base64
import io
from PIL import Image # Requires: pip install pillow
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app) 

BASE_DIR = "./Downloaded_Raw_Chapters"

@app.route('/', methods=['GET'])
def health_check():
    return "OK", 200

@app.route('/save_page', methods=['POST'])
def save_page():
    try:
        data = request.json
        manga_title = data.get('manga', 'Unknown_Manga')
        chapter_title = data.get('chapter', 'Unknown_Chapter')
        filename_base = data.get('filename', 'page') 
        image_b64 = data.get('image_data', '')

        save_path = os.path.join(BASE_DIR, manga_title, chapter_title)
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        if image_b64:
            # 1. Clean header if present
            if ',' in image_b64:
                header, image_b64 = image_b64.split(',', 1)

            # 2. Decode bytes
            image_bytes = base64.b64decode(image_b64)
            
            # 3. Detect Extension using Pillow
            try:
                with Image.open(io.BytesIO(image_bytes)) as img:
                    extension = img.format.lower()
                    if extension == 'jpeg': 
                        extension = 'jpg'
            except Exception:
                # Fallback if Pillow can't read it (rare)
                extension = 'jpg'

            # 4. Construct Final Filename
            # Strip any existing extension from the browser, then add the real one
            clean_name = os.path.splitext(filename_base)[0]
            final_filename = f"{clean_name}.{extension}"
            
            # 5. Save
            full_path = os.path.join(save_path, final_filename)
            with open(full_path, 'wb') as f:
                f.write(image_bytes)
            
            print(f"✅ Saved: {chapter_title} / {final_filename}")
            return jsonify({"status": "success"}), 200
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    print("📡 Manga Listener V3 (Auto-Extension) running...")
    app.run(port=5000)