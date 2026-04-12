import urllib.parse

class ImageService:
    @staticmethod
    def get_image_for_product(nombre: str) -> str:
        """
        Retorna la URL de una imagen representativa para el producto.
        Usa placehold.co para generar una imagen limpia y minimalista
        con las iniciales o el nombre corto, dándole un look profesional.
        """
        # Limpiamos el nombre para que quepa bien en la imagen
        short_name = nombre.split(" ")[0]
        # Usamos colores pasteles de Tailwind (Indigo 100 bg, Indigo 600 text)
        bg_color = "e0e7ff"
        text_color = "4f46e5"
        
        encoded_text = urllib.parse.quote(short_name)
        return f"https://placehold.co/400x300/{bg_color}/{text_color}?text={encoded_text}&font=raleway"
