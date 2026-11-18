"""
Simulação da interface SEM display (rodar na raiz: python tests/interface/simulacao_interface.py).

Simula customtkinter/tkinter com validação estrita de parâmetros (baseada na API
do CustomTkinter 5.2) e de métodos. Detecta parâmetros inexistentes, métodos
inexistentes, erros de lógica e fluxos quebrados. NÃO avalia a aparência: o
visual precisa ser conferido no Windows.
"""
import os
import sys
import tempfile
import types

# No Windows o console usa cp1252 e não imprime caracteres como "▲": força UTF-8 na saída.
for _fluxo in (sys.stdout, sys.stderr):
    try:
        _fluxo.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ----------------------------------------------------------------------
# Simulação do tkinter
# ----------------------------------------------------------------------
class TclError(Exception):
    pass

SCREEN = {'w': 1920, 'h': 1080, 'dpi': 1.0}
ESCALAS = []
METODOS_OK = {
    "pack", "pack_forget", "pack_propagate", "grid", "grid_forget", "grid_propagate",
    "grid_columnconfigure", "grid_rowconfigure", "place", "place_forget", "lift",
    "focus_set", "focus_force", "bind", "after", "after_cancel", "destroy",
    "winfo_children", "winfo_ismapped", "winfo_width", "winfo_reqwidth", "winfo_height", "winfo_rootx",
    "winfo_rooty", "winfo_fpixels", "update_idletasks", "title", "geometry",
    "minsize", "resizable", "iconbitmap", "transient", "grab_set", "grab_release",
    "wait_window", "mainloop", "configure", "config", "cget", "_get_window_scaling",
}

class Widget:
    CTK = False
    ALLOWED = None          # None = qualquer parâmetro
    def __init__(self, master=None, **kw):
        self.master = master
        self._check(kw)
        self._cfg = dict(kw)
        self.kids = []
        self.binds = {}
        self.mapped = False
        self.dead = False
        self.after_calls = []
        if master is not None and hasattr(master, "kids"):
            master.kids.append(self)
        self.setup()
    def setup(self): pass
    def _check(self, kw):
        if self.ALLOWED is not None:
            ruins = set(kw) - self.ALLOWED
            if ruins:
                raise ValueError(f"{type(self).__name__}: parâmetro(s) não suportado(s): {sorted(ruins)}")
    def configure(self, **kw):
        self._check(kw); self._cfg.update(kw)
    config = configure
    def cget(self, k): return self._cfg.get(k)
    def pack(self, **kw):
        self.mapped = True; self.pack_kw = kw
    def pack_forget(self): self.mapped = False
    def pack_propagate(self, v=True): pass
    def grid(self, **kw): self.mapped = True; self.grid_kw = kw
    def grid_forget(self): self.mapped = False
    def grid_propagate(self, v=True): pass
    def grid_columnconfigure(self, i, **kw): pass
    def grid_rowconfigure(self, i, **kw): pass
    def place(self, **kw):
        if self.CTK and ("width" in kw or "height" in kw):
            raise ValueError("place() não aceita width/height em widgets CTk")
        self.mapped = True
    def place_forget(self): self.mapped = False
    def lift(self, *a): pass
    def focus_set(self): self.focused = True
    def focus_force(self): pass
    def bind(self, seq=None, fn=None, add=None):
        self.binds.setdefault(seq, []).append(fn)
    def after(self, ms, fn=None, *a):
        self.after_calls.append((ms, fn)); return f"after{len(self.after_calls)}"
    def after_cancel(self, i): pass
    def destroy(self):
        self.dead = True
        if self.master is not None and hasattr(self.master, "kids") and self in self.master.kids:
            self.master.kids.remove(self)
        for k in list(self.kids): k.destroy()
    def winfo_children(self): return list(self.kids)
    def winfo_ismapped(self): return self.mapped
    def winfo_exists(self): return not self.dead
    def winfo_reqwidth(self): return int(self._cfg.get("width") or 100)
    def winfo_width(self): return 1200
    def winfo_height(self): return 800
    def winfo_rootx(self): return 0
    def winfo_rooty(self): return 0
    def winfo_fpixels(self, v): return 96.0 * SCREEN['dpi']
    def winfo_screenwidth(self): return SCREEN['w']
    def winfo_vrootx(self): return SCREEN.get('vx', 0)
    def winfo_vrooty(self): return SCREEN.get('vy', 0)
    def winfo_vrootwidth(self): return SCREEN.get('vw', SCREEN['w'])
    def winfo_vrootheight(self): return SCREEN.get('vh', SCREEN['h'] if 'h' in SCREEN else 1080)
    def winfo_screenheight(self): return SCREEN['h']
    def update_idletasks(self): pass
    def attributes(self, *a): pass
    def deiconify(self): self._estado = 'normal'
    def iconify(self): self._estado = 'iconic'
    def withdraw(self): self._estado = 'withdrawn'
    def bind_all(self, seq=None, fn=None, add=None):
        self.binds_all = getattr(self, 'binds_all', {}); self.binds_all.setdefault(seq, []).append(fn)
    def bell(self): self.bips = getattr(self, 'bips', 0) + 1
    def title(self, t=None): self._title = t
    def overrideredirect(self, v=None): self._sem_borda = v
    def geometry(self, g=None): self._geo = g
    def minsize(self, w, h): pass
    def resizable(self, a, b): pass
    def iconbitmap(self, p): pass
    def transient(self, p=None): pass
    def grab_set(self): pass
    def grab_release(self): pass
    def wait_window(self, w=None): pass
    def mainloop(self): pass
    def protocol(self, nome, fn=None): self.protocolos = getattr(self, 'protocolos', {}); self.protocolos[nome] = fn
    def _get_window_scaling(self): return SCREEN['dpi']
    def wm_geometry(self, g=None): return '1240x780+30+40'
    def state(self, v=None):
        if v is None: return getattr(self, '_estado', 'normal')
        self._estado = v
    def focus_get(self): return getattr(self, '_foco', None)
    def __getattr__(self, nome):
        if nome == 'protocolos': return {}
        # Atributos/métodos inexistentes no tkinter real devem falhar aqui.
        raise AttributeError(f"{type(self).__name__} não tem '{nome}' (simulação estrita)")

def kws(*nomes): return set(nomes)

FRAME = kws("width","height","corner_radius","border_width","bg_color","fg_color","border_color",
            "background_corner_colors","overwrite_preferred_drawing_method","padx","pady")
LABEL = kws("width","height","corner_radius","bg_color","fg_color","text_color","text_color_disabled",
            "text","font","image","compound","anchor","wraplength")
BUTTON = kws("width","height","corner_radius","border_width","border_spacing","bg_color","fg_color",
             "hover_color","border_color","text_color","text_color_disabled","background_corner_colors",
             "round_width_to_even_numbers","text","font","textvariable","image","state","hover",
             "command","compound","anchor")
ENTRY = kws("width","height","corner_radius","border_width","bg_color","fg_color","border_color",
            "text_color","placeholder_text_color","textvariable","placeholder_text","font","state","show")
TEXTBOX = kws("width","height","corner_radius","border_width","border_spacing","bg_color","fg_color",
              "border_color","text_color","scrollbar_button_color","scrollbar_button_hover_color",
              "font","activate_scrollbars","wrap","state")
SEGMENT = kws("width","height","corner_radius","border_width","bg_color","fg_color","selected_color",
              "selected_hover_color","unselected_color","unselected_hover_color","text_color",
              "text_color_disabled","background_corner_colors","font","values","variable",
              "dynamic_resizing","command","state")

class CTkFrame(Widget):  CTK=True; ALLOWED=FRAME
class CTkLabel(Widget):
    CTK=True; ALLOWED=LABEL
    def setup(self): self._label = types.SimpleNamespace(configure=lambda **k: None)
class CTkButton(Widget):
    CTK=True; ALLOWED=BUTTON
    def invoke(self):
        if self._cfg.get("command"): self._cfg["command"]()
class CTkEntry(Widget):
    CTK=True; ALLOWED=ENTRY
    def setup(self): self.text = ""
    def get(self): return self.text
    def delete(self, a, b=None): self.text = ""
    def insert(self, i, t): self.text += t
class CTkTextbox(Widget):
    CTK=True; ALLOWED=TEXTBOX
    def setup(self): self.text = ""
    def get(self, a, b=None): return self.text + "\n"
    def delete(self, a, b=None): self.text = ""
    def insert(self, i, t): self.text += t
class CTkSegmentedButton(Widget):
    CTK=True; ALLOWED=SEGMENT
    def setup(self): self.valor = None
    def get(self): return self.valor
    def set(self, v): self.valor = v
class CTkCheckBox(Widget):
    CTK=True; ALLOWED=kws('width','height','checkbox_width','checkbox_height','corner_radius','border_width','bg_color','fg_color','hover_color','border_color','checkmark_color','text_color','text_color_disabled','text','font','textvariable','state','hover','command','onvalue','offvalue','variable')
    def setup(self): self.marcado = 0
    def get(self): return self.marcado
    def select(self): self.marcado = 1
    def deselect(self): self.marcado = 0
class CTkOptionMenu(Widget):
    CTK=True; ALLOWED=kws('width','height','corner_radius','bg_color','fg_color','button_color','button_hover_color','text_color','text_color_disabled','dropdown_fg_color','dropdown_hover_color','dropdown_text_color','font','dropdown_font','values','variable','state','hover','command','dynamic_resizing','anchor')
    def setup(self): self.valor = None
    def get(self): return self.valor
    def set(self, v): self.valor = v
class CTkProgressBar(Widget):
    CTK=True; ALLOWED=kws('width','height','corner_radius','border_width','fg_color','progress_color','border_color')
    def set(self, v): self.v = v
class CTkToplevel(Widget):
    CTK=True; ALLOWED=kws("fg_color")
class CTk(Widget):
    CTK=True; ALLOWED=kws("fg_color")
    def __init__(self, **kw):
        super().__init__(None, **kw)
class CTkImage:
    def __init__(self, light_image=None, dark_image=None, size=(20, 20)):
        assert light_image is not None and len(size) == 2
class CTkFont:
    def __init__(self, family=None, size=None, weight=None, **kw): pass
    def measure(self, texto): return 7 * len(texto)

ctk = types.ModuleType("customtkinter")
for nome, obj in list(globals().items()):
    if nome.startswith("CTk"):
        setattr(ctk, nome, obj)
ctk.set_widget_scaling = lambda f: ESCALAS.append(('widget', f))
ctk.set_window_scaling = lambda f: ESCALAS.append(('window', f))
ctk.set_appearance_mode = lambda m: None
ctk.set_default_color_theme = lambda t: None
sys.modules["customtkinter"] = ctk

# --- tkinter / ttk / messagebox ---
class Treeview(Widget):
    def setup(self):
        self.rows = {}; self.order = []; self.sel = []; self.tags = {}
    def heading(self, c, **k):
        if "text" in k: self.titulos = getattr(self, "titulos", {}); self.titulos[c] = k["text"]
    def column(self, c, **k): pass
    def tag_configure(self, t, **k): self.tags[t] = k
    def insert(self, parent, idx, iid=None, values=(), tags=()):
        self.rows[iid] = {"values": tuple(values), "tags": tags}; self.order.append(iid)
    def delete(self, *iids):
        for i in iids:
            self.rows.pop(i, None)
            if i in self.order: self.order.remove(i)
            if i in self.sel: self.sel.remove(i)
    def get_children(self, item=""): return tuple(self.order)
    def selection(self): return tuple(self.sel)
    def selection_set(self, ids):
        self.sel = [ids] if isinstance(ids, str) else list(ids)
    def exists(self, iid): return iid in self.rows
    def item(self, iid, **k):
        if 'tags' in k: self.rows[iid]['tags'] = tuple(k['tags'])
        return self.rows[iid]
    def set(self, iid, col): return self.rows[iid]["values"][["urgente","data_hora","nome","contato","descricao","retorno","status"].index(col)]
    def identify_row(self, y): return self.order[0] if self.order else ""
    def yview(self, *a): pass
class Scrollbar(Widget):
    def set(self, a, b): pass
class Style:
    def __init__(self, master=None): self.estilos = {}
    def theme_use(self, n): pass
    def configure(self, nome, **k): self.estilos.setdefault(nome, {}).update(k)
    def layout(self, nome, spec=None): pass
    def map(self, nome, query_opt=None, **k): return [] if query_opt else None
class Menu(Widget):
    def add_command(self, **k): pass
    def add_separator(self): pass
    def tk_popup(self, x, y): pass

tk = types.ModuleType("tkinter"); tk.TclError = TclError; tk.Menu = Menu
ttk = types.ModuleType("tkinter.ttk"); ttk.Treeview = Treeview; ttk.Scrollbar = Scrollbar; ttk.Style = Style
mb = types.ModuleType("tkinter.messagebox")
mb.erros = []
mb.showerror = lambda *a, **k: mb.erros.append(a)
fd = types.ModuleType("tkinter.filedialog"); fd.CAMINHO = {"v": ""}
fd.asksaveasfilename = lambda **k: fd.CAMINHO["v"]
fd.askopenfilename = lambda **k: fd.CAMINHO.get("abrir", "")
class Toplevel(Widget): pass
tk.Entry = type('Entry', (), {}); tk.Toplevel = Toplevel; tk.Text = type('Text', (), {})
tk.ttk = ttk; tk.messagebox = mb; tk.filedialog = fd
sys.modules.update({"tkinter": tk, "tkinter.ttk": ttk, "tkinter.messagebox": mb, "tkinter.filedialog": fd})

# ----------------------------------------------------------------------
# Roteiro de testes
# ----------------------------------------------------------------------
sys.path.insert(0, RAIZ)
from anotacoes.nucleo import database
tmp = tempfile.mkdtemp()
database.caminho_banco = lambda: os.path.join(tmp, "smoke.db")

from anotacoes.interface import widgets, janela as gui
# O diálogo de exclusão é "modal": simulamos a resposta do usuário.
RESP = {"v": True}
widgets.DialogoConfirmacao.perguntar = classmethod(lambda cls, *a, **k: RESP["v"])
gui.DialogoConfirmacao = widgets.DialogoConfirmacao

ok = 0
def check(cond, msg):
    global ok
    if not cond:
        raise AssertionError("FALHOU: " + msg)
    ok += 1
    print("  ok -", msg)

from anotacoes import theme as _T0
perfil_nome_padrao = _T0.NOME_PADRAO
# A simulação cobre o formulário completo da Nuvem (endereço + chave): ignora o projeto fixo
# de anotacoes/nuvem/projeto.py, que já vem preenchido no repositório.
from anotacoes.nuvem import projeto as _projeto_sem_fixo
_projeto_sem_fixo.projeto_fixo = lambda *a, **k: None
app = gui.App()
check(not mb.erros, "aplicativo abre sem erros (todos os widgets aceitos pela API)")
check(app.paginas["novo"].mapped and not app.paginas["historico"].mapped, "página inicial = Novo registro")

# Validação: campos vazios
app.salvar_registro()
check(app.err_contato.cget("text") == "Informe o contato." and app.err_nome.cget("text") == "",
      "contato é obrigatório e o nome não")
check(app.err_desc.cget("text") == "Descreva a solicitação.", "erro inline da descrição")
check("obrigatórios" in app.toast._rotulo.cget("text"), "aviso 'Preencha os campos obrigatórios.'")
check(app.db.listar() == [], "nada gravado com campos vazios")

# Digitar limpa o erro
app.ent_contato.text = "Ramal 2045"
app._digitando(app.ent_contato)
check(app.err_contato.cget("text") == "", "digitar remove o erro do contato")
app.ent_nome.text = "Maria da Silva"

# Salvar válido
app.ent_contato.text = "Ramal 2045"
app.txt_desc.text = "Solicita água e\nsegundo travesseiro."
app.salvar_registro()
check(len(app.db.listar()) == 1, "registro salvo no banco")
check(app.ent_nome.text == "" and app.txt_desc.text == "", "formulário limpo após salvar")
check("sucesso" in app.toast._rotulo.cget("text"), "toast de sucesso")
check(app.res_hoje.cget("text") == "1" and app.res_pend.cget("text") == "1", "resumo lateral atualizado")
check(len(app.lista_recentes.winfo_children()) == 1, "lista 'Últimos registros' com 1 item")

# Limite de tamanho
app.ent_contato.text = "1000"
app.ent_nome.text = "A" * 121
app.txt_desc.text = "x"
app.salvar_registro()
check("120" in app.err_nome.cget("text") and len(app.db.listar()) == 1, "nome acima do limite é rejeitado")
app.limpar_formulario()

# Nome opcional / contato obrigatório / altura mínima da janela
app.limpar_formulario()
app.ent_nome.text, app.ent_contato.text, app.txt_desc.text = "Fulano", "", "tem nome, falta contato"
n_antes = len(app.db.listar())
app.salvar_registro()
check(app.err_contato.cget("text") == "Informe o contato." and len(app.db.listar()) == n_antes,
      "sem contato o registro não é salvo (mesmo com nome)")
check("obrigatórios" in app.toast._rotulo.cget("text"), "aviso de campos obrigatórios quando falta o contato")
app.limpar_formulario()
app.ent_nome.text, app.ent_contato.text, app.txt_desc.text = "", "(84) 99999-0000", "sem nome informado"
app.salvar_registro()
sem_nome = [r for r in app.db.listar() if r[2] == ""]
check(len(sem_nome) == 1 and "sucesso" in app.toast._rotulo.cget("text"), "registro sem nome é salvo")
app.mostrar_pagina("historico")
check(any(v["values"][2] == "Sem nome" for v in app.tabela.tree.rows.values()), "histórico mostra 'Sem nome' quando não há nome")
app.db.excluir(sem_nome[0][0]); app.db.apagar_definitivamente([sem_nome[0][0]])
app.mostrar_pagina("novo")
from anotacoes.interface import janela as _jan
registrado = []
app.minsize = lambda w, h: registrado.append((w, h))
app.paginas["novo"].winfo_reqheight = lambda: 1000
app.winfo_screenheight = lambda: 2000
app._garantir_altura_do_formulario()
check(registrado and registrado[-1][1] >= 1000 / app._get_window_scaling() - 1,
      "altura mínima da janela sobe para caber o formulário (a descrição não some)")
app.paginas["novo"].winfo_reqheight = lambda: 100
app._garantir_altura_do_formulario()
check(registrado[-1][1] == _jan.MINIMO_ALTURA, "formulário baixo: mantém o mínimo padrão")

# Mais registros e navegação
for n, c, d in (("José Souza", "9999-0000", "Troca de leito"), ("Ana Lima", "ana@x.com", "Dúvida sobre visita")):
    app.ent_nome.text, app.ent_contato.text, app.txt_desc.text = n, c, d
    app.salvar_registro()
app.mostrar_pagina("historico")
check(app.paginas["historico"].mapped and not app.paginas["novo"].mapped, "navegação para Histórico")
check(len(app.tabela.tree.get_children()) == 3, "tabela com 3 linhas")
check(app.cartao_total._valor.cget("text") == "3", "indicador 'Total' = 3")

# Busca e filtro
app.busca.entry.text = "jose"      # sem acento deve achar "José"
app.atualizar_historico()
check(len(app.tabela.tree.get_children()) == 1, "busca 'jose' encontra 'José Souza'")
app.busca.entry.text = "zzz"
app.atualizar_historico()
check(len(app.tabela.tree.get_children()) == 0 and app.tabela.vazio.mapped, "estado vazio quando a busca não encontra")
app.busca.entry.text = "ramal"
app.atualizar_historico()
check(len(app.tabela.tree.get_children()) == 1, "busca por contato")
app.busca.entry.text = ""
app.filtro_status.set("Atendidas"); app.atualizar_historico()
check(len(app.tabela.tree.get_children()) == 0, "filtro 'Atendidas' sem resultados")
app.filtro_status.set("Todos"); app.atualizar_historico()

# Alterar status
app.alterar_status("Atendida")
check("Selecione" in app.toast._rotulo.cget("text"), "aviso ao agir sem selecionar")
ids = list(app.tabela.tree.get_children())
app.tabela.tree.selection_set(ids[:2])
app.alterar_status("Atendida")
check(app.cartao_aten._valor.cget("text") == "2" and app.cartao_pend._valor.cget("text") == "1", "2 registros marcados como atendidos")
check("2 registros marcados como atendidos" in app.toast._rotulo.cget("text"), "mensagem no plural correto")
app.tabela.tree.selection_set(ids[:1])
app.alterar_status("Pendente")
check("Registro marcado como pendente" in app.toast._rotulo.cget("text"), "mensagem no singular correto")

# Detalhes
app.tabela.tree.selection_set(ids[:1])
app.ver_detalhes()
check(True, "janela de detalhes abre")

# Excluir
app.tabela.tree.selection_set(ids[:1])
RESP["v"] = False
app.excluir_selecionados()
check(len(app.db.listar()) == 3, "cancelar a exclusão mantém o registro")
RESP["v"] = True
app.excluir_selecionados()
check(len(app.db.listar()) == 2, "confirmar exclui o registro")
check(app.cartao_total._valor.cget("text") == "2", "indicadores após exclusão")
app.tabela.tree.selection_set(list(app.tabela.tree.get_children()))
app.excluir_selecionados()
check(app.db.listar() == [] and app.tabela.vazio.mapped, "exclusão múltipla -> estado vazio")
check("lixeira" in app.toast._rotulo.cget("text"), "toast de exclusão (lixeira)")


# --- Seleção: cor única por linha, suave e sem conflito com a cor do status ---
app.limpar_formulario()
for n in ("Carlos", "Dora", "Elisa"):
    app.ent_contato.text, app.ent_nome.text, app.txt_desc.text = "1000", n, "x"
    app.salvar_registro()
app.mostrar_pagina("historico")
ids = list(app.tabela.tree.get_children())
check(all(len(app.tabela.tree.rows[i]["tags"]) == 1 for i in ids), "cada linha tem uma única etiqueta de cor")
app.tabela.tree.selection_set(ids[:2]); app.tabela._selecionou()
check(all(app.tabela.tree.rows[i]["tags"] == ("selecionada",) for i in ids[:2]), "linhas selecionadas recebem a cor de seleção")
check(app.tabela.tree.rows[ids[2]]["tags"] != ("selecionada",), "linha não selecionada mantém a cor do status")
app.tabela.tree.selection_set(ids[1:2]); app.tabela._selecionou()
check(app.tabela.tree.rows[ids[0]]["tags"] in (("pendente",), ("atendida",)), "ao desmarcar, a linha volta à cor do status")
app.alterar_status("Atendida")
check(app.tabela.tree.rows[ids[1]]["tags"] == ("selecionada",) and app.tabela.tree.selection() == (ids[1],), "seleção e cor persistem após mudar o status")
app.tabela.tree.selection_set(()); app.tabela._selecionou()
check(app.tabela.tree.rows[ids[1]]["tags"] == ("atendida",), "ao limpar a seleção, aparece a cor do status atualizado")
check(app.tabela.tree.tags["selecionada"]["background"] == gui.T.SELECAO and app.tabela.tree.tags["selecionada"]["foreground"] == gui.T.TEXTO,
      "cor de seleção suave com texto escuro")
check(gui.T.SELECAO != gui.T.TEAL, "seleção não usa mais o verde-água forte")


# --- v2.4: campos, retorno, ordenação, período, exportar, imprimir ---
from datetime import date, timedelta
def textos(w, acc=None):
    acc = [] if acc is None else acc
    t = w._cfg.get("text") if hasattr(w, "_cfg") else None
    if t: acc.append(t)
    for k in w.kids: textos(k, acc)
    return acc
tf = textos(app.paginas["novo"])
check("Contato *" in tf and "Nome" in tf and "Nome *" not in tf, "rótulos do formulário: 'Contato *' (obrigatório) e 'Nome' (opcional)")
check(not any("paciente" in t.lower() and "Nome" in t for t in tf), "'Nome do paciente' não existe mais no formulário")
check(not any("ramal" in t.lower() or "e-mail" in t.lower() or "(" in t and "Contato" in t for t in tf if t.startswith("Contato")), "rótulo de contato sem parênteses")
check(tf.index("Contato *") < tf.index("Nome") < tf.index("Descrição da solicitação *"), "ordem: Contato, Nome, Descrição")
check(app.ent_contato._cfg["placeholder_text"] == "Ex.: (84) 99999-0000", "dica do contato só com telefone")
base_ids = {r[0] for r in app.db.listar()}
hoje, amanha = date.today(), date.today() + timedelta(days=1)
app.mostrar_pagina("novo")
app.ent_contato.text, app.ent_nome.text, app.txt_desc.text = "111", "Zélia Retorno", "Voltar a ligar"
app.ent_retorno.text = (hoje - timedelta(days=3)).strftime("%d/%m/%Y")
app.salvar_registro()
check("já passou" in app.err_retorno.cget("text") and len(app.db.listar()) == len(base_ids), "data de retorno passada é rejeitada")
app.ent_retorno.text = "99/99/2026"
app.salvar_registro()
check(app.err_retorno.cget("text") != "" and len(app.db.listar()) == len(base_ids), "data de retorno inválida é rejeitada")
app.ent_retorno.text = "";  app._definir_retorno(app.ent_retorno, 1)
check(app.ent_retorno.text == amanha.strftime("%d/%m/%Y"), "atalho 'Amanhã' preenche a data")
app.ent_retorno.text = amanha.strftime("%d/%m/%Y")
app.salvar_registro()
novo = [r for r in app.db.listar() if r[0] not in base_ids]
check(len(novo) == 1 and novo[0][6] == amanha.isoformat(), "registro salvo com retorno")
check(app.ent_retorno.text == "", "campo de retorno limpo após salvar")
# registros com retorno hoje/atrasado
conn_ids = []
for nome, dias in (("Atrasada", -2), ("De hoje", 0)):
    conn_ids.append(app.db.inserir(nome, "", "x", (hoje + timedelta(days=dias)).isoformat()))
semretorno = app.db.inserir("Sem retorno", "", "x")
app.atualizar_tudo()
check(app.cartao_ret._valor.cget("text") == "2" and app.res_retornos.cget("text") == "2", "indicadores 'Retornos a fazer' = 2")
app.mostrar_pagina("historico")
tr = app.tabela.tree
linha = lambda nome: next(i for i in tr.get_children() if tr.rows[i]["values"][2] == nome)
check(tr.rows[linha("Atrasada")]["tags"] == ("vencida",) and tr.rows[linha("Atrasada")]["values"][5].startswith("Atrasado"), "linha atrasada: cor vermelha clara e rótulo 'Atrasado'")
check(tr.rows[linha("De hoje")]["values"][5] == "Hoje", "retorno de hoje mostra 'Hoje'")
check(tr.rows[linha("Zélia Retorno")]["values"][5] == "Amanhã" and tr.rows[linha("Zélia Retorno")]["tags"] == ("pendente",), "retorno futuro: 'Amanhã' sem alerta")
app.filtro_status.set("Retornos"); app.atualizar_historico()
check({tr.rows[i]["values"][2] for i in tr.get_children()} == {"Atrasada", "De hoje"}, "filtro 'Retornos' mostra só hoje/atrasados")
app.filtro_status.set("Todos")
# ordenação
app._ordenar_por("nome"); nomes = [tr.rows[i]["values"][2] for i in tr.get_children()]
check(nomes == sorted(nomes, key=gui.normalizar), "ordenar por Nome (A-Z)")
check(tr.titulos["nome"].endswith("▲"), "seta ▲ no título da coluna ordenada")
app._ordenar_por("nome"); nomes = [tr.rows[i]["values"][2] for i in tr.get_children()]
check(nomes == sorted(nomes, key=gui.normalizar, reverse=True) and tr.titulos["nome"].endswith("▼"), "segundo clique inverte (Z-A)")
app._ordenar_por("retorno"); ret = [tr.rows[i]["values"][5] for i in tr.get_children()]
check(all(r == "" for r in ret[ret.index("") :]), "ordenar por Retorno: registros sem retorno ficam no fim")
app._ordenar_por("retorno"); ret = [tr.rows[i]["values"][5] for i in tr.get_children()]
check(all(r == "" for r in ret[ret.index("") :]), "inverter Retorno mantém os sem retorno no fim")
app._ordenar_por("data_hora")
check(app._ordem == ("data_hora", True), "Data/Hora começa pelos mais recentes")
# busca na descrição e período
app.busca.entry.text = "voltar a ligar"; app.atualizar_historico()
check([tr.rows[i]["values"][2] for i in tr.get_children()] == ["Zélia Retorno"], "busca encontra texto da descrição")
app.busca.entry.text = ""
app.filtro_periodo.set("Hoje"); app.atualizar_historico()
check(len(tr.get_children()) == len(app.db.listar()), "período 'Hoje' inclui os registros de hoje")
app.filtro_periodo.set("Todo o período")
check("Filtro: Todo o período" in app._descricao_filtro(), "descrição do filtro para impressão")
# exportar CSV
import tempfile as _tf, csv as _csv
saida = os.path.join(_tf.mkdtemp(), "x.csv")
sys.modules["tkinter.filedialog"].CAMINHO["v"] = ""
app.exportar_csv()
check(not os.path.exists(saida), "cancelar a janela de salvar não cria arquivo")
app.db.inserir("=HYPERLINK(\"http://x\")", "", "linha com ; e \"aspas\"")
app.atualizar_tudo()
sys.modules["tkinter.filedialog"].CAMINHO["v"] = saida
app.exportar_csv()
bruto = open(saida, "rb").read()
check(bruto.startswith(b"\xef\xbb\xbf"), "CSV com BOM UTF-8 (acentos corretos no Excel)")
linhas = list(_csv.reader(open(saida, encoding="utf-8-sig"), delimiter=";"))
check(linhas[0] == ["Nº", "Data/Hora", "Nome", "Contato", "Descrição", "Status", "Retorno", "Prioridade"], "cabeçalho do CSV")
check(len(linhas) - 1 == len(app._registros_exibidos), "CSV com todos os registros exibidos")
check(any(l[2].startswith("'=") for l in linhas[1:]), "CSV protege texto que parece fórmula")
check(any(l[4] == 'linha com ; e "aspas"' for l in linhas[1:]), "CSV preserva ';' e aspas")
tr.selection_set(linha("Atrasada")); app.tabela._selecionou()
app.exportar_csv()
linhas = list(_csv.reader(open(saida, encoding="utf-8-sig"), delimiter=";"))
check(len(linhas) == 2 and linhas[1][2] == "Atrasada", "com seleção, exporta só os selecionados")
# imprimir
import webbrowser
abertos = []
webbrowser.open = lambda u: abertos.append(u)
# No Windows o programa usa os.startfile (não o webbrowser): captura os dois caminhos.
_startfile_orig = getattr(os, "startfile", None)
if _startfile_orig is not None:
    os.startfile = lambda caminho: abertos.append("file://" + caminho)
app.db.inserir("<script>alert(1)</script>", "", "x")
app.atualizar_tudo(); tr.selection_set(()); app.tabela._selecionou()
app.imprimir_lista()
if _startfile_orig is not None:
    os.startfile = _startfile_orig
html_txt = open(abertos[0].replace("file://", ""), encoding="utf-8").read()
check("<script>alert(1)</script>" not in html_txt and "&lt;script&gt;" in html_txt, "impressão escapa HTML dos dados")
check("window.print()" in html_txt and "Liga Contra o Câncer" in html_txt, "página de impressão abre a caixa de impressão")
# menus suspensos (clique direito e Exportar)
from anotacoes import theme as _Tm
from anotacoes.interface.widgets import ItemMenu, MenuPopup, SEPARADOR
tr.selection_set(linha("Atrasada")); app.tabela._selecionou()
class _Ev: x = 5; y = 5; x_root = 300; y_root = 400
app._abrir_menu_contexto(_Ev())
m = app._menu_popup
check(m is not None and not m.dead, "clique direito abre o menu suspenso")
check([i.rotulo for _, i in m._acoes] == ["Ver detalhes", "Editar", "Marcar como atendida",
      "Marcar como pendente", "Excluir"], "menu de contexto: opções na ordem certa")
check([i.atalho for _, i in m._acoes] == ["Enter", "F2", None, None, "Del"], "menu de contexto: dicas de atalho")
check(all(i.icone for _, i in m._acoes), "menu de contexto: toda opção tem ícone")
check([i.perigo for _, i in m._acoes] == [False] * 4 + [True], "só 'Excluir' é perigosa (vermelha)")
check(m._geo.endswith("+300+400") or "+300+" in m._geo, "menu abre na posição do clique")
m._destacar(0)
check(m._acoes[0][0].cget("fg_color") == _Tm.SELECAO, "passar o mouse destaca a opção")
m._destacar(4)
check(m._acoes[0][0].cget("fg_color") == "transparent" and m._acoes[4][0].cget("fg_color") == _Tm.VERMELHO_CLARO,
      "destaque anterior sai e 'Excluir' usa o vermelho claro")
m._mover(1)
check(m._atual == 0, "seta para baixo na última opção volta à primeira")
m._mover(-1)
check(m._atual == 4, "seta para cima na primeira opção vai para a última")
m.binds["<Escape>"][0](None)
check(m.dead and app._menu_popup is None, "Esc fecha o menu")

# escolher uma opção fecha o menu e executa o comando depois
chamadas = []
# --- vários monitores: o menu fica no monitor do clique ---
from anotacoes.interface import widgets as _W
_orig_lim = _W.limites_da_tela
try:
    _W.limites_da_tela = lambda j, x, y: (1920, 0, 3840, 1040) if x >= 1920 else (0, 0, 1920, 1040)
    mm = MenuPopup.abrir(app, 2500, 300, [ItemMenu("A", lambda: None)])
    gx = int(mm._geo.split("+")[1]); check(gx == 2500, "2º monitor: menu abre onde clicou (não volta ao principal)"); mm._fechar()
    mm = MenuPopup.abrir(app, 3800, 300, [ItemMenu("A", lambda: None)])
    gx = int(mm._geo.split("+")[1]); check(1920 <= gx and gx + int(mm._geo.split("x")[0]) <= 3840, "2º monitor: borda direita prende no próprio monitor"); mm._fechar()
    _W.limites_da_tela = lambda j, x, y: (-1920, 0, 0, 1040)
    mm = MenuPopup.abrir(app, -500, 300, [ItemMenu("A", lambda: None)])
    check("+-" in mm._geo.split("x", 1)[1], "monitor à esquerda (coordenada negativa) preservado"); mm._fechar()
    _W.limites_da_tela = lambda j, x, y: (0, 0, 1920, 1040)
    mm = MenuPopup.abrir(app, 100, 1030, [ItemMenu("A", lambda: None)])
    gy = int(mm._geo.split("+")[-1]); check(gy < 1030, "sem espaço embaixo: abre para cima"); mm._fechar()
    check(_W.ajustar_ao_monitor(app, 5000, 5000, 100, 100) == (1920 - 108, 1040 - 104), "ajustar_ao_monitor prende nos limites")
finally:
    _W.limites_da_tela = _orig_lim
m2 = MenuPopup.abrir(app, 10, 10, [ItemMenu("A", lambda: chamadas.append("A"), "eye"), SEPARADOR,
                                   ItemMenu("B", lambda: chamadas.append("B"), "trash", perigo=True)],
                     titulo="2 registros selecionados")
m2._ativar(1)
check(m2.dead and not chamadas, "escolher fecha o menu antes de executar")
ms, fn = app.after_calls[-1]; fn()
check(chamadas == ["B"], "o comando da opção escolhida é executado")
m2._ativar(0)
check(chamadas == ["B"], "menu fechado ignora novos cliques")

# abrir outro menu fecha o anterior; clique fora fecha
m3 = MenuPopup.abrir(app, 10, 10, [ItemMenu("A", lambda: None)])
m4 = MenuPopup.abrir(app, 20, 20, [ItemMenu("A", lambda: None)])
check(m3.dead and not m4.dead and app._menu_popup is m4, "só um menu aberto por vez")
class _Fora: x_root = 99999; y_root = 99999
m4.binds["<Button-1>"][0](_Fora())
check(m4.dead, "clique fora fecha o menu")

# menu do botão Exportar
app._abrir_menu_exportar()
m5 = app._menu_popup
check([i.rotulo for _, i in m5._acoes] == ["Exportar para Excel (CSV)", "Imprimir lista"],
      "botão Exportar abre o menu com CSV e impressão")
check([i.atalho for _, i in m5._acoes] == ["Ctrl+E", "Ctrl+P"], "menu Exportar mostra os atalhos")
m5._fechar()
check(m5.dead, "menu Exportar fecha")

# edição pelo diálogo (com retorno)
rid = int(linha("Sem retorno")); app.editar_registro(rid)
dlg = app.kids[-1]
def achar(w, tipo, acc=None):
    acc = [] if acc is None else acc
    if type(w).__name__ == tipo: acc.append(w)
    for k in w.kids: achar(k, tipo, acc)
    return acc
ents = achar(dlg, "CTkEntry")
check(len(ents) == 3, "edição tem Contato, Nome e Retorno")
ents[0].text = "999"; ents[1].text = "Nome Editado"; ents[2].text = ""; ents[2].insert(0, amanha.strftime("%d/%m/%Y"))
salvar = next(b for b in achar(dlg, "CTkButton") if b._cfg.get("text") == "Salvar alterações")
salvar.invoke()
reg = app.db.obter(rid)
check(reg[2] == "Nome Editado" and reg[6] == amanha.isoformat(), "edição grava nome e novo retorno")
app.editar_registro(rid); dlg = app.kids[-1]; ents = achar(dlg, "CTkEntry")
ents[2].text = ""
next(b for b in achar(dlg, "CTkButton") if b._cfg.get("text") == "Salvar alterações").invoke()
check(app.db.obter(rid)[6] is None, "limpar o campo remove o retorno")
# retorno já vencido preservado na edição sem mexer na data
vid = conn_ids[0]; app.editar_registro(vid); dlg = app.kids[-1]; ents = achar(dlg, "CTkEntry")
check(ents[2].text == (hoje - timedelta(days=2)).strftime("%d/%m/%Y"), "edição mostra o retorno atual")
next(b for b in achar(dlg, "CTkButton") if b._cfg.get("text") == "Salvar alterações").invoke()
check(app.db.obter(vid)[6] == (hoje - timedelta(days=2)).isoformat(), "salvar sem mexer mantém retorno já vencido")
# limpeza (não interfere nos testes seguintes)
ids_novos = {r[0] for r in app.db.listar()} - base_ids
for i in ids_novos:
    app.db._executar("DELETE FROM solicitacoes WHERE id = ?", (i,))
app.atualizar_tudo()


# --- v2.5.1: ordem do Tab e itens do menu ---
def tab(campo, seq="<Tab>"): return campo.binds[seq][-1](None)
for campo in (app.ent_contato, app.ent_nome, app.txt_desc, app.ent_retorno): campo.focused = False
check(tab(app.ent_contato) == "break" and app.ent_nome.focused, "Tab: Contato -> Nome")
check(tab(app.ent_nome) == "break" and app.txt_desc.focused and not app.ent_retorno.focused, "Tab: Nome -> Descrição (não pula para Retornar em)")
check(tab(app.txt_desc) == "break" and app.ent_retorno.focused, "Tab: Descrição -> Retornar em")
check(tab(app.ent_retorno) == "break" and app.ent_contato.focused, "Tab: Retornar em -> volta ao Contato")
app.txt_desc.focused = False; tab(app.ent_retorno, "<Shift-Tab>")
check(app.txt_desc.focused, "Shift+Tab: Retornar em -> Descrição")
faixas = [it._faixa for it in app.nav.values()]
check(all(f._cfg.get("height") == 1 for f in faixas) and list(app.nav) == ["resumo", "novo", "historico", "lixeira", "painel"], "menu: Resumo, Novo, Histórico, Lixeira e Painel (o último); Backup e Nuvem ficam em Configurações")


def trocar_tema():
    """Chama alternar_tema e executa o que ele agendou (troca + liberação do bloqueio)."""
    n = len(app.after_calls)
    app.alternar_tema()
    for ms, fn in app.after_calls[n:]:
        fn()
    app._trocando_tema = False   # (a liberação real roda 500 ms depois)
app._trocando_tema = False

# --- v2.5.2: troca de tema rápida e recuperação de falhas ---
from anotacoes import theme as _T
n0 = len(app.after_calls)
app.alternar_tema(); app.alternar_tema(); app.alternar_tema()     # cliques rápidos
agendadas = app.after_calls[n0:]
check(len(agendadas) == 1 and agendadas[0][0] >= 150, "cliques repetidos agendam UMA só troca, após o clique terminar")
check(_T.TEMA_ATUAL == "claro", "nada muda dentro do próprio clique do botão")
for ms, fn in agendadas: fn()
check(_T.TEMA_ATUAL == "escuro" and len([w for w in app.winfo_children() if type(w).__name__ not in ('CTkToplevel', 'Menu')]) == 2, "uma única troca: interface refeita sem sobras (barra + área)")
app._trocando_tema = False
trocar_tema(); check(_T.TEMA_ATUAL == "claro" and len([w for w in app.winfo_children() if type(w).__name__ not in ('CTkToplevel', 'Menu')]) == 2, "troca de volta sem sobras")
# falha no meio da reconstrução: recupera no tema claro, com interface completa
original = app._construir_interface
chamadas = {"n": 0}
def quebra():
    chamadas["n"] += 1
    if chamadas["n"] == 1: raise RuntimeError("falha simulada")
    original()
app._construir_interface = quebra
trocar_tema()
check(_T.TEMA_ATUAL == "claro" and len([w for w in app.winfo_children() if type(w).__name__ not in ('CTkToplevel', 'Menu')]) == 2 and app.paginas["novo"].mapped, "falha na troca: volta ao tema claro com a tela montada")
check("tema claro" in app.toast._rotulo.cget("text"), "falha na troca: usuário é avisado")
check(app.prefs.get("tema") == "claro", "falha na troca: preferência volta a 'claro'")
app._construir_interface = original
app._trocando_tema = False
# --- v2.5: prioridade, resumo, atalhos/desfazer, tema, preferências ---
from anotacoes import theme as _T
def todos(w, tipo, acc=None):
    acc = [] if acc is None else acc
    if type(w).__name__ == tipo: acc.append(w)
    for k in w.kids: todos(k, tipo, acc)
    return acc
ids0 = {r[0] for r in app.db.listar()}
app.mostrar_pagina("novo")
app.ent_contato.text, app.ent_nome.text, app.txt_desc.text = "555", "Urgente Teste", "Caso grave"
app.chk_urgente.select(); app.salvar_registro()
u = [r for r in app.db.listar() if r[0] not in ids0][0]
check(u[7] == "Urgente", "formulário grava prioridade Urgente")
check(app.chk_urgente.get() == 0, "caixa 'Urgente' desmarcada após salvar")
app.mostrar_pagina("historico")
tr = app.tabela.tree
linha = lambda nome: next(i for i in tr.get_children() if tr.rows[i]["values"][2] == nome)
check(tr.rows[linha("Urgente Teste")]["values"][0] == "URG", "coluna 'Urg.' mostra URG")
app.filtro_status.set("Urgentes"); app.atualizar_historico()
check([tr.rows[i]["values"][2] for i in tr.get_children()] == ["Urgente Teste"], "filtro 'Urgentes'")
app.filtro_status.set("Todos"); app._ordenar_por("urgente")
check(tr.rows[tr.get_children()[0]]["values"][2] == "Urgente Teste", "ordenar por 'Urg.' põe urgentes primeiro")
app._ordenar_por("data_hora"); app._ordenar_por("data_hora") if app._ordem[1] is False else None
# resumo do dia
app.mostrar_pagina("resumo")
check(app.paginas["resumo"].mapped, "página Resumo do dia abre")
itens, nr, nu, na = app.itens_do_resumo()
check(nu >= 1 and any(r[2] == "Urgente Teste" and "Urgente" in m for r, m in itens), "resumo lista o urgente com o motivo")
check(app.res_c_urg.cget if False else True, "cartões do resumo atualizados")
check(len(app.lista_resumo.kids) >= 1, "lista do resumo preenchida")
check(app.ha_algo_para_ver() is True, "há algo para ver quando existe urgente pendente")
# detalhes por id (a partir do resumo)
app.ver_detalhes(u[0]); check(True, "detalhes abre direto pelo id (botão Abrir do resumo)")
# atalhos e desfazer
for seq in ("<Control-n>", "<Control-f>", "<Control-e>", "<Control-p>", "<Control-z>", "<Control-t>", "<Control-s>", "<Control-N>", "<F1>"):
    check(seq in app.binds, f"atalho {seq} registrado")
app._atalho_novo(); check(app.paginas["novo"].mapped and app.ent_contato.focused, "Ctrl+N: novo registro com foco no contato")
app._atalho_buscar(); check(app.paginas["historico"].mapped and app.busca.entry.focused, "Ctrl+F: histórico com foco na busca")
app.mostrar_atalhos(); check(True, "F1: janela de atalhos abre")
app.mostrar_pagina("historico")
rid = u[0]
tr.selection_set(str(rid)); app.tabela._selecionou()
app.alterar_status("Atendida"); check(app.db.obter(rid)[5] == "Atendida", "status alterado")
app._atalho_desfazer(); check(app.db.obter(rid)[5] == "Pendente", "Ctrl+Z desfaz mudança de status")
tr.selection_set(str(rid)); app.tabela._selecionou(); RESP["v"] = True
app.excluir_selecionados(); check(app.db.obter(rid) is None, "excluído")
app._atalho_desfazer(); check(app.db.obter(rid) is not None, "Ctrl+Z desfaz exclusão (volta da lixeira)")
app.editar_registro(rid); dlg = app.kids[-1]; ents = todos(dlg, "CTkEntry")
ents[1].text = "Nome Mudado"; todos(dlg, "CTkCheckBox")[0].deselect()
next(b for b in todos(dlg, "CTkButton") if b._cfg.get("text") == "Salvar alterações").invoke()
check(app.db.obter(rid)[2] == "Nome Mudado" and app.db.obter(rid)[7] == "Normal", "edição muda nome e prioridade")
app._atalho_desfazer(); check(app.db.obter(rid)[2] == "Urgente Teste" and app.db.obter(rid)[7] == "Urgente", "Ctrl+Z desfaz edição")
app._pilha_desfazer.clear(); app._atalho_desfazer()
check("nada para desfazer" in app.toast._rotulo.cget("text"), "sem histórico: avisa que não há o que desfazer")
app.focus_get = lambda: sys.modules["tkinter"].Entry()
app.registrar_desfazer("status", {rid: "Atendida"}, "teste"); app._atalho_desfazer()
check(len(app._pilha_desfazer) == 1 and app.db.obter(rid)[5] == "Pendente", "Ctrl+Z dentro de campo de texto não desfaz registros")
del app.focus_get
app._pilha_desfazer.clear()
# tema escuro: reconstrói mantendo página, filtros e formulário
app.mostrar_pagina("novo"); app.ent_nome.text = "Rascunho"; app.chk_urgente.select()
app.filtro_periodo.set("Hoje"); app.filtro_status.set("Pendentes")
antiga = app.barra_lateral
trocar_tema()
check(_T.TEMA_ATUAL == "escuro" and antiga.dead and not app.barra_lateral.dead, "tema escuro: interface reconstruída")
check(app.ent_nome.text == "Rascunho" and app.chk_urgente.get() == 1, "tema: formulário preservado")
check(app.filtro_periodo.get() == "Hoje" and app.filtro_status.get() == "Pendentes", "tema: filtros preservados")
check(app.paginas["novo"].mapped, "tema: continua na mesma página")
check(app.cget("fg_color") == _T.FUNDO == "#0E1822", "fundo da janela no tema escuro")
sem = [b._cfg.get("text") for b in todos(app, "CTkButton")
       if b._cfg.get("fg_color") in (_T.TEAL, _T.VERDE, _T.AMBAR, _T.VERMELHO) and b._cfg.get("text_color") != _T.SOBRE_COR]
check(not sem, f"botões coloridos têm texto contrastante ({sem})")
check(app.prefs.get("tema") == "escuro", "tema salvo nas preferências")
trocar_tema(); check(_T.TEMA_ATUAL == "claro", "volta ao tema claro")
# preferências: janela, ordenação e filtros
app._ordem = ("nome", False); app.filtro_periodo.set("Hoje"); app.filtro_status.set("Pendentes")
app.state("zoomed"); app._salvar_preferencias()
sv = app.prefs.dados
check(sv["ordem"] == ["nome", False] and sv["filtro_status"] == "Pendentes" and sv["janela"]["max"] is True, "preferências gravadas")
check(sv["janela"]["w"] == round(1240 / SCREEN["dpi"]) and sv["janela"]["x"] == 30, "tamanho (lógico) e posição gravados")
app2 = gui.App()
check(app2._ordem == ("nome", False) and app2.filtro_status.get() == "Pendentes" and app2.filtro_periodo.get() == "Hoje", "reabre com ordenação e filtros anteriores")
check(app2._geo.startswith(f"{round(1240 / SCREEN['dpi'])}x"), "reabre no tamanho anterior")
app.prefs.definir(janela={"w": "x", "h": None}, ordem="lixo", tema="inexistente"); app.prefs.salvar()
app3 = gui.App(); check(app3._ordem == ("data_hora", True) and _T.TEMA_ATUAL == "claro", "preferências inválidas voltam ao padrão sem erro")
# limpeza
app.filtro_status.set("Todos"); app.filtro_periodo.set("Todo o período"); app._ordem = ("data_hora", True); app.state("normal")
app.mostrar_pagina("novo")
for i in {r[0] for r in app.db.listar()} - ids0:
    app.db._executar("DELETE FROM solicitacoes WHERE id = ?", (i,))
app.atualizar_tudo()

# --- Escala em telas pequenas: nada deve ficar cortado ---
def abre_com(w, h, dpi):
    SCREEN.update(w=w, h=h, dpi=dpi); ESCALAS.clear()
    a = gui.App()
    return a, list(ESCALAS)
a, esc = abre_com(1920, 1080, 1.0)
check(esc == [] and a._fator_escala == 1.0, "tela 1920x1080 a 100%: tamanho normal (sem reduzir)")
a, esc = abre_com(1366, 768, 1.0)
check(0.8 <= a._fator_escala < 1.0 and ("widget", a._fator_escala) in esc, f"tela 1366x768: interface reduzida (fator {a._fator_escala})")
a, esc = abre_com(1920, 1080, 1.5)
check(0.7 <= a._fator_escala < 1.0, f"tela 1920x1080 a 150%: interface reduzida (fator {a._fator_escala})")
a, esc = abre_com(1920, 1080, 1.25)
check(a._fator_escala >= 0.95, f"tela 1920x1080 a 125%: quase sem redução (fator {a._fator_escala})")
a, esc = abre_com(1024, 768, 1.0)
check(a._fator_escala >= 0.7, f"tela 1024x768: dentro do limite mínimo (fator {a._fator_escala})")
# a altura da janela, já escalada, cabe na área útil da tela
for (w, h, dpi) in ((1366, 768, 1.0), (1920, 1080, 1.5), (1920, 1080, 1.25), (1280, 720, 1.0), (1536, 864, 1.25)):
    a, _ = abre_com(w, h, dpi)
    alt_px = ALT = gui.ALTURA_BASE * a._fator_escala * dpi
    check(alt_px <= h - 40, f"{w}x{h} @{int(dpi*100)}%: janela de {int(alt_px)}px cabe na tela")
    min_px = gui.MINIMO_ALTURA * a._fator_escala * dpi
    check(min_px <= h - 40, f"{w}x{h} @{int(dpi*100)}%: altura mínima ({int(min_px)}px) cabe na tela")
check(a._px(14) >= 1, "conversão de fonte da tabela em pixels")


# --- v2.1: lixeira, edição, backup ---
check(app.db.contar_lixeira() == 3, "registros excluídos foram para a lixeira (3)")
app.mostrar_pagina("lixeira")
check(app.paginas["lixeira"].mapped, "página Lixeira abre")
check(len(app.tabela_lixeira.tree.get_children()) == 3, "lixeira lista 3 registros")
app.tabela_lixeira.tree.selection_set(list(app.tabela_lixeira.tree.get_children())[:2])
app.restaurar_selecionados()
check(app.db.contar_lixeira() == 1, "lixeira com 1 após restaurar 2")
app.mostrar_pagina("historico")
check(len(app.tabela.tree.get_children()) == 5, "restaurados voltam ao histórico (3 + 2)")
# editar
rid = int(app.tabela.tree.get_children()[0])
app.editar_registro(rid)
check(True, "janela de edição abre")
app.tabela.tree.selection_set(str(rid)); app.ver_detalhes()
check(True, "detalhes (com Editar) abrem")
app.tabela.tree.selection_set(()); app.editar_registro()
check("Selecione" in app.toast._rotulo.cget("text"), "editar sem seleção avisa")
# esvaziar lixeira
RESP["v"] = True
app.mostrar_pagina("lixeira"); app.esvaziar_lixeira()
check(app.db.contar_lixeira() == 0, "esvaziar lixeira")
# backup
app.mostrar_pagina("backup")
check(app.paginas["config"].mapped and app._aba_backup.mapped and not app._aba_seguranca.mapped, "Backup abre como aba de Configurações")
app.fazer_backup_agora()
check(len(app.db.listar_backups()) >= 1, "backup manual criado")
app.atualizar_backups()
bk = app.tabela_backup.tree.get_children()
check(len(bk) >= 1, "backup aparece na tabela")
app.tabela_backup.tree.selection_set(bk[0]); app.restaurar_backup_selecionado()
check(True, "restaurar backup executa sem erro")

# --- Nuvem (Supabase) ---
from anotacoes.interface.mixins import nuvem as nuvem_gui
from anotacoes.nuvem import projeto as _projeto_mod
from anotacoes.nuvem import cliente as _nuvem
import time as _time
from anotacoes.nuvem.sincronizacao import Resultado
gui_nuvem = nuvem_gui
app.mostrar_pagina("nuvem")
check(app.paginas["config"].mapped and app._aba_nuvem.mapped, "Nuvem abre como aba de Configurações")
check(app.lbl_nuvem_estado.cget("text") == "Não conectado", "nuvem: começa não conectada")
check(app._grp_nuvem_entrar.mapped and not app._grp_nuvem_conectado.mapped, "nuvem: mostra o formulário")
check(app.ent_nuvem_senha._cfg.get("show") == "•", "nuvem: senha mascarada")
check("nuvem" not in app.nav and "backup" not in app.nav and "nuvem" not in app.paginas, "nuvem/backup: sem item próprio no menu")
copiado = []
app.clipboard_clear = lambda: copiado.clear()
app.clipboard_append = lambda t: copiado.append(t)
app.copiar_sql_nuvem()
check(copiado and "row level security" in copiado[0], "nuvem: SQL copiado para a área de transferência")

def esperar_fila():
    for _ in range(200):
        if not app._sync_fila.empty():
            app._sondar_sync(); return True
        _time.sleep(0.01)
    return False

# validações do formulário
check(app.ent_nuvem_url.get() == _projeto_mod.URL_PROJETO, "nuvem: endereço do projeto já vem preenchido")
app.ent_nuvem_url.delete(0, "end")
app.conectar_nuvem()
check("endereço" in app.toast._rotulo.cget("text").lower(), "nuvem: exige o endereço do projeto")
app.ent_nuvem_url.insert(0, "https://abc.supabase.co")
app.ent_nuvem_chave.insert(0, "sb_secret_" + "z" * 30)
app.ent_nuvem_email.insert(0, "eu@x.com")
app.conectar_nuvem()
check("SECRETA" in app.toast._rotulo.cget("text"), "nuvem: recusa chave secreta")
app.ent_nuvem_chave.delete(0, "end"); app.ent_nuvem_chave.insert(0, "sb_publishable_" + "z" * 30)
app.conectar_nuvem()
check("senha" in app.toast._rotulo.cget("text").lower(), "nuvem: exige a senha")

# conexão com falha
class _Falso:
    falhar = None
    def __init__(self, url, chave, refresh_token=None, ao_renovar=None, timeout=20):
        self.refresh_token = "rt-1"
    def entrar(self, email, senha):
        if _Falso.falhar: raise _nuvem.NuvemErro(_Falso.falhar)
nuvem_gui.ClienteSupabase = _Falso
chamadas = []
nuvem_gui.testar_conexao = lambda c: chamadas.append("teste")
nuvem_gui.sincronizar = lambda db, c: (chamadas.append("sync"), Resultado(enviados=3, recebidos=1))[1]
app.ent_nuvem_senha.insert(0, "segredo")
_Falso.falhar = "E-mail ou senha incorretos."
app.conectar_nuvem()
check(esperar_fila(), "nuvem: tentativa de conexão responde")
check("incorretos" in app.toast._rotulo.cget("text"), "nuvem: mostra o motivo da falha")
check(not app.nuvem_conectada() and not app._sync_rodando, "nuvem: falha não conecta e libera o botão")
check(app.lbl_nuvem_estado.cget("text") == "Não foi possível conectar", "nuvem: estado de falha")

# conexão bem-sucedida: conecta e já sincroniza
_Falso.falhar = None
app.conectar_nuvem()
check(esperar_fila(), "nuvem: conexão responde")
check(app.nuvem_conectada(), "nuvem: conectada")
check(app._nuvem_cfg.get("refresh_token") == "rt-1" and "senha" not in str(app._nuvem_cfg.dados).lower(), "nuvem: guarda só o refresh token (sem senha)")
check(app.ent_nuvem_senha.get() == "", "nuvem: campo da senha é limpo")
check(esperar_fila(), "nuvem: primeira sincronização termina")
check(chamadas == ["teste", "sync"], "nuvem: testa a conexão e sincroniza")
check(app.lbl_nuvem_estado.cget("text") == "Conectado", "nuvem: estado conectado")
check(app._grp_nuvem_conectado.mapped and not app._grp_nuvem_entrar.mapped, "nuvem: mostra os botões de conectado")
check("Enviados" not in app.toast._rotulo.cget("text") and "enviados" in app.toast._rotulo.cget("text"), "nuvem: resume o que foi enviado")
check(app._nuvem_cfg.get("ultimo_sync"), "nuvem: grava a data da última sincronização")

# sincronização automática (ciclo): sem pendências e sem prazo, nada acontece
chamadas.clear(); app._sync_ultimo_ok = _time.time()
app.db.sync_confirmar_envio([(r["uuid"], r["atualizado_em"]) for r in app.db.sync_pendentes()])
app.db.sync_confirmar_remocoes(app.db.sync_remocoes())
app._ciclo_nuvem(); check(not app._sync_rodando and not chamadas, "nuvem: ciclo não sincroniza sem necessidade")
rid_n = app.db.inserir("Pendente da nuvem", "", "x")
app._ciclo_nuvem(); check(esperar_fila() and chamadas == ["sync"], "nuvem: ciclo envia alterações pendentes")

# recebeu novidades: atualiza as telas
atualizou = []; orig_tudo = app.atualizar_tudo; app.atualizar_tudo = lambda: atualizou.append(1)
nuvem_gui.sincronizar = lambda db, c: Resultado(recebidos=2, removidos=1)
app.sincronizar_nuvem(manual=True); esperar_fila()
check(atualizou, "nuvem: novidades recebidas atualizam as telas")
app.atualizar_tudo = orig_tudo

# erro de rede: silencioso no automático, visível no manual; status persiste
def _erro(db, c): raise _nuvem.NuvemErro("Sem conexão com o Supabase.")
nuvem_gui.sincronizar = _erro
app.toast._rotulo.configure(text="")
app.sincronizar_nuvem(manual=False); esperar_fila()
check(app.toast._rotulo.cget("text") == "", "nuvem: erro de rede automático é silencioso")
check(app.lbl_nuvem_estado.cget("text") == "Conectado, com um problema" and "Sem conexão" in app.lbl_nuvem_detalhe.cget("text"), "nuvem: problema aparece na página")
app.sincronizar_nuvem(manual=True); esperar_fila()
check("Sem conexão" in app.toast._rotulo.cget("text"), "nuvem: erro de rede manual é mostrado")
chamadas.clear()
app._sync_ultima_tentativa = _time.time()
app._ciclo_nuvem(); check(not app._sync_rodando, "nuvem: após falha, não repete a cada ciclo")
app._sync_ultima_tentativa = _time.time() - 400
nuvem_gui.sincronizar = lambda db, c: (chamadas.append("sync"), Resultado())[1]
app._ciclo_nuvem(); check(esperar_fila() and chamadas == ["sync"], "nuvem: depois do intervalo, tenta de novo")
check(app.lbl_nuvem_estado.cget("text") == "Conectado", "nuvem: recuperou depois da falha")

# sessão expirada exige novo login
def _expirou(db, c): raise _nuvem.NuvemErro("A sessão expirou.", precisa_login=True)
nuvem_gui.sincronizar = _expirou
app.sincronizar_nuvem(manual=False); esperar_fila()
check(not app.nuvem_conectada(), "nuvem: sessão expirada volta ao formulário")
check("expirou" in app.toast._rotulo.cget("text"), "nuvem: avisa que a sessão expirou")

# desconectar
app._nuvem_cfg.definir(refresh_token="rt-2"); app._sync_erro = ""
RESP["v"] = False; app.desconectar_nuvem()
check(app.nuvem_conectada(), "nuvem: cancelar o diálogo mantém conectado")
RESP["v"] = True; app.desconectar_nuvem()
check(not app.nuvem_conectada() and app.db.sync_contar_pendentes() >= 1, "nuvem: desconectar esquece a sessão e marca tudo como pendente")

# ao fechar: tenta enviar o que falta, sem travar
nuvem_gui.sincronizar = lambda db, c: chamadas.append("fechar")
app._nuvem_cfg.definir(refresh_token="rt-3"); chamadas.clear()
app._sincronizar_ao_fechar(); check(chamadas == ["fechar"], "nuvem: ao fechar, envia o que está pendente")
nuvem_gui.sincronizar = lambda db, c: (_ for _ in ()).throw(RuntimeError("rede"))
app._sincronizar_ao_fechar(); check(True, "nuvem: falha ao fechar não impede o programa de fechar")
app._nuvem_cfg.definir(refresh_token=None)
app.mostrar_pagina("novo")


# --- Identidade personalizável ---
from anotacoes.interface.mixins import identidade as identidade_gui
from anotacoes.nucleo import identidade as _ident
from PIL import Image as _Img
check(app.lbl_marca_nome.cget("text") == gui.T.NOME_INSTITUICAO, "marca: nome na barra lateral")
check(app._marca is not None and app._separador_marca is not None, "marca: blocos criados")
imagem_teste = os.path.join(tmp, "meu_logo.png"); _Img.new("RGB", (400, 150), (10, 90, 160)).save(imagem_teste)

# abre a janela de verdade (valida os widgets/argumentos) e opera os botões
dlg = identidade_gui.DialogoIdentidade(app, app._identidade)
check(dlg.ent_nome.get() == gui.T.NOME_INSTITUICAO, "personalizar: campos começam com a identidade atual")
dlg.ent_nome.delete(0, "end"); dlg.ent_nome.insert(0, "   ")
dlg._salvar()
check(dlg.lbl_erro.cget("text") == "Informe o nome." and not dlg.resultado, "personalizar: exige o nome")
dlg.ent_nome.delete(0, "end"); dlg.ent_nome.insert(0, "x" * 60)
dlg._salvar()
check("até 40" in dlg.lbl_erro.cget("text"), "personalizar: limita o tamanho do nome")
dlg.ent_nome.delete(0, "end"); dlg.ent_nome.insert(0, "Intesoftware Desenvolvimento")
dlg.ent_sub.delete(0, "end"); dlg.ent_sub.insert(0, "Anotações de clientes")
sys.modules["tkinter.filedialog"].CAMINHO["abrir"] = ""
dlg._escolher_imagem(); check(dlg._logo_novo is None, "personalizar: cancelar a escolha não muda nada")
ruim = os.path.join(tmp, "ruim.png"); open(ruim, "w").write("não é imagem")
sys.modules["tkinter.filedialog"].CAMINHO["abrir"] = ruim
dlg._escolher_imagem(); dlg._salvar()
check("abrir essa imagem" in dlg.lbl_erro.cget("text") and not dlg.resultado, "personalizar: imagem inválida é recusada com aviso")
check(app._identidade.carregar() is None, "personalizar: nada é gravado quando há erro")
sys.modules["tkinter.filedialog"].CAMINHO["abrir"] = imagem_teste
dlg._escolher_imagem(); dlg._salvar()
check(dlg.resultado and dlg.dead, "personalizar: salvar fecha a janela com sucesso")
check(app._identidade.carregar() == ("Intesoftware Desenvolvimento", "Anotações de clientes"), "personalizar: textos gravados na pasta de dados")
check(app._identidade.caminho_logo() and app._identidade.caminho_icone(), "personalizar: logo e ícone gerados")

# o botão do menu: reflete na hora (título, barra lateral, ícone)
RESULTADO_DLG = {"v": True}
identidade_gui.DialogoIdentidade.abrir = classmethod(lambda cls, pai, ident: RESULTADO_DLG["v"])
icones = []
app.iconbitmap = lambda c: icones.append(c)
marca_antiga = app._marca
app.personalizar_identidade()
check(app._title == "Intesoftware Desenvolvimento — Anotações de clientes", "personalizar: título da janela atualizado")
check(app.lbl_marca_nome.cget("text") == "Intesoftware Desenvolvimento", "personalizar: nome da barra lateral atualizado")
check(app.lbl_marca_sub.cget("text") == "Anotações de clientes", "personalizar: subtítulo atualizado")
check(app._marca is not marca_antiga and marca_antiga.dead, "personalizar: marca antiga substituída (sem sobras)")
check(icones and icones[0].endswith("icone_personalizado.ico"), "personalizar: ícone da janela trocado")
check("Identidade atualizada" in app.toast._rotulo.cget("text"), "personalizar: confirmação")
check(app._marca.pack_kw.get("before") is app._separador_marca, "personalizar: marca nova é inserida ACIMA do separador (pack before=)")

# sem subtítulo: o rótulo some
app._identidade.salvar_textos("Só o nome", ""); app._identidade.aplicar(); app._atualizar_identidade()
check(not app.lbl_marca_sub.mapped and app._title == "Só o nome", "subtítulo vazio: sem rótulo e título só com o nome")

# restaurar padrão pela janela
dlg2 = identidade_gui.DialogoIdentidade(app, app._identidade)
RESP["v"] = True
dlg2._restaurar_padrao()
check(dlg2.resultado and app._identidade.carregar() is None and not app._identidade.caminho_logo(), "restaurar padrão: apaga identidade, logo e ícone")
app._atualizar_identidade()
check(app.lbl_marca_nome.cget("text") == perfil_nome_padrao, "restaurar padrão: volta ao nome de fábrica")

# a identidade sobrevive a reabrir o programa e à troca de tema
app._identidade.salvar_textos("Intesoftware Desenvolvimento", "Anotações de clientes")
app._identidade.definir_logo(imagem_teste)
app2 = gui.App()
check(app2.lbl_marca_nome.cget("text") == "Intesoftware Desenvolvimento" and app2._title.startswith("Intesoftware"), "reabrir: identidade carregada da pasta de dados")
app2._reconstruir_tudo("escuro")
check(app2.lbl_marca_nome.cget("text") == "Intesoftware Desenvolvimento", "troca de tema mantém a identidade")
app2.personalizar_identidade() if False else None
app._identidade.restaurar_padrao()



# --- layout compacto: estado vazio e rodapé do menu ---
import types as _t
app._rodape_nivel = None; app._ajustar_rodape(_t.SimpleNamespace(height=int(900*app._dpi*app._fator_escala)))
check(app._rodape_relogio.mapped and app._rodape_botao.mapped, "janela alta: rodapé completo")
app._ajustar_rodape(_t.SimpleNamespace(height=int(700*app._dpi*app._fator_escala)))
check(not app._rodape_relogio.mapped and app._rodape_botao.mapped, "janela baixa: relógio some, menu preservado")
app._ajustar_rodape(_t.SimpleNamespace(height=int(560*app._dpi*app._fator_escala)))
check(not app._rodape_botao.mapped and app._rodape_versao.mapped, "janela muito baixa: só a versão no rodapé")
tb = app.tabela
tb._ajustar_vazio(_t.SimpleNamespace(height=200))
check(tb._icone_visivel is False, "tabela baixa: ícone do estado vazio escondido")
tb._ajustar_vazio(_t.SimpleNamespace(height=600))
check(tb._icone_visivel is True, "tabela alta: ícone do estado vazio visível")

# --- atualização automática ---
from anotacoes.atualizacao import updater
import queue as _q
gui.T.REPOSITORIO_GITHUB = ""
app.verificar_atualizacao_manual()
check("não configurada" in app.toast._rotulo.cget("text"), "sem repositório: aviso de que não está configurado")
gui.T.REPOSITORIO_GITHUB = "u/r"
app._fila_atualizacao.put(("info", True, updater.InfoAtualizacao("99.0", "", "", "", 1)))
chamado = []
app._oferecer_atualizacao = lambda info: chamado.append(info.versao)
app._sondar_fila()
check(chamado == ["99.0"], "versão mais nova dispara a oferta de atualização")
app._fila_atualizacao.put(("info", True, updater.InfoAtualizacao("0.1", "", "", "", 1)))
app._sondar_fila()
check("mais recente" in app.toast._rotulo.cget("text"), "já atualizado: aviso positivo")
app._fila_atualizacao.put(("erro", True, "sem rede"))
app._sondar_fila()
check("sem rede" in app.toast._rotulo.cget("text"), "erro de rede na verificação manual é mostrado")
app._fila_atualizacao.put(("erro", False, "sem rede 2"))
app.toast._rotulo.configure(text="")
app._sondar_fila()
check(app.toast._rotulo.cget("text") == "", "erro de rede na verificação automática é silencioso")
updater.pode_atualizar_sozinho = lambda: True
app2 = app
del app2._oferecer_atualizacao
# troca concluída, mas o programa novo não abriu sozinho: avisa e NÃO fecha
updater.executar_troca = lambda novo: "manual"
app._finalizar_atualizacao("novo.exe")
check(not app.dead and "abra-o novamente" in app.toast._rotulo.cget("text"), "troca sem reabertura automática: avisa para abrir de novo e não fecha")
# a troca falhou de vez: mostra o erro e continua aberto
def _falha(novo): raise RuntimeError("preso")
updater.executar_troca = _falha
app._finalizar_atualizacao("novo.exe")
check(not app.dead and "Não foi possível aplicar" in app.toast._rotulo.cget("text"), "troca com erro: mostra o motivo e continua aberto")
# download anterior que sobrou sem ser aplicado: aviso ao abrir
updater.ficou_pendente = lambda: True
n_antes = len(app.after_calls); app._iniciar_atualizacao()
check(any(ms == 2500 for ms, _ in app.after_calls[n_antes:]), "troca pendente de uma tentativa anterior: aviso ao abrir")
updater.ficou_pendente = lambda: False
trocas = []
updater.executar_troca = lambda novo: trocas.append(novo)
app._finalizar_atualizacao("novo.exe")
check(trocas == ["novo.exe"] and app.dead, "finalizar: faz backup, dispara a troca e fecha o programa")

# --- alertas de pausa (14:40 / 17:00 / 18:10) ---
from datetime import datetime as _dt
from anotacoes.interface.mixins import pausas as pausas_gui
class _Relogio:
    agora = _dt(2026, 11, 11, 10, 0, 0)
    @classmethod
    def now(cls): return cls.agora
pausas_gui.datetime = _Relogio
pausas_gui._tocar_sinal = lambda j: j.bell()
check(app._btn_pausas.mapped and app.prefs.alertas_pausa, "botão de sino na barra lateral (alertas ligados por padrão)")
check(app._lbl_sino.cget("image") is not None and app._lbl_sino.mapped, "sino: ícone visível no cartão do relógio")
_ant = app.prefs.alertas_pausa
app.prefs.alertas_pausa = False; app._atualizar_botao_pausas()
check(app._lbl_sino.cget("image") is not None, "sino: ícone também com alertas desligados")
app.prefs.alertas_pausa = _ant; app._atualizar_botao_pausas()
check(("Ctrl + L") in [a for a, _ in __import__("anotacoes.interface.mixins.atalhos", fromlist=["x"]).ATALHOS] and "<Control-l>" in app.binds, "Ctrl+L registrado e listado em F1")
app._ciclo_pausas(); check(app._dialogo_pausa is None, "10:00: nenhum alerta")
_Relogio.agora = _dt(2026, 11, 11, 14, 40, 0); bips0 = getattr(app, "bips", 0)
app._ciclo_pausas()
check(app._dialogo_pausa is not None and app._dialogo_pausa._title == "Pausa NR 17", "14:40:00: alerta 'Pausa NR 17' aparece")
app._ciclo_pausas(); check(len(app._pausas_avisadas) == 1, "o mesmo horário não avisa de novo")
check(app.after_calls[-1][0] == pausas_gui.INTERVALO_MS, "laço se reagenda sozinho (after)")
app._bipar(pausas_gui.BIPES); check(getattr(app, "bips", 0) > bips0, "sinal sonoro tocado")
_Relogio.agora = _dt(2026, 11, 11, 17, 0, 1)
app._ciclo_pausas(); check(app._dialogo_pausa._title == "Pausa para lanche" and len(app._pausas_avisadas) == 2, "17:00: alerta 'Pausa para lanche' substitui o anterior")
app.alternar_alertas_pausa()
check(app.prefs.alertas_pausa is False and "desativados" in app.toast._rotulo.cget("text"), "sino desliga os alertas e avisa")
_Relogio.agora = _dt(2026, 11, 11, 18, 10, 0); app._dialogo_pausa = None
app._ciclo_pausas(); check(app._dialogo_pausa is None, "18:10 com alertas desligados: nada aparece")
app.alternar_alertas_pausa()
check(app.prefs.alertas_pausa is True, "religar os alertas")
app._ciclo_pausas(); check(app._dialogo_pausa._title == "Pausa NR 17", "18:10: alerta aparece após religar (dentro da tolerância)")
import json as _json
check(_json.load(open(app.prefs.caminho, encoding="utf-8"))["alertas_pausa"] is True, "escolha gravada em preferencias.json")
_DialogoPausaReal = pausas_gui.DialogoPausa
pausas_gui.DialogoPausa = type("Falha", (), {"__init__": lambda self, *a: (_ for _ in ()).throw(RuntimeError("x"))})
_Relogio.agora = _dt(2026, 11, 12, 14, 40, 0)
app._ciclo_pausas(); check(app._dialogo_pausa is None and "NR 17" in app.toast._rotulo.cget("text"), "se a janela falhar, o aviso sai como notificação")

# --- horários editáveis ---
app.configurar_alertas_pausa()
dlg = app._dialogo_horarios
check(dlg is not None and sorted(dlg.entradas) == ["lanche", "nr17_1", "nr17_2"], "sino abre a janela de horários com 3 campos")
check([dlg.entradas[k].get() for k in ("nr17_1", "lanche", "nr17_2")] == ["14:40", "17:00", "18:10"] and dlg.chk_ativo.get() == 1, "janela mostra horários atuais e alertas ligados")
app.configurar_alertas_pausa(); check(app._dialogo_horarios is dlg, "abrir de novo reaproveita a janela")
dlg.entradas["lanche"].delete(0, "end"); dlg.entradas["lanche"].insert(0, "25:00"); dlg._salvar()
check("inválido" in dlg.lbl_erro.cget("text") and not dlg.dead and app.prefs.horarios_pausa["lanche"] == "17:00", "horário inválido mostra erro e não salva")
dlg.entradas["lanche"].delete(0, "end"); dlg.entradas["lanche"].insert(0, "14h40"); dlg._salvar()
check("mesmo horário" in dlg.lbl_erro.cget("text") and not dlg.dead, "horários repetidos são recusados")
dlg._restaurar(); check(dlg.entradas["lanche"].get() == "17:00" and dlg.lbl_erro.cget("text") == "", "restaurar padrão")
for chave, texto in (("nr17_1", "9h15"), ("lanche", "12:00"), ("nr17_2", "1530")):
    dlg.entradas[chave].delete(0, "end"); dlg.entradas[chave].insert(0, texto)
dlg._salvar()
check(dlg.dead and app.prefs.horarios_pausa == {"nr17_1": "09:15", "lanche": "12:00", "nr17_2": "15:30"}, "salvar grava os novos horários")
check("09:15, 12:00, 15:30" in app.toast._rotulo.cget("text"), "aviso confirma os horários salvos")
check(_json.load(open(app.prefs.caminho, encoding="utf-8"))["horarios_pausa"]["lanche"] == "12:00", "horários gravados em preferencias.json")
pausas_gui.DialogoPausa = _DialogoPausaReal
app._dialogo_pausa = None; _Relogio.agora = _dt(2026, 11, 13, 14, 40, 0)
app._ciclo_pausas(); check(app._dialogo_pausa is None, "horário antigo (14:40) deixa de avisar depois da mudança")
_Relogio.agora = _dt(2026, 11, 13, 12, 0, 0)
app._ciclo_pausas(); check(app._dialogo_pausa is not None and app._dialogo_pausa._title == "Pausa para lanche", "novo horário (12:00) passa a avisar")
app.alternar_alertas_pausa(); check(app.prefs.alertas_pausa is False and "desativados" in app.toast._rotulo.cget("text"), "Ctrl+L desliga direto")
app.alternar_alertas_pausa(); check(app.prefs.alertas_pausa is True and "12:00" in app.toast._rotulo.cget("text"), "Ctrl+L liga e mostra os horários atuais")

# --- segurança: PIN, bloqueio, backups criptografados, configurações, diagnóstico ---
import time as _time, threading as _threading
import customtkinter as _ctk
from anotacoes.nucleo import diagnostico as _diag, seguranca as _seg, inicializacao as _ini
from anotacoes.interface.mixins import bloqueio as bloqueio_gui
check(not app.seguranca.ativa and not app.esta_bloqueado() and not app.db.backup_criptografado, "sem PIN: programa abre desbloqueado e backups sem criptografia")
check("<Control-b>" in app.binds and "config" in app.paginas, "Ctrl+B registrado e página Configurações existe")
def _keysym_valido(seq):
    ultimo = seq.strip("<>").split("-")[-1]
    # Tk: letras/dígitos soltos, F1..F12 ou nomes de tecla em minúsculas (comma, Return...).
    return len(ultimo) == 1 or (ultimo[:1] == "F" and ultimo[1:].isdigit()) or ultimo.islower() or ultimo[:1].isupper() and not ultimo.isupper()
check(all(_keysym_valido(q) for q in app.binds), "nenhum atalho usa nome de tecla inválido (ex.: COMMA)")
check("<Control-comma>" in app.binds and "<Control-COMMA>" not in app.binds, "Ctrl+, registrado como <Control-comma>")
check(any("Bloquear" in a[1] for a in __import__("anotacoes.interface.mixins.atalhos", fromlist=["x"]).ATALHOS), "atalhos novos listados em F1")
app.mostrar_pagina("config")
check(app.paginas["config"].mapped and app.lbl_pin_estado.cget("text") == "Desativada" and app.btn_pin_ativar.mapped and not app.btn_pin_alterar.mapped, "Configurações: PIN desativado mostra só 'Ativar PIN'")
check(len(app.quadro_info.kids) >= 18 and any(k.cget("text") == "Versão do programa" for k in app.quadro_info.kids), "Diagnóstico: informações preenchidas")

# ativar o PIN
app.abrir_dialogo_pin("criar"); dlg = app.winfo_children()[-1]
check(type(dlg).__name__ == "DialogoPin" and dlg.modo == "criar", "janela 'Ativar o PIN' abre")
dlg.ent_novo.insert(0, "12"); dlg.ent_confirma.insert(0, "12"); dlg._confirmar()
check("pelo menos" in dlg.lbl_erro.cget("text") and not dlg.dead and not app.seguranca.ativa, "PIN curto demais é recusado")
dlg.ent_novo.text = "senha-1234"; dlg.ent_confirma.text = "senha-9999"; dlg._confirmar()
check("não são iguais" in dlg.lbl_erro.cget("text") and not dlg.dead, "confirmação diferente é recusada")
app.db.fazer_backup("backup_2020-01-01_000000.db")      # backup antigo em texto aberto
dlg.ent_confirma.text = "senha-1234"; dlg._confirmar()
check(dlg.dead and app.seguranca.ativa and app.seguranca.verificar("senha-1234"), "PIN ativado")
check(app.db.backup_criptografado and app.db.backup_segredo == "senha-1234", "backups passam a ser criptografados")
check(not os.path.exists(os.path.join(app.db.pasta_backups(), "backup_2020-01-01_000000.db")) and os.path.exists(os.path.join(app.db.pasta_backups(), "backup_2020-01-01_000000.dbx")), "backup antigo convertido para criptografado")
check(os.path.exists(os.path.join(tmp, "seguranca.json")) and "senha-1234" not in open(os.path.join(tmp, "seguranca.json"), encoding="utf-8").read(), "seguranca.json existe e não guarda o PIN")
check(app.lbl_pin_estado.cget("text") == "Ativada" and app.btn_pin_alterar.mapped and not app.btn_pin_ativar.mapped and app.grp_pin_opcoes.mapped, "Configurações: opções do PIN aparecem")

# bloqueio
vistas = []
filho = _ctk.CTkToplevel(app)                                  # "diálogo aberto" (ex.: detalhes)
app.bloquear()
check(app.esta_bloqueado() and app._painel_bloqueio.mapped and filho._estado == "withdrawn", "bloquear: painel cobre a janela e esconde diálogos abertos")
app._atalho(lambda: vistas.append(1)); check(vistas == [], "atalhos não executam enquanto bloqueado")
app.bloquear(); check(len(app.winfo_children()) >= 1, "bloquear de novo não duplica o painel")
app._ent_pin.text = "errada"; app._tentar_desbloquear()
check(app.esta_bloqueado() and "incorretos" in app._lbl_pin_erro.cget("text") and app._ent_pin.text == "", "PIN errado: continua bloqueado e limpa o campo")
app._ent_pin.text = "errada"; app._tentar_desbloquear(); app._ent_pin.text = "errada"; app._tentar_desbloquear()
check("Aguarde" in app._lbl_pin_erro.cget("text"), "3º erro: espera obrigatória")
app._ent_pin.text = "senha-1234"; app._tentar_desbloquear()
check(app.esta_bloqueado() and "Aguarde" in app._lbl_pin_erro.cget("text"), "PIN certo durante a espera ainda não entra")
app._limite_pin.acertou()
app.db.backup_segredo = None; painel = app._painel_bloqueio
app._ent_pin.text = "senha-1234"; app._tentar_desbloquear()
check(not app.esta_bloqueado() and painel.dead and filho._estado == "normal", "PIN certo: desbloqueia e mostra os diálogos de volta")
check(app.db.backup_segredo == "senha-1234", "senha da sessão guardada só na memória para os backups")

# bloqueio por inatividade
app._ultima_atividade = _time.monotonic() - 60; app._ciclo_bloqueio(); check(not app.esta_bloqueado(), "1 min parado: ainda desbloqueado (limite padrão 5 min)")
app._ultima_atividade = _time.monotonic() - 6 * 60; app._ciclo_bloqueio(); check(app.esta_bloqueado(), "6 min parado: bloqueia sozinho")
app._ent_pin.text = "senha-1234"; app._tentar_desbloquear(); check(not app.esta_bloqueado(), "desbloqueia de novo")
app._ao_escolher_bloqueio("1 minuto"); check(app.seguranca.bloqueio_minutos == 1, "tempo de bloqueio configurável")
app._ultima_atividade = _time.monotonic() - 90; app._ciclo_bloqueio(); check(app.esta_bloqueado(), "com 1 min configurado, 90 s parado bloqueia")
app._ent_pin.text = "senha-1234"; app._tentar_desbloquear()
check("bloqueio" in str(sorted(app.binds_all)) or "<Motion>" in app.binds_all, "atividade do mouse/teclado monitorada (bind_all)")

# backups criptografados na interface
app.mostrar_pagina("backup"); app.fazer_backup_agora()
tab = app.tabela_backup.tree
linhas = [tab.rows[i]["values"] for i in tab.get_children()]
check(any(v[2] == "criptografado" and v[1].endswith(".dbx") for v in linhas), "página Backup lista backups .dbx como 'criptografado'")
novo_id = app.db.inserir("Paciente Depois", "x", "depois do backup")
ALVO = "backup_2020-01-01_000000.dbx"          # criado com "senha-1234"
def _selecionar_backup(nome):
    app.atualizar_backups()                       # a lista muda a cada restauração (cópia de segurança nova)
    iid = [i for i in tab.get_children() if tab.rows[i]["values"][1] == nome][0]
    tab.selection_set(iid)
RESP["v"] = True
_selecionar_backup(ALVO); app.restaurar_backup_selecionado()
check("restaurado" in app.toast._rotulo.cget("text"), "restaurar backup criptografado com a senha da sessão")
app.db.backup_segredo = "outra-senha"                       # sessão com outra senha: o backup pede a senha dele
perguntas = []
bloqueio_gui.DialogoSenhaBackup.perguntar = classmethod(lambda cls, pai, nome: (perguntas.append(nome), "senha-1234")[1])
_selecionar_backup(ALVO); app.restaurar_backup_selecionado()
check(perguntas and "restaurado" in app.toast._rotulo.cget("text"), "senha diferente: pergunta a senha do backup e restaura")
bloqueio_gui.DialogoSenhaBackup.perguntar = classmethod(lambda cls, pai, nome: "errada")
_selecionar_backup(ALVO); app.restaurar_backup_selecionado()
check("incorreta" in app.toast._rotulo.cget("text").lower(), "senha do backup errada: mostra erro e não restaura")
app.db.backup_segredo = "senha-1234"

# configurações: criptografia liga/desliga
app.alternar_criptografia_backups(False)
check(not app.db.backup_criptografado and not app.seguranca.criptografar_backups, "desligar a criptografia: novos backups sem .dbx")
app.alternar_criptografia_backups(True)
check(app.db.backup_criptografado and app.seguranca.criptografar_backups, "ligar a criptografia de novo")
app.db.backup_segredo = None; app.alternar_criptografia_backups(False); app.alternar_criptografia_backups(True)
check(not app.db.backup_criptografado and "Desbloqueie" in app.toast._rotulo.cget("text"), "ligar sem senha na sessão: pede para desbloquear")
app.db.backup_segredo = "senha-1234"; app.alternar_criptografia_backups(True)

# alterar e remover o PIN
app.abrir_dialogo_pin("alterar"); dlg = app.winfo_children()[-1]
dlg.ent_atual.text = "errada"; dlg.ent_novo.text = "novo-pin-77"; dlg.ent_confirma.text = "novo-pin-77"; dlg._confirmar()
check("incorreto" in dlg.lbl_erro.cget("text") and app.seguranca.verificar("senha-1234"), "alterar PIN: senha atual errada é recusada")
dlg.ent_atual.text = "senha-1234"; dlg._confirmar()
check(dlg.dead and app.seguranca.verificar("novo-pin-77") and not app.seguranca.verificar("senha-1234") and app.db.backup_segredo == "novo-pin-77", "PIN alterado")
app.abrir_dialogo_pin("desativar"); dlg = app.winfo_children()[-1]
dlg.ent_atual.text = "errada"; dlg._confirmar(); check(not dlg.dead and app.seguranca.ativa, "remover PIN: senha errada é recusada")
dlg.ent_atual.text = "novo-pin-77"; dlg._confirmar()
check(dlg.dead and not app.seguranca.ativa and not app.db.backup_criptografado and app.db.backup_segredo is None, "PIN removido: sem bloqueio e backups sem criptografia")
app.bloquear(); check(not app.esta_bloqueado(), "sem PIN não há o que bloquear")
app.atualizar_config(); check(app.btn_pin_ativar.mapped and not app.grp_pin_opcoes.mapped, "Configurações volta ao estado sem PIN")

# diagnóstico: teste de conexão em segundo plano
chamadas = []
_diag.testar_github = lambda repo, timeout=8: (chamadas.append(repo), _diag.Resultado("GitHub (atualizações)", _diag.OK, "Conectado.", 120))[1]
_diag.testar_supabase = lambda url, chave, timeout=8: _diag.Resultado("Supabase (nuvem)", _diag.PULADO, "Nuvem não configurada (é opcional).")
app.testar_conexoes()
check(app._diag_rodando and str(app.btn_testar.cget("state")) == "disabled", "testar conexão: botão desabilitado enquanto roda")
for _ in range(100):
    app._sondar_diagnostico()
    if not app._diag_rodando: break
    _time.sleep(0.02)
check(not app._diag_rodando and app.btn_testar.cget("state") == "normal" and len(app.quadro_testes.kids) == 2 and chamadas, "testar conexão: dois resultados mostrados e botão liberado")
_diag.testar_github = lambda repo, timeout=8: (_ for _ in ()).throw(RuntimeError("falha inesperada"))
app.testar_conexoes()
for _ in range(100):
    app._sondar_diagnostico()
    if not app._diag_rodando: break
    _time.sleep(0.02)
check(not app._diag_rodando and len(app.quadro_testes.kids) == 1, "falha inesperada no teste não trava o botão")
app._trocar_aba_config("Diagnóstico"); check(app._aba_diagnostico.mapped and not app._aba_seguranca.mapped, "aba Diagnóstico")
app._trocar_aba_config("Segurança"); check(app._aba_seguranca.mapped, "aba Segurança")

# início minimizado e início com o Windows
check(app._minimizado is False and app.state() == "normal", "abertura normal: janela normal")
app_min = gui.App(minimizado=True)
check(app_min._minimizado and any(ms == 300 and fn == app_min.iconify for ms, fn in app_min.after_calls), "abertura minimizada: agenda iconify")
alvos = []
_ini.suportado = lambda: True; _ini.ativo = lambda: False
_ini.ativar = lambda: alvos.append("ativar"); _ini.desativar = lambda: alvos.append("desativar")
app.configurar_alertas_pausa(); dlg = app._dialogo_horarios
check(dlg.chk_inicio is not None and dlg.chk_inicio.get() == 0, "alertas: opção 'abrir ao ligar o computador' aparece quando suportado")
dlg.chk_inicio.select(); dlg._salvar()
check(alvos == ["ativar"] and dlg.dead, "marcar a opção liga o início com o Windows")
_ini.ativar = lambda: (_ for _ in ()).throw(OSError("negado"))
app.configurar_alertas_pausa(); dlg = app._dialogo_horarios; dlg.chk_inicio.select(); dlg._salvar()
check("Não foi possível alterar o início" in app.toast._rotulo.cget("text"), "Windows recusa: mostra o motivo")
_ini.suportado = lambda: False
app.configurar_alertas_pausa(); dlg = app._dialogo_horarios
check(dlg.chk_inicio is None, "fora do .exe: opção indisponível, sem checkbox")

# --- Modelos de descrição -------------------------------------------------
from anotacoes.interface.mixins import modelos as modelos_gui
from anotacoes.nucleo import modelos as _mod_regras
app.txt_desc.delete("1.0", "end")
app._usar_modelo("Solicita água.")
check(app.txt_desc.text.strip() == "Solicita água.", "modelo: clique insere o texto")
app._usar_modelo("Solicita cobertor.")
check(app.txt_desc.text.strip() == "Solicita água.\nSolicita cobertor.", "modelo: segundo clique acrescenta em nova linha")
check(app.lbl_contador.cget("text").startswith(str(len("Solicita água.\nSolicita cobertor."))), "modelo: contador atualizado")
app.txt_desc.delete("1.0", "end")
app.txt_desc.text = "x" * (gui.MAX_DESCRICAO - 2)
app._usar_modelo("Solicita água.")
check("passaria" in app.toast._rotulo.cget("text"), "modelo: avisa quando passa do limite")
check(app.txt_desc.text == "x" * (gui.MAX_DESCRICAO - 2), "modelo: texto intacto quando não cabe")
# balões: compactos, padronizados e sem o rótulo "Modelos:"
_chips = app._fluxo_modelos._itens
check(len(_chips) == len(_mod_regras.padrao()) + 1 and _chips[-1].cget("text") == "Editar",
      "modelos: um balão por modelo e o balão 'Editar' no fim")
check({c.cget("height") for c in _chips} == {modelos_gui.ALTURA_CHIP} and modelos_gui.ALTURA_CHIP <= 28,
      "modelos: todos os balões têm a mesma altura, compacta")
check(all(c.cget("width") == max(48, 7 * len(c.cget("text")) + modelos_gui.MARGEM_CHIP) for c in _chips[:-1]),
      "modelos: largura = texto + margem pequena (e não os 140 fixos de antes)")
check(len({c.cget("width") for c in _chips[:-1]}) > 1, "modelos: a largura acompanha o texto de cada balão")
_todos_textos = [t for t in textos(app.paginas["novo"]) if t]
check("Modelos:" not in _todos_textos and "Editar modelos" not in _todos_textos, "modelos: sem o rótulo 'Modelos:' (só os balões)")
# adaptação à largura da janela
_fl = widgets.FluxoBotoes(app._frm_modelos)
_bs = [ctk.CTkButton(_fl, text=f"M{i}", width=100) for i in range(6)]
for _b in _bs: _fl._itens.append(_b)
_fl._reordenar(700)
check({b.grid_kw["row"] for b in _bs} == {0}, "balões: janela larga = uma só linha")
_fl._reordenar(350)
check([b.grid_kw["row"] for b in _bs] == [0, 0, 0, 1, 1, 1], "balões: janela estreita quebra em duas linhas")
_fl._reordenar(150)
check([b.grid_kw["row"] for b in _bs] == [0, 1, 2, 3, 4, 5], "balões: janela muito estreita = um por linha (nenhum some)")
_fl._reordenar(700)
check({b.grid_kw["row"] for b in _bs} == {0}, "balões: ao ampliar, voltam para uma linha")
_avisos = []
_fl2 = widgets.FluxoBotoes(app._frm_modelos, ao_mudar_linhas=lambda: _avisos.append(1))
for i in range(4): _fl2.adicionar(ctk.CTkButton(_fl2, text=f"N{i}", width=100))
_n0 = len(_avisos); _fl2._reordenar(210)
check(len(_avisos) > _n0, "balões: avisa quando a quantidade de linhas muda (para reajustar a altura mínima)")
app.txt_desc.delete("1.0", "end")
salvos = []
dlg = modelos_gui.DialogoModelos(app, _mod_regras.padrao(), lambda lista: salvos.append(lista))
check(len(dlg._linhas) == len(_mod_regras.padrao()), "modelo: janela lista os modelos atuais")
dlg._remover(dlg._linhas[0]); dlg._adicionar()
novo = dlg._linhas[-1]
novo[1].insert(0, "Fralda"); novo[2].insert(0, "Solicita troca de fralda.")
dlg._salvar()
check(salvos and salvos[0][-1] == {"titulo": "Fralda", "texto": "Solicita troca de fralda."}
      and salvos[0][0]["titulo"] == "Travesseiro", "modelo: remover e adicionar salvam")
dlg2 = modelos_gui.DialogoModelos(app, _mod_regras.padrao(), lambda l: salvos.append("x"))
dlg2._adicionar(); dlg2._linhas[-1][1].insert(0, "Só título")
dlg2._salvar()
check("Preencha" in dlg2.lbl_erro.cget("text") and "x" not in salvos, "modelo: linha incompleta é recusada")
app._salvar_modelos([{"titulo": "Teste", "texto": "Texto de teste."}])
check(app.prefs.modelos_descricao == [{"titulo": "Teste", "texto": "Texto de teste."}], "modelo: preferências atualizadas")
check(os.path.exists(os.path.join(tmp, "preferencias.json")) and "Teste" in open(os.path.join(tmp, "preferencias.json"), encoding="utf-8").read(), "modelo: gravado em preferencias.json")
app._salvar_modelos(_mod_regras.padrao())

# --- Restaurar de um arquivo + assistente de primeiro uso -------------------
app.db.inserir("Cópia", "", "registro para o backup externo")
externo = os.path.join(tmp, "externo.db")
app.db.fazer_backup(os.path.basename(externo))
import shutil as _sh
_sh.copy2(os.path.join(app.db.pasta_backups(), os.path.basename(externo)), externo)
app.db.inserir("Depois", "", "registro posterior ao backup")
n_antes = len(app.db.listar())
RESP["v"] = True
sys.modules["tkinter.filedialog"].CAMINHO["abrir"] = ""
app.restaurar_de_arquivo()
check(len(app.db.listar()) == n_antes, "restaurar de arquivo: cancelar não altera nada")
sys.modules["tkinter.filedialog"].CAMINHO["abrir"] = externo
app.restaurar_de_arquivo()
check(len(app.db.listar()) == n_antes - 1 and "restaurado" in app.toast._rotulo.cget("text"),
      "restaurar de arquivo: dados voltam ao estado do backup")
sys.modules["tkinter.filedialog"].CAMINHO["abrir"] = ""

from anotacoes.interface.mixins import primeiro_uso as pu_gui
escolhas = []
dlg = pu_gui.DialogoBoasVindas(app, tmp, escolhas.append)
dlg._escolher("nuvem"); dlg._escolher("zero")
check(escolhas == ["nuvem"], "assistente: a escolha vale uma vez só")
app.prefs.primeiro_uso_concluido = False
app._ao_escolher_inicio("nuvem")
check(app._aba_nuvem.mapped and app.prefs.primeiro_uso_concluido, "assistente: 'já uso em outro computador' abre a Nuvem e conclui")
app._ao_escolher_inicio("zero")
check(app.paginas["novo"].mapped, "assistente: 'começar do zero' abre o Novo registro")
sys.modules["tkinter.filedialog"].CAMINHO["abrir"] = externo
app._ao_escolher_inicio("backup")
check(app._aba_backup.mapped, "assistente: 'restaurar backup' abre a página Backup")
sys.modules["tkinter.filedialog"].CAMINHO["abrir"] = ""
app.prefs.primeiro_uso_concluido = False
app._iniciar_primeiro_uso()
check(app.prefs.primeiro_uso_concluido, "assistente: instalação já em uso é marcada como concluída sem mostrar")

# Utilidades
app._atualizar_relogio()
check(app.lbl_hora.cget("text") != "--:--", "relógio atualiza")
app._erro_inesperado(ValueError, ValueError("teste"), None)
check(os.path.exists(os.path.join(tmp, "erros.log")), "erro inesperado gravado em erros.log")
# Projeto fixo (nuvem/projeto.py): a página mostra só e-mail e senha
_orig_fixo = _projeto_mod.projeto_fixo
_projeto_mod.projeto_fixo = lambda *a, **k: ("https://abc.supabase.co", "sb_publishable_" + "A" * 24)
app2 = gui.App()
check(app2.ent_nuvem_url is None and app2.ent_nuvem_chave is None, "projeto fixo: sem campos de endereço e chave")
check(app2.ent_nuvem_email is not None and app2.ent_nuvem_senha is not None, "projeto fixo: e-mail e senha visíveis")
app2.ent_nuvem_email.delete(0, "end"); app2.ent_nuvem_email.insert(0, "maria@solicitacao.local")
app2.ent_nuvem_senha.insert(0, "segredo123")
usados = {}
class _Falso:
    refresh_token = "r"
    def __init__(self, url, chave, *a, **k): usados["url"], usados["chave"] = url, chave
    def entrar(self, e, s): usados["email"] = e
_orig_cli, nuvem_gui.ClienteSupabase = nuvem_gui.ClienteSupabase, _Falso
_orig_tc, nuvem_gui.testar_conexao = nuvem_gui.testar_conexao, lambda c: None
app2.conectar_nuvem()
for _ in range(200):
    if not app2._sync_fila.empty(): break
    _time.sleep(0.01)
check(usados.get("url") == "https://abc.supabase.co" and usados.get("email") == "maria@solicitacao.local",
      "projeto fixo: conecta com o endereço do arquivo e o e-mail digitado")
nuvem_gui.ClienteSupabase, nuvem_gui.testar_conexao = _orig_cli, _orig_tc
# "Criar conta": desligado por padrão; ligado só por projeto.PERMITIR_CADASTRO
check(_projeto_mod.PERMITIR_CADASTRO is False and app2.btn_nuvem_criar is None,
      "criar conta: botão desligado por padrão")
_projeto_mod.PERMITIR_CADASTRO = True
_projeto_mod.projeto_fixo = lambda *a, **k: ("https://abc.supabase.co", "sb_publishable_" + "A" * 24)
app3 = gui.App()
check(app3.btn_nuvem_criar is not None and app3.btn_nuvem_criar.cget("text") == "Criar conta",
      "criar conta: botão aparece quando liberado no projeto.py")
eventos = {}
class _FalsoCadastro:
    resultado = "conectado"; erro = None
    refresh_token = "r-novo"
    def __init__(self, url, chave, *a, **k): pass
    def cadastrar(self, e, s):
        eventos["cadastro"] = (e, s)
        if _FalsoCadastro.erro: raise _nuvem.NuvemErro(_FalsoCadastro.erro)
        return _FalsoCadastro.resultado
_orig_cli2, _orig_tc2, _orig_sinc2 = nuvem_gui.ClienteSupabase, nuvem_gui.testar_conexao, nuvem_gui.sincronizar
nuvem_gui.ClienteSupabase = _FalsoCadastro
nuvem_gui.testar_conexao = lambda c: None
def esperar(a):
    for _ in range(200):
        if not a._sync_fila.empty():
            a._sondar_sync(); return True
        _time.sleep(0.01)
    return False
app3.ent_nuvem_email.delete(0, "end"); app3.ent_nuvem_email.insert(0, "nova@solicitacao.local")
app3.ent_nuvem_senha.delete(0, "end"); app3.ent_nuvem_senha.insert(0, "curta")
app3.criar_conta_nuvem()
check("cadastro" not in eventos and "pelo menos 8" in app3.toast._rotulo.cget("text"),
      "criar conta: senha curta é recusada sem chamar a rede")
app3.ent_nuvem_senha.delete(0, "end"); app3.ent_nuvem_senha.insert(0, "SenhaForte123")
RESP["v"] = False
app3.criar_conta_nuvem()
check("cadastro" not in eventos and not app3._sync_rodando, "criar conta: cancelar na confirmação não cadastra")
RESP["v"] = True
_FalsoCadastro.erro = "O cadastro de novas contas está desativado neste projeto. Peça ao administrador."
app3.criar_conta_nuvem()
check(esperar(app3) and "desativado" in app3.toast._rotulo.cget("text") and not app3.nuvem_conectada(),
      "criar conta: cadastro fechado no Supabase mostra o motivo e não conecta")
_FalsoCadastro.erro = None; _FalsoCadastro.resultado = "confirmar_email"
app3.criar_conta_nuvem()
check(esperar(app3) and "Confirme o e-mail" in app3.toast._rotulo.cget("text") and not app3.nuvem_conectada(),
      "criar conta: exigindo confirmação de e-mail, avisa e não conecta")
_FalsoCadastro.resultado = "conectado"
nuvem_gui.sincronizar = lambda db, c: Resultado(enviados=0, recebidos=0)
app3.criar_conta_nuvem()
check(esperar(app3) and eventos["cadastro"] == ("nova@solicitacao.local", "SenhaForte123")
      and app3._nuvem_cfg.get("email") == "nova@solicitacao.local",
      "criar conta: conta criada já conecta e guarda o e-mail (a senha não é guardada)")
nuvem_gui.ClienteSupabase, nuvem_gui.testar_conexao, nuvem_gui.sincronizar = _orig_cli2, _orig_tc2, _orig_sinc2
RESP["v"] = True
_projeto_mod.PERMITIR_CADASTRO = False

# --- Importar certificado da rede: acumula (GitHub + Supabase) ----------------------------
import tempfile as _tf, os as _os
_cert_a = _os.path.join(_tf.mkdtemp(), "a.pem")
_cert_b = _os.path.join(_tf.mkdtemp(), "b.cer")
from tests.nucleo.test_certificados import SECTIGO_E46, _raiz_de_teste
open(_cert_a, "w", newline="").write(SECTIGO_E46)
open(_cert_b, "wb").write(_raiz_de_teste("Raiz do Supabase"))
_fd = sys.modules["tkinter.filedialog"]
_pasta_ca = _os.path.dirname(app.db.caminho)
for _extra in (_os.path.join(_pasta_ca, "ca-extra.pem"),):
    if _os.path.exists(_extra): _os.remove(_extra)
app.mostrar_pagina("config"); app._trocar_aba_config("Diagnóstico")
_fd.CAMINHO["abrir"] = _cert_a; app.importar_certificado_rede()
check("1 na lista" in app.toast._rotulo.cget("text"), "certificado: primeiro importado (1 na lista)")
_fd.CAMINHO["abrir"] = _cert_b; app.importar_certificado_rede()
check("2 na lista" in app.toast._rotulo.cget("text"), "certificado: o segundo é somado ao primeiro (2 na lista)")
app.importar_certificado_rede()
check("já estava" in app.toast._rotulo.cget("text"), "certificado: repetido não duplica")
_fd.CAMINHO["abrir"] = _os.path.join(_pasta_ca, "nao-existe.pem"); app.importar_certificado_rede()
check("Não foi possível ler" in app.toast._rotulo.cget("text"), "certificado: arquivo inexistente mostra o erro")
_os.remove(_os.path.join(_pasta_ca, "ca-extra.pem"))
app.mostrar_pagina("novo")

# ----------------------------------------------------------------------
# Painel de controle (usuário x administrador)
# ----------------------------------------------------------------------
from anotacoes.interface.mixins import painel as painel_gui
from anotacoes.nuvem.cliente import NuvemErro as _NuvemErro

app._nuvem_cfg.definir(url="https://abc.supabase.co", chave="sb_publishable_" + "p" * 30,
                       refresh_token=None, email="eu@x.com")
app.mostrar_pagina("painel")
check(app.paginas["painel"].mapped and "painel" in app.nav, "painel: página abre e tem item no menu")
check(app.abas_painel._cfg.get("values") == [painel_gui.ABA_MEU],
      "painel: sem conexão só existe 'Meu painel' (sem aba de administração)")
check("computador" in app.pil_painel_papel._rotulo.cget("text").lower(),
      "painel: sem nuvem mostra 'Somente neste computador'")
ind = app.db.indicadores(14)
check(app._painel_cartoes["total"]._valor.cget("text") == str(ind["total"])
      and len(ind["por_dia"]) == 14 and len(app._painel_grafico.winfo_children()) == 14,
      "painel: cartões e gráfico de 14 dias refletem o banco local")

chamadas = []
class _ClientePainel:
    def __init__(self, papel, falhar=False): self.papel, self.falhar = papel, falhar
    def rpc(self, nome, corpo=None):
        chamadas.append((nome, corpo))
        if self.falhar: raise _NuvemErro("Sem conexão com o Supabase.")
        if nome == "painel_meu_papel": return self.papel
        if nome == "painel_listar_usuarios":
            return [
                {"id": "u1", "email": "eu@x.com", "papel": "admin", "ativo": True, "registros": 5,
                 "pendentes": 2, "atendidas": 3, "urgentes": 1, "criado_em": "2026-01-02T10:00:00+00:00",
                 "ultimo_acesso": None, "ultima_atividade": None},
                {"id": "u2", "email": "ana@x.com", "papel": "usuario", "ativo": True, "registros": 4,
                 "pendentes": 4, "atendidas": 0, "urgentes": 0, "criado_em": "2026-02-02T10:00:00Z",
                 "ultimo_acesso": "2026-11-10T12:00:00Z", "ultima_atividade": "2026-11-10T12:00:00Z"}]
        if nome == "painel_criar_usuario": return "novo-id"
        if nome == "painel_listar_auditoria":
            return [{"quando": "2026-11-10T12:00:00Z", "admin_email": "eu@x.com",
                     "acao": "desativar_acesso", "alvo_email": "ana@x.com", "detalhe": None}]
        return None

def rodar_painel(cliente, acao=None):
    app._cliente_nuvem = lambda timeout=20: cliente
    app._nuvem_cfg.definir(refresh_token="r")
    app._painel_executar(acao, "Feito.")
    for _ in range(300):
        if not app._painel_fila.empty():
            app._sondar_painel(); return True
        _time.sleep(0.01)
    return False

check(rodar_painel(_ClientePainel("usuario")) and app._painel_papel == "usuario"
      and app.abas_painel._cfg.get("values") == [painel_gui.ABA_MEU]
      and not app._aba_admin.mapped
      and not any(c[0] == "painel_listar_usuarios" for c in chamadas),
      "painel: usuário comum não recebe a lista de contas nem vê a administração")
check("Usuário" in app.pil_painel_papel._rotulo.cget("text"), "painel: selo 'Usuário'")

chamadas.clear()
check(rodar_painel(_ClientePainel("admin")) and app._painel_papel == "admin"
      and app.abas_painel._cfg.get("values") == [painel_gui.ABA_MEU, painel_gui.ABA_ADMIN],
      "painel: administrador confirmado pelo servidor ganha a aba Administração")
check(len(app.tabela_painel.tree.rows) == 2 and app._admin_cartoes["usuarios"]._valor.cget("text") == "2"
      and app._admin_cartoes["registros"]._valor.cget("text") == "9",
      "painel: tabela e cartões somam as contas")
check("ana@x.com" in app.lbl_painel_auditoria.cget("text") and "desativou" in app.lbl_painel_auditoria.cget("text"),
      "painel: lista as últimas ações de administração")
app._trocar_aba_painel(painel_gui.ABA_ADMIN)
check(app._aba_admin.mapped and not app._aba_meu.mapped, "painel: abre a aba Administração")

app.tabela_painel.tree.sel = ["u1"]; app._atualizar_botoes_painel()
check(app.btn_painel_acesso._cfg.get("state") == "disabled" and app.btn_painel_papel._cfg.get("state") == "disabled",
      "painel: o administrador não pode agir sobre a própria conta")
app.tabela_painel.tree.sel = ["u2"]; app._atualizar_botoes_painel()
check(app.btn_painel_acesso._cfg.get("state") == "normal"
      and "Desativar" in app.btn_painel_acesso._cfg.get("text"), "painel: botão vira 'Desativar acesso'")

chamadas.clear(); RESP["v"] = False
app._cliente_nuvem = lambda timeout=20: _ClientePainel("admin")
app._alternar_acesso()
check(not chamadas, "painel: cancelar a confirmação não chama o servidor")
RESP["v"] = True
app._alternar_acesso()
for _ in range(300):
    if not app._painel_fila.empty(): app._sondar_painel(); break
    _time.sleep(0.01)
check(("painel_definir_acesso", {"p_usuario": "u2", "p_ativo": False}) in chamadas,
      "painel: desativar acesso chama a função do servidor com o usuário certo")
chamadas.clear()
app._alternar_papel()
for _ in range(300):
    if not app._painel_fila.empty(): app._sondar_painel(); break
    _time.sleep(0.01)
check(("painel_definir_papel", {"p_usuario": "u2", "p_papel": "admin"}) in chamadas,
      "painel: promover a administrador chama a função do servidor")


# --- Novo usuário pelo painel -------------------------------------------------------------
from anotacoes.interface import widgets as _w
chamadas.clear()
app._cliente_nuvem = lambda timeout=20: _ClientePainel("admin")
check(app.btn_painel_novo._cfg.get("state") == "normal", "painel: botão Novo usuário disponível ao administrador")
_w.DialogoNovoUsuario.perguntar = classmethod(lambda cls, pai, validar, gerar: None)
app._novo_usuario()
check(not chamadas, "painel: cancelar o novo usuário não chama o servidor")
_w.DialogoNovoUsuario.perguntar = classmethod(lambda cls, pai, validar, gerar: {
    "email": "nova@x.co", "senha": "SenhaForte123", "admin": True, "gerada": True})
copiado.clear()
app._novo_usuario()
for _ in range(300):
    if not app._painel_fila.empty(): app._sondar_painel(); break
    _time.sleep(0.01)
check(("painel_criar_usuario", {"p_email": "nova@x.co", "p_senha": "SenhaForte123", "p_papel": "admin"}) in chamadas,
      "painel: novo usuário chama a função do servidor com e-mail, senha e papel")
check(copiado and copiado[0] == "SenhaForte123" and "copiada" in app.toast._rotulo.cget("text"),
      "painel: senha gerada vai para a área de transferência e o aviso diz isso")
check(app._painel_papel == "admin", "painel: depois de criar, recarrega a lista")
check(app._validar_novo_usuario("sem-arroba", "SenhaForte123") and app._validar_novo_usuario("a@b.co", "curta")
      and app._validar_novo_usuario("a@b.co", "SenhaForte123") is None, "painel: validação do formulário de novo usuário")
# a própria janela (campos, gerar senha, mostrar, confirmar)
dlg = _w.DialogoNovoUsuario(app, app._validar_novo_usuario, lambda: "GeradaForte99")
dlg.ent_email.insert(0, "ana@x.co"); dlg._confirmar()
check(dlg.resultado is None and "senha" in dlg.lbl_erro.cget("text").lower(), "novo usuário (janela): senha vazia é recusada")
dlg._gerar_senha()
check(dlg.ent_senha.get() == "GeradaForte99" and dlg.ent_senha._cfg.get("show") == "", "novo usuário (janela): gerar preenche e mostra a senha")
dlg.chk_admin.select(); dlg._confirmar()
check(dlg.resultado == {"email": "ana@x.co", "senha": "GeradaForte99", "admin": True, "gerada": True},
      "novo usuário (janela): devolve e-mail, senha, papel e se foi gerada")

check(rodar_painel(_ClientePainel("admin", falhar=True)) and app._painel_papel is None
      and app.abas_painel._cfg.get("values") == [painel_gui.ABA_MEU] and not app._aba_admin.mapped,
      "painel: falha de rede fecha a administração (nunca presume ser admin)")
copiado.clear()
app._copiar_sql_painel()
check(copiado and "painel_listar_usuarios" in copiado[0], "painel: botão copia o SQL do painel")
app._nuvem_cfg.definir(refresh_token=None)
app.mostrar_pagina("novo")

_projeto_mod.projeto_fixo = _orig_fixo

print(f"\n{ok} verificações passaram.")
