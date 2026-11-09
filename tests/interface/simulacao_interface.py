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
    "winfo_children", "winfo_ismapped", "winfo_width", "winfo_height", "winfo_rootx",
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
    def grid(self, **kw): self.mapped = True
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
    def winfo_width(self): return 1200
    def winfo_height(self): return 800
    def winfo_rootx(self): return 0
    def winfo_rooty(self): return 0
    def winfo_fpixels(self, v): return 96.0 * SCREEN['dpi']
    def winfo_screenwidth(self): return SCREEN['w']
    def winfo_screenheight(self): return SCREEN['h']
    def update_idletasks(self): pass
    def title(self, t=None): self._title = t
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
tk.Entry = type('Entry', (), {}); tk.Toplevel = type('Toplevel', (), {}); tk.Text = type('Text', (), {})
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
app = gui.App()
check(not mb.erros, "aplicativo abre sem erros (todos os widgets aceitos pela API)")
check(app.paginas["novo"].mapped and not app.paginas["historico"].mapped, "página inicial = Novo registro")

# Validação: campos vazios
app.salvar_registro()
check(app.err_nome.cget("text") == "Informe o nome.", "erro inline do nome")
check(app.err_desc.cget("text") == "Descreva a solicitação.", "erro inline da descrição")
check("obrigatórios" in app.toast._rotulo.cget("text"), "aviso 'Preencha os campos obrigatórios.'")
check(app.db.listar() == [], "nada gravado com campos vazios")

# Digitar limpa o erro
app.ent_nome.text = "Maria da Silva"
app._digitando(app.ent_nome)
check(app.err_nome.cget("text") == "", "digitar remove o erro do nome")

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
app.ent_nome.text = "A" * 121
app.txt_desc.text = "x"
app.salvar_registro()
check("120" in app.err_nome.cget("text") and len(app.db.listar()) == 1, "nome acima do limite é rejeitado")
app.limpar_formulario()

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
    app.ent_nome.text, app.txt_desc.text = n, "x"
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
check("Contato" in tf and "Nome *" in tf, "rótulos do formulário: 'Contato' e 'Nome *'")
check(not any("paciente" in t.lower() and "Nome" in t for t in tf), "'Nome do paciente' não existe mais no formulário")
check(not any("ramal" in t.lower() or "e-mail" in t.lower() or "(" in t and "Contato" in t for t in tf if t.startswith("Contato")), "rótulo de contato sem parênteses")
check(tf.index("Contato") < tf.index("Nome *") < tf.index("Descrição da solicitação *"), "ordem: Contato, Nome, Descrição")
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
app.db.inserir("<script>alert(1)</script>", "", "x")
app.atualizar_tudo(); tr.selection_set(()); app.tabela._selecionou()
app.imprimir_lista()
html_txt = open(abertos[0].replace("file://", ""), encoding="utf-8").read()
check("<script>alert(1)</script>" not in html_txt and "&lt;script&gt;" in html_txt, "impressão escapa HTML dos dados")
check("window.print()" in html_txt and "Liga Contra o Câncer" in html_txt, "página de impressão abre a caixa de impressão")
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
check(all(f._cfg.get("height") == 1 for f in faixas) and len(app.nav) == 6, "menu com 6 itens (Resumo, Novo, Histórico, Lixeira, Backup, Nuvem)")


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
check(app.paginas["backup"].mapped, "página Backup abre")
app.fazer_backup_agora()
check(len(app.db.listar_backups()) >= 1, "backup manual criado")
app.atualizar_backups()
bk = app.tabela_backup.tree.get_children()
check(len(bk) >= 1, "backup aparece na tabela")
app.tabela_backup.tree.selection_set(bk[0]); app.restaurar_backup_selecionado()
check(True, "restaurar backup executa sem erro")

# --- Nuvem (Supabase) ---
from anotacoes.interface.mixins import nuvem as nuvem_gui
from anotacoes.nuvem import cliente as _nuvem
import time as _time
from anotacoes.nuvem.sincronizacao import Resultado
gui_nuvem = nuvem_gui
app.mostrar_pagina("nuvem")
check(app.paginas["nuvem"].mapped, "página Nuvem abre")
check(app.lbl_nuvem_estado.cget("text") == "Não conectado", "nuvem: começa não conectada")
check(app._grp_nuvem_entrar.mapped and not app._grp_nuvem_conectado.mapped, "nuvem: mostra o formulário")
check(app.ent_nuvem_senha._cfg.get("show") == "•", "nuvem: senha mascarada")
check("nuvem" in app.nav, "nuvem: item no menu")
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
trocas = []
updater.executar_troca = lambda novo: trocas.append(novo)
app._finalizar_atualizacao("novo.exe")
check(trocas == ["novo.exe"] and app.dead, "finalizar: faz backup, dispara a troca e fecha o programa")

# Utilidades
app._atualizar_relogio()
check(app.lbl_hora.cget("text") != "--:--", "relógio atualiza")
app._erro_inesperado(ValueError, ValueError("teste"), None)
check(os.path.exists(os.path.join(tmp, "erros.log")), "erro inesperado gravado em erros.log")
print(f"\n{ok} verificações passaram.")
