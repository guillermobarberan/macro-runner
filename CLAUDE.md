# Macro Runner — CLAUDE.md

## Stack
- Python 3.13
- tkinter para la interfaz gráfica
- pyautogui para simular pulsaciones de teclado reales

## Propósito
App de escritorio para escribir pseudocódigo y ejecutar macros de teclado reales en Windows. Útil para automatizar acciones en videojuegos.

## Sintaxis del pseudocódigo
begin
  n : number;

while (n < 10) {
  press "A", 1s;
  press "B", 1s;
  n++;
}

if (n == 10) {
}
end;

## Reglas de código
- Todo en un solo archivo: main.py
- Comentarios en español
- Interfaz oscura profesional
- El parser del pseudocódigo debe ser robusto ante errores de sintaxis

## Lo que NO hacer
- No usar librerías externas fuera de tkinter y pyautogui
- No crear múltiples archivos innecesarios