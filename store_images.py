import sqlite3
import base64
import os
from pathlib import Path

def create_images_table():
    conn = sqlite3.connect('newsletter_images.db')
    cursor = conn.cursor()
    
    # Create table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        image_data BLOB NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

def store_image(image_path, image_name):
    # Read the image file
    with open(image_path, 'rb') as file:
        image_data = file.read()
    
    # Connect to SQLite database
    conn = sqlite3.connect('newsletter_images.db')
    cursor = conn.cursor()
    
    try:
        # Insert or update the image
        cursor.execute('''
        INSERT OR REPLACE INTO images (name, image_data)
        VALUES (?, ?)
        ''', (image_name, image_data))
        
        conn.commit()
        print(f"Successfully stored {image_name}")
    except Exception as e:
        print(f"Error storing {image_name}: {str(e)}")
    finally:
        conn.close()

def get_image_base64(image_name):
    conn = sqlite3.connect('newsletter_images.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT image_data FROM images WHERE name = ?', (image_name,))
        result = cursor.fetchone()
        
        if result:
            # Convert binary data to base64
            image_base64 = base64.b64encode(result[0]).decode('utf-8')
            return f"data:image/png;base64,{image_base64}"
        else:
            print(f"Image {image_name} not found in database")
            return None
    finally:
        conn.close()

if __name__ == "__main__":
    # Create the images table
    create_images_table()
    
    # Get the directory where the images are stored
    images_dir = Path(__file__).parent / 'static' / 'newsletter_images'
    
    # List of required images
    required_images = [
        'company_logo.png',
        'twitter.png',
        'link.png',
        'whatsapp.png',
        'phone.png',
        'mail.png',
        'web.png'
    ]
    
    # Store each image
    for image_name in required_images:
        image_path = images_dir / image_name
        if image_path.exists():
            store_image(image_path, image_name)
        else:
            print(f"Warning: {image_name} not found in {images_dir}")
    
    # Test retrieval
    print("\nTesting image retrieval:")
    for image_name in required_images:
        base64_data = get_image_base64(image_name)
        if base64_data:
            print(f"Successfully retrieved {image_name}")
        else:
            print(f"Failed to retrieve {image_name}") 