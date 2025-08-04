from nicegui import ui
import requests
import os
import mimetypes

# Backend URL
BASE_URL = "http://65.1.248.169:8000"

# API helper functions
def fetch_all_books(min_rating="0"):
    try:
        res = requests.get(f"{BASE_URL}/books", params={"min_rating": min_rating})
        return res.json()
    except Exception:
        return []

def fetch_book_by_title(title):
    try:
        res = requests.get(f"{BASE_URL}/books/{title}")
        return res.json()
    except Exception:
        return None

def add_book(book):
    try:
        res = requests.post(f"{BASE_URL}/books", json=book)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

def add_review(title, review):
    try:
        res = requests.post(f"{BASE_URL}/books/{title}/review", json={"review": review})
        return res.json()
    except Exception as e:
        return {"error": str(e)}

def get_upload_url(filename):
    try:
        res = requests.get(f"{BASE_URL}/s3/upload-url", params={"filename": filename})
        return res.json()
    except:
        return {"error": "Failed to get pre-signed URL"}

# UI
ui.label("📚 Book Review Portal").classes("text-3xl mt-6 mb-4")

with ui.card().classes("w-full max-w-2xl"):
    ui.label("➕ Add a New Book").classes("text-xl mb-2")
    title_input = ui.input("Title").classes("w-full")
    author_input = ui.input("Author").classes("w-full")
    description_input = ui.textarea("Description").classes("w-full")
    rating_input = ui.input("Rating (1–5)").props("type=number min=1 max=5 step=0.5").classes("w-full")
    cover_filename_input = ui.input("Local Cover Image Filename (e.g. cover1.jpg)").classes("w-full")

    add_result_label = ui.label().classes("text-green-600 mt-1")

    def handle_add_book():
        filename = cover_filename_input.value.strip()
        cover_url = ""

        # Upload image to S3
        if filename:
            upload_info = get_upload_url(filename)
            if "upload_url" in upload_info:
                try:
                    mime_type, _ = mimetypes.guess_type(filename)
                    with open(filename, 'rb') as f:
                        requests.put(upload_info['upload_url'], data=f, headers={"Content-Type": mime_type or "image/jpeg"})
                    cover_url = upload_info['file_url']
                except FileNotFoundError:
                    add_result_label.text = "❌ Cover file not found."
                    return
            else:
                add_result_label.text = "❌ Failed to get upload URL"
                return

        try:
            rating = float(rating_input.value)
        except ValueError:
            add_result_label.text = "❌ Invalid rating"
            return

        book = {
            "title": title_input.value.strip(),
            "author": author_input.value.strip(),
            "description": description_input.value.strip(),
            "rating": rating,
            "cover_url": cover_url,
        }

        result = add_book(book)
        if "error" in result:
            add_result_label.text = f"❌ {result['error']}"
        elif "book" in result:
            add_result_label.text = f"✅ Book added: {result['book']['title']}"
            refresh_book_list()
        else:
            add_result_label.text = "❌ Unknown error"

    ui.button("Add Book", on_click=handle_add_book).classes("mt-2")

ui.separator()

# 🔍 Search Book
with ui.card().classes("w-full max-w-2xl"):
    ui.label("🔍 Search Book by Title").classes("text-xl mb-2")
    search_input = ui.input("Title").classes("w-full")
    search_result_label = ui.label().classes("mt-2 text-blue-800 whitespace-pre-line")

    def handle_search():
        title = search_input.value.strip()
        book = fetch_book_by_title(title)
        if not book or "title" not in book:
            search_result_label.text = f"❌ Book '{title}' not found"
            return

        search_result_label.text = f"""
Title: {book['title']}
Author: {book['author']}
Rating: {book['rating']}
Description: {book['description']}
Reviews: {', '.join(book['reviews']) if book['reviews'] else 'None'}
Cover: {book['cover_url']}
"""

    ui.button("Search", on_click=handle_search).classes("mt-2")

ui.separator()

# 📝 Submit Review
with ui.card().classes("w-full max-w-2xl"):
    ui.label("📝 Submit Review").classes("text-xl mb-2")
    review_title_input = ui.input("Book Title").classes("w-full")
    review_input = ui.textarea("Review").classes("w-full")
    review_result_label = ui.label().classes("mt-2 text-purple-800")

    def handle_review():
        title = review_title_input.value.strip()
        review = review_input.value.strip()
        if not title or not review:
            review_result_label.text = "❌ Please provide both title and review"
            return
        result = add_review(title, review)
        review_result_label.text = "✅ Review added" if "message" in result else "❌ Failed to add review"

    ui.button("Submit Review", on_click=handle_review).classes("mt-2")

ui.separator()

# 📖 All Books with Filter
with ui.row().classes("items-center"):
    ui.label("📖 All Books").classes("text-xl")
    filter_input = ui.input("Min Rating").props("type=number step=0.5").classes("w-32")

    def refresh_book_list():
        min_rating = filter_input.value or "0"
        books = fetch_all_books(min_rating)
        for book in books:
            book['rating'] = "⭐" * int(float(book['rating']))
        table.rows = books

    ui.button("🔄 Refresh", on_click=refresh_book_list)

table = ui.table(
    columns=[
        {"name": "title", "label": "Title", "field": "title"},
        {"name": "author", "label": "Author", "field": "author"},
        {"name": "rating", "label": "Rating", "field": "rating"},
        {"name": "description", "label": "Description", "field": "description"},
        {"name": "cover_url", "label": "Cover", "field": "cover_url"},
    ],
    rows=[],
    row_key="title",
    pagination=5,
).classes("w-full max-w-screen-lg mt-2")

ui.run(host="0.0.0.0", port=9000)
