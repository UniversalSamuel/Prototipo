"""
Envio de mensagem via Microsoft Teams (UI Automation por acessibilidade) - P&D Univel

Nao usa API/Graph (nao existe ferramenta de envio para Teams neste ambiente).
Usa a arvore de acessibilidade do Windows (UI Automation / pywinauto), achando
elementos pelo NOME ("Digite uma mensagem", "Enviar"), nunca por coordenada de
tela - mais robusto que automacao de tela pura.

Pre-requisito: a conversa certa (com o colaborador certo) precisa estar aberta
e visivel na janela do Teams antes de chamar enviar_mensagem(). Este script
nao abre/busca a conversa - so digita e envia na conversa que ja esta na tela.
Confirme com screenshot (computer-use) qual conversa esta aberta antes de
chamar esta funcao.

Descoberta importante: a janela do Teams precisa estar de fato em primeiro
plano (nao so ter "foco" no sentido da arvore UIA) para a digitacao cair no
lugar certo. Por isso este script forca o primeiro plano via
win32gui.SetForegroundWindow antes de interagir - Samuel autorizou esse uso
em 10/08/2026.

Uso:
    from enviar_teams import enviar_mensagem
    enviar_mensagem("texto da mensagem")
"""

import time

import win32con
import win32gui
from pywinauto import Desktop
from pywinauto.application import Application
from pywinauto.keyboard import send_keys


def _localizar_janela_teams():
    desktop = Desktop(backend="uia")
    for w in desktop.windows():
        if "Microsoft Teams" in w.window_text():
            return w.handle
    raise RuntimeError("Janela do Microsoft Teams nao encontrada - o app esta aberto?")


def _trazer_para_frente(handle) -> None:
    win32gui.ShowWindow(handle, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(handle)
    time.sleep(0.5)
    if win32gui.GetForegroundWindow() != handle:
        raise RuntimeError("Nao foi possivel trazer a janela do Teams para primeiro plano")


def enviar_mensagem(texto: str) -> None:
    handle = _localizar_janela_teams()
    _trazer_para_frente(handle)

    app = Application(backend="uia").connect(handle=handle)
    win = app.window(handle=handle)

    caixas = win.descendants(control_type="Edit")
    if not caixas:
        raise RuntimeError("Caixa de mensagem do Teams nao encontrada")
    caixa = caixas[0]
    caixa.set_focus()

    send_keys("^a{DELETE}")
    caixa.type_keys(texto, with_spaces=True)

    botoes = win.descendants(control_type="Button")
    enviar_btn = next((b for b in botoes if b.element_info.name and "Enviar" in b.element_info.name), None)
    if enviar_btn is None:
        raise RuntimeError("Botao Enviar do Teams nao encontrado")
    enviar_btn.invoke()
