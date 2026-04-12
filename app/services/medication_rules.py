import unicodedata

def _normalize_text(text: str) -> str:
    """
    Normaliza el texto: a minúsculas y quita tildes/acentos.
    """
    text = text.lower()
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return text

# Lista estricta configurable de medicamentos para evitar colisiones
# Usa nombres genéricos y marcas comerciales comunes
KNOWN_MEDICATIONS = [
    "loratadina","acetaminofen","ibuprofeno","paracetamol","amoxicilina","diclofenaco","naproxeno","aspirina",
    "omeprazol","lansoprazol","azitromicina","dolex","advil","apronax","buscapina","salbutamol","losartan",
    "enalapril","metformina","atorvastatina","tramadol","clonazepam","alprazolam","desloratadina","cetirizina",
    "fluoxetina","sertralina","ampicilina","cefalexina","ciprofloxacino",

    # analgésicos / antiinflamatorios (otc)
    "meloxicam","ketorolaco","piroxicam","dexketoprofeno","nimesulida","celecoxib",
    "tempra","panadol","tylenol","motrin",

    # gastrointestinal
    "ranitidina","esomeprazol","pantoprazol","hidroxidoaluminio","hidroxidomagnesio",
    "maalox","gaviscon","peptobismol","loperamida","enterogermina","dulcolax",
    "senosidos","bisacodilo","metoclopramida","domperidona",

    # antibióticos comunes
    "amoxicilinaclavulanato","clindamicina","doxiciclina","levofloxacino",
    "moxifloxacino","trimetoprimsulfametoxazol","penicilina","benzetacil",

    # antialérgicos
    "fexofenadina","levocetirizina","hidroxicina",

    # respiratorio
    "bromhexina","ambroxol","acetilcisteina","dextrometorfano","guaifenesina",
    "ventolin","berodual",

    # cardiovasculares
    "valsartan","captopril","amlodipino","nifedipino","propranolol","metoprolol",
    "hidroclorotiazida","furosemida",

    # diabetes
    "glibenclamida","insulina","insulinaglargin","insulinalispro","dapagliflozina",

    # sistema nervioso
    "diazepam","quetiapina","risperidona","olanzapina","haloperidol",
    "escitalopram","paroxetina","amitriptilina","venlafaxina",

    # dermatológicos / otros
    "clotrimazol","ketoconazol","fluconazol","itraconazol","miconazol",
    "aciclovir","valaciclovir","isotretinoina",
    # marcas comunes colombia
    "genfar","mk","lafrancol","tecnoquimicas","bayer","pfizer","abbott", "xraydol"
]

def is_medication_by_rule(name: str) -> bool:
    """
    Compara un nombre dado contra la base de datos de medicamentos conocidos.
    Normaliza asegurando que tildes o mayúsculas no afecten la búsqueda.
    """
    normalized_name = _normalize_text(name)
    
    for med in KNOWN_MEDICATIONS:
        # Se normaliza la base de datos también por seguridad, aunque estén en minúsculas
        norm_med = _normalize_text(med)
        if norm_med in normalized_name:
            return True
            
    return False
