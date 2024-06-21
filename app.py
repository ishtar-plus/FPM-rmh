import streamlit as st
import requests
from PIL import Image
from io import BytesIO
import main  # Assuming the main.py is in the same directory

# URL of the FastAPI endpoint
FASTAPI_URL = "http://localhost:9000/process_image/"

def main():
    st.title("Image Processing App")

    # Upload images
    uploaded_files = st.file_uploader("Upload Images", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])
    logo_file = st.file_uploader("Upload Logo", type=['png'])

    if uploaded_files and logo_file:
        # Display the uploaded images
        for uploaded_file in uploaded_files:
            image = Image.open(uploaded_file)
            st.image(image, use_column_width=True)

        # Input text and other parameters
        text = st.text_input("Text to add to the image")
        position_x = st.number_input("Logo position X", value=-130)
        position_y = st.number_input("Logo position Y", value=-180)
        text_x = st.number_input("Text position X", value=100)
        text_y = st.number_input("Text position Y", value=1140)
        text_zone_width = st.number_input("Text zone width", value=40)
        text_zone_height = st.number_input("Text zone height", value=150)
        text_color = st.text_input("Text color (R,G,B)", value="255,255,255")
        font_size = st.number_input("Font size", value=60)
        font_path = st.text_input("Font path", value="/System/Library/Fonts/Supplemental/Futura.ttc")
        alignment = st.selectbox("Text alignment", ["left", "center", "right"], index=0)
        image_width = st.number_input("Image width", value=1500)
        image_height = st.number_input("Image height", value=1500)
        logo_width = st.number_input("Logo width", value=600)
        logo_height = st.number_input("Logo height", value=600)

        # Submit button
        if st.button("Process Images"):
            files = [("images", (file.name, file, file.type)) for file in uploaded_files]
            files.append(("logo", (logo_file.name, logo_file, logo_file.type)))

            data = {
                "text": text,
                "position_x": position_x,
                "position_y": position_y,
                "text_x": text_x,
                "text_y": text_y,
                "text_zone_width": text_zone_width,
                "text_zone_height": text_zone_height,
                "text_color": text_color,
                "font_size": font_size,
                "font_path": font_path,
                "alignment": alignment,
                "image_width": image_width,
                "image_height": image_height,
                "logo_width": logo_width,
                "logo_height": logo_height,
            }

            response = requests.post(FASTAPI_URL, files=files, data=data)

            if response.status_code == 200:
                for idx, img_data in enumerate(response.json()):
                    img_bytes = requests.get(img_data["file"]).content
                    image = Image.open(BytesIO(img_bytes))
                    st.image(image, caption=f"Processed Image {idx + 1}")
            else:
                st.error(f"Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    main()
