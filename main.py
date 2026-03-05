#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Macro Runner — Automatización de macros de teclado para videojuegos.
Todo en un solo archivo: main.py
"""

import tkinter as tk
import threading
import time
import re

try:
    from pynput.keyboard import Key, Controller as KeyboardController
    _teclado = KeyboardController()
    TECLAS_ESPECIALES = {
        'enter':       Key.enter,       'space':       Key.space,
        'tab':         Key.tab,         'esc':         Key.esc,
        'backspace':   Key.backspace,   'delete':      Key.delete,
        'home':        Key.home,        'end':         Key.end,
        'pageup':      Key.page_up,     'pagedown':    Key.page_down,
        'insert':      Key.insert,      'capslock':    Key.caps_lock,
        'numlock':     Key.num_lock,    'scrolllock':  Key.scroll_lock,
        'printscreen': Key.print_screen,'pause':       Key.pause,
        'ctrl':        Key.ctrl_l,      'alt':         Key.alt_l,
        'shift':       Key.shift,       'win':         Key.cmd,
        'up':          Key.up,          'down':        Key.down,
        'left':        Key.left,        'right':       Key.right,
        'f1':  Key.f1,  'f2':  Key.f2,  'f3':  Key.f3,  'f4':  Key.f4,
        'f5':  Key.f5,  'f6':  Key.f6,  'f7':  Key.f7,  'f8':  Key.f8,
        'f9':  Key.f9,  'f10': Key.f10, 'f11': Key.f11, 'f12': Key.f12,
    }
    PYNPUT_OK = True
except ImportError:
    PYNPUT_OK = False
    TECLAS_ESPECIALES = {}

# ─────────────────────────────────────────────────────────────
# CONSTANTES DE ESTILO
# ─────────────────────────────────────────────────────────────
BG_OSCURO      = "#1e1e1e"
BG_PANEL       = "#252526"
BG_LINEAS      = "#252526"
FG_TEXTO       = "#d4d4d4"
FG_TENUE       = "#858585"
FG_LINEAS      = "#6e6e6e"
COLOR_VERDE    = "#4caf50"
COLOR_ROJO     = "#f44336"
COLOR_AZUL     = "#569cd6"
COLOR_NARANJA  = "#ce9178"
COLOR_VERDE_C  = "#4ec9b0"
COLOR_NUMERO   = "#b5cea8"
COLOR_COMMENT  = "#6a9955"
COLOR_BORDE    = "#3e3e42"
COLOR_SELECC   = "#264f78"
COLOR_STATUS   = "#007acc"

FUENTE_CODIGO  = ("Consolas", 12)
FUENTE_CODIGO_N= ("Consolas", 12, "bold")
FUENTE_UI_N    = ("Segoe UI", 10, "bold")
FUENTE_PEQUEÑA = ("Segoe UI", 9)

# ─────────────────────────────────────────────────────────────
# TOKENIZADOR
# ─────────────────────────────────────────────────────────────
class ErrorSintaxis(Exception):
    pass

class Token:
    def __init__(self, tipo, valor, linea):
        self.tipo  = tipo
        self.valor = valor
        self.linea = linea

def tokenizar(codigo):
    tokens = []
    linea  = 1
    i      = 0
    n      = len(codigo)

    while i < n:
        c = codigo[i]

        if c == '\n':
            linea += 1
            i += 1
            continue

        if c in ' \t\r':
            i += 1
            continue

        # Comentario de línea
        if codigo[i:i+2] == '//':
            while i < n and codigo[i] != '\n':
                i += 1
            continue

        # Comentario de bloque
        if codigo[i:i+2] == '/*':
            i += 2
            while i < n - 1 and codigo[i:i+2] != '*/':
                if codigo[i] == '\n':
                    linea += 1
                i += 1
            i += 2
            continue

        # Cadena de texto
        if c == '"':
            j = i + 1
            while j < n and codigo[j] != '"':
                j += 1
            tokens.append(Token('CADENA', codigo[i+1:j], linea))
            i = j + 1
            continue

        # Número (entero o decimal)
        if c.isdigit() or (c == '.' and i+1 < n and codigo[i+1].isdigit()):
            j = i
            while j < n and (codigo[j].isdigit() or codigo[j] == '.'):
                j += 1
            tokens.append(Token('NUM', float(codigo[i:j]), linea))
            i = j
            continue

        # Operadores dobles
        dos = codigo[i:i+2]
        if dos in ('<=', '>=', '==', '!=', '++', '--'):
            tokens.append(Token(dos, dos, linea))
            i += 2
            continue

        # Identificadores y palabras clave
        if c.isalpha() or c == '_':
            j = i
            while j < n and (codigo[j].isalnum() or codigo[j] == '_'):
                j += 1
            palabra = codigo[i:j]
            PALABRAS_CLAVE = {
                'begin', 'end', 'while', 'if', 'else',
                'press', 'wait', 'number', 'string'
            }
            tipo = ('KW_' + palabra.upper()) if palabra in PALABRAS_CLAVE else 'ID'
            tokens.append(Token(tipo, palabra, linea))
            i = j
            continue

        # Símbolos simples
        simples = {
            '{': 'LLLAV', '}': 'RLLAV',
            '(': 'LPAREN', ')': 'RPAREN',
            ';': 'SEMI', ':': 'DOSPUNTOS',
            ',': 'COMA',  '=': 'IGUAL',
            '<': 'MENOR', '>': 'MAYOR',
            '+': 'MAS',   '-': 'MENOS',
        }
        if c in simples:
            tokens.append(Token(simples[c], c, linea))
            i += 1
            continue

        # Carácter desconocido — ignorar silenciosamente
        i += 1

    tokens.append(Token('FIN', None, linea))
    return tokens

# ─────────────────────────────────────────────────────────────
# PARSER (DESCENSO RECURSIVO)
# ─────────────────────────────────────────────────────────────
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos    = 0

    @property
    def actual(self):
        return self.tokens[self.pos]

    def avanzar(self):
        tok = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return tok

    def esperar(self, tipo, descripcion=''):
        if self.actual.tipo != tipo:
            desc = descripcion or f"'{tipo}'"
            raise ErrorSintaxis(
                f"Línea {self.actual.linea}: "
                f"se esperaba {desc} pero se encontró {str(self.actual.valor)!r}"
            )
        return self.avanzar()

    def es(self, *tipos):
        return self.actual.tipo in tipos

    # ── Reglas de gramática ──────────────────────────────────

    def parsear(self):
        if not self.es('KW_BEGIN'):
            raise ErrorSintaxis(
                f"Línea {self.actual.linea}: el programa debe comenzar con 'begin'"
            )
        self.avanzar()
        cuerpo = self._bloque('KW_END')
        if not self.es('KW_END'):
            raise ErrorSintaxis(
                f"Línea {self.actual.linea}: se esperaba 'end' al final del programa"
            )
        self.avanzar()
        if self.es('SEMI'):
            self.avanzar()
        return {'nodo': 'programa', 'cuerpo': cuerpo}

    def _bloque(self, *terminadores):
        instrucciones = []
        while not self.es(*terminadores, 'FIN'):
            instr = self._instruccion()
            if instr is not None:
                instrucciones.append(instr)
        return instrucciones

    def _instruccion(self):
        tok = self.actual

        # Declaración: nombre : number;
        if tok.tipo == 'ID' and self.tokens[self.pos + 1].tipo == 'DOSPUNTOS':
            return self._declaracion()

        if tok.tipo == 'KW_WHILE':
            return self._while()

        if tok.tipo == 'KW_IF':
            return self._if()

        if tok.tipo == 'KW_PRESS':
            return self._press()

        if tok.tipo == 'KW_WAIT':
            return self._wait()

        if tok.tipo == 'ID':
            return self._asignacion()

        # Token inesperado — saltar para no bloquear el parser
        self.avanzar()
        return None

    def _declaracion(self):
        nombre = self.esperar('ID').valor
        self.esperar('DOSPUNTOS', "':'")
        tipo_var = self.avanzar().valor   # 'number' o 'string'
        self.esperar('SEMI', "';'")
        return {'nodo': 'declarar', 'nombre': nombre, 'tipo_var': tipo_var}

    def _while(self):
        linea = self.actual.linea
        self.esperar('KW_WHILE')
        self.esperar('LPAREN', "'('")
        cond = self._condicion()
        self.esperar('RPAREN', "')'")
        self.esperar('LLLAV', "'{'")
        cuerpo = self._bloque('RLLAV')
        self.esperar('RLLAV', "'}'")
        return {'nodo': 'while', 'condicion': cond, 'cuerpo': cuerpo, 'linea': linea}

    def _if(self):
        linea = self.actual.linea
        self.esperar('KW_IF')
        self.esperar('LPAREN', "'('")
        cond = self._condicion()
        self.esperar('RPAREN', "')'")
        self.esperar('LLLAV', "'{'")
        cuerpo = self._bloque('RLLAV')
        self.esperar('RLLAV', "'}'")
        return {'nodo': 'if', 'condicion': cond, 'cuerpo': cuerpo, 'linea': linea}

    def _press(self):
        linea = self.actual.linea
        self.esperar('KW_PRESS')
        tecla = self.esperar('CADENA', 'tecla entre comillas (ej: "a")').valor
        self.esperar('COMA', "','")
        dur = self._duracion()
        self.esperar('SEMI', "';'")
        return {'nodo': 'press', 'tecla': tecla, 'duracion': dur, 'linea': linea}

    def _wait(self):
        linea = self.actual.linea
        self.esperar('KW_WAIT')
        dur = self._duracion()
        self.esperar('SEMI', "';'")
        return {'nodo': 'wait', 'duracion': dur, 'linea': linea}

    def _duracion(self):
        tok = self.actual
        if tok.tipo != 'NUM':
            raise ErrorSintaxis(
                f"Línea {tok.linea}: se esperaba un número de segundos (ej: 1s)"
            )
        num = tok.valor
        self.avanzar()
        # Consumir 's' u otras unidades opcionales
        if self.es('ID') and self.actual.valor.startswith('s'):
            self.avanzar()
        return num

    def _asignacion(self):
        linea  = self.actual.linea
        nombre = self.esperar('ID').valor

        if self.es('++'):
            self.avanzar()
            self.esperar('SEMI', "';'")
            return {'nodo': 'incr', 'nombre': nombre, 'linea': linea}

        if self.es('--'):
            self.avanzar()
            self.esperar('SEMI', "';'")
            return {'nodo': 'decr', 'nombre': nombre, 'linea': linea}

        if self.es('IGUAL'):
            self.avanzar()
            val = self._expr()
            self.esperar('SEMI', "';'")
            return {'nodo': 'asignar', 'nombre': nombre, 'valor': val, 'linea': linea}

        raise ErrorSintaxis(
            f"Línea {linea}: instrucción inválida para '{nombre}'. "
            f"¿Quiso escribir '{nombre}++;', '{nombre}--;' o '{nombre} = valor;'?"
        )

    def _condicion(self):
        izq = self._expr()
        OPS = {
            'MENOR': '<', 'MAYOR': '>',
            '<=': '<=', '>=': '>=',
            '==': '==', '!=': '!='
        }
        if self.actual.tipo in OPS:
            op = OPS[self.actual.tipo]
            self.avanzar()
            der = self._expr()
            return {'nodo': 'condicion', 'izq': izq, 'op': op, 'der': der}
        return izq

    def _expr(self):
        tok = self.actual
        if tok.tipo == 'NUM':
            self.avanzar()
            return {'nodo': 'numero', 'val': tok.valor}
        if tok.tipo == 'ID':
            self.avanzar()
            return {'nodo': 'var', 'nombre': tok.valor}
        if tok.tipo == 'MENOS':
            self.avanzar()
            tok2 = self.actual
            if tok2.tipo == 'NUM':
                self.avanzar()
                return {'nodo': 'numero', 'val': -tok2.valor}
        raise ErrorSintaxis(
            f"Línea {tok.linea}: expresión inválida: {str(tok.valor)!r}"
        )

# ─────────────────────────────────────────────────────────────
# INTÉRPRETE
# ─────────────────────────────────────────────────────────────
LIMITE_ITER = 100_000

class Interprete:
    def __init__(self, ast, estado_cb=None, evento_stop=None):
        self.ast       = ast
        self.vars      = {}
        self.estado_cb = estado_cb or (lambda m: None)
        self.stop      = evento_stop or threading.Event()

    def ejecutar(self):
        self._bloque(self.ast['cuerpo'])

    def _bloque(self, instrucciones):
        for instr in instrucciones:
            if self.stop.is_set():
                return
            self._instr(instr)

    def _instr(self, nodo):
        tipo = nodo['nodo']

        if tipo == 'declarar':
            self.vars[nodo['nombre']] = 0

        elif tipo == 'while':
            iters = 0
            while self._cond(nodo['condicion']):
                if self.stop.is_set():
                    return
                iters += 1
                if iters > LIMITE_ITER:
                    raise RuntimeError(
                        f"Bucle infinito detectado (>{LIMITE_ITER:,} iteraciones)"
                    )
                self._bloque(nodo['cuerpo'])

        elif tipo == 'if':
            if self._cond(nodo['condicion']):
                self._bloque(nodo['cuerpo'])

        elif tipo == 'press':
            tecla = nodo['tecla']
            dur   = nodo['duracion']
            self.estado_cb(f"▶ Presionando '{tecla}' — {dur}s")
            self._presionar(tecla, dur)

        elif tipo == 'wait':
            dur = nodo['duracion']
            self.estado_cb(f"⏳ Esperando {dur}s")
            self._dormir(dur)

        elif tipo == 'incr':
            n = nodo['nombre']
            self.vars[n] = self.vars.get(n, 0) + 1
            self.estado_cb(f"{n}++ → {self.vars[n]}")

        elif tipo == 'decr':
            n = nodo['nombre']
            self.vars[n] = self.vars.get(n, 0) - 1
            self.estado_cb(f"{n}-- → {self.vars[n]}")

        elif tipo == 'asignar':
            n = nodo['nombre']
            v = self._expr(nodo['valor'])
            self.vars[n] = v
            self.estado_cb(f"{n} = {v}")

    def _expr(self, nodo):
        if nodo['nodo'] == 'numero':
            return nodo['val']
        if nodo['nodo'] == 'var':
            return self.vars.get(nodo['nombre'], 0)
        return 0

    def _cond(self, nodo):
        if nodo.get('nodo') != 'condicion':
            return bool(self._expr(nodo))
        izq = self._expr(nodo['izq'])
        der = self._expr(nodo['der'])
        op  = nodo['op']
        return (izq <  der if op == '<'  else
                izq >  der if op == '>'  else
                izq <= der if op == '<=' else
                izq >= der if op == '>=' else
                izq == der if op == '==' else
                izq != der if op == '!=' else False)

    def _presionar(self, tecla, dur):
        if not PYNPUT_OK:
            self._dormir(dur)
            return
        partes = [t.strip().lower() for t in tecla.split('+')]
        keys   = [TECLAS_ESPECIALES.get(t, t) for t in partes]
        try:
            for k in keys:
                _teclado.press(k)
            self._dormir(dur)
        finally:
            for k in reversed(keys):
                try:
                    _teclado.release(k)
                except Exception:
                    pass

    def _dormir(self, segundos):
        paso  = 0.05
        acum  = 0.0
        while acum < segundos:
            if self.stop.is_set():
                return
            dt = min(paso, segundos - acum)
            time.sleep(dt)
            acum += dt

# ─────────────────────────────────────────────────────────────
# WIDGET: EDITOR CON NUMERACIÓN DE LÍNEAS Y SINTAXIS
# ─────────────────────────────────────────────────────────────
class EditorConLineas(tk.Frame):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG_OSCURO, **kw)
        self._construir()
        self._configurar_tags()
        self._vincular_eventos()

    def _construir(self):
        self.lineas = tk.Text(
            self, width=4, padx=8, pady=6,
            bg=BG_LINEAS, fg=FG_LINEAS,
            font=FUENTE_CODIGO, state='disabled',
            relief='flat', cursor='arrow',
            selectbackground=BG_LINEAS,
            selectforeground=FG_LINEAS,
            takefocus=False, bd=0
        )
        self.lineas.pack(side='left', fill='y')

        self.barra = tk.Scrollbar(self, bg=BG_PANEL)
        self.barra.pack(side='right', fill='y')

        self.texto = tk.Text(
            self, bg=BG_OSCURO, fg=FG_TEXTO,
            font=FUENTE_CODIGO,
            insertbackground=FG_TEXTO,
            selectbackground=COLOR_SELECC,
            pady=6, padx=8, relief='flat',
            undo=True, wrap='none', bd=0,
            yscrollcommand=self._al_scroll,
            tabs=('1c',)
        )
        self.texto.pack(side='left', fill='both', expand=True)
        self.barra.config(command=self._scroll_sincro)

    def _configurar_tags(self):
        self.texto.tag_configure('kw',      foreground=COLOR_AZUL,    font=FUENTE_CODIGO_N)
        self.texto.tag_configure('cadena',  foreground=COLOR_NARANJA)
        self.texto.tag_configure('numero',  foreground=COLOR_NUMERO)
        self.texto.tag_configure('comment', foreground=COLOR_COMMENT,
                                            font=("Consolas", 12, "italic"))
        self.texto.tag_configure('op',      foreground=COLOR_VERDE_C)

    def _vincular_eventos(self):
        self.texto.bind('<KeyRelease>',    self._actualizar)
        self.texto.bind('<ButtonRelease>', self._actualizar)
        self.texto.bind('<Return>',        self._auto_indent)
        self.texto.bind('<Tab>',           self._insertar_tab)

    def _al_scroll(self, *args):
        self.barra.set(*args)
        self.lineas.yview_moveto(args[0])

    def _scroll_sincro(self, *args):
        self.texto.yview(*args)
        self.lineas.yview(*args)

    def _auto_indent(self, _=None):
        pos    = self.texto.index('insert')
        linea  = self.texto.get(f'{pos} linestart', pos)
        sangria = ''
        for c in linea:
            if c in ' \t':
                sangria += c
            else:
                break
        if linea.rstrip().endswith('{'):
            sangria += '    '
        self.texto.insert('insert', '\n' + sangria)
        return 'break'

    def _insertar_tab(self, _=None):
        self.texto.insert('insert', '    ')
        return 'break'

    def _actualizar(self, _=None):
        self._actualizar_lineas()
        self._resaltar()

    def _actualizar_lineas(self):
        self.lineas.config(state='normal')
        self.lineas.delete('1.0', 'end')
        total = int(self.texto.index('end-1c').split('.')[0])
        nums  = '\n'.join(str(i) for i in range(1, total + 1))
        self.lineas.insert('1.0', nums)
        self.lineas.config(state='disabled')

    def _resaltar(self):
        for tag in ('kw', 'cadena', 'numero', 'comment', 'op'):
            self.texto.tag_remove(tag, '1.0', 'end')

        contenido = self.texto.get('1.0', 'end')

        patrones = [
            ('kw',      r'\b(begin|end|while|if|else|press|wait|number|string)\b'),
            ('comment', r'//[^\n]*'),
            ('comment', r'/\*[\s\S]*?\*/'),
            ('cadena',  r'"[^"]*"'),
            ('numero',  r'\b\d+(?:\.\d+)?\b'),
            ('op',      r'\+\+|--|<=|>=|==|!=|[<>=]'),
        ]
        for tag, patron in patrones:
            for m in re.finditer(patron, contenido):
                ini = self._offset(contenido, m.start())
                fin = self._offset(contenido, m.end())
                self.texto.tag_add(tag, ini, fin)

    @staticmethod
    def _offset(texto, offset):
        linea  = texto[:offset].count('\n') + 1
        ultimo = texto[:offset].rfind('\n')
        col    = offset - (ultimo + 1)
        return f'{linea}.{col}'

    def get_codigo(self):
        return self.texto.get('1.0', 'end-1c')

    def set_codigo(self, codigo):
        self.texto.delete('1.0', 'end')
        self.texto.insert('1.0', codigo)
        self._actualizar()

# ─────────────────────────────────────────────────────────────
# CONTENIDO DE TEXTO ESTÁTICO
# ─────────────────────────────────────────────────────────────
EJEMPLO = """\
begin
  n : number;
  n = 0;

  while (n < 5) {
    press "a", 1s;
    wait 0.5s;
    n++;
  }

  if (n == 5) {
    press "enter", 0.1s;
  }
end;\
"""

REFERENCIA = """\
╔════════════════════════════╗
║   REFERENCIA DE COMANDOS   ║
╚════════════════════════════╝

▶ ESTRUCTURA
  begin
    ...
  end;

▶ VARIABLES
  n : number;

▶ BUCLES
  while (n < 10) {
    ...
  }

  Operadores:
  <   >   <=   >=   ==   !=

▶ CONDICIONALES
  if (n == 10) {
    ...
  }

▶ PRESIONAR TECLA
  press "a", 1s;
  press "ctrl+c", 0.5s;
  press "shift+tab", 0.1s;

  ── Teclas especiales ──────────

  Flechas:
    up        down
    left      right

  Control:
    esc       tab
    enter     space
    backspace delete
    home      end
    pageup    pagedown
    insert    capslock
    numlock   scrolllock
    printscreen pause

  Modificadores:
    ctrl      alt       shift
    win

  Función:
    f1   f2   f3   f4
    f5   f6   f7   f8
    f9   f10  f11  f12

  Combinaciones de ejemplo:
    press "ctrl+c", 0.1s;
    press "ctrl+v", 0.1s;
    press "ctrl+z", 0.1s;
    press "alt+tab", 0.5s;
    press "alt+f4", 0.1s;
    press "ctrl+alt+del", 1s;
    press "shift+a", 0.5s;
    press "ctrl+shift+esc", 0.1s;

▶ ESPERA
  wait 2s;
  wait 0.5s;

▶ OPERACIONES
  n++;       incremento
  n--;       decremento
  n = 5;     asignación

▶ COMENTARIOS
  // comentario de línea
  /* bloque de comentario */

▶ NOTA
  La app se minimiza y espera
  3 segundos antes de ejecutar.
  Mueve el cursor al juego
  durante ese tiempo.
"""

# ─────────────────────────────────────────────────────────────
# APLICACIÓN PRINCIPAL
# ─────────────────────────────────────────────────────────────
class MacroRunner:
    def __init__(self, root: tk.Tk):
        self.root       = root
        self.hilo       = None
        self.stop_evt   = threading.Event()
        self.ejecutando = False

        root.title("Macro Runner")
        root.geometry("1100x700")
        root.minsize(800, 500)
        root.configure(bg=BG_OSCURO)

        self._construir_ui()
        self.editor.set_codigo(EJEMPLO)

    # ── Construcción de la UI ────────────────────────────────
    def _construir_ui(self):
        # Barra superior
        top = tk.Frame(self.root, bg=BG_PANEL, height=52)
        top.pack(fill='x', side='top')
        top.pack_propagate(False)

        tk.Label(
            top, text="⚙ MACRO RUNNER",
            bg=BG_PANEL, fg=FG_TEXTO,
            font=("Segoe UI", 13, "bold"), padx=16
        ).pack(side='left', pady=12)

        self.btn_stop = tk.Button(
            top, text="■  DETENER",
            bg=COLOR_ROJO, fg='white',
            font=FUENTE_UI_N, relief='flat',
            padx=20, pady=5, cursor='hand2',
            activebackground="#c62828", activeforeground='white',
            command=self.detener, state='disabled'
        )
        self.btn_stop.pack(side='right', padx=(4, 16), pady=12)

        self.btn_run = tk.Button(
            top, text="▶  EJECUTAR",
            bg=COLOR_VERDE, fg='white',
            font=FUENTE_UI_N, relief='flat',
            padx=20, pady=5, cursor='hand2',
            activebackground="#388e3c", activeforeground='white',
            command=self.iniciar
        )
        self.btn_run.pack(side='right', padx=4, pady=12)

        # Paneles principales
        paneles = tk.PanedWindow(
            self.root, orient='horizontal',
            bg=COLOR_BORDE, sashwidth=4, sashpad=0, relief='flat'
        )
        paneles.pack(fill='both', expand=True)

        # Panel izquierdo: editor
        frame_ed = tk.Frame(paneles, bg=BG_OSCURO)
        tk.Label(
            frame_ed, text="  EDITOR DE PSEUDOCÓDIGO",
            bg=BG_PANEL, fg=FG_TENUE,
            font=FUENTE_PEQUEÑA, anchor='w', pady=5
        ).pack(fill='x')
        self.editor = EditorConLineas(frame_ed)
        self.editor.pack(fill='both', expand=True)
        paneles.add(frame_ed, minsize=420, stretch='always')

        # Panel derecho: referencia
        frame_ref = tk.Frame(paneles, bg=BG_PANEL)
        tk.Label(
            frame_ref, text="  REFERENCIA DE COMANDOS",
            bg=BG_PANEL, fg=FG_TENUE,
            font=FUENTE_PEQUEÑA, anchor='w', pady=5
        ).pack(fill='x')
        ref_scroll = tk.Scrollbar(frame_ref, bg=BG_PANEL)
        ref_scroll.pack(side='right', fill='y')
        ref = tk.Text(
            frame_ref, bg=BG_PANEL, fg="#9a9a9a",
            font=("Consolas", 10), relief='flat',
            padx=14, pady=8, wrap='word', bd=0,
            cursor='arrow', yscrollcommand=ref_scroll.set
        )
        ref.pack(fill='both', expand=True)
        ref_scroll.config(command=ref.yview)
        ref.insert('1.0', REFERENCIA)
        ref.config(state='disabled')
        paneles.add(frame_ref, minsize=260, stretch='never')

        # Barra de estado inferior
        self.frame_status = tk.Frame(self.root, bg=COLOR_STATUS, height=28)
        self.frame_status.pack(fill='x', side='bottom')
        self.frame_status.pack_propagate(False)

        self.lbl_status = tk.Label(
            self.frame_status, text="  Listo.",
            bg=COLOR_STATUS, fg='white',
            font=FUENTE_PEQUEÑA, anchor='w'
        )
        self.lbl_status.pack(fill='x', padx=8, pady=4)

    # ── Actualización de estado (thread-safe) ────────────────
    def set_status(self, msg, bg=None):
        def _upd():
            color = bg or COLOR_STATUS
            self.frame_status.config(bg=color)
            self.lbl_status.config(text=f"  {msg}", bg=color)
        self.root.after(0, _upd)

    # ── Lógica de ejecución ──────────────────────────────────
    def iniciar(self):
        if self.ejecutando:
            return
        codigo = self.editor.get_codigo()

        # Parsear antes de lanzar el hilo
        try:
            tokens = tokenizar(codigo)
            ast    = Parser(tokens).parsear()
        except ErrorSintaxis as e:
            self.set_status(f"❌ Error de sintaxis: {e}", "#8b0000")
            self.root.after(5000, lambda: self.set_status("Listo."))
            return

        self.ejecutando = True
        self.stop_evt.clear()
        self.btn_run.config(state='disabled')
        self.btn_stop.config(state='normal')
        self.set_status("⏳ Iniciando…", "#c17f00")

        self.hilo = threading.Thread(
            target=self._hilo_ejecucion, args=(ast,), daemon=True
        )
        self.hilo.start()

    def _hilo_ejecucion(self, ast):
        try:
            # Minimizar para no tapar el juego
            self.root.after(0, self.root.iconify)

            # Countdown de 3 segundos
            for i in range(3, 0, -1):
                if self.stop_evt.is_set():
                    return
                self.set_status(f"⏳ Empezando en {i}…", "#c17f00")
                time.sleep(1)

            if self.stop_evt.is_set():
                return

            self.set_status("▶ Ejecutando macro…")
            interprete = Interprete(
                ast,
                estado_cb=lambda m: self.set_status(m),
                evento_stop=self.stop_evt
            )
            interprete.ejecutar()

            if not self.stop_evt.is_set():
                self.set_status("✅ Ejecución completada.")

        except Exception as e:
            self.set_status(f"❌ Error en ejecución: {e}", "#8b0000")
        finally:
            self.root.after(0, self._finalizar)
            # Restaurar ventana
            self.root.after(600, self.root.deiconify)

    def _finalizar(self):
        self.ejecutando = False
        self.btn_run.config(state='normal')
        self.btn_stop.config(state='disabled')
        self.frame_status.config(bg=COLOR_STATUS)
        self.lbl_status.config(bg=COLOR_STATUS)

    def detener(self):
        self.stop_evt.set()
        self.set_status("⏹ Detenido por el usuario.")

# ─────────────────────────────────────────────────────────────
# ENTRADA PRINCIPAL
# ─────────────────────────────────────────────────────────────
def main():
    root = tk.Tk()
    MacroRunner(root)
    root.mainloop()

if __name__ == '__main__':
    main()
