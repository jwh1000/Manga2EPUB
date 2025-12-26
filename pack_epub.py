import os
import re
import sys

try:
    from ebooklib import epub
except ImportError:
    print("❌ Error: You need to install ebooklib.")
    print("Run: pip install EbookLib")
    sys.exit()

ROOT_DIR = "./Downloaded_Raw_Chapters"

def get_chapter_sort_key(folder_name):
    """Sorts chapters by the number found in their name."""
    match = re.search(r'Chapter_(\d+)(?:[_.](\d+))?', folder_name, re.IGNORECASE)
    if match:
        main_num = int(match.group(1))
        sub_num = int(match.group(2)) if match.group(2) else 0
        return main_num + (sub_num * 0.01)
    return 999999.0

def find_images_recursively(directory):
    """Walks through all subfolders to find images anywhere inside."""
    valid_images = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                full_path = os.path.join(root, file)
                valid_images.append(full_path)
    return valid_images

def create_deep_epub():
    print(f"🔍 scanning in: {os.path.abspath(ROOT_DIR)}")
    
    if not os.path.exists(ROOT_DIR):
        print("❌ Error: Downloaded_Manga folder not found.")
        return

    # 1. Gather Chapter Folders
    all_chapters = [d for d in os.listdir(ROOT_DIR) if os.path.isdir(os.path.join(ROOT_DIR, d))]
    
    if not all_chapters:
        print("❌ No chapter folders found.")
        return

    # 2. Sort Chapters
    sorted_chapters = sorted(all_chapters, key=get_chapter_sort_key)
    print(f"✅ Found {len(sorted_chapters)} chapter folders.")

    # 3. Setup Book
    book_title = input("Enter Manga Title: ") or "Manga_Compilation"

    safe_title = re.sub(r'[<>:\"/\\|?*]', '_', book_title).strip()
    output_filename = f"./EPUB_Output/{safe_title}.epub"
    output_dir = os.path.dirname(output_filename)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print(f"🔧 Created output directory: {os.path.abspath(output_dir)}")
    
    book = epub.EpubBook()
    book.set_identifier('id_123456')
    book.set_title(book_title)
    book.set_language('en')

    spine = []
    toc_links = []
    global_image_count = 0

    print("\n🚀 Starting Compilation...")
    
    for chapter_folder in sorted_chapters:
        chapter_path = os.path.join(ROOT_DIR, chapter_folder)
        
        images_paths = find_images_recursively(chapter_path)
        
        images_paths.sort(key=lambda x: int(re.search(r'\d+', os.path.basename(x)).group()) if re.search(r'\d+', os.path.basename(x)) else 0)

        if not images_paths:
            print(f"⚠️  WARNING: Still found 0 images in '{chapter_folder}' (checked subfolders).")
            continue
        
        clean_chapter_title = chapter_folder.split("___")[0].replace("_", " ")
        print(f"   -> {clean_chapter_title} ... Found {len(images_paths)} images.")

        first_page_item = None

        for i, full_img_path in enumerate(images_paths):
            global_image_count += 1
            
            with open(full_img_path, 'rb') as f:
                img_data = f.read()

            ext = os.path.splitext(full_img_path)[1].lower()
            media_type = 'image/webp' if ext == '.webp' else 'image/jpeg'

            internal_img_name = f"img_{global_image_count:06d}{ext}"
            
            epub_img = epub.EpubImage()
            epub_img.file_name = f"images/{internal_img_name}"
            epub_img.media_type = media_type
            epub_img.content = img_data
            book.add_item(epub_img)

            page_file_name = f"page_{global_image_count:06d}.xhtml"
            epub_html = epub.EpubHtml(title=clean_chapter_title, file_name=page_file_name)
            epub_html.content = f'''
                <html>
                    <body style="margin:0;padding:0;text-align:center;background-color:#000;">
                        <img src="images/{internal_img_name}" style="height:100%; object-fit:contain;" />
                    </body>
                </html>
            '''
            book.add_item(epub_html)
            spine.append(epub_html)

            if i == 0:
                first_page_item = epub_html

        if first_page_item:
            toc_links.append(epub.Link(first_page_item.file_name, clean_chapter_title, clean_chapter_title))

    if global_image_count == 0:
        print("\n❌ FAILED: No images found.")
    else:
        book.toc = toc_links
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ['nav'] + spine

        print(f"\n💾 Writing EPUB ({global_image_count} pages)...")
        try:
            epub.write_epub(output_filename, book, {})
        except Exception as e:
            print(f"❌ FAILED to write EPUB: {e}")
            return
        abs_out = os.path.abspath(output_filename)
        if os.path.exists(abs_out):
            print(f"✅ SUCCESS! Created '{abs_out}'")
        else:
            print(f"⚠️  Warning: write_epub completed but '{abs_out}' not found. Check permissions and EbookLib version.")

if __name__ == "__main__":
    create_deep_epub()