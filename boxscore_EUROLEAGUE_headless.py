import requests
import pandas as pd
import numpy as np
import time
import os

# ==============================================================================
# 1. CONFIGURACIÓN HEADLESS (TODOS LOS EQUIPOS)
# ==============================================================================
SEASON_CODE = "E2025" 
SEASON_LABEL = "2025/2026"
MAX_GAMES = 350
CARPETA_SALIDA = "data"
NOMBRE_ARCHIVO = f"BoxScore_Euroleague_{SEASON_LABEL[:4]}_Cumulative.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

# ==============================================================================
# 2. FUNCIONES DE AYUDA
# ==============================================================================
def formatear_nombre_euro(nombre_raw):
    """Convierte 'LYLES, TREY' -> 'LYLES, T.'"""
    if not nombre_raw: return "UNKNOWN"
    nombre = nombre_raw.strip().upper()
    
    if "," in nombre:
        parts = nombre.split(",")
        apellido = parts[0].strip()
        inicial = parts[1].strip()[0] if len(parts[1].strip()) > 0 else ""
        return f"{apellido}, {inicial}."
    elif " " in nombre:
        parts = nombre.split(" ")
        return f"{parts[-1]}, {parts[0][0]}."
    return nombre

def time_to_min(t_str):
    """Convierte MM:SS a minutos decimales"""
    try:
        t_str = str(t_str)
        if ":" in t_str:
            m, s = map(int, t_str.split(':'))
            return m + s/60
        return float(t_str)
    except: return 0.0

# ==============================================================================
# 3. LÓGICA DE EXTRACCIÓN (Bucle Universal)
# ==============================================================================
def main():
    print(f"🚀 INICIANDO SCRAPER EUROLIGA: TODOS LOS EQUIPOS")
    print(f"📅 Temporada: {SEASON_LABEL}")
    
    if not os.path.exists(CARPETA_SALIDA):
        os.makedirs(CARPETA_SALIDA)
        print(f"📁 Carpeta creada: {CARPETA_SALIDA}")

    all_stats = []
    games_found = 0

    print(f"⏳ Escaneando partidos...")

    for game_id in range(1, MAX_GAMES + 1):
        if game_id % 20 == 0: print(".", end="", flush=True)
        
        url = "https://live.euroleague.net/api/Boxscore"
        params = {"gamecode": str(game_id), "seasoncode": SEASON_CODE}
        
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=5)
            
            if r.status_code == 200:
                data = r.json()
                
                if 'Stats' in data and len(data['Stats']) >= 2:
                    
                    # Cálculo de semana (Aprox. 9 partidos por jornada en Euroliga)
                    jornada_estimada = ((game_id - 1) // 9) + 1
                    week_label = f"Jornada {jornada_estimada}"
                    
                    for i, team_data in enumerate(data['Stats']):
                        target_team = team_data
                        rival_idx = 1 - i
                        rival_team = data['Stats'][rival_idx]
                        location = "Home" if i == 0 else "Away"
                        
                        team_code = target_team.get('TeamCode') or target_team.get('Team', 'UNK')[:3].upper()
                        rival_code = rival_team.get('TeamCode') or rival_team.get('Team', 'UNK')[:3].upper()
                        
                        pts_us = sum([p.get('Points', 0) for p in target_team.get('PlayersStats', []) if not p.get('IsTeam')])
                        pts_them = sum([p.get('Points', 0) for p in rival_team.get('PlayersStats', []) if not p.get('IsTeam')])
                        win = 1 if pts_us > pts_them else 0
                        
                        for p in target_team.get('PlayersStats', []):
                            if p.get('IsTeam', False): continue 
                            if p.get('IsPlaying', False) is False and p.get('Minutes') == "00:00": continue 
                            
                            clean_name = formatear_nombre_euro(p.get('Player'))
                            
                            t2m = p.get('FieldGoalsMade2', 0); t2a = p.get('FieldGoalsAttempted2', 0)
                            t3m = p.get('FieldGoalsMade3', 0); t3a = p.get('FieldGoalsAttempted3', 0)
                            ftm = p.get('FreeThrowsMade', 0);  fta = p.get('FreeThrowsAttempted', 0)
                            
                            row = {
                                'Season': SEASON_LABEL, 'Week': week_label, 'GameID': game_id,
                                'Team': team_code, 'Rival': rival_code, 'Location': location, 'Win': win,
                                'Name': clean_name, 
                                'PlayerID': p.get('Player_ID', ''),
                                'Dorsal': p.get('Dorsal', ''),
                                'Starter': 1 if p.get('IsStarter') else 0,
                                'Min': p.get('Minutes', '00:00'),
                                'PTS': p.get('Points', 0), 
                                'VAL': p.get('Valuation', 0), 
                                '+/-': p.get('Plusminus', 0), 
                                
                                '2FG_M': t2m, '2FG_A': t2a, '3FG_M': t3m, '3FG_A': t3a, 'FT_M': ftm, 'FT_A': fta,
                                
                                'Reb_O': p.get('OffensiveRebounds', 0), 
                                'Reb_D': p.get('DefensiveRebounds', 0),
                                'Reb_T': p.get('TotalRebounds', 0), 
                                'AST': p.get('Assistances', 0),
                                'STL': p.get('Steals', 0), 
                                'TO': p.get('Turnovers', 0),
                                'BLK': p.get('BlocksFavour', 0), 
                                'PF': p.get('FoulsCommited', 0), 
                                'PF_R': p.get('FoulsReceived', 0)
                            }
                            all_stats.append(row)
                            
                    games_found += 1

        except Exception as e: 
            pass
        time.sleep(0.05)

    print("\n" + "-" * 60)

    # ==============================================================================
    # 4. CÁLCULOS AVANZADOS (Ajustados para todos los equipos)
    # ==============================================================================
    if all_stats:
        df = pd.DataFrame(all_stats)
        print("🧠 Calculando métricas avanzadas de toda la liga...")
        
        df['MIN_FL'] = df['Min'].apply(time_to_min)
        df['FGA'] = df['2FG_A'] + df['3FG_A']
        df['FGM'] = df['2FG_M'] + df['3FG_M']
        
        # Corrección Crítica: Agrupar por Partido y por Equipo
        team_stats = df.groupby(['GameID', 'Team']).agg({
            'MIN_FL': 'sum', 'FGA': 'sum', 'FT_A': 'sum', 'TO': 'sum', 'FGM': 'sum'
        }).rename(columns={'MIN_FL': 'Tm_MIN', 'FGA': 'Tm_FGA', 'FT_A': 'Tm_FTA', 'TO': 'Tm_TO', 'FGM': 'Tm_FGM'}).reset_index()
        
        df = df.merge(team_stats, on=['GameID', 'Team'], how='left')
        
        df['eFG%'] = np.where(df['FGA']>0, (df['FGM'] + 0.5*df['3FG_M'])/df['FGA'], 0.0) * 100
        tsa = df['FGA'] + 0.44 * df['FT_A']
        df['TS%'] = np.where(tsa>0, df['PTS']/(2*tsa), 0.0) * 100
        df['3PAr'] = np.where(df['FGA']>0, df['3FG_A']/df['FGA'], 0.0) * 100
        df['FTr'] = np.where(df['FGA']>0, df['FT_A']/df['FGA'], 0.0) * 100
        
        num_usg = (df['FGA'] + 0.44*df['FT_A'] + df['TO']) * (df['Tm_MIN']/5)
        den_usg = df['MIN_FL'] * (df['Tm_FGA'] + 0.44*df['Tm_FTA'] + df['Tm_TO'])
        df['USG%'] = np.where((den_usg>0) & (df['MIN_FL']>0), (num_usg/den_usg)*100, 0.0)
        
        tm_fg = ((df['MIN_FL']/(df['Tm_MIN']/5)) * df['Tm_FGM']) - df['FGM']
        df['AST%'] = np.where(tm_fg>0, (df['AST']/tm_fg)*100, 0.0)
        
        plays = df['FGA'] + 0.44*df['FT_A'] + df['TO']
        df['TOV%'] = np.where(plays>0, (df['TO']/plays)*100, 0.0)
        
        df['GmSc'] = (df['PTS'] + 0.4*df['FGM'] - 0.7*df['FGA'] - 0.4*(df['FT_A']-df['FT_M']) + 
                      0.7*df['Reb_O'] + 0.3*df['Reb_D'] + df['STL'] + 0.7*df['AST'] + 
                      0.7*df['BLK'] - 0.4*df['PF'] - df['TO'])
        
        # Posesiones (para igualar a ACB)
        df['Game_Poss'] = df['Tm_FGA'] + 0.44 * df['Tm_FTA'] + df['Tm_TO']

        cols_pct = ['eFG%', 'TS%', '3PAr', 'FTr', 'USG%', 'AST%', 'TOV%', 'GmSc']
        for c in cols_pct: df[c] = df[c].round(1)

        cols_finales = ['GameID', 'Season', 'Week', 'Team', 'Location', 'Win', 
                        'PlayerID', 'Dorsal', 'Name', 'Min', 'Game_Poss', 'PTS', 'VAL', '+/-',
                        'Reb_O', 'Reb_D', 'Reb_T', 'AST', 'STL', 'TO', 'BLK', 'PF', 'PF_R',
                        'GmSc', 'TS%', 'eFG%', 'USG%', '3PAr', 'FTr', 'AST%', 'TOV%']
        
        df_final = df[cols_finales]
        
        ruta_completa = os.path.join(CARPETA_SALIDA, NOMBRE_ARCHIVO)
        df_final.to_csv(ruta_completa, index=False, encoding='utf-8-sig')
        
        print(f"🎉 ¡HECHO! Estadísticas guardadas en: {ruta_completa}")
        print(f"📊 Filas: {len(df_final)} | Partidos procesados: {games_found}")
    else:
        print("⚠️ No se encontraron datos.")

if __name__ == "__main__":
    main()
