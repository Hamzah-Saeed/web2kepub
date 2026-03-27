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
import time

TEMP_DIR = Path("temp")
TEMP_DIR.mkdir(exist_ok=True)

def get_driver(headless=False): ## this line makes a popup chrome, for my use case it is required.
    options = Options()

    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--incognito")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")


    driver = webdriver.Chrome(options=options)
    return driver

def fetch_page(url: str) -> str:
    driver = get_driver(headless=False)  # keep False for reliability

    driver.get(url)

    wait = WebDriverWait(driver, 20)

    # Wait until actual text appears inside the chapter
    def content_loaded(d):
        try:
            el = d.find_element(By.CSS_SELECTOR, ".chapter-container") ##Class might vary by sight
            return el if el.text.strip() != "" else False ##Checks if there is actual content
        except:
            return False

    content_div = wait.until(content_loaded) 

    # Remove ads + junk using JS before grabbing HTML from the site im using
    driver.execute_script("""
        document.querySelectorAll('.chapter-ad-container').forEach(el => el.remove());
        document.querySelectorAll('style').forEach(el => el.remove());
        document.querySelectorAll('script').forEach(el => el.remove());
    """)

    html_content = content_div.get_attribute("outerHTML")

    driver.quit()
    return html_content

def url_to_kepub(url: str) -> Path:
    job_id = str(uuid.uuid4())

    epub_path = TEMP_DIR / f"{job_id}.epub"
    kepub_path = TEMP_DIR / f"{job_id}.kepub.epub"

    html = fetch_page(url)
    soup = BeautifulSoup(html, "html.parser")

    # Extract only paragraphs
    paragraphs = soup.find_all("p")
    clean_html = "".join(str(p) for p in paragraphs)

    #This does not have error checking, might add in the future
    title_tag = soup.find("a", class_="novel-title")
    title = title_tag.get_text(strip=True)
    chapter_tag = soup.find("h1", class_="chapter-title")
    chapterTitle = chapter_tag.get_text(strip=True)

    #Build EPUB
    book = epub.EpubBook()
    book.set_identifier(job_id)
    book.set_title(title)
    book.set_language("en")

    chapter = epub.EpubHtml(
        title=chapterTitle,
        file_name="chap_01.xhtml",
        content=clean_html
    )

    book.add_item(chapter)
    book.toc = [chapter]
    book.spine = ["nav", chapter]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    epub.write_epub(epub_path, book)

    # 4. Convert → KEPUB
    subprocess.run([
        "/Applications/calibre.app/Contents/MacOS/ebook-convert",
        str(epub_path),
        str(kepub_path),
        "--output-profile=kobo"
    ], check=True)

    return kepub_path