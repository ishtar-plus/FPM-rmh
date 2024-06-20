from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from PIL import Image, ImageDraw, ImageFont
import io
import shutil
import os
from models import Base, SessionLocal, ImageData, engine
import arabic_reshaper
from bidi.algorithm import get_display
from typing import List, Optional
import re
import textwrap

app = FastAPI()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def sanitize_filename(filename: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)

def reshape_text(text: str) -> str:
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

def wrap_text(text: str, draw: ImageDraw.Draw, font: ImageFont.ImageFont, max_width: int) -> List[str]:
    lines = []
    words = text.split(' ')
    line = ''
    for word in words:
        test_line = f'{line} {word}'.strip()
        bbox = draw.textbbox((0, 0), test_line, font=font)
        width = bbox[2] - bbox[0]
        if width <= max_width:
            line = test_line
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines

def add_logo_and_text(image: Image.Image, logo: Image.Image, position: tuple, text: Optional[str], text_zone: tuple, text_color: tuple, font_path: str, font_size: int, alignment: str) -> Image.Image:
    try:
        # Resize logo if it's larger than the image
        if logo.size[0] > image.size[0] or logo.size[1] > image.size[1]:
            logo = logo.resize((image.size[0] // 4, image.size[1] // 4), Image.LANCZOS)

        # Paste the logo onto the original image
        image.paste(logo, position, logo)

        if text:
            # Initialize ImageDraw
            draw = ImageDraw.Draw(image)

            # Load a font
            if font_path and os.path.exists(font_path):
                font = ImageFont.truetype(font_path, font_size)
            else:
                font = ImageFont.load_default()

            # Reshape and bidi the Arabic text
            reshaped_text = reshape_text(text)

            # Calculate text wrapping to fit within the text zone
            text_x, text_y, zone_width, zone_height = text_zone
            lines = wrap_text(reshaped_text, draw, font, zone_width)

            # Draw text within the text zone
            current_y = text_y
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
                line_height = bbox[3] - bbox[1]
                if current_y + line_height > text_y + zone_height:
                    break  # Stop drawing if text exceeds the text zone height

                if alignment == "right":
                    draw.text((text_x + zone_width - line_width, current_y), line, fill=text_color, font=font)
                elif alignment == "center":
                    draw.text((text_x + (zone_width - line_width) // 2, current_y), line, fill=text_color, font=font)
                else:  # Default to left alignment
                    draw.text((text_x, current_y), line, fill=text_color, font=font)

                current_y += line_height  # Move down by the height of the text line

        return image
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing the image: {e}")

@app.post("/process_image/")
async def process_image(
    images: List[UploadFile] = File(...),
    logo: UploadFile = File(...),
    text: Optional[str] = Form(None),
    position_x: int = Form(-130),
    position_y: int = Form(-180),
    text_x: int = Form(100),
    text_y: int = Form(1140),
    text_zone_width: int = Form(800),
    text_zone_height: int = Form(150),
    text_color: str = Form("255,255,255"),
    font_size: int = Form(60),
    font_path: str = Form("/System/Library/Fonts/Supplemental/Futura.ttc"),
    alignment: str = Form("left"),
    image_width: Optional[int] = Form(1500),
    image_height: Optional[int] = Form(1500),
    logo_width: Optional[int] = Form(600),
    logo_height: Optional[int] = Form(600),
    db: Session = Depends(get_db)
):
    try:
        processed_images_paths = []

        # Save the uploaded logo file
        logo_path = f"logos/{sanitize_filename(logo.filename)}"
        os.makedirs(os.path.dirname(logo_path), exist_ok=True)

        with open(logo_path, "wb") as logo_f:
            shutil.copyfileobj(logo.file, logo_f)

        # Load the logo image
        logo = Image.open(logo_path)

        # Resize the logo if dimensions are provided
        if logo_width and logo_height:
            logo = logo.resize((logo_width, logo_height), Image.LANCZOS)

        # Convert text_color to tuple
        text_color = tuple(map(int, text_color.split(',')))

        for image_file in images:
            # Save each uploaded image file
            image_path = f"images/{sanitize_filename(image_file.filename)}"
            os.makedirs(os.path.dirname(image_path), exist_ok=True)

            with open(image_path, "wb") as img_f:
                shutil.copyfileobj(image_file.file, img_f)

            # Load the image
            image = Image.open(image_path)

            # Resize the image if dimensions are provided
            if image_width and image_height:
                image = image.resize((image_width, image_height), Image.LANCZOS)

            # Process the image
            processed_image = add_logo_and_text(
                image,
                logo,
                (position_x, position_y),
                text,
                (text_x, text_y, text_zone_width, text_zone_height),
                text_color,
                font_path,
                font_size,
                alignment
            )

            # Save the processed image
            processed_image_path = f"processed_images/processed_{sanitize_filename(image_file.filename)}"
            os.makedirs(os.path.dirname(processed_image_path), exist_ok=True)
            processed_image.save(processed_image_path)
            processed_images_paths.append(processed_image_path)

            # Save the metadata to the database
            db_image = ImageData(
                image_path=image_path,
                logo_path=logo_path,
                text=text if text else "",
                text_position_x=text_x,
                text_position_y=text_y,
                text_color=str(text_color),
                font_size=font_size,
                font_path=font_path,
                logo_position_x=position_x,
                logo_position_y=position_y
            )
            db.add(db_image)
            db.commit()

        return [FileResponse(path, media_type="image/png", filename=os.path.basename(path)) for path in processed_images_paths]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing the request: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
