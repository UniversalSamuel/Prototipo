"""
Envio de e-mail via Outlook classico (COM/Interop) - P&D Univel

Nao usa Microsoft Graph API nem exige nenhuma permissao/consentimento de
administrador no Entra. Controla o Outlook classico ja aberto e autenticado
como o proprio Samuel, via win32com.client (pywin32) - o mesmo mecanismo que
macros VBA do Office usam.

So funciona com o Outlook classico (Win32), nao com o "Novo Outlook". Se
Samuel migrar pro Novo Outlook, esse metodo para de funcionar e precisa ser
reavaliado (ver CLAUDE.md, secao "Como enviar mensagens").

Desde 10/08/2026: como o Teams nao tem como enviar sem a janela em primeiro
plano (nao da pra automatizar sem interromper Samuel), atividades urgentes
tambem sao roteadas por aqui, sinalizadas com importancia alta e prefixo
"URGENTE" no assunto (ver parametro `urgente`).

Uso:
    python enviar_outlook.py destinatario@dominio.com "Assunto" "Corpo da mensagem"

Ou importado:
    from enviar_outlook import enviar
    enviar("destinatario@dominio.com", "Assunto", "Corpo da mensagem")
    enviar("destinatario@dominio.com", "Assunto", "Corpo da mensagem", urgente=True)
"""

import sys

import win32com.client

IMPORTANCIA_ALTA = 2  # olImportanceHigh


def enviar(destinatario: str, assunto: str, corpo: str, urgente: bool = False) -> None:
    outlook = win32com.client.Dispatch("Outlook.Application")
    mail = outlook.CreateItem(0)  # 0 = olMailItem
    mail.To = destinatario
    mail.Subject = f"URGENTE - {assunto}" if urgente else assunto
    mail.Body = corpo
    if urgente:
        mail.Importance = IMPORTANCIA_ALTA
    mail.Send()


if __name__ == "__main__":
    if len(sys.argv) not in (4, 5):
        print("Uso: python enviar_outlook.py destinatario assunto corpo [urgente]", file=sys.stderr)
        sys.exit(1)
    urgente = len(sys.argv) == 5 and sys.argv[4].lower() in ("urgente", "1", "true")
    enviar(sys.argv[1], sys.argv[2], sys.argv[3], urgente=urgente)
    print("Enviado com sucesso")
