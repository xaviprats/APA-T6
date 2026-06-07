"""
Autor: Xavi Prats Castillo

Módulo para la normalización de expresiones horarias en un texto.
Convierte cualquier expresión horaria válida al formato estándar HH:MM.
"""

import re


def normalizaHoras(ficText, ficNorm):
    """
    Lee el fichero ficText, detecta todas las expresiones horarias válidas
    y las escribe normalizadas al formato HH:MM en el fichero ficNorm.
    Las expresiones incorrectas se dejan tal cual.
    """

    # --- FUNCIONES AUXILIARES INTERNAS ---

    def obtener_minutos(grupos):
        """
        Determina el valor numérico de los minutos a partir de los grupos capturados.
        Gestiona tanto minutos numéricos (ej: 30 de '8h30m') como literales
        (ej: 'y media', 'menos cuarto', 'en punto').
        Devuelve None si el valor está fuera de rango.
        """
        # Minutos escritos en número detrás de la 'h' (ej: 10h45m)
        if grupos['m_col'] is not None:
            m = int(grupos['m_col'])
            return m if m <= 59 else None

        # Minutos expresados en palabras
        texto_minutos = grupos['min_lit']
        if texto_minutos:
            texto_minutos = texto_minutos.lower()
            if 'en punto'     in texto_minutos: return 0
            if 'y cuarto'     in texto_minutos: return 15
            if 'y media'      in texto_minutos: return 30
            if 'menos cuarto' in texto_minutos: return 45  # La hora se resta 1 aparte

        # Si no se indican minutos, se asume que es en punto
        return 0

    def convertir_a_24h(h_hablada, m, grupos):
        """
        Valida la hora dentro de la franja horaria indicada (mañana, tarde, etc.)
        y la convierte al formato de 24 horas.
        Devuelve None si la expresión es incorrecta (hora fuera de franja).
        """
        periodo = grupos['periode']
        texto_minutos = grupos['min_lit']

        # Si hay palabras asociadas (franja o literal de minutos), aplicamos reloj de 12h
        if periodo or texto_minutos:

            # En formato hablado la hora va de 1 a 12, nunca 0
            if not (1 <= h_hablada <= 12):
                return None

            if periodo:
                periodo = periodo.lower()

                # Comprobamos que la hora encaja dentro de la franja horaria indicada
                if 'mañana'    in periodo and not (4  <= h_hablada <= 12): return None
                if 'mediodía'  in periodo and not (h_hablada == 12 or 1 <= h_hablada <= 3): return None
                if 'tarde'     in periodo and not (3  <= h_hablada <= 8):  return None
                if 'noche'     in periodo and not (8  <= h_hablada <= 12 or 1 <= h_hablada <= 4): return None
                if 'madrugada' in periodo and not (1  <= h_hablada <= 6):  return None

                # Ajuste por 'menos cuarto': la hora real es la hablada menos 1
                h_digital = h_hablada
                if texto_minutos and 'menos cuarto' in texto_minutos.lower():
                    h_digital -= 1

                # Conversión de la hora hablada a valor digital de 24h
                if 'mañana' in periodo or 'madrugada' in periodo:
                    if h_digital == 12:
                        h_digital = 0
                elif 'mediodía' in periodo or 'tarde' in periodo:
                    if h_digital != 12:
                        h_digital += 12
                elif 'noche' in periodo:
                    if 8 <= h_digital <= 11:
                        h_digital += 12
                    elif h_digital == 12:
                        h_digital = 0
                    # De 1 a 4 de la noche se quedan como están

                return h_digital

            else:
                # Minutos literales sin franja (ej: '8 y media', '3 en punto')
                h_digital = h_hablada
                if texto_minutos and 'menos cuarto' in texto_minutos.lower():
                    h_digital -= 1

                if h_digital == 12:
                    h_digital = 0
                elif h_digital < 0:
                    h_digital = 11  # Caso límite: 1 menos cuarto -> 00:45

                return h_digital

        else:
            # Formato numérico puro (ej: '18h30m'): rango completo de 0 a 23
            if not (0 <= h_hablada <= 23):
                return None
            return h_hablada

    def gestionar_coincidencia(match):
        """
        Función llamada por re.sub() para cada expresión encontrada.
        Decide si la expresión es válida y devuelve la forma normalizada
        o el texto original si no es correcta.
        """
        texto_original = match.group(0)
        grupos = match.groupdict()

        # --- CASO 1: Formato digital con dos puntos (ej: 18:30, 8:05) ---
        if grupos['h_std'] is not None:
            h = int(grupos['h_std'])
            m = int(grupos['m_std'])
            if 0 <= h <= 23 and 0 <= m <= 59:
                return f"{h:02d}:{m:02d}"
            return texto_original

        # --- CASO 2: Formato hablado (ej: 8h, 10h30m, 5 y media de la tarde) ---
        if grupos['h_col'] is not None:
            h_hablada = int(grupos['h_col'])
            m = obtener_minutos(grupos)

            if m is None:
                return texto_original

            h_final = convertir_a_24h(h_hablada, m, grupos)

            if h_final is None:
                return texto_original

            return f"{h_final:02d}:{m:02d}"

        return texto_original

    # --- DEFINICIÓN DE LAS EXPRESIONES REGULARES ---

    # Formato digital estándar: acepta 1 o 2 dígitos para la hora, siempre 2 para los minutos
    regex_std = r'(?P<h_std>\d{1,2}):(?P<m_std>\d{2})\b'

    # Formato hablado: hora seguida de 'h', literales de minutos o franja horaria
    regex_col = (
        r'\b(?P<h_col>\d{1,2})'
        r'(?:'
            r'(?:h(?P<m_col>\d{1,2})?m?\b)'                                          # 8h, 8h30m, 8h30
            r'|(?:\s+(?P<min_lit>en punto|y cuarto|y media|menos cuarto)\b)'          # 8 y media
            r'|(?:\s+(?:de la|del)\s+(?P<periode>mañana|mediodía|tarde|noche|madrugada)\b)'  # 8 de la tarde
        r')'
    )

    # Compilamos el patrón combinado (primero el digital, luego el hablado)
    patron_completo = re.compile(f'{regex_std}|{regex_col}', re.IGNORECASE)

    # --- LECTURA Y ESCRITURA ---
    try:
        with open(ficText, 'r', encoding='utf-8') as f_entrada, \
             open(ficNorm, 'w', encoding='utf-8') as f_salida:

            for linea in f_entrada:
                linea_normalizada = patron_completo.sub(gestionar_coincidencia, linea)
                f_salida.write(linea_normalizada)

    except FileNotFoundError:
        raise FileNotFoundError(f"No se ha podido abrir el fichero: '{ficText}'")