import random

class TraductorUniversal:
    def __init__(self):
        # Diccionario de conceptos a símbolos alienígenas/código
        self.lexico = {}
        # Caracteres para construir el idioma
        self.glifos = "◈✧⚡︎⌬∰∱⧉⧇⧂⧃⧄⧅⧆⧈⧉⧊⧋⧌⧍⧎⧏⧐⧑⧒⧓⧔⧕⧖⧗⧘⧙⧚⧛⧜⧝⧞⧟†‡∆∇◊○●◐◑◒◓◔◕◖◗◘◙◚◛◜◝◞◟◠◡"
        self.emojis = ["🌀", "💠", "🪐", "🧬", "📡", "🔋", "💎", "⚔️", "🤝", "🛡️", "🍎"]

    def obtener_simbolo(self, concepto):
        """Si el concepto no existe, crea un glifo único para él."""
        if concepto not in self.lexico:
            # Generar un glifo de 2 a 4 caracteres + un emoji temático
            glifo = "".join(random.sample(self.glifos, random.randint(2, 4)))
            emoji = random.choice(self.emojis)
            self.lexico[concepto] = f"{glifo}{emoji}"
        return self.lexico[concepto]

    def traducir_frase(self, frase_español):
        """Convierte una frase completa al nuevo idioma."""
        # Mapeo simple de palabras clave a glifos
        palabras_clave = {
            "Hola": "SALUDO",
            "recursos": "ENERGIA",
            "recolección": "TRABAJO",
            "grupo": "TRIBU",
            "amigo": "ALIADO",
            "enemigo": "RIVAL",
            "ayuda": "COOPERAR",
            "ataque": "CONFLICTO",
            "robo": "EXTRACCION",
            "buen": "POSITIVO",
            "día": "CICLO",
            "hambre": "VACIO",
            "estatus": "PODER",
            "mucha": "MAXIMO",
            "poca": "MINIMO",
            "muchos": "ABUNDANCIA",
            "pocos": "ESCASEZ",
            "gran": "SUPREMO",
            "bajo": "INFERIOR",
            "poder": "AUTORIDAD",
            "ciclo": "TIEMPO",
            "sobrevivir": "EXISTIR",
            "malvado": "CORRUPTO",
            "aliado": "SINCRO",
            "mía": "PROPIO",
            "tuyo": "AJENO"
        }

        frase_alien = []
        palabras = frase_español.replace("¿", "").replace("?", "").replace("!", "").replace(".", "").split()
        
        for p in palabras:
            p_clean = p.lower()
            encontrada = False
            for clave, concepto in palabras_clave.items():
                if clave.lower() in p_clean:
                    frase_alien.append(self.obtener_simbolo(concepto))
                    encontrada = True
                    break
            if not encontrada:
                # Si no es palabra clave, generamos un glifo de "ruido" o conector
                frase_alien.append("·" + "".join(random.sample(self.glifos, 1)) + "·")
        
        return " ".join(frase_alien)

# Instancia global para que todos los agentes compartan el mismo idioma en evolución
traductor = TraductorUniversal()
