import os
import re
import sys

# Try to import ebooklib. If missing, tell user.
try:
    from ebooklib import epub
except ImportError:
    print("❌ Error: You need to install ebooklib.")
    print("Run: pip install EbookLib")
    sys.exit()

# CONFIGURATION
ROOT_DIR = "./Downloaded_Manga"

def get_chapter_sort_key(folder_name):
    """Sorts chapters by the number found in their name."""
    match = re.search(r'Chapter_(\d+)(?:[_.](\d+))?', folder_name, re.IGNORECASE)
    if match:
        main_num = int(match.group(1))
        sub_num = int(match.group(2)) if match.group(2) else 0
        return main_num + (sub_num * 0.01)
    return 999999.0

def create_debug_epub():
    print(f"🔍 Looking for manga folders in: {os.path.abspath(ROOT_DIR)}")
    
    if not os.path.exists(ROOT_DIR):
        print(f"❌ Error: The directory '{ROOT_DIR}' does not exist.")
        print("   Make sure you created the 'Downloaded_Manga' folder.")
        return

    # 1. Gather Folders
    all_chapters = [d for d in os.listdir(ROOT_DIR) if os.path.isdir(os.path.join(ROOT_DIR, d))]
    
    if not all_chapters:
        print("❌ No chapter folders found inside Downloaded_Manga.")
        return

    # 2. Sort
    sorted_chapters = sorted(all_chapters, key=get_chapter_sort_key)
    print(f"✅ Found {len(sorted_chapters)} chapter folders.")

    # 3. Setup Book
    book_title = "Gachiakuta_Full" # Hardcoded for test, rename later if you want
    output_filename = f"./EPUB_Output/{book_title}.epub"
    
    book = epub.EpubBook()
    book.set_identifier('id_123456')
    book.set_title(book_title)
    book.set_language('en')

    spine = []
    toc_links = []
    global_image_count = 0

    print("\n🚀 Starting Compilation...")
    
    # 4. Iterate Chapters
    for chapter_folder in sorted_chapters:
        chapter_path = os.path.join(ROOT_DIR, chapter_folder)
        
        # LOGGING: Print what we are scanning
        # We look for .jpg, .jpeg, .png, .webp (case insensitive)
        images = [f for f in os.listdir(chapter_path) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
        
        # Natural Sort (Page_1, Page_2, Page_10)
        images.sort(key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0)

        if not images:
            print(f"⚠️  WARNING: Skipping '{chapter_folder}' - Found 0 images inside!")
            # DEBUG: List first 3 files found in this folder anyway, to see what's wrong
            try:
                files = os.listdir(chapter_path)[:3]
                print(f"      (Files found instead: {files})")
            except: pass
            continue
        
        print(f"   -> {chapter_folder} ... Found {len(images)} images.")

        clean_chapter_title = chapter_folder.split("___")[0].replace("_", " ")
        first_page_item = None

        for i, img_file in enumerate(images):
            global_image_count += 1
            full_img_path = os.path.join(chapter_path, img_file)
            
            # Read Data
            with open(full_img_path, 'rb') as f:
                img_data = f.read()

            # Determine Media Type explicitly
            ext = os.path.splitext(img_file)[1].lower()
            media_type = 'image/jpeg'
            if ext == '.png': media_type = 'image/png'
            elif ext == '.webp': media_type = 'image/webp'

            # Define internal path
            internal_img_name = f"img_{global_image_count:06d}{ext}"
            
            # Create Image Item
            epub_img = epub.EpubImage()
            epub_img.file_name = f"images/{internal_img_name}"
            epub_img.media_type = media_type
            epub_img.content = img_data
            book.add_item(epub_img)

            # Create Page HTML
            page_file_name = f"page_{global_image_count:06d}.xhtml"
            epub_html = epub.EpubHtml(title=clean_chapter_title, file_name=page_file_name)
            epub_html.content = f'''
                <html>
                    <body style="margin:0;padding:0;text-align:center;background-color:#000;">
                        <img src="images/{internal_img_name}" alt="page" style="height:100%; object-fit:contain;" />
                    </body>
                </html>
            '''
            book.add_item(epub_html)
            spine.append(epub_html)

            if i == 0:
                first_page_item = epub_html

        if first_page_item:
            toc_links.append(epub.Link(first_page_item.file_name, clean_chapter_title, clean_chapter_title))

    # 5. Final Save
    if global_image_count == 0:
        print("\n❌ FAILED: No images were added to the book. Check the logs above.")
    else:
        book.toc = toc_links
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ['nav'] + spine

        print(f"\n💾 Writing EPUB file with {global_image_count} pages... (Wait for it)")
        epub.write_epub(output_filename, book, {})
        print(f"✅ SUCCESS! Created '{output_filename}'")

if __name__ == "__main__":
    create_debug_epub()