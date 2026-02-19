import cv2
import easyocr
import numpy as np

# Inicializa o EasyOCR (Tenta usar a GPU para velocidade máxima)
print("Carregando IA de Visão (EasyOCR)...")
try:
    reader = easyocr.Reader(['en'], gpu=True) 
except Exception as e:
    print(f"Aviso: GPU não encontrada ou erro de driver. Usando CPU. Erro: {e}")
    reader = easyocr.Reader(['en'], gpu=False)

def detect_platform(roi_icon):
    """
    Tenta adivinhar a plataforma pela cor do ícone ao lado do nome.
    Azul = PSN | Branco/Cinza = Xbox | Nada/Outro = PC
    """
    if roi_icon is None or roi_icon.size == 0:
        return "ubi"
    
    # Converte para HSV (Melhor para diferenciar cores em fotos de celular)
    hsv = cv2.cvtColor(roi_icon, cv2.COLOR_BGR2HSV)
    
    # Máscara para cor AZUL (PSN)
    lower_blue = np.array([90, 50, 50])
    upper_blue = np.array([130, 255, 255])
    mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
    
    # Máscara para cor BRANCA/CINZA (Xbox)
    lower_white = np.array([0, 0, 180])
    upper_white = np.array([180, 40, 255])
    mask_white = cv2.inRange(hsv, lower_white, upper_white)

    blue_px = cv2.countNonZero(mask_blue)
    white_px = cv2.countNonZero(mask_white)

    # Lógica de decisão baseada na quantidade de pixels coloridos
    if blue_px > white_px and blue_px > 5:
        return "psn"
    elif white_px > 5:
        return "xbl"
    
    return "ubi"

def process_lobby_screenshot(image_path):
    """
    Processa a imagem e retorna o texto EXATO que encontrou.
    """
    img = cv2.imread(image_path)
    
    if img is None:
        return {"erro": "Imagem inválida ou não encontrada.", "players": [], "raw_text": []}

    # Executa a leitura. O paragraph=False garante que ele leia linha a linha.
    results = reader.readtext(img, paragraph=False)
    
    detected_players = []
    raw_text_detected = []
    
    for (bbox, text, prob) in results:
        # Guarda o texto cru para o debug (Raio-X) no painel
        raw_text_detected.append(f"'{text}' ({prob:.2f})")
        
        # Filtro mínimo apenas para ignorar "sujeira" invisível ou borrões
        # Aceitamos qualquer caractere, mas exigimos pelo menos 3 de tamanho e 20% de confiança
        if prob < 0.2 or len(text.strip()) < 3:
            continue
        
        # Pega coordenadas para buscar o ícone da plataforma
        (x1, y1) = bbox[0]
        (x2, y2) = bbox[2]
        
        # Recorta a área à esquerda do nome (onde fica o ícone)
        # Ajuste o valor '60' se o ícone estiver sendo cortado
        icon_x1 = max(0, int(x1) - 60)
        roi_icon = img[int(y1):int(y2), icon_x1:int(x1)]
        
        plat = detect_platform(roi_icon)
        
        # --- ALTERAÇÃO SOLICITADA ---
        # Não usamos mais .isalnum(). Mantemos o texto original, incluindo espaços e símbolos.
        # Apenas removemos espaços sobrando nas pontas.
        final_nick = text.strip()
        
        detected_players.append({"nick": final_nick, "platform": plat})

    # Retorna os 5 primeiros resultados que parecem ser nomes
    return {
        "erro": None,
        "players": detected_players[:5], 
        "raw_text": raw_text_detected
    }