import glob
import os
import shutil
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.textinput import TextInput
from kivy.utils import get_color_from_hex as hx, platform

try:
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
except Exception:
    pass

ROXO = hx("#8b5cf6")
CARD = hx("#232333")
SUAVE = hx("#a1a1aa")
VERDE = hx("#22c55e")
VERMELHO = hx("#ef4444")
BRANCO = (1, 1, 1, 1)
EXTS = (".m4a", ".mp3", ".opus", ".webm", ".mp4", ".ogg")

Window.clearcolor = hx("#0f0f14")


def achar_destino():
    """Pasta publica de musicas; None se o Android nao deixar escrever."""
    if platform == "android":
        base = "/storage/emulated/0"
        for sub in ("Music/BaixarMusica", "Download/BaixarMusica"):
            pasta = os.path.join(base, sub)
            teste = os.path.join(pasta, "._teste.m4a")
            try:
                os.makedirs(pasta, exist_ok=True)
                open(teste, "w").close()
                os.remove(teste)
                return pasta
            except Exception:
                continue
        return None
    return os.path.join(os.path.expanduser("~"), "Music", "BaixarMusica")


def avisar_galeria(caminho):
    """Pede ao Android para indexar o arquivo, assim ele aparece no player."""
    if platform != "android":
        return
    try:
        from jnius import autoclass
        atividade = autoclass("org.kivy.android.PythonActivity").mActivity
        scanner = autoclass("android.media.MediaScannerConnection")
        scanner.scanFile(atividade, [caminho], None, None)
    except Exception:
        pass
    class MainApp(App):
    title = "Baixar Musica"

    def build(self):
        if platform == "android":
            try:
                from android.permissions import Permission, request_permissions
                request_permissions([Permission.WRITE_EXTERNAL_STORAGE,
                                     Permission.READ_EXTERNAL_STORAGE])
            except Exception:
                pass

        raiz = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(14))
        raiz.add_widget(Label(text="Baixar Música", font_size=sp(28), bold=True,
                              size_hint_y=None, height=dp(70)))

        self.entry = TextInput(hint_text="Cole o link do YouTube", multiline=False,
                               size_hint_y=None, height=dp(52), background_color=CARD,
                               foreground_color=BRANCO, hint_text_color=SUAVE,
                               cursor_color=ROXO, padding=[dp(12), dp(14)])
        raiz.add_widget(self.entry)

        linha = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10))
        linha.add_widget(self._botao("Colar", self.colar, CARD))
        self.btn = self._botao("Baixar", self.baixar, ROXO)
        linha.add_widget(self.btn)
        raiz.add_widget(linha)

        self.barra = ProgressBar(max=100, value=0, size_hint_y=None, height=dp(10))
        raiz.add_widget(self.barra)

        self.status = Label(text="Cole um link e toque em Baixar.", color=SUAVE,
                            halign="center", valign="top")
        self.status.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
        raiz.add_widget(self.status)
        return raiz

    def _botao(self, texto, acao, cor):
        return Button(text=texto, bold=True, font_size=sp(16), background_normal="",
                      background_color=cor, on_release=acao)

    def colar(self, *args):
        try:
            self.entry.text = (Clipboard.paste() or "").strip()
        except Exception:
            pass
                def baixar(self, *args):
        url = self.entry.text.strip()
        if not url:
            self._ui(0, "Cole um link primeiro.", VERMELHO)
            return
        self.btn.disabled = True
        self._ui(0, "Buscando...", SUAVE)
        threading.Thread(target=self._baixar, args=(url,), daemon=True).start()

    def _ui(self, pct, texto, cor=SUAVE):
        def aplicar(dt):
            self.barra.value = pct
            self.status.text = texto
            self.status.color = cor
        Clock.schedule_once(aplicar, 0)

    def _hook(self, d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            pct = min(d.get("downloaded_bytes", 0) / total * 100, 100) if total else 0
            self._ui(pct, f"Baixando... {pct:.0f}%")
        elif d["status"] == "finished":
            self._ui(100, "Salvando...")
                def _baixar(self, url):
        try:
            import yt_dlp

            tmp = os.path.join(self.user_data_dir, "tmp")
            shutil.rmtree(tmp, ignore_errors=True)
            os.makedirs(tmp, exist_ok=True)

            opcoes = {
                "format": "bestaudio[ext=m4a]/bestaudio/best",
                "outtmpl": os.path.join(tmp, "%(title).80s.%(ext)s"),
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "cachedir": False,
                "windowsfilenames": True,
                "progress_hooks": [self._hook],
            }
            with yt_dlp.YoutubeDL(opcoes) as ydl:
                ydl.download([url])

            destino = achar_destino()
            if destino is None:
                destino = os.path.join(self.user_data_dir, "musicas")
                os.makedirs(destino, exist_ok=True)

            salvos = []
            for arq in glob.glob(os.path.join(tmp, "*")):
                if arq.lower().endswith(EXTS):
                    final = os.path.join(destino, os.path.basename(arq))
                    shutil.copyfile(arq, final)
                    avisar_galeria(final)
                    salvos.append(final)
            shutil.rmtree(tmp, ignore_errors=True)

            if not salvos:
                raise RuntimeError("Nenhum arquivo de áudio foi gerado.")
            self._ui(100, f"Pronto!\nSalvo em:\n{destino}", VERDE)
        except Exception as e:
            self._ui(0, f"Erro: {str(e)[:200]}", VERMELHO)
        finally:
            Clock.schedule_once(lambda dt: setattr(self.btn, "disabled", False), 0)


if __name__ == "__main__":
    MainApp().run()
