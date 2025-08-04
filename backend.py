import os
import psycopg2
import boto3
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PostgreSQL Database connection
conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)
cur = conn.cursor()

# S3 configuration
s3 = boto3.client('s3')
S3_BUCKET = os.getenv("S3_BUCKET")

# Models
class Book(BaseModel):
    title: str
    author: str
    description: str
    rating: float
    cover_url: str

class ReviewRequest(BaseModel):
    review: str

# Helper function
def get_reviews_by_book_id(book_id: int):
    cur.execute("SELECT content FROM reviews WHERE book_id = %s", (book_id,))
    return [r[0] for r in cur.fetchall()]

# Routes
@app.get("/books")
def get_books(min_rating: float = Query(0.0)):
    try:
        cur.execute("SELECT id, title, author, description, rating, cover_url FROM books WHERE rating >= %s", (min_rating,))
        return [
            {"id": r[0], "title": r[1], "author": r[2], "description": r[3], "rating": r[4], "cover_url": r[5]}
            for r in cur.fetchall()
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/books/{title}")
def get_book(title: str):
    cur.execute("SELECT id, title, author, description, rating, cover_url FROM books WHERE title=%s", (title,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Book not found")
    return {
        "id": row[0],
        "title": row[1],
        "author": row[2],
        "description": row[3],
        "rating": row[4],
        "cover_url": row[5],
        "reviews": get_reviews_by_book_id(row[0])
    }

@app.post("/books")
def add_book(book: Book):
    try:
        cur.execute("""INSERT INTO books (title, author, description, rating, cover_url)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (book.title, book.author, book.description, book.rating, book.cover_url))
        conn.commit()
        return {"message": "Book added successfully", "book": book.dict()}
    except Exception as e:
        conn.rollback()
        import traceback
        print("❌ ERROR while inserting book:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/books/{title}/review")
def add_review(title: str, review_data: ReviewRequest):
    cur.execute("SELECT id FROM books WHERE title=%s", (title,))
    result = cur.fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="Book not found")
    book_id = result[0]
    try:
        cur.execute("INSERT INTO reviews (book_id, content) VALUES (%s, %s)", (book_id, review_data.review))
        conn.commit()
        return {"message": "Review added"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/s3/upload-url")
def get_upload_url(filename: str):
    try:
        url = s3.generate_presigned_url(
            ClientMethod='put_object',
            Params={'Bucket': S3_BUCKET, 'Key': filename, 'ContentType': 'image/jpeg'},
            ExpiresIn=3600
        )
        return {"upload_url": url, "file_url": f"https://{S3_BUCKET}.s3.amazonaws.com/{filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
