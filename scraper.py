import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def get_r6_team_stats(player_configs, season="40", playlist="ranked", fetch_type="both"):
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    
    driver = None
    all_team_results = {"mapas": [], "agentes": [], "fase": [], "erros": []}
    
    try:
        driver = uc.Chrome(options=options)
        wait = WebDriverWait(driver, 15)

        for player in player_configs:
            nick = player['nick']
            plat = player['platform']
            
            try:
                suffix = f"?season={season}&playlist={playlist}"
                base_url = f"https://r6.tracker.network/r6siege/profile/{plat}/{nick}"
                
                # --- 1. COLETA DE FASE ATUAL (W/L SIMPLES) ---
                if fetch_type in ["both", "fase"]:
                    driver.get(f"{base_url}/matches{suffix}")
                    time.sleep(3) # Tempo para o histórico carregar
                    
                    try:
                        # Lê todo o texto da tela, separa por linhas e joga para maiúsculo
                        page_text = driver.find_element(By.TAG_NAME, "body").text.upper().split('\n')
                        history = []
                        
                        # Varre as linhas procurando os resultados das partidas
                        for line in page_text:
                            clean_line = line.strip()
                            if clean_line in ["WIN", "VICTORY", "VITÓRIA"]:
                                history.append("W")
                            elif clean_line in ["LOSS", "DEFEAT", "DERROTA", "ABANDON", "ABANDONO"]:
                                history.append("L")
                            elif clean_line in ["DRAW", "EMPATE", "TIE"]:
                                history.append("D")
                                
                            if len(history) >= 8: # Guarda apenas as últimas 8 partidas
                                break
                                
                        if not history:
                            history = ["?"] # Sem dados ou perfil privado
                            
                    except Exception as e:
                        history = ["?"]

                    all_team_results["fase"].append({
                        "Jogador": nick, 
                        "Plataforma": plat.upper(),
                        "History": history
                    })

                # --- 2. COLETA DE MAPAS ---
                if fetch_type in ["both", "maps"]:
                    driver.get(f"{base_url}/maps{suffix}")
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table")))
                    map_rows = driver.find_elements(By.CSS_SELECTOR, "table tr")[1:]
                    for row in map_rows:
                        cols = row.find_elements(By.TAG_NAME, "td")
                        if len(cols) >= 3:
                            all_team_results["mapas"].append({
                                "Jogador": nick, "Plataforma": plat.upper(),
                                "Mapa": cols[0].text.split('\n')[0],
                                "WinPct": float(cols[2].text.replace('%', '').strip()),
                                "Partidas": int(cols[1].text.replace(',', '').strip())
                            })

                # --- 3. COLETA DE AGENTES ---
                if fetch_type in ["both", "agentes"]:
                    driver.get(f"{base_url}/operators{suffix}")
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table")))
                    op_rows = driver.find_elements(By.CSS_SELECTOR, "table tr")[1:]
                    for row in op_rows:
                        cols = row.find_elements(By.TAG_NAME, "td")
                        if len(cols) >= 4:
                            op_name = cols[0].text.split('\n')[0]
                            imgs = cols[0].find_elements(By.TAG_NAME, "img")
                            img_url = imgs[0].get_attribute("src") if imgs else ""
                            all_team_results["agentes"].append({
                                "Jogador": nick, "Plataforma": plat.upper(),
                                "Agente": op_name, "Icone": img_url,
                                "Partidas": int(cols[1].text.replace(',', '').strip()),
                                "WinPct": float(cols[2].text.replace('%', '').strip()),
                                "KD": float(cols[3].text.strip()) if cols[3].text != '-' else 0.0
                            })
            except Exception:
                all_team_results["erros"].append(nick)
                continue

        return all_team_results

    except Exception as e:
        return {"erro_critico": str(e)}
    finally:
        if driver:
            driver.quit()