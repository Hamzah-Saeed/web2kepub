import uuid
from pathlib import Path
from bs4 import BeautifulSoup
from ebooklib import epub
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import time

TEMP_DIR = Path("temp")
TEMP_DIR.mkdir(exist_ok=True)

def get_driver(headless=False): #makes a popup chrome, for my use case it is required.
    options = Options()

    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--incognito")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")


    driver = webdriver.Chrome(options=options)
    return driver

def get_chapter_list(driver, url):
    driver.get(url)

    wait = WebDriverWait(driver, 20)

    # Wait for dropdown to exist
    select = wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, "novel-info"))
    )

    option = select.find_element(By.CLASS_NAME, "stat-value")

    chapter = int(option.text.strip())

    return chapter

def fetch_page(driver, url: str) -> str:
    driver.get(url)

    wait = WebDriverWait(driver, 20)

    # Wait until actual text appears inside the chapter
    def content_loaded(d):
        try:
            el = d.find_element(By.CLASS_NAME, "chapter-container") ##Class might vary by site
            return el if el.text.strip() != "" else False ##Checks if there is actual content
        except:
            return False

    content_div = wait.until(content_loaded) 
    time.sleep(random.uniform(2, 5)) #mimics reading

    # Remove ads + junk using JS before grabbing HTML from the site im using
    driver.execute_script("""
        document.querySelectorAll('.chapter-ad-container').forEach(el => el.remove());
        document.querySelectorAll('style').forEach(el => el.remove());
        document.querySelectorAll('script').forEach(el => el.remove());
    """)

    html_content = content_div.get_attribute("outerHTML")

    return html_content

def fetch_single_chapter(driver, base_url, ch):


    url = f"{base_url}chapter/{ch}/"
    time.sleep(random.uniform(1, 3)) #Delay to prevent getting rate limited, modify if too slow 
    html = fetch_page(driver, url)
    soup = BeautifulSoup(html, "html.parser")

    novel_title = soup.find("a", class_="novel-title").get_text(strip=True)
    chapter_title = soup.find("h1", class_="chapter-title").get_text(strip=True)

    paragraphs = soup.find_all("p")
    clean_html = "".join(str(p) for p in paragraphs)

    return {
        "chapter_num": int(ch),
        "novel_title": novel_title,
        "chapter_title": chapter_title,
        "content": clean_html
    }

def fetch_all_chapters(driver, base_url, chapters):
    results = []

    for ch in chapters:
        try:
            result = fetch_single_chapter(driver, base_url, ch)
            results.append(result)
            print(f"✅ Finished chapter {ch}")
        except Exception as e:
            print(f"❌ Failed chapter {ch}: {e}")

    return results

def build_epub(chapter_data, job_id):
    epub_path = TEMP_DIR / f"{job_id}.epub"

    book = epub.EpubBook()
    book.set_identifier(job_id)
    book.set_title(chapter_data[0]["novel_title"])
    book.set_language("en")

    epub_chapters = []

    for i, ch in enumerate(chapter_data):
        file_name = f"chap_{i+1}.xhtml"

        chapter_html = f"<h2>{ch['chapter_title']}</h2>" + ch["content"]

        epub_chapter = epub.EpubHtml(
            title=ch["chapter_title"],
            file_name=file_name,
            content=chapter_html
        )

        book.add_item(epub_chapter)
        epub_chapters.append(epub_chapter)

    # Table of Contents
    book.toc = epub_chapters

    # Reading order
    book.spine = ["nav"] + epub_chapters

    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    epub.write_epub(epub_path, book)

    return epub_path

def url_to_kepub(url: str) -> Path:
    job_id = str(uuid.uuid4())
    driver = get_driver(headless=False)
    try:
        total_chapters = get_chapter_list(driver, url)
        chapters = range(1, total_chapters+1)
        chapter_data = fetch_all_chapters(driver, url, chapters)
    finally:
        driver.quit()

    epub_path = build_epub(chapter_data, job_id)
    kepub_path = TEMP_DIR / f"{job_id}.kepub.epub"

    # Convert --> KEPUB, ensure the path is correct.
    subprocess.run([
        "/Applications/calibre.app/Contents/MacOS/ebook-convert",
        str(epub_path),
        str(kepub_path),
        "--output-profile=kobo"
    ], check=True)

    return kepub_path