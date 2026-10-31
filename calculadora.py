"""Calculadora moderna con Python y Tkinter.

- Pantalla doble: expresión escrita y vista previa del resultado.
- Botones: AC, borrar (⌫), paréntesis, %, ±, dígitos, punto, operadores y =.
- Teclado físico completo; los manejadores devuelven "break" para que
  Tkinter no procese el mismo evento dos veces (era el fallo del borrado).
- Evaluación segura con ast (sin eval), con límite de exponente.
"""

import ast
import re
import tkinter as tk


class _VisitanteAritmetico(ast.NodeVisitor):
    """Evalúa un árbol de ast limitado a la aritmética permitida."""

    max_exp = 500

    def visit_Constant(self, nodo):
        valor = nodo.value
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            raise ValueError("solo se permiten números")
        return valor

    def visit_BinOp(self, nodo):
        tipo = type(nodo.op)
        izq = self.visit(nodo.left)
        der = self.visit(nodo.right)
        if tipo is ast.Add:
            return izq + der
        if tipo is ast.Sub:
            return izq - der
        if tipo is ast.Mult:
            return izq * der
        if tipo is ast.Div:
            return izq / der
        if tipo is ast.Pow:
            if abs(der) > self.max_exp:
                raise ValueError("exponente demasiado grande")
            return izq**der
        raise ValueError("operador no permitido")

    def visit_UnaryOp(self, nodo):
        valor = self.visit(nodo.operand)
        if isinstance(nodo.op, ast.USub):
            return -valor
        if isinstance(nodo.op, ast.UAdd):
            return +valor
        raise ValueError("operador no permitido")

    def generic_visit(self, nodo):
        raise ValueError("expresión no permitida")


OPERADORES = "+-*/"


def evaluar(texto):
    """Calcula una expresión aritmética segura. Lanza ValueError si la
    expresión es inválida y ZeroDivisionError al dividir entre cero."""
    if not texto:
        raise ValueError("expresión vacía")
    arbol = ast.parse(texto, mode="eval")
    return _VisitanteAritmetico().visit(arbol.body)


def formatear(valor):
    """Texto legible del resultado: recorta el ruido del punto flotante."""
    if isinstance(valor, int):
        return str(valor)
    return f"{valor:.10g}"


FONDO = "#10141c"
FONDO_DISPLAY = "#0b0e14"
BTN_NUMERO = "#1d2330"
BTN_OPERADOR = "#263046"
BTN_ACENTO = "#ffb545"
SOMBRA_NUM = "#2a3140"
SOMBRA_OP = "#313b52"
TEXTO_CLARO = "#e8eaf0"
TEXTO_OSCURO = "#10141c"
TEXTO_GRIS = "#7c8598"
ROJO = "#ff6b6b"


class Calculadora:
    def __init__(self, raiz):
        self.raiz = raiz
        self.raiz.title("Calculadora")
        self.raiz.configure(bg=FONDO)
        self.raiz.resizable(False, False)

        self.expresion = ""

        self.crear_pantalla()
        self.crear_botones()
        self.teclado()
        self.refrescar()


    def crear_pantalla(self):
        marco = tk.Frame(
            self.raiz, bg=FONDO_DISPLAY, padx=16, pady=12, highlightthickness=0
        )
        marco.grid(
            row=0, column=0, columnspan=4, sticky="nsew", padx=10, pady=(12, 6)
        )

        self.texto_expresion = tk.Label(
            marco, text="", font=("Segoe UI", 15), fg=TEXTO_GRIS,
            bg=FONDO_DISPLAY, anchor="e",
        )
        self.texto_expresion.pack(fill="both", expand=True)

        self.texto_resultado = tk.Label(
            marco, text="0", font=("Segoe UI Semibold", 30),
            fg=TEXTO_CLARO, bg=FONDO_DISPLAY, anchor="e",
        )
        self.texto_resultado.pack(fill="both", expand=True)

    def crear_botones(self):
        tipografia = ("Segoe UI", 14, "bold")

        disposicion = [
            [("ac", "AC", 1, 0, 1), ("util", "(", 1, 1, 1), ("util", ")", 1, 2, 1),
             ("borrar", "⌫", 1, 3, 1)],
            [("num", "7", 2, 0, 1), ("num", "8", 2, 1, 1), ("num", "9", 2, 2, 1),
             ("op", "÷", 2, 3, 1)],
            [("num", "4", 3, 0, 1), ("num", "5", 3, 1, 1), ("num", "6", 3, 2, 1),
             ("op", "×", 3, 3, 1)],
            [("num", "1", 4, 0, 1), ("num", "2", 4, 1, 1), ("num", "3", 4, 2, 1),
             ("op", "−", 4, 3, 1)],
            [("util", "±", 5, 0, 1), ("num", "0", 5, 1, 1), ("util", ".", 5, 2, 1),
             ("op", "+", 5, 3, 1)],
            [("util", "%", 6, 0, 1), ("igual", "=", 6, 1, 3)],
        ]

        estilos = {
            "num": (BTN_NUMERO, TEXTO_CLARO, SOMBRA_NUM, TEXTO_CLARO),
            "op": (BTN_OPERADOR, BTN_ACENTO, SOMBRA_OP, BTN_ACENTO),
            "igual": (BTN_ACENTO, TEXTO_OSCURO, "#f2a63a", TEXTO_OSCURO),
            "ac": (BTN_OPERADOR, ROJO, SOMBRA_OP, ROJO),
            "borrar": (BTN_OPERADOR, BTN_ACENTO, SOMBRA_OP, BTN_ACENTO),
            "util": (BTN_OPERADOR, TEXTO_CLARO, SOMBRA_OP, TEXTO_CLARO),
        }

        operador_de = {"÷": "/", "×": "*", "−": "-", "+": "+"}
        utilidades = {
            "(": self.agregar_par_abre,
            ")": self.agregar_par_cierra,
            "±": self.cambiar_signo,
            ".": self.agregar_punto,
            "%": self.aplicar_percent,
        }

        for fila_botones in disposicion:
            for tipo, texto, fila, columna, ancho in fila_botones:
                fondo, frente, fondo_hover, frente_hover = estilos[tipo]
                if tipo == "num":
                    comando = lambda d=texto: self.agregar(d)
                elif tipo == "op":
                    interno = operador_de[texto]
                    comando = lambda o=interno: self.agregar_operador(o)
                elif tipo == "igual":
                    comando = self.calcular
                elif tipo == "ac":
                    comando = self.limpiar
                elif tipo == "borrar":
                    comando = self.borrar_ultimo
                else:
                    comando = utilidades[texto]

                boton = tk.Button(
                    self.raiz, text=texto, font=tipografia,
                    bg=fondo, fg=frente,
                    activebackground=fondo_hover, activeforeground=frente_hover,
                    relief="flat", bd=0, highlightthickness=0,
                    cursor="hand2", command=comando,
                )
                boton.grid(
                    row=fila, column=columna, columnspan=ancho,
                    sticky="nsew", padx=3, pady=3,
                )
                self._efecto_hover(boton, fondo, fondo_hover)

        for fila in range(1, 7):
            self.raiz.rowconfigure(fila, weight=1, uniform="btn")
        for columna in range(4):
            self.raiz.columnconfigure(columna, weight=1, uniform="col")

    def _efecto_hover(self, boton, fondo_base, fondo_hover):
        boton.bind("<Enter>", lambda e: boton.config(bg=fondo_hover))
        boton.bind("<Leave>", lambda e: boton.config(bg=fondo_base))


    def teclado(self):
        self.raiz.bind("<Key>", self.tecla)
        self.raiz.bind("<Return>", self.al_calcular)
        self.raiz.bind("<BackSpace>", self.al_borrar)
        self.raiz.bind("<Escape>", self.al_limpiar)
        self.raiz.bind("<Delete>", self.al_limpiar)
        self.raiz.focus_set()

    def tecla(self, evento):
        caracter = evento.char
        if caracter in "0123456789":
            self.agregar(caracter)
        elif caracter in OPERADORES:
            self.agregar_operador(caracter)
        elif caracter == ".":
            self.agregar_punto()
        elif caracter == "%":
            self.aplicar_percent()
        elif caracter == "(":
            self.agregar_par_abre()
        elif caracter == ")":
            self.agregar_par_cierra()
        elif caracter.lower() == "c":
            self.limpiar()
        return "break"

    def al_calcular(self, evento=None):
        self.calcular()
        return "break"

    def al_borrar(self, evento=None):
        self.borrar_ultimo()
        return "break"

    def al_limpiar(self, evento=None):
        self.limpiar()
        return "break"


    def _num_final(self, texto):
        """Devuelve (inicio, numero) del número al final de la expresión."""
        m = re.search(r"(\d+\.?\d*|\.\d+)$", texto)
        if m:
            return m.start(), m.group(0)
        return None, None

    def agregar(self, texto):
        self.expresion += texto
        self.refrescar()

    def agregar_operador(self, operador):
        """Inserta un operador evitando expresiones imposibles.

        - No arranca con + * / (solo − unario).
        - Sobre operador previo: un − extra se comporta como unario (5+−5);
          cualquier otro reemplaza al anterior (5 +1 signo × -> 5×).
        """
        ultimo = self.expresion[-1:]
        if not ultimo or ultimo == "(":
            if operador in "+*/":
                return
        elif ultimo in OPERADORES:
            if operador == "-" and ultimo != "-":
                self.expresion += operador
                self.refrescar()
                return
            self.expresion = self.expresion[:-1] + operador
            self.refrescar()
            return
        self.expresion += operador
        self.refrescar()

    def agregar_par_abre(self):
        self.expresion += "("
        self.refrescar()

    def agregar_par_cierra(self):
        if self.expresion.count("(") > self.expresion.count(")"):
            self.expresion += ")"
            self.refrescar()

    def agregar_punto(self):
        _, numero = self._num_final(self.expresion)
        if numero is None or "." not in numero:
            self.expresion += "."
            self.refrescar()

    def cambiar_signo(self):
        """Cambia el signo del número final: 5 <-> (-5)."""
        texto = self.expresion
        m = re.search(r"\(-(\d+\.?\d*|\.\d+)\)$", texto)
        if m:
            self.expresion = texto[:m.start()] + m.group(1)
        else:
            inicio, numero = self._num_final(texto)
            if numero is None:
                return
            self.expresion = (texto[:inicio] + f"(-{numero})"
                              + texto[inicio + len(numero):])
        self.refrescar()

    def aplicar_percent(self):
        """Convierte el número final en (número/100): 50 % -> 0.5."""
        inicio, numero = self._num_final(self.expresion)
        if numero is None:
            return
        antes = self.expresion[:inicio]
        self.expresion = antes + f"({numero}/100)"
        self.refrescar()

    def borrar_ultimo(self):
        if self.expresion:
            self.expresion = self.expresion[:-1]
            self.refrescar()

    def limpiar(self):
        self.expresion = ""
        self.refrescar()


    def calcular(self):
        if not self.expresion:
            return
        try:
            resultado = evaluar(self.expresion)
        except ZeroDivisionError:
            self.refrescar(aviso="No se puede dividir entre cero")
        except (ValueError, SyntaxError, OverflowError):
            self.refrescar(aviso="Error")
        else:
            self.expresion = formatear(resultado)
            self.refrescar()

    def refrescar(self, aviso=None):
        self.raiz.focus_set()

        visual = self.expresion
        for interno, bonito in (("+", "+"), ("-", "−"), ("*", "×"), ("/", "÷")):
            visual = visual.replace(interno, bonito)
        self.texto_expresion.config(text=visual)

        if aviso is not None:
            self.texto_resultado.config(text=aviso, fg=ROJO)
            return

        if self.expresion:
            try:
                previa = evaluar(self.expresion)
                self.texto_resultado.config(text=formatear(previa), fg=TEXTO_CLARO)
            except Exception:
                self.texto_resultado.config(text="0", fg=TEXTO_GRIS)
        else:
            self.texto_resultado.config(text="0", fg=TEXTO_CLARO)


def main():
    raiz = tk.Tk()
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    Calculadora(raiz)
    ancho, alto = 400, 620
    raiz.update_idletasks()
    x = max((raiz.winfo_screenwidth() - ancho) // 2, 0)
    y = max((raiz.winfo_screenheight() - alto) // 2, 0)
    raiz.geometry(f"{ancho}x{alto}+{x}+{y}")
    raiz.mainloop()


if __name__ == "__main__":
    main()
